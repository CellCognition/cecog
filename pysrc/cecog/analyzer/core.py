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
       logging, \
       logging.handlers
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
                            TERTIARY_REGIONS,
                            TRACKING_DURATION_UNIT_FRAMES,
                            TRACKING_DURATION_UNIT_MINUTES,
                            TRACKING_DURATION_UNIT_SECONDS,
                            )
from cecog.analyzer.analyzer import (CellAnalyzer,
                                     TimeHolder,
                                     )
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.analyzer.celltracker import *
from cecog.io.imagecontainer import (ImageContainer,
                                     Coordinate,
                                     )
from cecog.learning.collector import CellCounterReader, CellCounterReaderXML
from cecog.learning.learning import CommonObjectLearner, CommonClassPredictor
from cecog.traits.config import NAMING_SCHEMAS

from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.traits.analyzer.tracking import SECTION_NAME_TRACKING

from cecog.analyzer.gallery import EventGallery

from cecog.io.imagecontainer import MetaImage

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

    def __init__(self, plate_id, P, strPathOut, oSettings, lstAnalysisFrames,
                 lstSampleReader, dctSamplePositions, oObjectLearner,
                 image_container,
                 qthread=None, myhack=None):

        self.plate_id = plate_id
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

        self._meta_data = self._imagecontainer.get_meta_data()

        self._has_timelapse = len(self._meta_data.times) > 1

        self.lstAnalysisFrames = lstAnalysisFrames

        self.lstSampleReader = lstSampleReader
        self.dctSamplePositions = dctSamplePositions
        self.oObjectLearner = oObjectLearner

        self._qthread = qthread
        self._myhack = myhack

        name_lookup = {self.PRIMARY_CHANNEL   : 'primary',
                       self.SECONDARY_CHANNEL : 'secondary',
                       self.TERTIARY_CHANNEL  : 'tertiary',
                       }
        self._resolve_name = lambda channel, name: '%s_%s' % \
                             (name_lookup[channel], name)


        # setup output directories

        if self._has_timelapse:
            self.strPathOutPosition = os.path.join(self.strPathOutAnalyzed, "%s" % self.P)
        else:
            self.strPathOutPosition = self.strPathOutAnalyzed
        bMkdirsOk = safe_mkdirs(self.strPathOutPosition)
        self._oLogger.debug("Starting analysis for '%s', ok: %s" % (self.strPathOutPosition, bMkdirsOk))

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
        if self.oSettings.get('Processing', 'tertiary_processchannel'):
            self.channel_mapping[self.TERTIARY_CHANNEL] = self.oSettings.get2('tertiary_channelid')

        self.channel_mapping_reversed = dict([(v,k) for k,v in self.channel_mapping.iteritems()])

        self.tplChannelIds = tuple(self.channel_mapping.values())

        self.classifier_infos = {}
        for channel in [self.PRIMARY_CHANNEL,
                        self.SECONDARY_CHANNEL,
                        self.TERTIARY_CHANNEL,
                        ]:
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
                predictor.importFromArff()
                predictor.loadClassifier()
                classifier_infos['predictor'] = predictor
                self.classifier_infos[channel_id] = classifier_infos



    def _configRootLogger(self):
        self.strPathLog = os.path.join(self.strPathOut, 'log')
        safe_mkdirs(self.strPathLog)
        #self._oLogger = logging.getLogger('PositionAnalyzer')
        oLogger = logging.getLogger(str(os.getpid()))
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

    def __convert_tracking_duration(self, option_name):
        """
        Converts a tracking duration according to the selected unit and the
        mean time-lapse of the current position.
        Returns the number of frames (int).
        """
        value = self.oSettings.get(SECTION_NAME_TRACKING, option_name)
        unit = self.oSettings.get(SECTION_NAME_TRACKING,
                                  'tracking_duration_unit')

        # get mean and stddev for the current position
        info = self._meta_data.get_timestamp_info(self.P)
        if unit == TRACKING_DURATION_UNIT_FRAMES or info is None:
            result = value
        elif unit == TRACKING_DURATION_UNIT_MINUTES:
            result = (value * 60.) / info[0]
        elif unit == TRACKING_DURATION_UNIT_SECONDS:
            result = value / info[0]
        else:
            raise ValueError("Wrong unit '%s' specified." % unit)
        return int(round(result))

    def __call__(self):
        # turn libtiff warnings off
        ccore.turn_off()

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
        self._oLogger.debug("Creating '%s', ok: %s" %\
                           (strPathOutPositionStats,
                            bMkdirsOk))
                            #self.oSettings.bClearTrackingPath))

        #max_frames = max(self.lstAnalysisFrames)
        filename_netcdf = os.path.join(self._path_dump, '%s.nc4' % self.P)
        filename_hdf5 = os.path.join(self._path_dump, '%s.hdf5' % self.P)
        self.oSettings.set_section('Output')
        channel_names = [PrimaryChannel.NAME]
        for name in [SecondaryChannel.NAME, TertiaryChannel.NAME]:
            if self.oSettings.get('Processing', '%s_processchannel' % name.lower()):
                channel_names.append(name)

        create_nc = self.oSettings.get2('netcdf_create_file')
        reuse_nc = self.oSettings.get2('netcdf_reuse_file')
        # turn the reuse NetCDF4 option off in case the create option was switched off too
        # FIXME: GUI and process logic differ here. create_nc is a GUI switch on a higher level than reuse_nc
        if not create_nc:
            reuse_nc = False

        oTimeHolder = TimeHolder(self.P,
                                 channel_names,
                                 filename_netcdf, filename_hdf5,
                                 self._meta_data, self.oSettings,
                                 create_nc=create_nc,
                                 reuse_nc=reuse_nc,
                                 hdf5_create=False,#self.oSettings.get2('hdf5_create_file'),
                                 hdf5_include_raw_images=self.oSettings.get2('hdf5_include_raw_images'),
                                 hdf5_include_label_images=self.oSettings.get2('hdf5_include_label_images'),
                                 hdf5_include_features=self.oSettings.get2('hdf5_include_features')
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

                tracker_options.update({'iBackwardCheck'       : self.__convert_tracking_duration('tracking_backwardCheck'),
                                        'iForwardCheck'        : self.__convert_tracking_duration('tracking_forwardCheck'),

                                        'iBackwardRange'       : self.__convert_tracking_duration('tracking_backwardrange'),
                                        'iForwardRange'        : self.__convert_tracking_duration('tracking_forwardrange'),

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

            primary_channel_id = PrimaryChannel.NAME
            self.oCellTracker.initTrackingAtTimepoint(primary_channel_id, 'primary')

        else:
            self.oCellTracker = None

        oCellAnalyzer = CellAnalyzer(time_holder=oTimeHolder,
                                     #oCellTracker=self.oCellTracker,
                                     P = self.P,
                                     bCreateImages = True,#self.oSettings.bCreateImages,
                                     iBinningFactor = 1,
                                     detect_objects = self.oSettings.get('Processing', 'objectdetection'),
                                     )

        self.export_features = {}
        for name in [PrimaryChannel.NAME,
                     SecondaryChannel.NAME,
                     TertiaryChannel.NAME]:
            #if self.oSettings.get('Classification', self._resolve_name(channel, 'featureextraction')):
            region_features = {}
            prefix = name.lower()
            if name == PrimaryChannel.NAME:
                regions = self.oSettings.get('ObjectDetection', '%s_regions' % prefix)
            elif name == SecondaryChannel.NAME:
                regions = [v for k,v in SECONDARY_REGIONS.iteritems()
                           if self.oSettings.get('ObjectDetection', k)]
            elif name == TertiaryChannel.NAME:
                regions = [v for k,v in TERTIARY_REGIONS.iteritems()
                           if self.oSettings.get('ObjectDetection', k)]

            for region in regions:
                # export all features extracted per regions
                if self.oSettings.get('Output', 'events_export_all_features'):
                    region_features[region] = None
                # export selected features from settings
                else:
                    region_features[region] = \
                        self.oSettings.get('General',
                                           '%s_featureextraction_exportfeaturenames' % prefix)
            self.export_features[name] = region_features


        #try:
        iNumberImages = self._analyzePosition(oCellAnalyzer)
        #except Exception as e:
        #    iNumberImages = 0
        #    oTimeHolder.close_all()
        #    raise e

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
                filename = os.path.join(strPathOutPositionStats,
                                        'P%s__object_details.txt' % self.P)
                oTimeHolder.extportObjectDetails(filename, excel_style=False)
                filename = os.path.join(strPathOutPositionStats,
                                        'P%s__object_details_excel.txt' % self.P)
                oTimeHolder.extportObjectDetails(filename, excel_style=True)


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

                if self.oSettings.get('Output', 'export_tracking_as_dot'):
                    self.oCellTracker.exportGraph(os.path.join(strPathOutPositionStats,
                                                               'tracking_graph___P%s.dot' % self.P))

                if not self._qthread is None:
                    if self._qthread.get_abort():
                        return 0
                    stage_info.update({'max' : 1,
                                       'progress' : 1})
                    self._qthread.set_stage_info(stage_info)

            #oTimeHolder.export_hdf5(os.path.join(self._path_dump,
            #                                     '%s.hdf5' % self.P))


            # remove all features from all channels to free memory
            # for the generation of gallery images
            oTimeHolder.purge_features()

            if self.oSettings.get('Output', 'events_export_gallery_images'):

                strPathCutter = os.path.join(self.strPathOutPosition, "gallery")
                # clear the cutter data
                if os.path.isdir(strPathCutter):
                    shutil.rmtree(strPathCutter)
                gallery_images = ['primary']
                for prefix in [SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]:
                    if self.oSettings.get('Processing',
                                          '%s_processchannel' % prefix):
                        gallery_images.append(prefix)
                for render_name in gallery_images:
                    strPathCutterIn = os.path.join(self.strPathOutPositionImages, render_name)
                    if os.path.isdir(strPathCutterIn):
                        if not self.oCellTracker is None:
                            strPathCutterOut = os.path.join(strPathCutter, render_name)
                            self._oLogger.info("running Cutter for '%s'..." % render_name)
                            image_size =\
                                self.oSettings.get('Output', 'events_gallery_image_size')
                            EventGallery(self.oCellTracker,
                                         strPathCutterIn,
                                         self.P,
                                         strPathCutterOut,
                                         self._meta_data,
                                         oneFilePerTrack=True,
                                         size=(image_size,image_size))
                        # FIXME: be careful here. normally only raw images are
                        #        used for the cutter and can be deleted
                        #        afterwards
                        shutil.rmtree(strPathCutterIn, ignore_errors=True)

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
            self._oLogger.info(" - %d image sets analyzed, %s / image set" %
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
        debug_mode = False #self.oSettings.get('General', 'debugMode')
        
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
                      'item_name': 'image set',
                      }

        iNumberImages = 0
        iLastFrame = self.lstAnalysisFrames[-1]

        stopwatch = StopWatch()

        # - loop over a sub-space with fixed position 'P' and reduced time and
        #   channel axis (in case more channels or time-points exist)
        # - define break-points at C and Z which will yield two nested generators
        coordinate = Coordinate(plate=self.plate_id,
                                position = self.origP,
                                time = self.lstAnalysisFrames,
                                channel = self.tplChannelIds)
        for frame, iter_channel in self._imagecontainer(coordinate,
                                                        interrupt_channel=True,
                                                        interrupt_zslice=True):

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

                zslice_images = []
                for zslice, meta_image in iter_zslice:

                    #P, iFrame, strC, iZ = oMetaImage.position, oMetaImage.time, oMetaImage.channel, oMetaImage.zslice
                    #self._oLogger.info("Image P %s, T %05d / %05d, C %s, Z %d" % (self.P, iFrame, iLastFrame, strC, iZ))
                    zslice_images.append(meta_image)


                # compute values for the registration of multiple channels
                # (translation only)
                self.oSettings.set_section('ObjectDetection')
                xs = [0]
                ys = [0]
                for prefix in [SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]:
                    if self.oSettings.get('Processing','%s_processchannel' % prefix):
                        reg_x = self.oSettings.get2('%s_channelregistration_x' % prefix)
                        reg_y = self.oSettings.get2('%s_channelregistration_y' % prefix)
                        xs.append(reg_x)
                        ys.append(reg_y)
                diff_x = []
                diff_y = []
                for i in range(len(xs)):
                    for j in range(i, len(xs)):
                        diff_x.append(abs(xs[i]-xs[j]))
                        diff_y.append(abs(ys[i]-ys[j]))
                # new image size after registration of all images
                new_image_size = (meta_image.width - max(diff_x),
                                  meta_image.height - max(diff_y))

                self._meta_data.real_image_width = new_image_size[0]
                self._meta_data.real_image_height = new_image_size[1]

                # relative start point of registered image
                registration_start = (max(xs), max(ys))

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
                        feature_extraction = self.oSettings.get(SECTION_NAME_PROCESSING,
                                                                self._resolve_name(channel_section,
                                                                                   'featureextraction'))
                        lstFeatureCategories = []
                        if feature_extraction:
                            for feature in FEATURE_MAP.keys():
                                if self.oSettings.get(SECTION_NAME_FEATURE_EXTRACTION,
                                                      self._resolve_name(channel_section,
                                                                         feature)):
                                    lstFeatureCategories += FEATURE_MAP[feature]


                        dctFeatureParameters = {}
                        if feature_extraction:
                            for name in lstFeatureCategories[:]:
                                if 'haralick' in name:
                                    lstFeatureCategories.remove(name)
                                    dict_append_list(dctFeatureParameters, 'haralick_categories', name)
                                    dctFeatureParameters['haralick_distances'] = (1, 2, 4, 8)

                        if channel_section == self.PRIMARY_CHANNEL:
                            lstPostprocessingFeatureCategories = []
                            lstPostprocessingConditions = []
                            bPostProcessing = False
                            if self.oSettings.get2('primary_postprocessing_roisize_min') > -1:
                                lstPostprocessingFeatureCategories.append('roisize')
                                lstPostprocessingConditions.append('roisize >= %d' % self.oSettings.get2('primary_postprocessing_roisize_min'))
                            if self.oSettings.get2('primary_postprocessing_roisize_max') > -1:
                                lstPostprocessingFeatureCategories.append('roisize')
                                lstPostprocessingConditions.append('roisize <= %d' % self.oSettings.get2('primary_postprocessing_roisize_max'))
                            if self.oSettings.get2('primary_postprocessing_intensity_min') > -1:
                                lstPostprocessingFeatureCategories.append('normbase2')
                                lstPostprocessingConditions.append('n2_avg >= %d' % self.oSettings.get2('primary_postprocessing_intensity_min'))
                            if self.oSettings.get2('primary_postprocessing_intensity_max') > -1:
                                lstPostprocessingFeatureCategories.append('normbase2')
                                lstPostprocessingConditions.append('n2_avg <= %d' % self.oSettings.get2('primary_postprocessing_intensity_max'))

                            if self.oSettings.get2('primary_flat_field_correction') and \
                               os.path.exists(self.oSettings.get2('primary_flat_field_correction_image_file')):
                                strBackgroundImagePath = self.oSettings.get2('primary_flat_field_correction_image_file')
                            else:
                                strBackgroundImagePath = None
                                 
                            lstPostprocessingFeatureCategories = unique(lstPostprocessingFeatureCategories)
                            if len(lstPostprocessingFeatureCategories) > 0 and \
                                self.oSettings.get2('primary_postprocessing'):
                                bPostProcessing = True
                            strPostprocessingConditions = ' and '.join(lstPostprocessingConditions)

                            if self.oSettings.get2('primary_lat2'):
                                iLatWindowSize2 = self.oSettings.get2('primary_latwindowsize2')
                                iLatLimit2 = self.oSettings.get2('primary_latlimit2')
                            else:
                                iLatWindowSize2 = None
                                iLatLimit2 = None
                            channel_registration = (0,0)
                            params = dict(oZSliceOrProjection = projection_info,
                                          channelRegistration=channel_registration,
                                          new_image_size=new_image_size,
                                          registration_start=registration_start,

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
                                          strBackgroundImagePath = strBackgroundImagePath,
                                          bFlatfieldCorrection = self.oSettings.get2('primary_flat_field_correction'),
                                          )
                        elif channel_section in [self.SECONDARY_CHANNEL,
                                                 self.TERTIARY_CHANNEL]:
                            prefix = cls.PREFIX
                            if channel_section == self.SECONDARY_CHANNEL:
                                regions_lookup = SECONDARY_REGIONS
                            else:
                                regions_lookup = TERTIARY_REGIONS
                            regions = [v for k,v in regions_lookup.iteritems()
                                       if self.oSettings.get2(k)]
                            channel_registration = (self.oSettings.get2('%s_channelregistration_x' % prefix),
                                                    self.oSettings.get2('%s_channelregistration_y' % prefix))
                            if self.oSettings.get2('%s_flat_field_correction' % prefix) and \
                               os.path.exists(self.oSettings.get2('%s_flat_field_correction_image_file' % prefix)):
                                strBackgroundImagePath = self.oSettings.get2('%s_flat_field_correction_image_file' % prefix)
                            else:
                                strBackgroundImagePath = None
                            
                            params = dict(oZSliceOrProjection = projection_info,
                                          channelRegistration=channel_registration,
                                          new_image_size=new_image_size,
                                          registration_start=registration_start,

                                          fNormalizeMin = self.oSettings.get2('%s_normalizemin' % prefix),
                                          fNormalizeMax = self.oSettings.get2('%s_normalizemax' % prefix),
                                          #iMedianRadius = self.oSettings.get2('medianradius'),
                                          iExpansionSizeExpanded = self.oSettings.get2('%s_regions_expanded_expansionsize' % prefix),
                                          iShrinkingSizeInside = self.oSettings.get2('%s_regions_inside_shrinkingsize' % prefix),
                                          iExpansionSizeOutside = self.oSettings.get2('%s_regions_outside_expansionsize' % prefix),
                                          iExpansionSeparationSizeOutside = self.oSettings.get2('%s_regions_outside_separationsize' % prefix),
                                          iExpansionSizeRim = self.oSettings.get2('%s_regions_rim_expansionsize' % prefix),
                                          iShrinkingSizeRim = self.oSettings.get2('%s_regions_rim_shrinkingsize' % prefix),

                                          fPropagateLambda = self.oSettings.get2('%s_regions_propagate_lambda' % prefix),
                                          iPropagateDeltaWidth = self.oSettings.get2('%s_regions_propagate_deltawidth' % prefix),

                                          iConstrainedWatershedGaussFilterSize = self.oSettings.get2('%s_regions_constrained_watershed_gauss_filter_size' % prefix),

                                          bPresegmentation = self.oSettings.get2('%s_presegmentation' % prefix),
                                          iPresegmentationMedianRadius = self.oSettings.get2('%s_presegmentation_medianradius' % prefix),
                                          fPresegmentationAlpha = self.oSettings.get2('%s_presegmentation_alpha' % prefix),

                                          # FIXME
                                          fExpansionCostThreshold = 1.5,
                                          lstAreaSelection = regions,
                                          lstFeatureCategories = lstFeatureCategories,
                                          dctFeatureParameters = dctFeatureParameters,
                                          
                                          strBackgroundImagePath = strBackgroundImagePath,
                                          bFlatfieldCorrection = self.oSettings.get2('%s_flat_field_correction' % prefix),
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
                img_rgb = oCellAnalyzer.collectObjects(self.plate_id,
                                                       self.origP,
                                                       self.lstSampleReader,
                                                       self.oObjectLearner,
                                                       byTime=True)

                if not img_rgb is None:
                    iNumberImages += 1
                    if not self._qthread is None:
                        #if self._qthread.get_renderer() == strType:
                        self._qthread.set_image(None,
                                                img_rgb,
                                                'PL %s - P %s - T %05d' % (self.plate_id, self.origP, frame))


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
                        size = oCellAnalyzer.getImageSize(PrimaryChannel.NAME)
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

                    if not self._qthread is None and not img_rgb is None:
                        self._qthread.set_image(strType,
                                                img_rgb,
                                                'PL %s - P %s - T %05d' % (self.plate_id, self.origP, frame),
                                                filename)
                        time.sleep(.05)


                prefixes = [PrimaryChannel.PREFIX, SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]
                self.oSettings.set_section('General')
                for strType, dctRenderInfo in self.oSettings.get2('rendering').iteritems():
                    if not strType in prefixes:
                        strPathOutImages = os.path.join(self.strPathOutPositionImages, strType)
                        img_rgb, filename = oCellAnalyzer.render(strPathOutImages,
                                                                 dctRenderInfo=dctRenderInfo,
                                                                 writeToDisc=self.oSettings.get('Output', 'rendering_contours_discwrite'),
                                                                 images=images)

                        if (not self._qthread is None and not img_rgb is None and
                            not strType in [PrimaryChannel.PREFIX, SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]):
                            self._qthread.set_image(strType,
                                                    img_rgb,
                                                    'PL %s - P %s - T %05d' % (self.plate_id, self.origP, frame),
                                                    filename)
                            time.sleep(.05)

                if not self._myhack is None:
                    d = {}
                    for name in oCellAnalyzer.get_channel_names():
                        channel = oCellAnalyzer.get_channel(name)
                        d[channel.strChannelId] = channel.meta_image.image
                    self._myhack.set_image(d)

                    channel_name, region_name = self._myhack._object_region
                    channel = oCellAnalyzer.get_channel(channel_name)
                    if channel.has_region(region_name):
                        region = channel.get_region(region_name)
                        container = channel.get_container(region_name)
                        coords = {}
                        for obj_id in region:
                            coords[obj_id] = \
                                [(pos[0]+region[obj_id].oRoi.upperLeft[0],
                                  pos[1]+region[obj_id].oRoi.upperLeft[1])
                                 for pos in
                                 container.getCrackCoordinates(obj_id)]
                        self._myhack.set_coords(coords)

                # treat the raw images used for the gallery images differently
                for strType, dctRenderInfo in self.oSettings.get2('rendering').iteritems():
                    if strType in prefixes:
                        strPathOutImages = os.path.join(self.strPathOutPositionImages, strType)
                        img_rgb, filename = oCellAnalyzer.render(strPathOutImages,
                                                                 dctRenderInfo=dctRenderInfo,
                                                                 writeToDisc=True)

                if self.oSettings.get('Output', 'rendering_labels_discwrite'):
                    strPathOutImages = os.path.join(self.strPathOutPositionImages, '_labels')
                    safe_mkdirs(strPathOutImages)
                    oCellAnalyzer.exportLabelImages(strPathOutImages)
                    

            self._oLogger.info(" - Frame %d, duration: %s" % (frame, stopwatch.current_interval().format(msec=True)))

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

    def __init__(self, plate_id, settings, imagecontainer, learner=None):

        #self.guid = newGuid()
        self.oStopWatch = StopWatch()

        self.oSettings = settings
        self.plate_id = plate_id
        #self.plate = plate
        self._oLogger = logging.getLogger(self.__class__.__name__)


        self.oSettings.set_section('General')
        self.strPathOut = imagecontainer.get_path_out(plate_id)
        imagecontainer.set_plate(plate_id)

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

        ci = self.oSettings.get('General', 'crop_image')
        x0 = self.oSettings.get('General', 'crop_image_x0')
        y0 = self.oSettings.get('General', 'crop_image_y0')
        x1 = self.oSettings.get('General', 'crop_image_x1')
        y1 = self.oSettings.get('General', 'crop_image_y1')
        print ci, x0, y0,x1,y1
        if ci:
            MetaImage.enable_cropping(x0, y0, x1-x0, y1-y0)
        else:
            MetaImage.disable_cropping()
            
        print MetaImage._crop_coordinates

        self._imagecontainer = imagecontainer
        self.lstAnalysisFrames = []
        self._openImageContainer()

        self.lstSampleReader = []
        self.dctSamplePositions = {}
        self.oObjectLearner = learner

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

            if self.oObjectLearner is None:
                self.oObjectLearner = CommonObjectLearner(dctCollectSamples=classifier_infos)
                self.oObjectLearner.loadDefinition()

            # FIXME: if the resulting .ARFF file is trained directly from
            # Python SVM (instead of easy.py) NO leading ID need to be inserted
            self.oObjectLearner.hasZeroInsert = False

            # FIXME:
            lookup = {'primary'   : 'Primary',
                      'secondary' : 'Secondary',
                      'tertiary'  : 'Tertiary',
                      }
            self.oObjectLearner.channel_name = lookup[self.oSettings.get2('collectsamples_prefix')]

            annotation_re = re.compile('((.*?_{3})?PL(?P<plate>.*?)_{3})?P(?P<position>.+?)_{1,3}T(?P<time>\d+).*?')

            strAnnotationsPath = self.oObjectLearner.dctEnvPaths['annotations']
            for strFilename in os.listdir(strAnnotationsPath):
                strSampleFilename = os.path.join(strAnnotationsPath, strFilename)

                result = annotation_re.match(strFilename)
                strFilenameExt = os.path.splitext(strSampleFilename)[1]
                if (os.path.isfile(strSampleFilename) and
                    strFilenameExt == self.oSettings.get2(_resolve('classification_annotationfileext')) and
                    not strFilename[0] in ['.', '_'] and
                    not result is None and
                    (result.group('plate') is None or result.group('plate') == self.plate_id)):


                    reference = self._meta_data.times

                    if strFilenameExt == '.xml':
                        clsReader = CellCounterReaderXML
                    else:
                        clsReader = CellCounterReader
                    oReader = clsReader(result, strSampleFilename, reference)

                    self.lstSampleReader.append(oReader)

                    position = result.group('position')
                    if not position in self.dctSamplePositions:
                        self.dctSamplePositions[position] = []
                    self.dctSamplePositions[position].extend(oReader.getTimePoints())

            for position in self.dctSamplePositions:
                if not self.dctSamplePositions[position] is None:
                    self.dctSamplePositions[position] = sorted(unique(self.dctSamplePositions[position]))

            self.lstPositions = sorted(self.dctSamplePositions.keys())

        self.oClassPredictor = None


    def _openImageContainer(self):
        self.oSettings.set_section('General')
        self.lstPositions = self.oSettings.get2('positions')
        if self.lstPositions == '' or not self.oSettings.get2('constrain_positions'):
            self.lstPositions = None
        else:
            self.lstPositions = self.lstPositions.split(',')

        self._meta_data = self._imagecontainer.get_meta_data()

        # does a position selection exist?
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


    def processPositions(self, qthread=None, myhack=None):
        # loop over positions
        lstJobInputs = []
        for oP in self.lstPositions:

            if oP in self.dctSamplePositions:
                analyze = len(self.dctSamplePositions[oP]) > 0
            else:
                analyze = len(self.lstAnalysisFrames) > 0

            if analyze:
                tplArgs = (self.plate_id,
                           oP,
                           self.strPathOut,
                           self.oSettings,
                           self.lstAnalysisFrames,
                           self.lstSampleReader,
                           self.dctSamplePositions,
                           self.oObjectLearner,
                           self._imagecontainer,
                           )
                dctOptions = dict(qthread = qthread,
                                  myhack = myhack,
                                  )
                lstJobInputs.append((tplArgs, dctOptions))


        stage_info = {'stage': 1,
                      'min': 1,
                      'max': len(lstJobInputs),
                       }
        for idx, (tplArgs, dctOptions) in enumerate(lstJobInputs):

            if not qthread is None:
                if qthread.get_abort():
                    break

                stage_info.update({'progress': idx+1,
                                   'text': 'P %s (%d/%d)' % (tplArgs[0], idx+1, len(lstJobInputs)),
                                   })
                qthread.set_stage_info(stage_info)
            try:
                analyzer = PositionAnalyzer(*tplArgs, **dctOptions)
                analyzer()
            except Exception, e:
                logging.getLogger(str(os.getpid())).error(e.message)
                raise

        return self.oObjectLearner

#        if self.oSettings.get('Classification', 'collectsamples'):
#            self.oObjectLearner.export()

            #f = file(os.path.join(self.oObjectLearner.dctEnvPaths['data'],
            #                      self.oObjectLearner.getOption('filename_pickle')), 'wb')
            #pickle.dump(self.oObjectLearner, f)
            #f.close()

#            stage_info['progress'] = len(lstJobInputs)
#            qthread.set_stage_info(stage_info)


