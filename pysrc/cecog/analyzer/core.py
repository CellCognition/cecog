"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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

# Core module of the image processing work flow handling all positions of an
# experiment including the general setup (AnalyzerCore), and the analysis of
# a single position (PositionAnalyzer). This separation was necessary for the
# distributed computing of positions.

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys, \
       time, \
       copy
import cPickle as pickle

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.datetimeutils import StopWatch
from pdk.iterator import is_subset

#-------------------------------------------------------------------------------
# cecog module imports:
#
from cecog import ccore
from cecog.analyzer import (REGION_NAMES_PRIMARY,
                            SECONDARY_REGIONS,
                            )
from cecog.analyzer.analyzer import (CellAnalyzer,
                                     TimeHolder,
                                     )
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.analyzer.celltracker import *
from cecog.io.imagecontainer import ImageContainer
from cecog.learning.collector import CellCounterReader, CellCounterReaderXML
from cecog.learning.learning import CommonObjectLearner, CommonClassPredictor
from cecog.traits.config import NAMING_SCHEMAS

#from cecog.analyzer.cutter import Cutter

#-------------------------------------------------------------------------------
# constants:
#
FILENAME_CELLTRACKER_DUMP = "P%04d_CellTracker.pkl"


FEATURE_MAP = {
               'featurecategory_intensity': ['normbase', 'normbase2'],
               'featurecategory_haralick': ['haralick', 'haralick2'],
               'featurecategory_stat_geom': ['levelset'],
               'featurecategory_granugrey': ['granulometry'],
               'featurecategory_basicshape': ['roisize',
                                              'circularity',
                                              'irregularity',
                                              'irregularity2',
                                              'axes',
                                              ],
               'featurecategory_convhull': ['convexhull'],
               'featurecategory_distance': ['distance'],
               'featurecategory_moments': ['moments'],
               }


CHANNEL_CLASSES = {'PrimaryChannel'   : PrimaryChannel,
                   'SecondaryChannel' : SecondaryChannel,
                   'TertiaryChannel'  : TertiaryChannel,
                   }

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
    TERTIARY_CHANNEL = 'TertiaryChannel'

    def __init__(self, P, strPathOut, oSettings, lstAnalysisFrames,
                 lstSampleReader, dctSamplePositions, oObjectLearner,
                 image_container,
                 qthread=None):

        self.origP = P
        self.P = self._adjustPositionLength(P)
        self.P = P
        self.strPathOut = mapDirectory(strPathOut)


        self._oLogger = self._configRootLogger()
        #self._oLogger = logging.getLogger()

        self.strPathOutAnalyzed = os.path.join(self.strPathOut, 'analyzed')
        self.oSettings = oSettings

        self._path_dump = os.path.join(self.strPathOut, 'dump')
        self._imagecontainer = image_container

        # FIXME: a bit of a hack but the entire ImageContainer path is mapped to the current OS
        #self._imagecontainer.setPathMappingFunction(mapDirectory)

        self._meta_data = self._imagecontainer.meta_data
        self.lstAnalysisFrames = lstAnalysisFrames

        self.lstSampleReader = lstSampleReader
        self.dctSamplePositions = dctSamplePositions
        self.oObjectLearner = oObjectLearner

        self._qthread = qthread

        name_lookup = {self.PRIMARY_CHANNEL   : 'primary',
                       self.SECONDARY_CHANNEL : 'secondary',
                       self.TERTIARY_CHANNEL  : 'tertiary',
                       }
        self._resolve_name = lambda channel, name: '%s_%s' % \
                             (name_lookup[channel], name)


        # setup output directories

        if self.oSettings.get('General', 'timelapseData'):
            self.strPathOutPosition = os.path.join(self.strPathOutAnalyzed, "%s" % self.P)
        else:
            self.strPathOutPosition = self.strPathOutAnalyzed
        bMkdirsOk = safe_mkdirs(self.strPathOutPosition)
        self._oLogger.info("strPathOutPosition '%s', ok: %s" % (self.strPathOutPosition, bMkdirsOk))

        self.strPathOutPositionImages = os.path.join(self.strPathOutPosition, "images")
        self.strPathOutPositionDebug = os.path.join(self.strPathOutPosition, "debug")

        if self.oSettings.get('Classification', 'collectsamples'):
            # disable tracking!
            self.oSettings.set('Processing', 'tracking', False)
            self.lstAnalysisFrames = dctSamplePositions[self.origP]


        self.oSettings.set_section('ObjectDetection')
        self.channel_mapping = {self.PRIMARY_CHANNEL : self.oSettings.get2('primary_channelid')}
        if self.oSettings.get('Processing', 'secondary_processchannel'):
            self.channel_mapping[self.SECONDARY_CHANNEL] = self.oSettings.get2('secondary_channelid')

        self.channel_mapping_reversed = dict([(v,k) for k,v in self.channel_mapping.iteritems()])

        self.tplChannelIds = tuple(self.channel_mapping.values())
        #print self.tplChannelIds

        self.classifier_infos = {}
        for channel in [self.PRIMARY_CHANNEL, self.SECONDARY_CHANNEL]:
            process_channel = channel in self.channel_mapping

            self.oSettings.set_section('Processing')
            if (process_channel and
                self.oSettings.get2(self._resolve_name(channel, 'classification'))):
                channel_id = self.channel_mapping[channel]
                self.oSettings.set_section('Classification')
                classifier_infos = {'strEnvPath' : mapDirectory(self.oSettings.get2(self._resolve_name(channel, 'classification_envpath'))),
                                    'strChannelId' : CHANNEL_CLASSES[channel].NAME,
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
        #ccore.turn_off()

        oStopWatchPos = StopWatch()


#        if self.oSettings.bQualityControl:
#            strPathOutQualityControl = os.path.join(self.strPathOut, 'qc')
#            oQualityControl = QualityControl(strPathOutQualityControl,
#                                             self._meta_data,
#                                             self.oSettings.dctQualityControl)
#            oQualityControl.initPosition(self.P, self.origP)


        strPathOutPositionStats = os.path.join(self.strPathOutPosition,
                                               'statistics')
        bMkdirsOk = safe_mkdirs(strPathOutPositionStats)
        self._oLogger.info("strPathOutPositionStats '%s', ok: %s, cleared: %s" %\
                           (strPathOutPositionStats,
                            bMkdirsOk,
                            'DISABLED FOR NOW'))
                            #self.oSettings.bClearTrackingPath))

        max_frames = max(self.lstAnalysisFrames)
        filename_netcdf = os.path.join(self._path_dump, '%s.nc4' % self.P)
        self.oSettings.set_section('Output')
        oTimeHolder = TimeHolder(self.P, self.tplChannelIds, filename_netcdf,
                                 self._meta_data, self.oSettings,
                                 create_nc4=self.oSettings.get2('netcdf_create_file'),
                                 reuse_nc4=self.oSettings.get2('netcdf_reuse_file')
                                 )

        self.oSettings.set_section('Tracking')
        # structure and logic to handle object trajectories
        if self.oSettings.get('Processing', 'tracking'):

            # clear the tracking data
            #if self.oSettings.bClearTrackingPath and os.path.isdir(strPathOutPositionTracking):
            #    shutil.rmtree(strPathOutPositionTracking)


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

                                    'lstLabelTransitions'  : [],
                                    'lstBackwardLabels'    : [],
                                    'lstForwardLabels'     : [],
                                    })

            if self.oSettings.get('Processing', 'tracking_synchronize_trajectories'):
                tracker_options.update({'iBackwardCheck'       : self.oSettings.get2('tracking_backwardCheck'),
                                        'iForwardCheck'        : self.oSettings.get2('tracking_forwardCheck'),

                                        'iBackwardRange'       : self.oSettings.get2('tracking_backwardrange'),
                                        'iForwardRange'        : self.oSettings.get2('tracking_forwardrange'),

                                        'bBackwardRangeMin'    : self.oSettings.get2('tracking_backwardrange_min'),
                                        'bForwardRangeMin'     : self.oSettings.get2('tracking_forwardrange_min'),

                                        'lstLabelTransitions'  : transitions,
                                        'lstBackwardLabels'    : map(int, self.oSettings.get2('tracking_backwardlabels').split(',')),
                                        'lstForwardLabels'     : map(int, self.oSettings.get2('tracking_forwardlabels').split(',')),
                                        })

#            elif self.oSettings.get2('tracking_event_tracjectory'):
#                clsCellTracker = SplitCellTracker
#                tracker_options.update({'iBackwardCheck'       : self.oSettings.get2('tracking_backwardcheck'),
#                                        'iForwardCheck'        : self.oSettings.get2('tracking_forwardcheck'),
#                                        })
#            elif self.oSettings.get2('tracking_event_no_constraint'):
#                clsCellTracker = PlotCellTracker

            self.oCellTracker = clsCellTracker(oTimeHolder=oTimeHolder,
                                          oMetaData=self._meta_data,
                                          P=self.P,
                                          origP=self.origP,
                                          strPathOut=strPathOutPositionStats,
                                          **tracker_options)

            primary_channel_id = self.channel_mapping[self.PRIMARY_CHANNEL]
            self.oCellTracker.initTrackingAtTimepoint(primary_channel_id, 'primary')

        else:
            self.oCellTracker = None

        oCellAnalyzer = CellAnalyzer(time_holder=oTimeHolder,
                                     #oCellTracker=self.oCellTracker,
                                     P = self.P,
                                     bCreateImages = True,#self.oSettings.bCreateImages,
                                     iBinningFactor = self.oSettings.get('General', 'binningFactor'),
                                     )

        self.export_features = {}
        for channel, channel_id in self.channel_mapping.iteritems():
            #if self.oSettings.get('Classification', self._resolve_name(channel, 'featureextraction')):
            region_features = {}
            if channel == self.PRIMARY_CHANNEL:
                regions = self.oSettings.get('ObjectDetection', self._resolve_name(channel, 'regions'))
            else:
                regions = [v for k,v in SECONDARY_REGIONS.iteritems()
                           if self.oSettings.get('ObjectDetection', k)]
            for region in regions:
                region_features[region] = self.oSettings.get('General', self._resolve_name(channel, 'featureextraction_exportfeaturenames'))
            self.export_features[channel_id] = region_features


        iNumberImages = self._analyzePosition(oCellAnalyzer)

        if iNumberImages > 0:

            if self.oSettings.get('Output', 'export_object_counts'):
                filename = os.path.join(strPathOutPositionStats, 'P%s__object_counts.txt' % self.P)

                channel_id = self.channel_mapping[self.PRIMARY_CHANNEL]
                if channel_id in self.classifier_infos:
                    infos = self.classifier_infos[channel_id]
                    prim_info = (infos['strRegionId'], infos['predictor'].lstClassNames)
                else:
                    # at least the total count for primary is always exported
                    prim_info = ('primary', [])

                sec_info = None
                if self.SECONDARY_CHANNEL in self.channel_mapping:
                    channel_id = self.channel_mapping[self.SECONDARY_CHANNEL]
                    if channel_id in self.classifier_infos:
                        infos = self.classifier_infos[channel_id]
                        sec_info = (infos['strRegionId'], infos['predictor'].lstClassNames)

                oTimeHolder.extportObjectCounts(filename, self.P, self._meta_data,
                                                prim_info, sec_info)

            if self.oSettings.get('Output', 'export_object_details'):
                filename = os.path.join(strPathOutPositionStats, 'P%s__object_details.txt' % self.P)

                oTimeHolder.extportObjectDetails(filename)

                #filename = os.path.join(strPathOutPositionStats, 'P%s__objects.nc4' % self.P)
                #oTimeHolder.export_netcdf4(filename)


            self.oSettings.set_section('Tracking')
            if self.oSettings.get('Processing', 'tracking'):

                stage_info = {'stage': 0,
                              'meta': 'Motif selection:',
                              'text': 'find events...',
                              'min': 0,
                              'max': 0,
                              'progress': 0,
                              }
                if not self._qthread is None:
                    if self._qthread.get_abort():
                        return 0
                    self._qthread.set_stage_info(stage_info)

                self.oCellTracker.initVisitor()
                self._oLogger.debug("--- visitor ok")

                if self.oSettings.get('Processing', 'tracking_synchronize_trajectories'):

                    if not self._qthread is None:
                        if self._qthread.get_abort():
                            return 0
                        stage_info.update({'text' : 'export events...'})
                        self._qthread.set_stage_info(stage_info)

                    # clear the _tracking path
                    self.oCellTracker.analyze(self.export_features,
                                              channelId=primary_channel_id,
                                              clear_path=True)
                    self._oLogger.debug("--- visitor analysis ok")


                if self.oSettings.get('Output', 'export_track_data'):
                    self.oCellTracker.exportFullTracks()

                if not self._qthread is None:
                    if self._qthread.get_abort():
                        return 0
                    stage_info.update({'max' : 1,
                                       'progress' : 1})
                    self._qthread.set_stage_info(stage_info)


            #if self.oSettings.bDoObjectCutting:
#            if True:
#
#                strPathCutter = os.path.join(self.strPathOutPosition, "cutter")
#                # clear the cutter data
#                if os.path.isdir(strPathCutter):
#                    shutil.rmtree(strPathCutter)
#                for strRenderName in self.oSettings.lstCutterRenderInfos:
#                    strPathCutterIn = os.path.join(self.strPathOutPositionImages, strRenderName)
#                    if os.path.isdir(strPathCutterIn):
#                        strPathCutterOut = os.path.join(strPathCutter, strRenderName)
#                        self._oLogger.info("running Cutter for '%s'..." % strRenderName)
#                        Cutter(self.oCellTracker,
#                               strPathCutterIn,
#                               self.P,
#                               strPathCutterOut,
#                               self._meta_data)#,
#                               #**self.oSettings.dctCutterInfos)
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
#                                            self._meta_data,
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
#                                       'Timestamp' : self._meta_data.getTimestamp(self.origP, iT),
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
        oFile = file(os.path.join(strPathFinished, '%s__finished.txt' % self.P), 'w')
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


        if (self.oSettings.get('Output', 'rendering_labels_discwrite') or
            self.oSettings.get('Output', 'rendering_contours_discwrite') or
            self.oSettings.get('Output', 'rendering_class_discwrite')):
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
                      'min': 1,
                      'max': len(self.lstAnalysisFrames),
                      'meta' : 'Image processing:',
                      'item_name': 'timepoint',
                      }

        iNumberImages = 0
        iLastFrame = self.lstAnalysisFrames[-1]

        stopwatch = StopWatch()

        # - loop over a sub-space with fixed position 'P' and reduced time and
        #   channel axis (in case more channels or time-points exist)
        # - define break-points at C and Z which will yield two nested generators
        for frame, iter_channel in self._imagecontainer(position=self.origP,
                                                        time=self.lstAnalysisFrames,
                                                        channel=self.tplChannelIds,
                                                        interrupt_channel=True,
                                                        interrupt_zslice=True):
            print frame

            if not self._qthread is None:
                if self._qthread.get_abort():
                    return 0

                stage_info.update({'progress': self.lstAnalysisFrames.index(frame)+1,
                                   'text': 'T %d (%d/%d)' % (frame, self.lstAnalysisFrames.index(frame)+1, len(self.lstAnalysisFrames)),
                                   'interval': stopwatch.current_interval(),
                                   })
                self._qthread.set_stage_info(stage_info)
                # FIXME: give the GUI a moment to recover
                time.sleep(.1)

            stopwatch.reset()

            oCellAnalyzer.initTimepoint(frame)
            # loop over the channels
            for channel_id, iter_zslice in iter_channel:
                print channel_id

                zslice_images = []
                for zslice, meta_image in iter_zslice:
                    print zslice

                    #P, iFrame, strC, iZ = oMetaImage.position, oMetaImage.time, oMetaImage.channel, oMetaImage.zslice
                    #self._oLogger.info("Image P %s, T %05d / %05d, C %s, Z %d" % (self.P, iFrame, iLastFrame, strC, iZ))
                    zslice_images.append(meta_image)


                self.oSettings.set_section('ObjectDetection')
                registration_x = self.oSettings.get2('secondary_channelRegistration_x')
                registration_y = self.oSettings.get2('secondary_channelRegistration_y')
                if registration_x == 0 and registration_y == 0:
                    channel_registration = None
                else:
                    channel_registration = (registration_x, registration_y)

                # important change: image channels can be assigned to multiple
                # processing channels

                # loop over all possible channels:
                for channel_section, cls in CHANNEL_CLASSES.iteritems():

                    if (channel_section in self.channel_mapping and
                        channel_id == self.channel_mapping[channel_section]):

                        self.oSettings.set_section('ObjectDetection')
                        if self.oSettings.get2(self._resolve_name(channel_section,
                                                                  'zslice_selection')):
                            projection_info = self.oSettings.get2(self._resolve_name(
                                                                    channel_section,
                                                                    'zslice_selection_slice'))
                        else:
                            assert self.oSettings.get2(self._resolve_name(channel_section,
                                                                  'zslice_projection'))
                            method = self.oSettings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_method'))
                            begin = self.oSettings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_begin'))
                            end = self.oSettings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_end'))
                            step = self.oSettings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_step'))
                            projection_info = (method, begin, end, step)


                        # determine the list of features to be calculated from each object
                        lstFeatureCategories = []
                        for feature in FEATURE_MAP.keys():
                            if self.oSettings.get('Classification',
                                                  self._resolve_name(channel_section,
                                                                     feature)):
                                lstFeatureCategories += FEATURE_MAP[feature]

                        # temp: print fetures to be calculated
                        print 'features: ', lstFeatureCategories

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

                            if self.oSettings.get2('primary_lat2'):
                                iLatWindowSize2 = self.oSettings.get2('primary_latwindowsize2')
                                iLatLimit2 = self.oSettings.get2('primary_latlimit2')
                            else:
                                iLatWindowSize2 = None
                                iLatLimit2 = None

                            params = dict(oZSliceOrProjection = projection_info,
                                          channelRegistration=channel_registration,
                                          fNormalizeMin = self.oSettings.get2('primary_normalizemin'),
                                          fNormalizeMax = self.oSettings.get2('primary_normalizemax'),
                                          iMedianRadius = self.oSettings.get2('primary_medianradius'),
                                          iLatWindowSize = self.oSettings.get2('primary_latwindowsize'),
                                          iLatLimit = self.oSettings.get2('primary_latlimit'),
                                          iLatWindowSize2 = iLatWindowSize2,
                                          iLatLimit2 = iLatLimit2,
                                          bDoShapeWatershed = self.oSettings.get2('primary_shapewatershed'),
                                          iGaussSizeShape = self.oSettings.get2('primary_shapewatershed_gausssize'),
                                          iMaximaSizeShape = self.oSettings.get2('primary_shapewatershed_maximasize'),
                                          bDoIntensityWatershed = self.oSettings.get2('primary_intensitywatershed'),
                                          iGaussSizeIntensity = self.oSettings.get2('primary_intensitywatershed_gausssize'),
                                          iMaximaSizeIntensity = self.oSettings.get2('primary_intensitywatershed_maximasize'),
                                          # FIXME:
                                          lstAreaSelection = REGION_NAMES_PRIMARY,
                                          # FIXME:
                                          iMinMergeSize = self.oSettings.get2('primary_shapewatershed_minmergesize'),
                                          bRemoveBorderObjects = self.oSettings.get2('primary_removeborderobjects'),
                                          hole_filling = self.oSettings.get2('primary_holefilling'),
                                          bPostProcessing = bPostProcessing,
                                          lstPostprocessingFeatureCategories = lstPostprocessingFeatureCategories,
                                          strPostprocessingConditions = strPostprocessingConditions,
                                          bPostProcessDeleteObjects = True,
                                          lstFeatureCategories = lstFeatureCategories,
                                          dctFeatureParameters = dctFeatureParameters,
                                          )
                        elif channel_section == self.SECONDARY_CHANNEL:
                            secondary_regions = [v for k,v in SECONDARY_REGIONS.iteritems()
                                                 if self.oSettings.get2(k)]
                            params = dict(oZSliceOrProjection = projection_info,
                                          channelRegistration=channel_registration,
                                          fNormalizeMin = self.oSettings.get2('secondary_normalizemin'),
                                          fNormalizeMax = self.oSettings.get2('secondary_normalizemax'),
                                          #iMedianRadius = self.oSettings.get2('medianradius'),
                                          iExpansionSizeExpanded = self.oSettings.get2('secondary_regions_expanded_expansionsize'),
                                          iShrinkingSizeInside = self.oSettings.get2('secondary_regions_inside_shrinkingsize'),
                                          iExpansionSizeOutside = self.oSettings.get2('secondary_regions_outside_expansionsize'),
                                          iExpansionSeparationSizeOutside = self.oSettings.get2('secondary_regions_outside_separationsize'),
                                          iExpansionSizeRim = self.oSettings.get2('secondary_regions_rim_expansionsize'),
                                          iShrinkingSizeRim = self.oSettings.get2('secondary_regions_rim_shrinkingsize'),
                                          # FIXME
                                          fExpansionCostThreshold = 1.5,
                                          lstAreaSelection = secondary_regions,
                                          lstFeatureCategories = lstFeatureCategories,
                                          dctFeatureParameters = dctFeatureParameters,
                                          )

                        channel = cls(strChannelId=channel_id,
                                      bDebugMode=debug_mode,
                                      strPathOutDebug=self.strPathOutPositionDebug,
                                      **params)

                        # loop over the z-slices
                        for meta_image in zslice_images:
                            channel.append_zslice(meta_image)

                        oCellAnalyzer.register_channel(channel)



            if self.oSettings.get('Classification', 'collectsamples'):
                img_rgb = oCellAnalyzer.collectObjects(self.origP,
                                                       self.lstSampleReader,
                                                       self.oObjectLearner,
                                                       byTime=self.oSettings.get('General', 'timelapsedata'))

                if not img_rgb is None:
                    iNumberImages += 1
                    if not self._qthread is None:
                        #if self._qthread.get_renderer() == strType:
                        self._qthread.set_image(None,
                                                img_rgb,
                                                'P %s - T %05d' % (self.origP, frame))

                    #channel_id = self.oObjectLearner.strChannelId
                    #self.oObjectLearner.setFeatureNames(oCellAnalyzer.getChannel(channel_id).lstFeatureNames)

            else:
                oCellAnalyzer.process()
                iNumberImages += 1

                if not self._qthread:
                    time.sleep(.1)

                images = []
                if self.oSettings.get('Processing', 'tracking'):
                    self.oCellTracker.trackAtTimepoint(frame)

                    self.oSettings.set_section('Tracking')
                    if self.oSettings.get2('tracking_visualization'):
                        size = oCellAnalyzer.getImageSize(self.channel_mapping[self.PRIMARY_CHANNEL])
                        img_conn, img_split = self.oCellTracker.visualizeTracks(frame, size,
                                                                                n=self.oSettings.get2('tracking_visualize_track_length'),
                                                                                radius=self.oSettings.get2('tracking_centroid_radius'))
                        images += [(img_conn, '#FFFF00', 1.0),
                                   (img_split, '#00FFFF', 1.0),
                                   ]

                for infos in self.classifier_infos.itervalues():
                    oCellAnalyzer.classifyObjects(infos['predictor'])


                self.oSettings.set_section('General')
                for strType, dctRenderInfo in self.oSettings.get2('rendering_class').iteritems():
                    strPathOutImages = os.path.join(self.strPathOutPositionImages, strType)
                    img_rgb, filename = oCellAnalyzer.render(strPathOutImages, dctRenderInfo=dctRenderInfo,
                                                             writeToDisc=self.oSettings.get('Output', 'rendering_class_discwrite'),
                                                             images=images)
                    #print strType, self._qthread.get_renderer(), self.oSettings.get('Rendering', 'rendering_class')

                    if not self._qthread is None and not img_rgb is None:
                        self._qthread.set_image(strType,
                                                img_rgb,
                                                'P %s - T %05d' % (self.origP, frame),
                                                filename)
                        time.sleep(.05)

                self.oSettings.set_section('General')
                for strType, dctRenderInfo in self.oSettings.get2('rendering').iteritems():
                    strPathOutImages = os.path.join(self.strPathOutPositionImages, strType)
                    img_rgb, filename = oCellAnalyzer.render(strPathOutImages, dctRenderInfo=dctRenderInfo,
                                                             writeToDisc=self.oSettings.get('Output', 'rendering_contours_discwrite'),
                                                             images=images)
                    if not self._qthread is None and not img_rgb is None:
                        #print strType, self._qthread.get_renderer(), self.oSettings.get('Rendering', 'rendering')
                        self._qthread.set_image(strType,
                                                img_rgb,
                                                'P %s - T %05d' % (self.origP, frame),
                                                filename)
                        time.sleep(.05)

                if self.oSettings.get('Output', 'rendering_labels_discwrite'):
                    strPathOutImages = os.path.join(self.strPathOutPositionImages, '_labels')
                    safe_mkdirs(strPathOutImages)
                    oCellAnalyzer.exportLabelImages(strPathOutImages)

            self._oLogger.info("* duration: %s" % stopwatch.current_interval().format(msec=True))

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

    def __init__(self, settings, imagecontainer=None):

        #self.guid = newGuid()
        self.oStopWatch = StopWatch()

        self.oSettings = settings
        #self.plate = plate
        self._oLogger = logging.getLogger(self.__class__.__name__)

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

        self._imagecontainer = imagecontainer
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

            # FIXME:
            lookup = {'primary'   : 'Primary',
                      'secondary' : 'Secondary',
                      }
            self.oObjectLearner.channel_name = lookup[self.oSettings.get2('collectsamples_prefix')]

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
#                                                  self._meta_data,
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
        print 'MOOO', self.lstPositions, type(self.lstPositions)
        if self.lstPositions == '' or not self.oSettings.get2('constrain_positions'):
            self.lstPositions = None
        else:
            self.lstPositions = self.lstPositions.split(',')


        if self._imagecontainer is None:
            self._imagecontainer = ImageContainer.from_settings(self.oSettings)
        self._meta_data = self._imagecontainer.meta_data

        # does a position selection exist?
        #print self.lstPositions, self._meta_data.setP
        if not self.lstPositions is None:
            if not is_subset(self.lstPositions, self._meta_data.positions):
                raise ValueError("The list of selected positions is not valid! %s\nValid values are %s" %\
                                 (self.lstPositions, self._meta_data.positions))
        else:
            # take all positions found
            self.lstPositions = list(self._meta_data.positions)
        self.lstPositions.sort()

        if self.oSettings.get2('redoFailedOnly'):
            strPathFinished = os.path.join(self.strPathOutLog, '_finished')
            setFound = set()
            if os.path.isdir(strPathFinished):
                for strFilePath in collect_files(strPathFinished, ['.txt'], absolute=True, force_python=True):
                    filename = os.path.split(strFilePath)[1]
                    # stay compatible with an old filename definition (which did
                    # not support _ in the position name
                    if filename[0] == '_':
                        P = filename.split('_')[1]
                    else:
                        P = filename.split('__')[0]
                    if P in self._meta_data.positions:
                        setFound.add(P)
                self.lstPositions = [P for P in self.lstPositions
                                     if not P in setFound]
                self.lstPositions.sort()
                self._oLogger.info("* redo failed positions only: %s" % self.lstPositions)
            else:
                self._oLogger.warning("Cannot redo failed positions without directory '%s'!" % strPathFinished)


        self._oLogger.info("\n%s" % self._meta_data.format(time=self.oSettings.get2('timelapseData')))

        # define range of frames to do analysis within
        lstFrames = list(self._meta_data.times)

        if self.oSettings.get2('frameRange'):
            frames_begin = self.oSettings.get2('frameRange_begin')
            if frames_begin < lstFrames[0] or frames_begin > lstFrames[-1]:
                frames_begin = lstFrames[0]

            frames_end = self.oSettings.get2('frameRange_end')
            if frames_end < 0 or frames_end > lstFrames[-1] or frames_begin > frames_end:
                frames_end = lstFrames[-1]
        else:
            frames_begin = lstFrames[0]
            frames_end = lstFrames[-1]

        self.tplFrameRange = (frames_begin, frames_end)

        lstAnalysisFrames = lstFrames[lstFrames.index(self.tplFrameRange[0]):
                                      lstFrames.index(self.tplFrameRange[1])+1]

        # take every n'th element from the list
        self.lstAnalysisFrames = lstAnalysisFrames[::self.oSettings.get2('frameincrement')]



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
                       self._imagecontainer,
                       )
            dctOptions = dict(qthread = qthread,
                              )
            lstJobInputs.append((tplArgs, dctOptions))


        stage_info = {'stage': 1,
                      'min': 1,
                      'max': len(lstJobInputs),
                       }
        for idx, (tplArgs, dctOptions) in enumerate(lstJobInputs):

            if not qthread is None:
                if qthread.get_abort():
                    return 0

                stage_info.update({'progress': idx+1,
                                   'text': 'P %s (%d/%d)' % (tplArgs[0], idx+1, len(lstJobInputs)),
                                   })
                qthread.set_stage_info(stage_info)

            analyzer = PositionAnalyzer(*tplArgs, **dctOptions)
            analyzer()

        if self.oSettings.get('Classification', 'collectsamples'):
            self.oObjectLearner.export()

            f = file(os.path.join(self.oObjectLearner.dctEnvPaths['data'],
                                  self.oObjectLearner.getOption('filename_pickle')), 'wb')
            pickle.dump(self.oObjectLearner, f)
            f.close()

#            stage_info['progress'] = len(lstJobInputs)
#            qthread.set_stage_info(stage_info)


