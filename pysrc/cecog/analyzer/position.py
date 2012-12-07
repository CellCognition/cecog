"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
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

import os
import time
import shutil
from collections import OrderedDict
from os.path import join, basename, isdir

from pdk.datetimeutils import StopWatch
from pdk.map import dict_append_list

from cecog import ccore
from cecog.io.imagecontainer import Coordinate
from cecog.plugin.segmentation import REGION_INFO
from cecog.analyzer import (TRACKING_DURATION_UNIT_FRAMES,
                            TRACKING_DURATION_UNIT_MINUTES,
                            TRACKING_DURATION_UNIT_SECONDS)

from cecog.analyzer.analyzer import CellAnalyzer, TimeHolder
from cecog.analyzer.celltracker import ClassificationCellTracker2

from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel)

from cecog.learning.learning import CommonClassPredictor

from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.traits.analyzer.tracking import SECTION_NAME_TRACKING

from cecog.analyzer.gallery import EventGallery
from cecog.util.logger import LoggerObject
from cecog.util.util import makedirs

FILENAME_CELLTRACKER_DUMP = "P%04d_CellTracker.pkl"

FEATURE_MAP = {'featurecategory_intensity': ['normbase', 'normbase2'],
               'featurecategory_haralick': ['haralick', 'haralick2'],
               'featurecategory_stat_geom': ['levelset'],
               'featurecategory_granugrey': ['granulometry'],
               'featurecategory_basicshape': ['roisize',
                                              'circularity',
                                              'irregularity',
                                              'irregularity2',
                                              'axes'],
               'featurecategory_convhull': ['convexhull'],
               'featurecategory_distance': ['distance'],
               'featurecategory_moments': ['moments']}

CHANNEL_CLASSES = {'Primary' : PrimaryChannel,
                   'Secondary' : SecondaryChannel,
                   'Tertiary' : TertiaryChannel}


class PositionAnalyzer(LoggerObject):

    POSITION_LENGTH = 4
    PRIMARY_CHANNEL = 'Primary'
    SECONDARY_CHANNEL = 'Secondary'
    TERTIARY_CHANNEL = 'Tertiary'

    CHANNELS = OrderedDict( primary=PrimaryChannel,
                            secondary=SecondaryChannel,
                            tertiary=TertiaryChannel)

    _info = {'stage': 0,
             'meta': 'Motif selection:',
             'text': '---',
             'min': 0,
             'max': 0,
             'progress': 0}


    def __init__(self, plate_id, P, out_dir, settings, lstAnalysisFrames,
                 lstSampleReader, dctSamplePositions, learner,
                 image_container, qthread=None, myhack=None):
        super(PositionAnalyzer, self).__init__()
        self._out_dir = out_dir
        self.settings = settings
        self._imagecontainer = image_container
        self.plate_id = plate_id
        self.origP = P
        self.P = P

        if not self.has_timelapse:
            self.settings.set('Processing', 'tracking', False)

        self._makedirs()
        self.add_file_handler(join(self._log_dir, "%s.log" %P), self._lvl.DEBUG)

        self.lstAnalysisFrames = lstAnalysisFrames
        self.lstSampleReader = lstSampleReader
        self.dctSamplePositions = dctSamplePositions
        self.learner = learner

        self._qthread = qthread
        self._myhack = myhack

        # disable tracking
        if self.settings.get('Classification', 'collectsamples'):
            self.settings.set('Processing', 'tracking', False)
            self.lstAnalysisFrames = dctSamplePositions[self.origP]

        self.setup_classifiers()

    def setup_classifiers(self):
        self.classifier_infos = {}
        sttg = self.settings
        for channel, channel_id in self.ch_mapping.iteritems():
            self.settings.set_section('Processing')
            if sttg.get2(self._resolve_name(channel, 'classification')):
                sttg.set_section('Classification')
                classifier_infos = {'strEnvPath' :
                                        sttg.get2(self._resolve_name(channel,
                                                                     'classification_envpath')),
                                    # varnames are messed up!
                                    'strChannelId' : CHANNEL_CLASSES[channel].NAME,
                                    'channel_id': channel_id,
                                    'strRegionId' :
                                    sttg.get2(self._resolve_name(channel,
                                                                 'classification_regionname'))}
                clf = CommonClassPredictor(dctCollectSamples=classifier_infos)
                clf.importFromArff()
                clf.loadClassifier()
                classifier_infos['classifier'] = clf
                self.classifier_infos[channel] = classifier_infos

    # FIXME the following functions do moreless the same!
    def _resolve_name(self, channel, name):
        _channel_lkp = {self.PRIMARY_CHANNEL   : 'primary',
                        self.SECONDARY_CHANNEL : 'secondary',
                        self.TERTIARY_CHANNEL  : 'tertiary'}
        return '%s_%s' % (_channel_lkp[channel], name)

    @property
    def ch_mapping(self):
        sttg =self.settings
        chm = OrderedDict()
        chm[self.PRIMARY_CHANNEL] = sttg.get('ObjectDetection',
                                             'primary_channelid')
        if sttg.get('Processing', 'secondary_processchannel'):
            chm[self.SECONDARY_CHANNEL] = sttg.get('ObjectDetection',
                                                   'secondary_channelid')
        if sttg.get('Processing', 'tertiary_processchannel'):
            chm[self.TERTIARY_CHANNEL] = sttg.get('ObjectDetection',
                                                  'tertiary_channelid')
        return chm

    @property
    def channels_to_process(self):
        # refactor this function with ch_mapping
        channels = (PrimaryChannel.NAME, )
        for name in [SecondaryChannel.NAME, TertiaryChannel.NAME]:
            if self.settings.get('Processing', '%s_processchannel' % name.lower()):
                channels = channels + (name,)
        return channels

    @property
    def meta_data(self):
        return self._imagecontainer.get_meta_data()

    @property
    def has_timelapse(self):
        return self.meta_data.has_timelapse
        # self._has_timelapse = len(self.meta_data.times) > 1

    def _makedirs(self):
        assert isinstance(self.P, basestring)
        assert isinstance(self._out_dir, basestring)

        self._analyzed_dir = join(self._out_dir, "analyzed")
        if self.has_timelapse:
            self._position_dir = join(self._analyzed_dir, self.P)
        else:
            self._position_dir = self._analyzed_dir

        odirs = (self._analyzed_dir,
                 join(self._out_dir, "debug"),
                 join(self._out_dir, "dump"),
                 join(self._out_dir, "log"),
                 join(self._out_dir, "log", "_finished"),
                 join(self._out_dir, "hdf5"),
                 join(self._out_dir, "plots", "population"),
                 join(self._position_dir, "statistics"),
                 join(self._position_dir, "gallery"),
                 join(self._position_dir, "images"),
                 join(self._position_dir, "images","_labels"))

        for odir in odirs:
            try:
                makedirs(odir)
            except os.error: # no permissions
                self.logger.error("mkdir %s: failed" %odir)
            else:
                self.logger.info("mkdir %s: ok" %odir)
            setattr(self, "_%s_dir" %basename(odir.lower()).strip("_"), odir)

    def __del__(self):
        # XXX - is it really necessary?
        self.logger.removeHandler(self._file_handler)

    def _convert_tracking_duration(self, option_name):
        """
        Converts a tracking duration according to the unit and the
        mean time-lapse of the current position.
        Returns number of frames.
        """
        value = self.settings.get(SECTION_NAME_TRACKING, option_name)
        unit = self.settings.get(SECTION_NAME_TRACKING,
                                  'tracking_duration_unit')

        # get mean and stddev for the current position
        info = self.meta_data.get_timestamp_info(self.P)
        if unit == TRACKING_DURATION_UNIT_FRAMES or info is None:
            result = value
        elif unit == TRACKING_DURATION_UNIT_MINUTES:
            result = (value * 60.) / info[0]
        elif unit == TRACKING_DURATION_UNIT_SECONDS:
            result = value / info[0]
        else:
            raise ValueError("Wrong unit '%s' specified." % unit)
        return int(round(result))

    @property
    def _hdf_options(self):
        self.settings.set_section('Output')
        h5opts = {"hdf5_include_tracking": self.settings.get2('hdf5_include_tracking'),
                  "hdf5_include_events": self.settings.get2('hdf5_include_events'),
                  "hdf5_compression": "gzip" if self.settings.get2("hdf5_compression") else None,
                  "hdf5_create": self.settings.get2('hdf5_create_file'),
                  "hdf5_reuse": self.settings.get2('hdf5_reuse'),
                  "hdf5_include_raw_images": self.settings.get2('hdf5_include_raw_images'),
                  "hdf5_include_label_images": self.settings.get2('hdf5_include_label_images'),
                  "hdf5_include_features": self.settings.get2('hdf5_include_features'),
                  "hdf5_include_crack": self.settings.get2('hdf5_include_crack'),
                  "hdf5_include_classification": self.settings.get2('hdf5_include_classification')}

        # Processing overwrites Output
        if not self.settings.get('Processing', 'tracking'):
            h5opts["hdf5_include_tracking"] = False
            h5opts["hdf5_include_events"] = False
        return h5opts

    @property
    def _tracking_options(self):
        tropts = {'fMaxObjectDistance': self.settings.get2('tracking_maxobjectdistance'),
                  'iMaxSplitObjects': self.settings.get2('tracking_maxsplitobjects'),
                  'iMaxTrackingGap': self.settings.get2('tracking_maxtrackinggap'),
                  'bExportTrackFeatures': self.settings.get2('tracking_exporttrackfeatures'),
                  'featureCompression': None if self.settings.get2('tracking_compressiontrackfeatures') == 'raw' else self.settings.get2('tracking_compressiontrackfeatures'),
                  'bHasClassificationData': True,
                  'iBackwardCheck': 0,
                  'iForwardCheck': 0,
                  'iBackwardRange': -1,
                  'iForwardRange': -1,
                  'iMaxInDegree': self.settings.get2('tracking_maxindegree'),
                  'iMaxOutDegree': self.settings.get2('tracking_maxoutdegree'),
                  'lstLabelTransitions': [],
                  'lstBackwardLabels': [],
                  'lstForwardLabels': []}

        # if event selection is on
        # what is this good for?
        transitions = self.settings.get2('tracking_labeltransitions').replace('),(', ')__(')
        transitions = map(eval, transitions.split('__'))
        if self.settings.get('Processing', 'tracking_synchronize_trajectories'):
            tropts.update({'iBackwardCheck': self._convert_tracking_duration('tracking_backwardCheck'),
                           'iForwardCheck': self._convert_tracking_duration('tracking_forwardCheck'),
                           'iBackwardRange': self._convert_tracking_duration('tracking_backwardrange'),
                           'iForwardRange': self._convert_tracking_duration('tracking_forwardrange'),
                           'bBackwardRangeMin': self.settings.get2('tracking_backwardrange_min'),
                           'bForwardRangeMin': self.settings.get2('tracking_forwardrange_min'),
                           'lstLabelTransitions': transitions,
                           'lstBackwardLabels': map(int, self.settings.get2('tracking_backwardlabels').split(',')),
                           'lstForwardLabels': map(int, self.settings.get2('tracking_forwardlabels').split(','))})
        return tropts

    def define_exp_features(self):
        features = {}
        for name in [PrimaryChannel.NAME, SecondaryChannel.NAME,
                     TertiaryChannel.NAME]:
            region_features = {}
            for region in REGION_INFO.names[name.lower()]:
                # export all features extracted per regions
                if self.settings.get('Output', 'events_export_all_features') or \
                        self.settings.get('Output', 'export_track_data'):
                    region_features[region] = None
                # export selected features from settings
                else:
                    region_features[region] = \
                        self.settings.get('General',
                                          '%s_featureextraction_exportfeaturenames'
                                          % name.lower())
            features[name] = region_features
        return features

    def export_object_counts(self, timeholder):
        fname = join(self._statistics_dir, 'P%s__object_counts.txt' % self.P)

        # at least the total count for primary is always exported
        ch_info = {'Primary': ('primary', [], [])}


        for ch_name, channel_id in self.ch_mapping.iteritems():
            if self.classifier_infos.has_key(ch_name):
                infos = self.classifier_infos[ch_name]
                ch_info[ch_name] = (infos['strRegionId'],
                                    infos['classifier'].lstClassNames,
                                    infos['classifier'].lstHexColors)

        timeholder.exportObjectCounts(fname, self.P, self.meta_data, ch_info)
        pplot_ymax = \
            self.settings.get('Output', 'export_object_counts_ylim_max')

        # plot only for primary channel so far!
        timeholder.exportPopulationPlots(fname, self._population_dir, self.P,
                                         self.meta_data, ch_info['Primary'], pplot_ymax)


    def export_object_details(self, timeholder):
        fname = join(self._statistics_dir,
                        'P%s__object_details.txt' % self.P)
        timeholder.exportObjectDetails(fname, excel_style=False)
        fname = join(self._statistics_dir,
                        'P%s__object_details_excel.txt' % self.P)
        timeholder.exportObjectDetails(fname, excel_style=True)

    def export_image_names(self, timeholder):
        timeholder.exportImageFileNames(self._statistics_dir,
                                         self.P,
                                         self._imagecontainer,
                                         self.ch_mapping)

    def export_full_tracks(self, celltracker):
        celltracker.exportFullTracks()

    def export_graphviz(self, celltracker):
        self.oCellTracker.exportGraph(\
            join(self._statistics_dir, 'tracking_graph___P%s.dot' % self.P))

    def export_gallery_images(self, celltracker):
        gallery_images = ['primary']
        for prefix in [SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]:
            if self.settings.get('Processing', '%s_processchannel' % prefix):
                gallery_images.append(prefix)

        for render_name in gallery_images:
            cutter_in = join(self._images_dir, render_name)
            if isdir(cutter_in):
                cutter_out = join(self._gallery_dir, render_name)
                self.logger.info("running Cutter for '%s'..." % render_name)
                image_size = \
                    self.settings.get('Output', 'events_gallery_image_size')
                EventGallery(celltracker, cutter_in, self.P, cutter_out,
                             self.meta_data, oneFilePerTrack=True,
                             size=(image_size, image_size))
            # FIXME: be careful here. normally only raw images are
            #        used for the cutter and can be deleted
            #        afterwards
            shutil.rmtree(cutter_in, ignore_errors=True)

    def tracking(self, timeholder, celltracker):
        """Invoke Tracking, just tracking"""
        self.logger.debug("--- serializing tracking start")
        timeholder.serialize_tracking(celltracker)
        self.logger.debug("--- serializing tracking ok")

        if self.is_aborted():
            return 0 # number of processed images
        self.update_stage({'text': "find events"})

        self.logger.debug("--- visitor start")
        celltracker.initVisitor()
        self.logger.debug("--- visitor ok")

    def event_selection(self, timeholder, celltracker):
        """Invoke event_selection"""
        celltracker.analyze(self.export_features,
                            channelId=PrimaryChannel.NAME,
                            clear_path=True)

        self.logger.debug("--- visitor analysis ok")
        timeholder.serialize_events(celltracker)
        self.logger.debug("--- serializing events ok")

    def __call__(self):
        self.logger.info('')
        # turn libtiff warnings off
        if not __debug__:
            ccore.turn_off()
        stopwatch = StopWatch()
        self.settings.set_section('Output')

        # include hdf5 file name in hdf5_options
        # perhaps timeholder might be a good placke to read out the options
        # fils must not exist to proceed
        hdf5_fname = join(self._hdf5_dir, '%s.hdf5' % self.P)
        self.oTimeHolder = TimeHolder(self.P, self.channels_to_process,
                                      hdf5_fname,
                                      self.meta_data, self.settings,
                                      self.lstAnalysisFrames,
                                      self.plate_id,
                                      **self._hdf_options)

        self.settings.set_section('Tracking')
        # structure and logic to handle object trajectories
        if not self.settings.get('Processing', 'tracking'):
            self.oCellTracker = None
        else:
            clsCellTracker = ClassificationCellTracker2
            self.oCellTracker = clsCellTracker(oTimeHolder=self.oTimeHolder,
                                               oMetaData=self.meta_data,
                                               P=self.P,
                                               origP=self.origP,
                                               strPathOut=self._statistics_dir,
                                               **self._tracking_options)
            primary_channel_id = PrimaryChannel.NAME
            region_name = self.settings.get2('tracking_regionname')
            self.oCellTracker.initTrackingAtTimepoint(primary_channel_id, region_name)


        # object detection??
        oCellAnalyzer = CellAnalyzer(time_holder=self.oTimeHolder,
                                     P = self.P,
                                     bCreateImages = True,
                                     iBinningFactor = 1,
                                     detect_objects = self.settings.get('Processing', 'objectdetection'))

        self.export_features = self.define_exp_features()
        n_images = self._analyzePosition(oCellAnalyzer)

        if n_images > 0:
            # exports also
            if self.settings.get('Output', 'export_object_counts'):
                self.export_object_counts(self.oTimeHolder)
            if self.settings.get('Output', 'export_object_details'):
                self.export_object_details(self.oTimeHolder)
            if self.settings.get('Output', 'export_file_names'):
                self.export_image_names(self.oTimeHolder)

            # invoke tracking
            self.settings.set_section('Tracking')
            if self.settings.get('Processing', 'tracking'):
                ret = self.tracking(self.oTimeHolder, self.oCellTracker)
                if self.is_aborted() or ret == 0:
                    return 0 # number of processed images
                self.update_stage({'text': 'export events...'})
                # invoke event selection
                if self.settings.get('Processing', 'tracking_synchronize_trajectories'):
                    self.event_selection(self.oTimeHolder, self.oCellTracker)

                if self.settings.get('Output', 'export_track_data'):
                    self.export_full_tracks(self.oCellTracker)
                if self.settings.get('Output', 'export_tracking_as_dot'):
                    self.export_graphviz(self.oCellTracker)

            if self.is_aborted():
                return 0
            self.update_stage({'text': 'export events...',
                               'max': 1,
                               'progress': 1})

            # remove all features from all channels to free memory
            # for the generation of gallery images
            self.oTimeHolder.purge_features()

            if self.settings.get('Output', 'events_export_gallery_images'):
                self.export_gallery_images(self.oCellTracker)
        stopwatch.stop()

        if n_images > 0:
            oInterval = stopwatch.stop_interval()/n_images
            self.logger.info(" - %d image sets analyzed, %s / image set" %
                             (n_images, oInterval.format(msec=True)))

        # write an empty file to mark this position as finished
        oFile = file(join(self._finished_dir, '%s__finished.txt' % self.P), 'w')
        oFile.close()
        self.clear()
        return {'iNumberImages': n_images, 'filename_hdf5': hdf5_fname}

    def clear(self):
        # closes hdf5
        self.oTimeHolder.close_all()

    def is_aborted(self):
        if self._qthread is None:
            return False
        elif self._qthread.get_abort():
            return True

    def update_stage(self, info):
        self._info.update(info)
        if not self._qthread is None:
            self._qthread.set_stage_info(self._info)

    def _analyzePosition(self, oCellAnalyzer):
        stage_info = {'stage': 2,
                      'min': 1,
                      'max': len(self.lstAnalysisFrames),
                      'meta' : 'Image processing:',
                      'item_name': 'image set'}

        n_images = 0
        iLastFrame = self.lstAnalysisFrames[-1]
        stopwatch = StopWatch()

        # - loop over a sub-space with fixed position 'P' and reduced time and
        # channel axis (in case more channels or time-points exist)
        # - define break-points at C and Z which will yield two nested generators
        coordinate = Coordinate(plate=self.plate_id,
                                position = self.origP,
                                time = self.lstAnalysisFrames,
                                channel = self.ch_mapping.values())

        for frame, iter_channel in self._imagecontainer(coordinate,
                                                        interrupt_channel=True,
                                                        interrupt_zslice=True):

            if self.is_aborted():
                self.clear()
                return 0
            else:
                stage_info.update({'progress': self.lstAnalysisFrames.index(frame)+1,
                                   'text': 'T %d (%d/%d)' % (frame, self.lstAnalysisFrames.index(frame)+1, len(self.lstAnalysisFrames)),
                                   'interval': stopwatch.current_interval()})
                if not self._qthread is None:
                    self._qthread.set_stage_info(stage_info)
                # FIXME: give the GUI a moment to recover
                time.sleep(.1)
            stopwatch.reset()

            oCellAnalyzer.initTimepoint(frame)
            # loop over the channels
            for channel_id, iter_zslice in iter_channel:

                zslice_images = []
                for zslice, meta_image in iter_zslice:
                    zslice_images.append(meta_image)


                # compute values for the registration of multiple channels
                # (translation only)
                self.settings.set_section('ObjectDetection')
                xs = [0]
                ys = [0]
                for prefix in [SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]:
                    if self.settings.get('Processing','%s_processchannel' % prefix):
                        reg_x = self.settings.get2('%s_channelregistration_x' % prefix)
                        reg_y = self.settings.get2('%s_channelregistration_y' % prefix)
                        xs.append(reg_x)
                        ys.append(reg_y)
                diff_x = []
                diff_y = []
                for i in range(len(xs)):
                    for j in range(i, len(xs)):
                        diff_x.append(abs(xs[i]-xs[j]))
                        diff_y.append(abs(ys[i]-ys[j]))

                # new image size after registration of all images


                new_image_size = (self.meta_data.dim_x - max(diff_x),
                                  self.meta_data.dim_y - max(diff_y))
#
                self.meta_data.real_image_width = new_image_size[0]
                self.meta_data.real_image_height = new_image_size[1]

                # relative start point of registered image
                registration_start = (max(xs), max(ys))

                # important change: image channels can be assigned to multiple
                # processing channels

                # loop over all possible channels:
                for channel_section, cls in CHANNEL_CLASSES.iteritems():

                    if (channel_section in self.ch_mapping and
                        channel_id == self.ch_mapping[channel_section]):

                        self.settings.set_section('ObjectDetection')
                        if self.settings.get2(self._resolve_name(channel_section,
                                                                  'zslice_selection')):
                            projection_info = self.settings.get2(self._resolve_name(
                                                                    channel_section,
                                                                    'zslice_selection_slice'))
                        else:
                            assert self.settings.get2(self._resolve_name(channel_section,
                                                                  'zslice_projection'))
                            method = self.settings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_method'))
                            begin = self.settings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_begin'))
                            end = self.settings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_end'))
                            step = self.settings.get2(self._resolve_name(
                                                           channel_section,
                                                           'zslice_projection_step'))
                            projection_info = (method, begin, end, step)


                        # determine the list of features to be calculated from each object
                        feature_extraction = self.settings.get(SECTION_NAME_PROCESSING,
                                                                self._resolve_name(channel_section,
                                                                                   'featureextraction'))
                        lstFeatureCategories = []
                        if feature_extraction:
                            for feature in FEATURE_MAP.keys():
                                if self.settings.get(SECTION_NAME_FEATURE_EXTRACTION,
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
                            channel_registration = (0,0)

                        elif channel_section in [self.SECONDARY_CHANNEL,
                                                 self.TERTIARY_CHANNEL]:
                            prefix = cls.PREFIX
                            channel_registration = (self.settings.get2('%s_channelregistration_x' % prefix),
                                                    self.settings.get2('%s_channelregistration_y' % prefix))

                        channel = cls(strChannelId=channel_id,
                                      oZSliceOrProjection = projection_info,

                                      channelRegistration = channel_registration,
                                      new_image_size = new_image_size,
                                      registration_start = registration_start,

                                      fNormalizeMin = self.settings.get2('%s_normalizemin' % prefix),
                                      fNormalizeMax = self.settings.get2('%s_normalizemax' % prefix),

                                      lstFeatureCategories = lstFeatureCategories,
                                      dctFeatureParameters = dctFeatureParameters,
                                      )

                        # loop over the z-slices
                        for meta_image in zslice_images:
                            channel.append_zslice(meta_image)
                        oCellAnalyzer.register_channel(channel)


            if self.settings.get('Classification', 'collectsamples'):
                img_rgb = oCellAnalyzer.collectObjects(self.plate_id,
                                                       self.origP,
                                                       self.lstSampleReader,
                                                       self.learner,
                                                       byTime=True)

                if not img_rgb is None:
                    n_images += 1
                    if not self._qthread is None:
                        #if self._qthread.get_renderer() == strType:
                        self._qthread.set_image(None,
                                                img_rgb,
                                                'PL %s - P %s - T %05d' % (self.plate_id, self.origP, frame))

            else:
                oCellAnalyzer.process()
                n_images += 1

                if not self._qthread:
                    time.sleep(.1)

                images = []
                if self.settings.get('Processing', 'tracking'):
                    self.oCellTracker.trackAtTimepoint(frame)

                    self.settings.set_section('Tracking')
                    if self.settings.get2('tracking_visualization'):
                        size = oCellAnalyzer.getImageSize(PrimaryChannel.NAME)
                        img_conn, img_split = self.oCellTracker.visualizeTracks(frame, size,
                                                                                n=self.settings.get2('tracking_visualize_track_length'),
                                                                                radius=self.settings.get2('tracking_centroid_radius'))
                        images += [(img_conn, '#FFFF00', 1.0),
                                   (img_split, '#00FFFF', 1.0)]

                for name, infos in self.classifier_infos.iteritems():
                    oCellAnalyzer.classify_objects(infos['classifier'])

                self.settings.set_section('General')
                for strType, dctRenderInfo in self.settings.get2('rendering_class').iteritems():
                    out_images = join(self._images_dir, strType)
                    img_rgb, filename = oCellAnalyzer.render(out_images, dctRenderInfo=dctRenderInfo,
                                                             writeToDisc=self.settings.get('Output', 'rendering_class_discwrite'),
                                                             images=images)

                    if not self._qthread is None and not img_rgb is None:
                        self._qthread.set_image(strType,
                                                img_rgb,
                                                'PL %s - P %s - T %05d' % (self.plate_id, self.origP, frame),
                                                filename)
                        time.sleep(.05)


                prefixes = [PrimaryChannel.PREFIX, SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]
                self.settings.set_section('General')
                for strType, dctRenderInfo in self.settings.get2('rendering').iteritems():
                    if not strType in prefixes:
                        out_images = join(self._images_dir, strType)
                        img_rgb, filename = oCellAnalyzer.render(out_images,
                                                                 dctRenderInfo=dctRenderInfo,
                                                                 writeToDisc=self.settings.get('Output', 'rendering_contours_discwrite'),
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
                        coords = {}
                        for obj_id, obj in region.iteritems():
                            coords[obj_id] = obj.crack_contour
                        self._myhack.set_coords(coords)

                # treat the raw images used for the gallery images differently
                for strType, dctRenderInfo in self.settings.get2('rendering').iteritems():
                    if strType in prefixes:
                        out_images = join(self._images_dir, strType)
                        img_rgb, filename = oCellAnalyzer.render(out_images,
                                                                 dctRenderInfo=dctRenderInfo,
                                                                 writeToDisc=True)

                if self.settings.get('Output', 'rendering_labels_discwrite'):
                    oCellAnalyzer.exportLabelImages(self._labels_dir)

            self.logger.info(" - Frame %d, duration: %s" \
                                 %(frame, stopwatch.current_interval().format(msec=True)))

            oCellAnalyzer.purge(features=self.export_features)

        if self.is_aborted():
            return 0
        return n_images
