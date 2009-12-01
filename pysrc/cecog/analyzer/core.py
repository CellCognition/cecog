"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2009 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys, \
       os, \
       re, \
       pprint, \
       logging, \
       copy, \
       shutil, \
       types, \
       time, \
       weakref, \
       traceback, \
       csv

import cPickle as pickle

#from guppy import hpy

#-------------------------------------------------------------------------------
# extension module imports:
#
from numpy import array, asarray, transpose, min, max, median, isnan, sum
import svm

# pdk imports
from pdk.optionmanagers import OptionManager
#from pdk.processes import ChildProcess, ChildProcessProxy
#from pdk.idgenerators import newGuid
#from pdk.messaging import registerSlot
from pdk.datetimeutils import StopWatch
from pdk.map import (dict_subset,
                     dict_append_list, dict_except)
from pdk.iterator import (unique,
                          difference,
                          is_subset)
from pdk.fileutils import safe_mkdirs
#from pdk.util.exit import registerExitHandler
#from pdk.util.command import sendEmail


# PyFarm imports
#from pyfarm.launcher import (launchClient,
#                             ClientLauncher)
#from pyfarm.clients import closeClient
#from pyfarm.farming import (MSG_FARMING_JOB_COMPLETE,
#                            MSG_FARMING_JOB_ITEM_COMPLETE)
#from pyfarm.farms import getFarm


#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog import ccore
from cecog.analyzer.analyzer import (CellAnalyzer,
                                    QualityControl,
                                    PrimaryChannel,
                                    SecondaryChannel,
                                    TimeHolder)
from cecog.analyzer.celltracker import *
#from cecog.analyzer.cutter import Cutter, CutterLabel
from cecog.io.reader import (create_image_container,
                             load_image_container,
                             dump_image_container,
                             has_image_container,
                             )
#from cecog.experiment.plate import *
from cecog.util import hexToRgb
#from cecog.settings import Settings, ConstSettings, SettingsError, mapDirectory
from cecog.learning.collector import CellCounterReader, CellCounterReaderXML
from cecog.learning.learning import CommonObjectLearner, CommonClassPredictor
from cecog.learning.classifier import LibSvmClassifier
#from cecog.colors import makeColors

#from cecog.commonanalysis.test import Test

#-------------------------------------------------------------------------------
# constants:
#
FILENAME_CELLTRACKER_DUMP = "P%04d_CellTracker.pkl"


FEATURE_CATEGORIES_SHAPE = ['roisize',
                            'circularity',
                            'irregularity',
                            'irregularity2',
                            'axes',
                            ]
FEATURE_CATEGORIES_TEXTURE = ['normbase',
                              'normbase2',
                              'levelset',
                              'haralick',
                              'haralick2',
                              #'convexhull',
                              #'dynamics',
                              #'granulometry',
                              #'distance',
                              #moments',
                              ]


# set the max. recursion depth
# WARNING: this might crash your Python interpreter.
# use Python from stackless.com
sys.setrecursionlimit(10000)

#-------------------------------------------------------------------------------
# functions:
#

def mapDirectory(path):
    return path

#-------------------------------------------------------------------------------
# classes:
#

class PositionAnalyzer(object):

    POSITION_LENGTH = 4
    PRIMARY_CHANNEL = 'PrimaryChannel'
    SECONDARY_CHANNEL = 'SecondaryChannel'
    CHANNEL_METHODS = {'PrimaryChannel'   : PrimaryChannel,
                       'SecondaryChannel' : SecondaryChannel,
                       }

    def __init__(self, P, strPathOut, oSettings, lstAnalysisFrames,
                 lstSampleReader, dctSamplePositions, oObjectLearner,
                 qthread=None):

        self.origP = P
        self.P = self._adjustPositionLength(P)
        self.P = P
        self.strPathOut = mapDirectory(strPathOut)


        self._oLogger = self._configRootLogger()
        #self._oLogger = logging.getLogger()

        self.strPathOutAnalyzed = os.path.join(self.strPathOut, 'analyzed')
        self.oSettings = oSettings

        self.oImageContainer = load_image_container(os.path.join(self.strPathOut, 'dump'))

        # FIXME: a bit of a hack but the entire ImageContainer path is mapped to the current OS
        self.oImageContainer.setPathMappingFunction(mapDirectory)

        self.oMetaData = self.oImageContainer.oMetaData
        self.lstAnalysisFrames = lstAnalysisFrames

        self.lstSampleReader = lstSampleReader
        self.dctSamplePositions = dctSamplePositions
        self.oObjectLearner = oObjectLearner

        self._qthread = qthread

        name_lookup = {self.PRIMARY_CHANNEL : 'primary',
                       self.SECONDARY_CHANNEL : 'secondary',
                       }
        self._resolve_name = lambda channel, name: '%s_%s' % (name_lookup[channel], name)


        # setup output directories

        if self.oSettings.get('General', 'timelapseData'):
            self.strPathOutPosition = os.path.join(self.strPathOutAnalyzed, "%s" % self.P)
        else:
            self.strPathOutPosition = self.strPathOutAnalyzed
        bMkdirsOk = safe_mkdirs(self.strPathOutPosition)
        self._oLogger.info("strPathOutPosition '%s', ok: %s" % (self.strPathOutPosition, bMkdirsOk))

        self.strPathOutPositionImages = os.path.join(self.strPathOutPosition, "_images")
        self.strPathOutPositionDebug = os.path.join(self.strPathOutPosition, "_debug")

        if self.oSettings.get('Classification', 'collectsamples'):
            # disable tracking!
            self.oSettings.set('Tracking', 'tracking', False)
            self.lstAnalysisFrames = dctSamplePositions[self.origP]


        self.oSettings.set_section('ObjectDetection')
        self.channel_mapping = {self.PRIMARY_CHANNEL : self.oSettings.get2('primary_channelid')}
        if self.oSettings.get2('secondary_processchannel'):
            self.channel_mapping[self.SECONDARY_CHANNEL] = self.oSettings.get2('secondary_channelid')

        self.channel_mapping_reversed = dict([(v,k) for k,v in self.channel_mapping.iteritems()])

        self.tplChannelIds = tuple(self.channel_mapping.values())
        #print self.tplChannelIds

        self.classifier_infos = {}
        for channel in [self.PRIMARY_CHANNEL, self.SECONDARY_CHANNEL]:
            process_channel = channel in self.channel_mapping

            self.oSettings.set_section('Classification')
            if (process_channel and
                self.oSettings.get2(self._resolve_name(channel, 'classification'))):
                channel_id = self.channel_mapping[channel]
                classifier_infos = {'strEnvPath' : mapDirectory(self.oSettings.get2(self._resolve_name(channel, 'classification_envpath'))),
                                    'strChannelId' : channel_id,
                                    'strRegionId' : self.oSettings.get2(self._resolve_name(channel, 'classification_regionname')),
                                    }
                predictor = CommonClassPredictor(dctCollectSamples=classifier_infos)
                #print predictor.getOption('strEnvPath')
                predictor.importFromArff()
                predictor.loadClassifier()
                classifier_infos['predictor'] = predictor
                self.classifier_infos[channel_id] = classifier_infos



    def _configRootLogger(self):
        self.strPathLog = os.path.join(self.strPathOut, 'log')
        safe_mkdirs(self.strPathLog)
        #self._oLogger = logging.getLogger('PositionAnalyzer')
        oLogger = logging.getLogger(self.__class__.__name__)
        oLogger.setLevel(logging.DEBUG)
        self._oLogHandler = logging.FileHandler(os.path.join(self.strPathLog, "%s.log" % self.P), 'w')
        self._oLogHandler.setLevel(logging.DEBUG)
        self._oLogHandler.setFormatter(logging.Formatter('%(asctime)s %(name)-24s %(levelname)-6s %(message)s'))
        oLogger.addHandler(self._oLogHandler)
        return oLogger

    def __del__(self):
        # remove the FileHandler from the current root (necessary for PyFarm
        # where one worker runs in one Python session for more than one position)
        #self._oLogHandler.close()
        #oLogger = logging.getLogger()
        self._oLogger.removeHandler(self._oLogHandler)

    def __call__(self):
        # turn libtiff warnings off
        ccore.turn_off()

        oStopWatchPos = StopWatch()


#        if self.oSettings.bQualityControl:
#            strPathOutQualityControl = os.path.join(self.strPathOut, 'qc')
#            oQualityControl = QualityControl(strPathOutQualityControl,
#                                             self.oMetaData,
#                                             self.oSettings.dctQualityControl)
#            oQualityControl.initPosition(self.P, self.origP)


        oTimeHolder = TimeHolder(channels=self.tplChannelIds)

        self.oSettings.set_section('Tracking')
        # structure and logic to handle object trajectories
        if self.oSettings.get2('tracking'):
            strPathOutPositionTracking = os.path.join(self.strPathOutPosition,
                                                      '_tracking')

            # clear the tracking data
            #if self.oSettings.bClearTrackingPath and os.path.isdir(strPathOutPositionTracking):
            #    shutil.rmtree(strPathOutPositionTracking)

            bMkdirsOk = safe_mkdirs(strPathOutPositionTracking)
            self._oLogger.info("strPathOutPositionTracking '%s', ok: %s, cleared: %s" %\
                               (strPathOutPositionTracking,
                                bMkdirsOk,
                                'DISABLED FOR NOW'))
                                #self.oSettings.bClearTrackingPath))

            tracker_options = {'fMaxObjectDistance'      : self.oSettings.get2('tracking_maxobjectdistance'),
                               'iMaxSplitObjects'        : self.oSettings.get2('tracking_maxsplitobjects'),
                               'iMaxTrackingGap'         : self.oSettings.get2('tracking_maxtrackinggap'),

                               'bExportTrackFeatures'    : self.oSettings.get2('tracking_exporttrackfeatures'),
                               'featureCompression'      : None if self.oSettings.get2('tracking_compressiontrackfeatures') == 'raw' else self.oSettings.get2('tracking_compressiontrackfeatures'),
                               'bHasClassificationData'  : True,
                               }

            clsCellTracker = ClassificationCellTracker2
            transitions = self.oSettings.get2('tracking_labeltransitions').replace('),(', ')__(')
            transitions = map(eval, transitions.split('__'))
            tracker_options.update({'iBackwardCheck'       : 0,
                                    'iForwardCheck'        : 0,

                                    'iBackwardRange'       : -1,
                                    'iForwardRange'        : -1,

                                    'iMaxInDegree'         : self.oSettings.get2('tracking_maxindegree'),
                                    'iMaxOutDegree'        : self.oSettings.get2('tracking_maxoutdegree'),

                                    'lstLabelTransitions'  : transitions,
                                    'lstBackwardLabels'    : map(int, self.oSettings.get2('tracking_backwardlabels').split(',')),
                                    'lstForwardLabels'     : map(int, self.oSettings.get2('tracking_forwardlabels').split(',')),
                                    })

            if self.oSettings.get2('tracking_synchronize_trajectories'):
                tracker_options.update({'iBackwardCheck'       : self.oSettings.get2('tracking_backwardCheck'),
                                        'iForwardCheck'        : self.oSettings.get2('tracking_forwardCheck'),

                                        'iBackwardRange'       : self.oSettings.get2('tracking_backwardrange'),
                                        'iForwardRange'        : self.oSettings.get2('tracking_forwardrange'),

                                        'bBackwardRangeMin'    : self.oSettings.get2('tracking_backwardrange_min'),
                                        'bForwardRangeMin'     : self.oSettings.get2('tracking_forwardrange_min'),
                                        })

#            elif self.oSettings.get2('tracking_event_tracjectory'):
#                clsCellTracker = SplitCellTracker
#                tracker_options.update({'iBackwardCheck'       : self.oSettings.get2('tracking_backwardcheck'),
#                                        'iForwardCheck'        : self.oSettings.get2('tracking_forwardcheck'),
#                                        })
#            elif self.oSettings.get2('tracking_event_no_constraint'):
#                clsCellTracker = PlotCellTracker

            self.oCellTracker = clsCellTracker(oTimeHolder=oTimeHolder,
                                          oMetaData=self.oMetaData,
                                          P=self.P,
                                          origP=self.origP,
                                          strPathOut=strPathOutPositionTracking,
                                          **tracker_options)

            primary_channel_id = self.channel_mapping[self.PRIMARY_CHANNEL]
            self.oCellTracker.initTrackingAtTimepoint(primary_channel_id, 'primary')

        else:
            self.oCellTracker = None

        oCellAnalyzer = CellAnalyzer(oTimeHolder=oTimeHolder,
                                     oCellTracker=self.oCellTracker,
                                     P = self.P,
                                     bCreateImages = True,#self.oSettings.bCreateImages,
                                     iBinningFactor = self.oSettings.get('General', 'binningFactor'),
                                     )

        self.export_features = {}
        for channel, channel_id in self.channel_mapping.iteritems():
            #if self.oSettings.get('Classification', self._resolve_name(channel, 'featureextraction')):
            region_features = {}
            for region in self.oSettings.get('ObjectDetection', self._resolve_name(channel, 'regions')):
                region_features[region] = self.oSettings.get('General', self._resolve_name(channel, 'featureextraction_exportfeaturenames'))
            self.export_features[channel_id] = region_features


        iNumberImages = self._analyzePosition(oCellAnalyzer)


        self.oSettings.set_section('Tracking')
        if (self.oSettings.get2('tracking') and
            self.oSettings.get2('tracking_synchronize_trajectories') and
            iNumberImages > 0):

            stage_info = {'stage': 2,
                          'text': 'Tracking',
                          'min': 1,
                          'max': 3,
                          }
#            if not self._qthread is None:
#                if self._qthread.get_abort():
#                    return 0
#            stage_info.update({'progress' : 1,
#                               'meta': 'Track objects...',})
#            self._qthread.set_stage_info(stage_info)
#
#            primary_channel_id = self.channel_mapping[self.PRIMARY_CHANNEL]
#            oCellTracker.trackObjects(primary_channel_id, 'primary')

            # analyze trajectories
            #oCellTracker.exportGraph(os.path.join(self.strPathOutPosition, "graph.dot"))


            if not self._qthread is None:
                if self._qthread.get_abort():
                    return 0
            stage_info.update({'progress' : 1,
                               'meta': 'Find events...',})
            #self._qthread.set_stage_info(stage_info)

            self.oCellTracker.initVisitor()
            self._oLogger.debug("--- visitor ok")


            if not self._qthread is None:
                if self._qthread.get_abort():
                    return 0
            stage_info.update({'progress' : 2,
                               'meta': 'Analyze/export events...',})
            #self._qthread.set_stage_info(stage_info)

            self.oCellTracker.analyze(self.export_features,
                                      channelId=primary_channel_id)
            self._oLogger.debug("--- visitor analysis ok")

#            if self.oSettings.bDoObjectCutting:
#
#                strPathCutter = os.path.join(self.strPathOutPosition, "_cutter")
#                # clear the cutter data
#                if os.path.isdir(strPathCutter):
#                    shutil.rmtree(strPathCutter)
#                for strRenderName in self.oSettings.lstCutterRenderInfos:
#                    strPathCutterIn = os.path.join(self.strPathOutPositionImages, strRenderName)
#                    if os.path.isdir(strPathCutterIn):
#                        strPathCutterOut = os.path.join(strPathCutter, strRenderName)
#                        self._oLogger.info("running Cutter for '%s'..." % strRenderName)
#                        Cutter(oCellTracker,
#                               strPathCutterIn,
#                               self.P,
#                               strPathCutterOut,
#                               self.oMetaData,
#                               **self.oSettings.dctCutterInfos)
#
#            if (isinstance(oCellTracker, PlotCellTracker) and
#                hasattr(self.oSettings, "bDoObjectCutting3") and
#                self.oSettings.bDoObjectCutting3):
#                strPathLabels = os.path.join(self.strPathOutPositionImages, "_labels")
#                for strChannelId in os.listdir(strPathLabels):
#                    strPathChannel = os.path.join(strPathLabels, strChannelId)
#                    if os.path.isdir(strPathChannel):
#                        for strRegionId in os.listdir(strPathChannel):
#                            strPathRegion = os.path.join(strPathChannel, strRegionId)
#                            if os.path.isdir(strPathRegion):
#                                strPathCutterOut = os.path.join(strPathCutter, '_labels', strChannelId, strRegionId)
#                                self._oLogger.info("running CutterLabel for '%s' / '%s'..." % (strChannelId, strRegionId))
#                                CutterLabel(oCellTracker,
#                                            strPathRegion,
#                                            self.P,
#                                            strPathCutterOut,
#                                            self.oMetaData,
#                                            **self.oSettings.dctCutter3Infos)

#            if self.oSettings.bQualityControl:
#                self._oLogger.info("running quality control...")
#                oQualityControl.processPosition(oTimeHolder)

#            if self.oSettings.bDumpCellTracker:
#                oFile = file(strFilenameCellTrackerDump, 'wb')
#                pickle.dump(oCellTracker, oFile, 1)
#                oFile.close()

#        if self.oSettings.bClassify and self.oSettings.bExportUnifiedClassCounts:
#
#            for classifierName, classifierInfos in self.oSettings.dctClassificationInfos.iteritems():
#                self._oLogger.info("exporting unified class counts for '%s'" % classifierName)
#
#                oClassPredictor = classifierInfos['predictor']
#                oTableClassCounts = newTable(['Position', 'GeneSymbol', 'Group', 'Frame'] +
#                                              oClassPredictor.lstClassNames,
#                                              columnTypeCodes=['i','c', 'c', 'i'] +
#                                              ['i']*oClassPredictor.iClassNumber)
#
#                for iT, dctChannels in oTimeHolder.iteritems():
#
#                    oRecord = {'Position'   : self.P,
#                               'Frame'      : iT}
#
#                    dctClassCount = dict([(x, 0) for x in oClassPredictor.dctClassLabels])
#                    oChannel = dctChannels[classifierInfos['strChannelId']]
#                    strRegionId = classifierInfos['strRegionId']
#                    if strRegionId in oChannel.getRegionNames():
#                        oRegion = oChannel.getRegion(strRegionId)
#                        for iObjId, oObj in oRegion.iteritems():
#                            dctClassCount[oObj.strClassName] += 1
#                    oRecord.update(dctClassCount)
#                    oTableClassCounts.append(oRecord)
#
#                strFilename = os.path.join(self.strPathOutAnalyzed,
#                                           'unified_class_counts__%s__P%s.tsv' %\
#                                           (classifierName, self.P))
#                exportTable(self.oTableClassCounts,
#                            strFilename,
#                            fieldDelimiter='\t',
#                            stringDelimiter='')
#                self._oLogger.info("Predicted class counts for '%s' exported to '%s'." %\
#                                   (classifierName, strFilename))

#        for strChannelId, tplChannelInfo in self.oSettings.dctChannelMapping.iteritems():
#            dctChannelSettings = getattr(self.oSettings, tplChannelInfo[1])
#            if dctChannelSettings.get('bEstimateBackground', False):
#                oTable = newTable(['Frame', 'Timestamp', 'Background_avg'],
#                                  columnTypeCodes=['i','f', 'f'])
#                for iT, dctChannels in oTimeHolder.iteritems():
#                    oChannel = dctChannels[strChannelId]
#                    if oChannel.bSegmentationSuccessful:
#                        oTable.append({'Frame' : iT,
#                                       'Timestamp' : self.oMetaData.getTimestamp(self.origP, iT),
#                                       'Background_avg' : oChannel.fBackgroundAverage})
#                exportTable(oTable,
#                            os.path.join(self.strPathOutPosition,
#                                         '_background_estimates__P%s__C%s.tsv' % (self.P, strChannelId)),
#                            fieldDelimiter='\t',
#                            typeFormatting={FloatType: lambda x: "%E" % x},
#                            stringDelimiter='')

        # clean-up
#        if hasattr(self.oSettings, 'cleanUpPosition'):
#            # remove render images
#            if 'render_images' in self.oSettings.cleanUpPosition:
#                for render_name in self.oSettings.cleanUpPosition['render_images']:
#                    render_path = os.path.join(self.strPathOutPositionImages, render_name)
#                    if os.path.isdir(render_path):
#                        shutil.rmtree(render_path, True)
#                # remove the image directory if empty
#                if len(os.listdir(self.strPathOutPositionImages)) == 0:
#                    shutil.rmtree(self.strPathOutPositionImages, True)


        oStopWatchPos.stop()
        #self._oLogger.info("* position %d ok, %s" % (self.P, oStopWatchPos.stopInterval().format(msec=True)))

        if iNumberImages > 0:
            oInterval = oStopWatchPos.stop_interval() / iNumberImages
            self._oLogger.info("* %d image sets analyzed, %s / image set" %
                               (iNumberImages, oInterval.format(msec=True)))

        # write an empty file to mark this position as finished
        strPathFinished = os.path.join(self.strPathLog, '_finished')
        safe_mkdirs(strPathFinished)
        oFile = file(os.path.join(strPathFinished, '_%s_finished.txt' % self.P), 'w')
        oFile.close()

        return iNumberImages

    def _adjustPositionLength(self, pos):
        #if pos.isdigit() and len(pos) < self.POSITION_LENGTH:
        #    pos = pos.zfill(self.POSITION_LENGTH)
        return str(pos).zfill(self.POSITION_LENGTH)

    def _analyzePosition(self, oCellAnalyzer):

        debug_mode = self.oSettings.get('General', 'debugMode')
        if debug_mode:
            bMkdirsOk = safe_mkdirs(self.strPathOutPositionDebug)
            self._oLogger.info("strPathOutPositionDebug '%s', ok: %s" % (self.strPathOutPositionDebug,
                                                                         bMkdirsOk))
        else:
            strPathOutPositionDebug = ""

        create_images = self.oSettings.get('General', 'createImages')
        if create_images:
            bMkdirsOk = safe_mkdirs(self.strPathOutPositionImages)
            self._oLogger.info("strPathOutPositionImages '%s', ok: %s" % (self.strPathOutPositionImages,
                                                                          bMkdirsOk))

#        # create a persistenz object if export of features is True
#        if self.oSettings.bCreateFeatureFiles:
#            oPersistenz = FlatfileExperimentPersistenz(self.strFeatureFile, self.tplChannelIds)
#            #oPersistenz = SqliteExperimentWriter(self.strFeatureFile, self.tplChannelIds)
#        else:
#            oPersistenz = None

        stage_info = {'stage': 2,
                      'text': 'Image processing',
                      'min': 1,
                      'max': len(self.lstAnalysisFrames),
                      }

        iNumberImages = 0
        iLastFrame = self.lstAnalysisFrames[-1]

        # - loop over a sub-space with fixed position 'P' and reduced time and
        #   channel axis (in case more channels or time-points exist)
        # - define break-points at C and Z which will yield two nested generators
        for iT, oIteratorC in self.oImageContainer(oP=self.origP,
                                                   oT=self.lstAnalysisFrames,
                                                   oC=self.tplChannelIds,
                                                   bBreakC=True,
                                                   bBreakZ=True):

            if not self._qthread is None:
                if self._qthread.get_abort():
                    return 0

                stage_info.update({'progress': self.lstAnalysisFrames.index(iT)+1,
                                   'meta': 'Frame %d' % iT,
                                   })
                self._qthread.set_stage_info(stage_info)
                # FIXME: give the GUI a moment to recover
                time.sleep(.2)

            oCellAnalyzer.initTimepoint(iT)
            # loop over the channels
            for strC, oIteratorZ in oIteratorC:
#                if hasattr(self.oSettings, 'tplCropRegion'):
#                    tplCropRegion = self.oSettings.tplCropRegion
#                else:
#                    tplCropRegion = None

                channel_section = self.channel_mapping_reversed[strC]
                clsChannel = self.CHANNEL_METHODS[channel_section]
                self.oSettings.set_section('ObjectDetection')

                registration_x = self.oSettings.get2('secondary_channelRegistration_x')
                registration_y = self.oSettings.get2('secondary_channelRegistration_y')
                if registration_x == 0 and registration_y == 0:
                    channel_registration = None
                else:
                    channel_registration = (registration_x, registration_y)

                lstFeatureCategories = []
                if self.oSettings.get('Classification',
                                      self._resolve_name(channel_section,
                                                         'simplefeatures_shape')):
                    lstFeatureCategories += FEATURE_CATEGORIES_SHAPE
                if self.oSettings.get('Classification',
                                      self._resolve_name(channel_section,
                                                         'simplefeatures_texture')):
                    lstFeatureCategories += FEATURE_CATEGORIES_TEXTURE
                dctFeatureParameters = {}
                for name in lstFeatureCategories[:]:
                    if 'haralick' in name:
                        lstFeatureCategories.remove(name)
                        dict_append_list(dctFeatureParameters, 'haralick_categories', name)
                        dctFeatureParameters['haralick_distances'] = (1, 2, 4, 8)

                if channel_section == self.PRIMARY_CHANNEL:
                    lstPostprocessingFeatureCategories = []
                    lstPostprocessingConditions = []
                    bPostProcessing = False
                    if self.oSettings.get2('primary_postProcessing_roisize_min') > -1:
                        lstPostprocessingFeatureCategories.append('roisize')
                        lstPostprocessingConditions.append('roisize >= %d' % self.oSettings.get2('primary_postProcessing_roisize_min'))
                    if self.oSettings.get2('primary_postProcessing_roisize_max') > -1:
                        lstPostprocessingFeatureCategories.append('roisize')
                        lstPostprocessingConditions.append('roisize <= %d' % self.oSettings.get2('primary_postProcessing_roisize_max'))
                    if self.oSettings.get2('primary_postProcessing_intensity_min') > -1:
                        lstPostprocessingFeatureCategories.append('normbase2')
                        lstPostprocessingConditions.append('n2_avg >= %d' % self.oSettings.get2('primary_postProcessing_intensity_min'))
                    if self.oSettings.get2('primary_postProcessing_intensity_max') > -1:
                        lstPostprocessingFeatureCategories.append('normbase2')
                        lstPostprocessingConditions.append('n2_avg <= %d' % self.oSettings.get2('primary_postProcessing_intensity_max'))

                    lstPostprocessingFeatureCategories = unique(lstPostprocessingFeatureCategories)
                    if len(lstPostprocessingFeatureCategories) > 0:
                        bPostProcessing = True
                    strPostprocessingConditions = ' and '.join(lstPostprocessingConditions)

                    params = dict(oZSliceOrProjection = self.oSettings.get2('primary_zsliceorprojection'),
                                  channelRegistration=channel_registration,
                                  fNormalizeMin = self.oSettings.get2('primary_normalizemin'),
                                  fNormalizeMax = self.oSettings.get2('primary_normalizemax'),
                                  iMedianRadius = self.oSettings.get2('primary_medianradius'),
                                  iLatWindowSize = self.oSettings.get2('primary_latwindowsize'),
                                  iLatLimit = self.oSettings.get2('primary_latlimit'),
                                  #iLatWindowSize2 = self.oSettings.get2(''),
                                  #iLatLimit2 = self.oSettings.get2(''),
                                  bDoShapeWatershed = self.oSettings.get2('primary_shapewatershed'),
                                  iGaussSizeShape = self.oSettings.get2('primary_shapewatershed_gausssize'),
                                  iMaximaSizeShape = self.oSettings.get2('primary_shapewatershed_maximasize'),
                                  bDoIntensityWatershed = self.oSettings.get2('primary_intensitywatershed'),
                                  iGaussSizeIntensity = self.oSettings.get2('primary_intensitywatershed_gausssize'),
                                  iMaximaSizeIntensity = self.oSettings.get2('primary_intensitywatershed_maximasize'),
                                  # FIXME:
                                  iMinMergeSize = self.oSettings.get2('primary_shapewatershed_minmergesize'),
                                  bRemoveBorderObjects = self.oSettings.get2('primary_removeborderobjects'),
                                  iEmptyImageMax = self.oSettings.get2('primary_emptyimagemax'),
                                  bPostProcessing = bPostProcessing,
                                  lstPostprocessingFeatureCategories = lstPostprocessingFeatureCategories,
                                  strPostprocessingConditions = strPostprocessingConditions,
                                  bPostProcessDeleteObjects = True,
                                  lstFeatureCategories = lstFeatureCategories,
                                  dctFeatureParameters = dctFeatureParameters,
                                  )
                elif channel_section == self.SECONDARY_CHANNEL:
                    params = dict(oZSliceOrProjection = self.oSettings.get2('secondary_zsliceorprojection'),
                                  channelRegistration=channel_registration,
                                  fNormalizeMin = self.oSettings.get2('secondary_normalizemin'),
                                  fNormalizeMax = self.oSettings.get2('secondary_normalizemax'),
                                  #iMedianRadius = self.oSettings.get2('medianradius'),
                                  iExpansionSize = self.oSettings.get2('secondary_regions_expansionsize'),
                                  iExpansionSeparationSize = self.oSettings.get2('secondary_regions_expansionseparationsize'),
                                  iShrinkingSeparationSize = self.oSettings.get2('secondary_regions_shrinkingseparationsize'),
                                  # FIXME
                                  fExpansionCostThreshold = 1.5,
                                  lstAreaSelection = self.oSettings.get2('secondary_regions'),
                                  lstFeatureCategories = lstFeatureCategories,
                                  dctFeatureParameters = dctFeatureParameters,
                                  )

                oChannel = clsChannel(strChannelId=strC,
                                      bDebugMode=debug_mode,
                                      #tplCropRegion=tplCropRegion,
                                      strPathOutDebug=self.strPathOutPositionDebug,
                                      **params)

                # loop over the z-slices
                for iZ, oMetaImage in oIteratorZ:

                    P, iFrame, strC, iZ = oMetaImage.P, oMetaImage.iT, oMetaImage.strC, oMetaImage.iZ
                    self._oLogger.info("Image P %s, T %05d / %05d, C %s, Z %d" % (self.P, iFrame, iLastFrame, strC, iZ))
                    oChannel.appendZSlice(oMetaImage)

                oCellAnalyzer.registerChannel(oChannel)


            #self._oLogger.info("  timestamp: %.2f sec" % (self.oMetaData.dctTimestamps[P][iFrame]))

            oStopWatch = StopWatch()

            if self.oSettings.get('Classification', 'collectsamples'):
                img_rgb = oCellAnalyzer.collectObjects(self.origP,
                                                       self.lstSampleReader,
                                                       self.oObjectLearner,
                                                       byTime=self.oSettings.get('General', 'timelapsedata'))

                if not img_rgb is None:
                    iNumberImages += 1
                    if not self._qthread is None:
                        #if self._qthread.get_renderer() == strType:
                        self._qthread.set_image(img_rgb,
                                                'P %s - T %05d' % (self.origP, iT))

                    #channel_id = self.oObjectLearner.strChannelId
                    #self.oObjectLearner.setFeatureNames(oCellAnalyzer.getChannel(channel_id).lstFeatureNames)

            elif oCellAnalyzer.process():
                iNumberImages += 1

                images = []
                if self.oSettings.get('Tracking', 'tracking'):
                    self.oCellTracker.trackAtTimepoint(iT)

                    if self.oSettings.get('Tracking', 'tracking_visualization'):
                        size = oCellAnalyzer.getImageSize(self.channel_mapping[self.PRIMARY_CHANNEL])
                        img_conn, img_split = self.oCellTracker.visualizeTracks(iT, size, self.oSettings.get('Tracking', 'tracking_visualize_track_length'))
                        images += [(img_conn, '#FFFF00', 1.0),
                                   (img_split, '#00FFFF', 1.0),
                                   ]

                for channel_id, infos in self.classifier_infos.iteritems():
                    oCellAnalyzer.classifyObjects(infos['predictor'])


                if True: #self.oSettings.bCreateImages:
                    self.oSettings.set_section('General')
                    for strType, dctRenderInfo in self.oSettings.get2('rendering_class').iteritems():
                        strPathOutImages = os.path.join(self.strPathOutPositionImages, strType)
                        img_rgb, filename = oCellAnalyzer.render(strPathOutImages, dctRenderInfo=dctRenderInfo,
                                                                 writeToDisc=self.oSettings.get2('rendering_class_discwrite'),
                                                                 images=images)
                        #print strType, self._qthread.get_renderer(), self.oSettings.get('Rendering', 'rendering_class')

                        if not self._qthread is None and not img_rgb is None:
                            if self._qthread.get_renderer() == strType:
                                self._qthread.set_image(img_rgb,
                                                        'P %s - T %05d' % (self.origP, iT),
                                                        filename)

                if True: #self.oSettings.bCreateImages:
                    self.oSettings.set_section('General')
                    for strType, dctRenderInfo in self.oSettings.get2('rendering').iteritems():
                        strPathOutImages = os.path.join(self.strPathOutPositionImages, strType)
                        img_rgb, filename = oCellAnalyzer.render(strPathOutImages, dctRenderInfo=dctRenderInfo,
                                                                 writeToDisc=self.oSettings.get2('rendering_discwrite'),
                                                                 images=images)
                        if not self._qthread is None and not img_rgb is None:
                            #print strType, self._qthread.get_renderer(), self.oSettings.get('Rendering', 'rendering')
                            if self._qthread.get_renderer() == strType:
                                self._qthread.set_image(img_rgb,
                                                        'P %s - T %05d' % (self.origP, iT),
                                                        filename)

                    strPathOutImages = os.path.join(self.strPathOutPositionImages, '_labels')
                    safe_mkdirs(strPathOutImages)
                    oCellAnalyzer.exportLabelImages(strPathOutImages)

            self._oLogger.info("* duration: %s" % oStopWatch.current_interval().format(msec=True))

            oCellAnalyzer.purge(features=self.export_features)


        if not self._qthread is None:
            if self._qthread.get_abort():
                return 0
#            stage_info['progress'] = len(self.lstAnalysisFrames)
#            self._qthread.set_stage_info(stage_info)

        return iNumberImages


def analyzePosition(*tplArgs, **dctOptions):
    oPositionAnalyzer = PositionAnalyzer(*tplArgs, **dctOptions)
    return oPositionAnalyzer()


class AnalyzerCore(object):

    EMAIL_SENDER = 'analyzer@cellcognition.org'
    EMAIL_SERVER = 'mail.cellcognition.org'
    EMAIL_SERVER_LOGIN = ('analyzer@cellcognition.org', 'ana_3866')

    def __init__(self, settings):

        #self.guid = newGuid()
        self.oStopWatch = StopWatch()

        self.oSettings = settings
        #self.plate = plate
        self._oLogger = logging.getLogger('Main')

        #self._oClient = oClient

        #self.strPathIn  = strPathIn
        #self.strPathOut = strPathOut

        self.oSettings.set_section('General')
        self.strPathIn = self.oSettings.get2('pathIn')
        self.strPathOut = self.oSettings.get2('pathOut')

        bMkdirsOk = safe_mkdirs(self.strPathOut)
        self._oLogger.info("strPathOut '%s', ok: %s" % (self.strPathOut, bMkdirsOk))

        self.strPathOutAnalyzed = os.path.join(self.strPathOut, 'analyzed')
        bMkdirsOk = safe_mkdirs(self.strPathOutAnalyzed)
        self._oLogger.info("strPathOutAnalyzed '%s', ok: %s" % (self.strPathOutAnalyzed, bMkdirsOk))

        self.strPathOutDump = os.path.join(self.strPathOut, 'dump')
        bMkdirsOk = safe_mkdirs(self.strPathOutDump)
        #if self.oSettings.bDumpCellTracker:
        self._oLogger.info("strPathOutDump '%s', ok: %s" % (self.strPathOutDump, bMkdirsOk))

        self.strPathOutLog = os.path.join(self.strPathOut, 'log')
        bMkdirsOk = safe_mkdirs(self.strPathOutLog)
        self._oLogger.info("strPathOutLog '%s', ok: %s" % (self.strPathOutLog, bMkdirsOk))

        # FIXME:
        #if self.oSettings.bCollectSamples:
        #    self.oSettings.tplFrameRange = None

        self._openImageContainer()

        self.lstSampleReader = []
        self.dctSamplePositions = {}
        self.oObjectLearner = None

        self.oSettings.set_section('Classification')
        if self.oSettings.get2('collectSamples'):

            self.oSettings.bUsePyFarm = False

            _resolve = lambda x: '%s_%s' % (self.oSettings.get2('collectsamples_prefix'), x)
            classifier_path = self.oSettings.get2(_resolve('classification_envpath'))

            classifier_infos = {'strEnvPath' : mapDirectory(classifier_path),
                                'strChannelId' : self.oSettings.get('ObjectDetection', _resolve('channelid')),
                                'strRegionId' : self.oSettings.get2(_resolve('classification_regionname')),
                                }

            if not os.path.isdir(classifier_path):
                raise IOError("Classifier path '%s' not found." % classifier_path)

            self.oObjectLearner = CommonObjectLearner(dctCollectSamples=classifier_infos)
            self.oObjectLearner.loadDefinition()

            # FIXME: if the resulting .ARFF file is trained directly from
            # Python SVM (instead of easy.py) NO leading ID needs to be inserted
            self.oObjectLearner.hasZeroInsert = False

            strAnnotationsPath = self.oObjectLearner.dctEnvPaths['annotations']
            for strFilename in os.listdir(strAnnotationsPath):
                strSampleFilename = os.path.join(strAnnotationsPath, strFilename)

                print strSampleFilename, os.path.splitext(strSampleFilename)[1]

                strFilenameExt = os.path.splitext(strSampleFilename)[1]
                if (os.path.isfile(strSampleFilename) and
                    strFilenameExt == self.oSettings.get2(_resolve('classification_annotationfileext')) and
                    not strFilename[0] in ['.', '_']):

                    has_timelapse = self.oSettings.get('General', 'timelapsedata')

                    if has_timelapse:
                        reference = self.lstAnalysisFrames
                    else:
                        reference = self.lstPositions

                    if strFilenameExt == '.xml':
                        clsReader = CellCounterReaderXML
                    else:
                        clsReader = CellCounterReader
                    oReader = clsReader(strSampleFilename, reference,
                                        scale=self.oSettings.get('General', 'binningfactor'),
                                        timelapse=has_timelapse)

                    self.lstSampleReader.append(oReader)

                    if has_timelapse:
                        oP = oReader.getPosition()
                        if not oP in self.dctSamplePositions:
                            self.dctSamplePositions[oP] = []
                        self.dctSamplePositions[oP].extend(oReader.getTimePoints())
                    else:
                        for oP in oReader.keys():
                            self.dctSamplePositions[oP] = [1]

            for oP in self.dctSamplePositions:
                if not self.dctSamplePositions[oP] is None:
                    self.dctSamplePositions[oP] = sorted(unique(self.dctSamplePositions[oP]))

            #self.oSettings.lstPositions = sorted(self.dctSamplePositions.keys())
            #self.lstPositions = self.oSettings.lstPositions
            self.lstPositions = sorted(self.dctSamplePositions.keys())
            #print self.oSettings.lstPositions
            print self.dctSamplePositions



        elif self.oSettings.get('General', 'qualityControl'):
            strPathOutQualityControl = os.path.join(self.strPathOut, 'qc')
            bMkdirsOk = safe_mkdirs(strPathOutQualityControl)
            self._oLogger.info("strPathOutQualityControl '%s', ok: %s" % (strPathOutQualityControl, bMkdirsOk))

#            self.oQualityControl = QualityControl(oPlate,
#                                                  strPathOutQualityControl,
#                                                  self.oMetaData,
#                                                  self.oSettings.dctQualityControl,
#                                                  dctPlotterInfos={'bUseCairo' : True})
#        else:
#            self.oQualityControl = None


#        if self.oSettings.bClassify:
#            dctCollectSamples = self.oSettings.dctCollectSamples
#            self.oClassPredictor = CommonClassPredictor(dctCollectSamples,
#                                                        strEnvPath=dctCollectSamples['strEnvPath'],
#                                                        strModelPrefix=dctCollectSamples['strModelPrefix'])
#            self.oClassPredictor.importFromArff()
#
#        else:
        self.oClassPredictor = None


    def _openImageContainer(self):
        self.oSettings.set_section('General')
        self.lstPositions = self.oSettings.get2('positions')
        print self.lstPositions, type(self.lstPositions)
        if self.lstPositions == '':
            self.lstPositions = None
        else:
            self.lstPositions = self.lstPositions.split(',')

        # dump the file-structure and meta data in a file
        if has_image_container(self.strPathOutDump) and self.oSettings.get2('preferimagecontainer'):
            self.oImageContainer = load_image_container(self.strPathOutDump)
            self.oImageContainer.setOption('iBinningFactor',
                                           self.oSettings.get2('binningFactor'))

        else:
            # determine which ImageContainer to generate by input directory and read
            # file structure in
            # read ALL positions in dump-mode (otherwise things are getting complicated)
            self.oSettings.lstPositions = None

            naming_scheme = {}
            for option, value in self.oSettings.naming_schemes.items(self.oSettings.get2('namingScheme')):
                naming_scheme[option] = value
            self.oImageContainer = create_image_container(self.strPathIn,
                                                          naming_scheme,
                                                          self.lstPositions)

            self.oImageContainer.setOption('iBinningFactor', self.oSettings.get2('binningFactor'))

            dump_image_container(self.strPathOutDump, self.oImageContainer)

        self.oMetaData = self.oImageContainer.oMetaData

        # does a position selection exist?
        #print self.lstPositions, self.oMetaData.setP
        if not self.lstPositions is None:
            if not is_subset(self.lstPositions, self.oMetaData.setP):
                raise ValueError("The list of selected positions is not valid! %s\nValid values are %s" %\
                                 (self.lstPositions, self.oMetaData.setP))
        else:
            # take all positions found
            self.lstPositions = list(self.oMetaData.setP)
        self.lstPositions.sort()

        if self.oSettings.get2('redoFailedOnly'):
            strPathFinished = os.path.join(self.strPathOutLog, '_finished')
            setFound = set()
            if os.path.isdir(strPathFinished):
                for strFilePath in collect_files(strPathFinished, ['.txt'], absolute=True, force_oswalk=True):
                    strFilename = os.path.split(strFilePath)[1]
                    P = strFilename.split('__')[1]
                    if P in self.oMetaData.setP:
                        setFound.add(P)
                self.lstPositions = [P for P in self.lstPositions
                                     if not P in setFound]
                self.lstPositions.sort()
                self._oLogger.info("* redo failed positions only: %s" % self.lstPositions)
                bHasPositions = True
            else:
                self._oLogger.warning("Cannot redo failed positions without directory '%s'!" % strPathFinished)

        #print self.lstPositions


#        # set image scale options per channel (optional third parameter of 'dctChannelMapping')
#        for strChannelId, tplData in self.oSettings.dctChannelMapping.iteritems():
#            if len(tplData) > 2:
#                self.oImageContainer.getOption('dctScaleChannels')[strChannelId] = tplData[2]

        self._oLogger.info("\n%s" % self.oMetaData.format(time=self.oSettings.get2('timelapseData')))
        #print self.oMetaData.format(time=self.oSettings.get2('timelapseData'))

        # define range of frames to do analysis within
        lstFrames = range(1, self.oMetaData.iDimT+1)

        frames_begin = self.oSettings.get2('frameRange_begin')
        if frames_begin <= 0 or frames_begin > lstFrames[-1]:
            frames_begin = lstFrames[0]

        frames_end = self.oSettings.get2('frameRange_end')
        if frames_end <= 0 or frames_end > lstFrames[-1] or frames_begin > frames_end:
            frames_end = lstFrames[-1]

        self.tplFrameRange = (frames_begin, frames_end)

        lstAnalysisFrames = lstFrames[lstFrames.index(self.tplFrameRange[0]):
                                      lstFrames.index(self.tplFrameRange[1])+1]
#        else:
#            tplValid = (1, self.oMetaData.iDimT)
#            raise SettingsError("tplFrameRange %s has an incorrect value. A valid range is e.g. %s." %
#                                (tplFrameRange, tplValid))

        # take every n'th element from the list
        self.lstAnalysisFrames = lstAnalysisFrames[::self.oSettings.get2('frameincrement')]


        # check channel settings
#        self.tplChannelIds = tuple(self.oSettings.dctChannelMapping.keys())
#        #
#        for strChannelId in self.oSettings.dctChannelMapping:
#            if strChannelId not in self.oMetaData.setC:
#                raise SettingsError("Channel Id '%s' not known in image meta data. Valid channels are %s" %
#                                    (strChannelId, self.oMetaData.setC))


    @classmethod
    def notifyByEmail(cls, lstEmailRecipients, strSubject, strMsg):
        if len(lstEmailRecipients) > 0:
            sendEmail(cls.EMAIL_SENDER,
                      lstEmailRecipients,
                      strSubject,
                      strMsg,
                      smtp=cls.EMAIL_SERVER,
                      login=cls.EMAIL_SERVER_LOGIN,
                      useTls=True)

#    def onSignalJobCompleted(self, info):
#        print "result available for item %d.  %s" % (info["itemIndex"], info)

    def onSignalJobItemCompleted(self, infos):
        if infos['guid'] == self.oJobGuid:
            #print infos
            self._oLogger.info("P %04d completed. %4d / %4d items, %3.1f%%" %\
                               (self.lstPositions[infos['itemIndex']],
                                infos['numberDoneItems'],
                                infos['numberScheduledItems'],
                                infos['percentComplete']))

    def processPositions(self, qthread=None):
        # loop over positions
        lstJobInputs = []
        for oP in self.lstPositions:
            tplArgs = (oP,
                       self.strPathOut,
                       self.oSettings,
                       self.lstAnalysisFrames,
                       self.lstSampleReader,
                       self.dctSamplePositions,
                       self.oObjectLearner,
                       )
            dctOptions = dict(qthread = qthread,
                              )
            lstJobInputs.append((tplArgs, dctOptions))

        #if self.oSettings.get('Farming', 'usePyFarm'):
        if False:

            registerSlot(MSG_FARMING_JOB_ITEM_COMPLETE,
                         self,
                         self.onSignalJobItemCompleted,
                         remote=True,
                         threadSafe=False,
                         domain='farming')
            getFarm().registerEventObserver(self.guid)

            self.oJobGuid = self._oClient.submitJob("cecog.commonanalysis.commonanalysis_pyfarm.analyzePosition",
                                                    lstJobInputs,
                                                    **self.oSettings.dctJobParameters)
            self._oLogger.info("Job submitted successfully! '%s'" % self.oJobGuid)

            self._pollResults()

        else:

            stage_info = {'stage': 1,
                          'min': 1,
                          'max': len(lstJobInputs),
                           }
            for idx, (tplArgs, dctOptions) in enumerate(lstJobInputs):

                if not qthread is None:
                    if qthread.get_abort():
                        return 0

                    stage_info.update({'progress': idx+1,
                                       'text': 'Position %s' % tplArgs[0],
                                       })
                    qthread.set_stage_info(stage_info)

                analyzePosition(*tplArgs, **dctOptions)

            if self.oSettings.get('Classification', 'collectsamples'):
                self.oObjectLearner.export()

                f = file(os.path.join(self.oObjectLearner.dctEnvPaths['data'],
                                      self.oObjectLearner.getOption('filename_pickle')), 'wb')
                pickle.dump(self.oObjectLearner, f)
                f.close()

#            stage_info['progress'] = len(lstJobInputs)
#            qthread.set_stage_info(stage_info)


    def _pollResults(self):
        while True:
            try:
                lstJobOutput = self._oClient.getJobOutput(self.oJobGuid)
            except:
                self._oLogger.error(traceback.format_exc())
            else:
                # job finished?
                if not lstJobOutput is None:
                    self.oStopWatch.stop()
                    strSubject = '[cecog analyzer] finished %s' % os.path.split(self.oSettings.strFilename)[1]

                    if not None in lstJobOutput:
                        self._oLogger.info("Job finished successfully! %d images analyzed." % sum(lstJobOutput))

                        iNumberImageSets = sum(lstJobOutput)
                        if iNumberImageSets > 0:
                            strTimePerImageSet = (self.oStopWatch.stop_interval() / float(iNumberImageSets)).format(msec=True)
                        else:
                            strTimePerImageSet = 'NaN'

                        strMsg = "*** THIS IS AN AUTOMATIC EMAIL. DO NOT REPLY. ***\n\n"
                        strMsg +=  "Job '%s' finished successfully via PyFarm!\n\n" % self.oJobGuid
                        strMsg += "Settings: '%s'\n" % self.oSettings.strFilename
                        strMsg += "Analyzed: %d image sets\n" % iNumberImageSets
                        strMsg += "Start:    %s\n" % time.ctime(self.oStopWatch.get_start_time())
                        strMsg += "Stop:     %s\n" % time.ctime(self.oStopWatch.get_stopt_time())
                        strMsg += "Duration: %s\n" % self.oStopWatch.stop_interval()
    #                    strMsg += "Average:  %s / image set\n" % strTimePerImageSet
                        strMsg += "\n*** THIS IS AN AUTOMATIC EMAIL. DO NOT REPLY. ***\n"
                    else:
                        self._oLogger.info("Job finished NOT successfully!")
                        strMsg =  "Job '%s' finished NOT successfully via PyFarm!\n\n" % self.oJobGuid

                    if (hasattr(self.oSettings, 'lstEmailRecipients') and
                        self.oSettings.lstEmailRecipients is not None):
                        self.notifyByEmail(self.oSettings.lstEmailRecipients,
                                           strSubject, strMsg)

                    break
                else:
                    infos = getFarm().getJobInfo(self.oJobGuid)
                    self._oLogger.info("   done: %04d, scheduled: %04d, queued: %04d, pending: %04d" %\
                                       (infos['numberDoneItems'],
                                        infos['numberScheduledItems'],
                                        infos['numberQueuedItems'],
                                        infos['numberPendingItems']))

            time.sleep(30)


#-------------------------------------------------------------------------------
# main:
#

if __name__ ==  "__main__":

    from pdk.settings import prepareSystemSettings
    from pdk.cmdlinehandlers import (getCommandLineOptionValue,
                                     processCommandLine,
                                     registerClassCommandLineOptions,
                                     registerCommandLineOptions)
    #from pdk.farming.launcher import ClientLauncher

    oLogger = logging.getLogger()
    oHandler = logging.StreamHandler(sys.stdout)
    oHandler.setLevel(logging.DEBUG)
    oFormatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    oHandler.setFormatter(oFormatter)
    oLogger.addHandler(oHandler)
    oLogger.setLevel(logging.DEBUG)

    oLogger.info("*************************************")
    oLogger.info("*** Gerlich Lab - Common Analysis ***")
    oLogger.info("*************************************")

    registerCommandLineOptions(("s:", "settings=", None, "absolute path (including filename) of settings file"),
                               ("i:", "input=", None, "absolute path to image data (optional)"),
                               ("o:", "output=", None, "absolute path to analysis results (optional)"),
                               )
    registerClassCommandLineOptions(ClientLauncher)
    prepareSystemSettings('core')
    tplArgs, oOptions = processCommandLine()

    strPathSettings     = oOptions.settings
    strPathIn           = oOptions.input
    strPathOut          = oOptions.output

    # read the settings data from file
    oSettings = Settings(os.path.abspath(strPathSettings), dctGlobals=globals())

    if oSettings.bUsePyFarm:
        # launch the PyFarm client
        oLogger.info("Launching client ...")
        oClient = launchClient()

        oLogger = logging.getLogger()
        oHandler = logging.StreamHandler(sys.stdout)
        oHandler.setLevel(logging.DEBUG)
        oFormatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
        oHandler.setFormatter(oFormatter)
        oLogger.addHandler(oHandler)
        oLogger.setLevel(logging.DEBUG)

        # make sure that the client is shut down when the applications quits
        registerExitHandler(closeClient,
                            args=(weakref.proxy(oClient),),
                            handleExitSignals=True,
                            handleSystemExit=True
                            )
        oLogger.info("PyFarm Client successfully launched with GUID '%s'", oClient.guid)
    else:
        oClient = None

    # take input and output directories from settings file

    if strPathIn is None:
        strPathIn  = oSettings.strPathIn
    if strPathOut is None:
        strPathOut = oSettings.strPathOut


    # create output path
    safe_mkdirs(strPathOut)

    oPlate = oSettings.clsPlate()
#    if oSettings.bQualityControl or oSettings.bUsePlateInformation:
    if oSettings.bUsePlateInformation:
        strPlateFilename = resolveMappingFile(strPathOut)
        logging.info("Read plate mapping from '%s'" % strPlateFilename)
        oPlateMapper = oSettings.clsPlateMapper(strPlateFilename)
        oPlate.importMapping(oPlateMapper)


    # FIXME: we should have a factory here, determining the kind of class needed
    clsTimeseriesAnalyzer = CommonAnalysis

    if not oSettings.lstPositions is None:
        lstPositions = []
        for oPos in oSettings.lstPositions:
            if type(oPos) == types.TupleType:
                strKey, strValue = oPos
                lstPos = oPlate.selectPositions(strKey, strValue)
                lstPositions.extend(lstPos)
            else:
                lstPositions.append(oPos)
        oSettings.lstPositions = map(int, sorted(unique(lstPositions)))
        logging.info("Analyzing Positions: %d %s" % \
                     (len(oSettings.lstPositions), oSettings.lstPositions))

    oTimeseriesAnalyzer = clsTimeseriesAnalyzer(strPathIn,
                                                strPathOut,
                                                oSettings,
                                                oPlate,
                                                oClient)
    oTimeseriesAnalyzer.processPositions()

