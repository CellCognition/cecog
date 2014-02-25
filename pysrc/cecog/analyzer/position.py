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

import os
import shutil
import numpy as np
from collections import OrderedDict
from os.path import join, basename, isdir

from cecog.io.imagecontainer import Coordinate
from cecog.plugin.metamanager import MetaPluginManager
from cecog.units.time import TimeConverter

from cecog.analyzer.timeholder import TimeHolder
from cecog.analyzer.analyzer import CellAnalyzer
from cecog.analyzer.tracker import Tracker
from cecog.analyzer.eventselection import EventSelection
from cecog.analyzer.eventselection import UnsupervisedEventSelection

from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    MergedChannel)

from cecog.learning.learning import CommonClassPredictor

from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING

from cecog.gallery import TrackGallery
from cecog.gallery import ChannelGallery
from cecog.export import TrackExporter, EventExporter, TC3Exporter
from cecog.util.logger import LoggerObject
from cecog.util.stopwatch import StopWatch
from cecog.util.util import makedirs

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


class PositionCore(LoggerObject):

    POSITION_LENGTH = 4
    PRIMARY_CHANNEL = PrimaryChannel.NAME
    SECONDARY_CHANNEL = SecondaryChannel.NAME
    TERTIARY_CHANNEL = TertiaryChannel.NAME
    MERGED_CHANNEL = MergedChannel.NAME

    CHANNELS = OrderedDict()
    CHANNELS['primary'] = PrimaryChannel
    CHANNELS['secondary'] = SecondaryChannel
    CHANNELS['tertiary'] = TertiaryChannel
    CHANNELS['merged'] = MergedChannel

    _info = {'stage': 0,
             'meta': 'Motif selection:',
             'text': '---',
             'min': 0,
             'max': 0,
             'progress': 0}

    def __init__(self, plate_id, position, out_dir, settings, frames,
                 sample_readers, sample_positions, learner,
                 image_container, qthread=None):
        super(PositionCore, self).__init__()

        self._out_dir = out_dir
        self.settings = settings
        self._imagecontainer = image_container
        self.plate_id = plate_id
        self.position = position

        self._frames = frames # frames to process
        self.sample_readers = sample_readers
        self.sample_positions = sample_positions
        self.learner = learner

        self._tracker = None
        self.timeholder = None
        self.classifiers = OrderedDict()

        self._qthread = qthread

    def _analyze(self):
        self._info.update({'stage': 2,
                           'min': 1,
                           'max': len(self._frames),
                           'meta' : 'Image processing:',
                           'item_name': 'image set'})

    def zslice_par(self, ch_name):
        """Returns either the number of the zslice to select or a tuple of
        parmeters to control the zslice projcetion"""
        self.settings.set_section('ObjectDetection')
        if self.settings.get2(self._resolve_name(ch_name, 'zslice_selection')):
            par = self.settings.get2(self._resolve_name(
                    ch_name, 'zslice_selection_slice'))
        elif self.settings.get2(self._resolve_name(ch_name, 'zslice_projection')):
            method = self.settings.get2(self._resolve_name(
                    ch_name, 'zslice_projection_method'))
            begin = self.settings.get2(self._resolve_name(
                    ch_name, 'zslice_projection_begin'))
            end = self.settings.get2(self._resolve_name(
                    ch_name, 'zslice_projection_end'))
            step = self.settings.get2(self._resolve_name(
                    ch_name, 'zslice_projection_step'))
            par = (method, begin, end, step)
        return par

    def registration_shift(self):
        # compute values for the registration of multiple channels
        # (translation only)
        self.settings.set_section('ObjectDetection')
        xs = [0]
        ys = [0]
        for prefix in [SecondaryChannel.PREFIX, TertiaryChannel.PREFIX]:
            if self.settings.get('Processing','%s_processchannel' %prefix):
                reg_x = self.settings.get2('%s_channelregistration_x' %prefix)
                reg_y = self.settings.get2('%s_channelregistration_y' %prefix)
                xs.append(reg_x)
                ys.append(reg_y)
        diff_x = []
        diff_y = []
        for i in range(len(xs)):
            for j in range(i, len(xs)):
                diff_x.append(abs(xs[i]-xs[j]))
                diff_y.append(abs(ys[i]-ys[j]))

        image_width = self.meta_data.dim_x
        image_height = self.meta_data.dim_y

        if self.settings.get('General', 'crop_image'):
            y0 = self.settings.get('General', 'crop_image_y0')
            y1 = self.settings.get('General', 'crop_image_y1')
            x0 = self.settings.get('General', 'crop_image_x0')
            x1 = self.settings.get('General', 'crop_image_x1')

            image_width = x1 - x0
            image_height = y1 - y0


        # new image size after registration of all images
        image_size = (image_width - max(diff_x),
                      image_height - max(diff_y))

        self.meta_data.real_image_width = image_size[0]
        self.meta_data.real_image_height = image_size[1]

        # relative start point of registered image
        return (max(xs), max(ys)), image_size

    def feature_params(self, ch_name):

        # XXX unify list and dict
        f_categories = list()
        f_cat_params = dict()

        # unfortunateley some classes expecte empty list and dict
        if not self.settings.get(SECTION_NAME_PROCESSING,
                             self._resolve_name(ch_name,
                                                'featureextraction')):
            return f_categories, f_cat_params

        for category, feature in FEATURE_MAP.iteritems():
            if self.settings.get(SECTION_NAME_FEATURE_EXTRACTION,
                                 self._resolve_name(ch_name, category)):
                if "haralick" in category:
                    try:
                        f_cat_params['haralick_categories'].extend(feature)
                    except KeyError:
                        assert isinstance(feature, list)
                        f_cat_params['haralick_categories'] = feature
                else:
                    f_categories += feature

        if f_cat_params.has_key("haralick_categories"):
            f_cat_params['haralick_distances'] = (1, 2, 4, 8)

        return f_categories, f_cat_params

    def setup_channel(self, proc_channel, col_channel, zslice_images):

        # determine the list of features to be calculated from each object
        f_cats, f_params = self.feature_params(proc_channel)
        reg_shift, im_size = self.registration_shift()
        ch_cls = self.CHANNELS[proc_channel.lower()]

        # default value is (0, 0)
        channel_registration = (self.settings.get2('%s_channelregistration_x' %proc_channel),
                                self.settings.get2('%s_channelregistration_y' %proc_channel))
        channel = ch_cls(strChannelId=col_channel,
                         oZSliceOrProjection = self.zslice_par(proc_channel),
                         channelRegistration = channel_registration,
                         new_image_size = im_size,
                         registration_start = reg_shift,
                         fNormalizeMin = self.settings.get2('%s_normalizemin' %proc_channel),
                         fNormalizeMax = self.settings.get2('%s_normalizemax' %proc_channel),
                         bFlatfieldCorrection = self.settings.get2('%s_flat_field_correction' %proc_channel),
                         strBackgroundImagePath = self.settings.get2('%s_flat_field_correction_image_dir' %proc_channel),
                         lstFeatureCategories = f_cats,
                         dctFeatureParameters = f_params)

        if channel.is_virtual():
            channel.merge_regions = self._channel_regions(proc_channel)

        # loop over the z-slices
        for meta_image in zslice_images:
            channel.append_zslice(meta_image)
        return channel

    def register_channels(self, cellanalyzer, col_channels):

        channels = list()
        for channel_id, zslices in col_channels:
            zslice_images = [meta_image for _, meta_image in zslices]
            for ch_name in self.processing_channels:
                # each process channel has a destinct color channel
                if channel_id != self.ch_mapping[ch_name]:
                    continue
                channel = self.setup_channel(ch_name, channel_id, zslice_images)
                cellanalyzer.register_channel(channel)

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


    # FIXME the following functions do moreless the same!
    def _resolve_name(self, channel, name):
        _channel_lkp = {self.PRIMARY_CHANNEL: 'primary',
                        self.SECONDARY_CHANNEL: 'secondary',
                        self.TERTIARY_CHANNEL: 'tertiary',
                        self.MERGED_CHANNEL: 'merged'}
        return '%s_%s' %(_channel_lkp[channel], name)

    @property
    def meta_data(self):
        return self._imagecontainer.get_meta_data()

    @property
    def has_timelapse(self):
        return self.meta_data.has_timelapse
        # self._has_timelapse = len(self.meta_data.times) > 1

    @property
    def processing_channels(self):
        channels = (self.PRIMARY_CHANNEL, )
        for name in [self.SECONDARY_CHANNEL, self.TERTIARY_CHANNEL, self.MERGED_CHANNEL]:
            if self.settings.get('Processing', '%s_processchannel' % name.lower()):
                channels = channels + (name,)
        return channels

    @property
    def ch_mapping(self):
        """Maps processing channels to color channels. Mapping is not
        necessariliy one-to-one.
        """
        sttg = self.settings
        chm = OrderedDict()
        for channel in self.processing_channels:
            chm[channel] = sttg.get('ObjectDetection',
                                    '%s_channelid' %channel.lower())
        return chm

    def is_aborted(self):
        if self._qthread is None:
            return False
        elif self._qthread.is_aborted():
            return True

    def update_status(self, info):
        self._info.update(info)
        if not self._qthread is None:
            self._qthread.update_status(self._info, stime=50)

    def set_image(self, images, message, stime=0):
        """Propagate a rendered image to QThread."""
        assert isinstance(images, dict)
        assert isinstance(message, basestring)
        if not (self._qthread is None or not images):
            self._qthread.show_image(images, message, stime)

    def _channel_regions(self, p_channel):
        """Return a dict of of channel region pairs according to the classifier"""
        regions = OrderedDict()
        if self.CHANNELS[p_channel.lower()].is_virtual():
            for prefix, channel in self.CHANNELS.iteritems():
                if channel.is_virtual():
                    continue
                if self.settings.get("Classification", "merge_%s" %prefix):
                    regions[prefix.title()] = \
                        self.settings.get("Classification", "%s_%s_region"
                                          %(self.MERGED_CHANNEL.lower(), prefix))
        else:
            regions[p_channel] = self.settings.get("Classification",
                self._resolve_name(p_channel, 'classification_regionname'))
        return regions

    @property
    def _all_channel_regions(self):
        chreg = OrderedDict()
        for chname in self.processing_channels:
            region = self._channel_regions(chname)
            if isinstance(region, basestring):
                chreg[chname] = region
            else:
                chreg[chname] = tuple(region.values())
        return chreg


class PositionPicker(PositionCore):

    def __call__(self):
        self.timeholder = TimeHolder(self.position, self._all_channel_regions,
                                     None,
                                     self.meta_data, self.settings,
                                     self._frames,
                                     self.plate_id,
                                     **self._hdf_options)

        ca = CellAnalyzer(timeholder=self.timeholder,
                          position = self.position,
                          create_images = True,
                          binning_factor = 1,
                          detect_objects = self.settings.get('Processing',
                                                             'objectdetection'))
        n_images = self._analyze(ca)

    def _analyze(self, cellanalyzer):
        super(PositionPicker, self)._analyze()
        n_images = 0
        stopwatch = StopWatch(start=True)
        crd = Coordinate(self.plate_id, self.position,
                         self._frames, list(set(self.ch_mapping.values())))

        for frame, channels in self._imagecontainer( \
            crd, interrupt_channel=True, interrupt_zslice=True):
            if self.is_aborted():
                return 0
            else:
                txt = 'T %d (%d/%d)' %(frame, self._frames.index(frame)+1,
                                       len(self._frames))
                self.update_status({'progress': self._frames.index(frame)+1,
                                   'text': txt,
                                   'interval': stopwatch.interim()})

            stopwatch.reset(start=True)
            # initTimepoint clears channel_registry
            cellanalyzer.initTimepoint(frame)
            self.register_channels(cellanalyzer, channels)
            image = cellanalyzer.collectObjects(self.plate_id,
                                                self.position,
                                                self.sample_readers,
                                                self.learner,
                                                byTime=True)

            if image is not None:
                n_images += 1
                msg = 'PL %s - P %s - T %05d' %(self.plate_id, self.position,
                                                frame)
                self.set_image(image, msg)



class PositionAnalyzer(PositionCore):
    def __init__(self, *args, **kw):
        super(PositionAnalyzer, self).__init__(*args, **kw)

        if not self.has_timelapse:
            self.settings.set('Processing', 'tracking', False)

        self._makedirs()
        self.add_file_handler(join(self._log_dir, "%s.log" %self.position),
                              self._lvl.DEBUG)

    def _makedirs(self):
        assert isinstance(self.position, basestring)
        assert isinstance(self._out_dir, basestring)

        self._analyzed_dir = join(self._out_dir, "analyzed")
        if self.has_timelapse:
            self._position_dir = join(self._analyzed_dir, self.position)
        else:
            self._position_dir = self._analyzed_dir

        odirs = (self._analyzed_dir,
                 join(self._out_dir, "log"),
                 join(self._out_dir, "log", "_finished"),
                 join(self._out_dir, "hdf5"),
                 join(self._out_dir, "plots"),
                 join(self._position_dir, "statistics"),
                 join(self._position_dir, "tc3"),
                 join(self._position_dir, "gallery"),
                 join(self._position_dir, "channel_gallery"),
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

    def setup_classifiers(self):
        sttg = self.settings
        # processing channel, color channel
        for p_channel, c_channel in self.ch_mapping.iteritems():
            self.settings.set_section('Processing')
            if sttg.get2(self._resolve_name(p_channel, 'classification')):
                sttg.set_section('Classification')
                clf = CommonClassPredictor(
                    clf_dir=sttg.get2(self._resolve_name(p_channel,
                                                         'classification_envpath')),
                    name=p_channel,
                    channels=self._channel_regions(p_channel),
                    color_channel=c_channel)
                clf.importFromArff()
                clf.loadClassifier()
                self.classifiers[p_channel] = clf

    @property
    def _transitions(self):
        if self.settings.get('EventSelection', 'unsupervised_event_selection'):
            transitions = np.array((0, 1))
        else:
            transitions = eval(self.settings.get('EventSelection', 'labeltransitions'))
            transitions = np.array(transitions)
        return transitions.reshape((-1, 2))

    def setup_eventselection(self, graph):
        """Setup the method for event selection."""

        opts = {'transitions': self._transitions,
                'backward_range': self._convert_tracking_duration('backwardrange'),
                'forward_range': self._convert_tracking_duration('forwardrange'),
                'max_in_degree': self.settings.get('EventSelection', 'maxindegree'),
                'max_out_degree': self.settings.get('EventSelection', 'maxoutdegree')}

        if self.settings.get('EventSelection', 'supervised_event_selection'):
            opts.update({'backward_labels': [int(i) for i in self.settings.get('EventSelection', 'backwardlabels').split(',')],
                         'forward_labels': [int(i) for i in self.settings.get('EventSelection', 'forwardlabels').split(',')],
                         'backward_range_min': self.settings.get('EventSelection', 'backwardrange_min'),
                         'forward_range_min': self.settings.get('EventSelection', 'forwardrange_min'),
                         'backward_check': self._convert_tracking_duration('backwardCheck'),
                         'forward_check': self._convert_tracking_duration('forwardCheck')})
            es = EventSelection(graph, **opts)

        elif self.settings.get('EventSelection', 'unsupervised_event_selection'):
            opts.update({'forward_check': self._convert_tracking_duration('min_event_duration'),
                         'forward_labels': (1, ),
                         'backward_check': -1, # unsused for unsupervised usecase
                         'backward_labels': (0, ),
                         'num_clusters': self.settings.get('EventSelection', 'num_clusters'),
                         'min_cluster_size': self.settings.get('EventSelection', 'min_cluster_size')})
            es = UnsupervisedEventSelection(graph, **opts)

        return es

    def _convert_tracking_duration(self, option_name):
        """Converts a tracking duration according to the unit and the
        mean time-lapse of the current position.
        Returns number of frames.
        """
        value = self.settings.get('EventSelection', option_name)
        unit = self.settings.get('EventSelection', 'duration_unit')

        # get mean and stddev for the current position
        info = self.meta_data.get_timestamp_info(self.position)
        if unit == TimeConverter.FRAMES or info is None:
            result = value
        elif unit == TimeConverter.MINUTES:
            result = (value * 60.) / info[0]
        elif unit == TimeConverter.SECONDS:
            result = value / info[0]
        else:
            raise ValueError("Wrong unit '%s' specified." %unit)
        return int(round(result))

    def define_exp_features(self):
        features = {}
        for name in self.processing_channels:
            region_features = {}

            for region in MetaPluginManager().region_info.names[name.lower()]:
                # export all features extracted per regions
                if self.settings.get('Output', 'events_export_all_features') or \
                        self.settings.get('Output', 'export_track_data'):
                    # None means all features
                    region_features[region] = None
                # export selected features from settings
                else:
                    region_features[region] = \
                        self.settings.get('General',
                                          '%s_featureextraction_exportfeaturenames'
                                          % name.lower())

                features[name] = region_features

            # special case for merged channel
            if name is self.MERGED_CHANNEL:
                mftrs = list()
                for channel, region in self._channel_regions(name).iteritems():
                    if features[channel][region] is None:
                        mftrs = None
                    else:
                        for feature in features[channel][region]:
                            mftrs.append("_".join((channel, region, feature)))
                region_features[self._all_channel_regions[name]] = mftrs
                features[name] = region_features

        return features


    def export_object_counts(self):
        fname = join(self._statistics_dir, 'P%s__object_counts.txt' % self.position)

        # at least the total count for primary is always exported
        # OLD: ch_info = OrderedDict([('Primary', ('primary', [], []))])
        # but this does not work any more if we admit merged channels
        # (which might be the only ones we are interested in)
        ch_info = OrderedDict()
        for name, clf in self.classifiers.iteritems():
            names = clf.class_names.values()
            colors = [clf.hexcolors[n] for n in names]
            ch_info[name] = (clf.regions, names, colors)

        # if no classifier has been loaded, no counts can be exported.
        if len(ch_info) == 0:
            return

        self.timeholder.exportObjectCounts(fname, self.position, self.meta_data, ch_info)
        pplot_ymax = \
            self.settings.get('Output', 'export_object_counts_ylim_max')

        # plot only for primary channel so far!
        #if 'Primary' in ch_info:
        #    self.timeholder.exportPopulationPlots(fname, self._plots_dir, self.position,
        #                                          self.meta_data, ch_info['Primary'], pplot_ymax)
        self.timeholder.exportPopulationPlots(ch_info, self._plots_dir,
                                              self.plate_id, self.position,
                                              ymax=pplot_ymax)



    def export_object_details(self):
        fname = join(self._statistics_dir,
                        'P%s__object_details.txt' % self.position)
        self.timeholder.exportObjectDetails(fname)

    def export_image_names(self):
        self.timeholder.exportImageFileNames(self._statistics_dir,
                                             self.position,
                                             self._imagecontainer._importer,
                                             self.ch_mapping)

    def export_full_tracks(self):
        odir = join(self._statistics_dir, 'full')
        exporter = EventExporter(self.meta_data)
        exporter.full_tracks(self.timeholder, self._tes.visitor_data,
                             self.position, odir)

    def export_graphviz(self, channel_name='Primary', region_name='primary'):
        filename = 'tracking_graph___P%s.dot' %self.position
        exporter = TrackExporter()
        exporter.graphviz_dot(join(self._statistics_dir, filename),
                              self._tracker)

        sample_holders = OrderedDict()
        for frame in self.timeholder.keys():
            channel = self.timeholder[frame][channel_name]
            sample_holders[frame] = channel.get_region(region_name)

        filename = join(self._statistics_dir, filename.replace('.dot', '_features.csv'))
        exporter.tracking_data(filename, sample_holders)

    def export_gallery_images(self):
        for ch_name in self.processing_channels:
            cutter_in = join(self._images_dir, ch_name.lower())

            if not isdir(cutter_in):
                self.logger.warning('directory not found (%s)' %cutter_in)
                self.logger.warning('can not write the gallery images')
            else:
                cutter_out = join(self._gallery_dir, ch_name.lower())
                self.logger.info("running Cutter for '%s'..." %ch_name)
                image_size = \
                    self.settings.get('Output', 'events_gallery_image_size')
                TrackGallery(self._tes.centers(),
                             cutter_in, cutter_out, self.position, size=image_size)
            # FIXME: be careful here. normally only raw images are
            #        used for the cutter and can be deleted
            #        afterwards
            shutil.rmtree(cutter_in, ignore_errors=True)

    def export_tracks_hdf5(self):
        """Save tracking data to hdf file"""
        self.logger.debug("--- serializing tracking start")
        self.timeholder.serialize_tracking(self._tes.graph)
        self.logger.debug("--- serializing tracking ok")

    def export_events(self):
        """Export and save event selection data"""
        exporter = EventExporter(self.meta_data)
        # writes to the event folder
        odir = join(self._statistics_dir, "events")
        exporter.track_features(self.timeholder, self._tes.visitor_data,
                                self.export_features, self.position, odir)

        # writes event data to hdf5
        self.timeholder.serialize_events(self._tes)
        self.logger.debug("--- serializing events ok")

    def export_tc3(self):
        t_mean = self.meta_data.get_timestamp_info(self.position)[0]
        tu = TimeConverter(t_mean, TimeConverter.SECONDS)
        increment = self.settings('General', 'frameincrement')
        t_step = tu.sec2min(t_mean)*increment

        nclusters = self.settings.get('EventSelection', 'num_clusters')
        exporter = TC3Exporter(self._tes.tc3data, self._tc3_dir, nclusters, t_step,
                               TimeConverter.MINUTES, self.position)
        exporter()

    def __call__(self):
        # include hdf5 file name in hdf5_options
        # perhaps timeholder might be a good place to read out the options
        # file does not have to exist to proceed
        hdf5_fname = join(self._hdf5_dir, '%s.ch5' % self.position)

        self.timeholder = TimeHolder(self.position, self._all_channel_regions,
                                     hdf5_fname,
                                     self.meta_data, self.settings,
                                     self._frames,
                                     self.plate_id,
                                     **self._hdf_options)

        self.settings.set_section('Tracking')
        # setup tracker
        if self.settings('Processing', 'tracking'):
            region = self.settings('Tracking', 'tracking_regionname')
            tropts = (self.settings('Tracking', 'tracking_maxobjectdistance'),
                      self.settings('Tracking', 'tracking_maxsplitobjects'),
                      self.settings('Tracking', 'tracking_maxtrackinggap'))
            self._tracker = Tracker(*tropts)
            self._tes = self.setup_eventselection(self._tracker.graph)

        stopwatch = StopWatch(start=True)
        ca = CellAnalyzer(timeholder=self.timeholder,
                          position = self.position,
                          create_images = True,
                          binning_factor = 1,
                          detect_objects = self.settings('Processing',
                                                             'objectdetection'))

        self.setup_classifiers()
        self.export_features = self.define_exp_features()
        n_images = self._analyze(ca)

        if n_images > 0:
            # invoke event selection
            if self.settings('Processing', 'eventselection') and \
                    self.settings('Processing', 'tracking'):
                self.logger.debug("--- visitor start")
                self._tes.find_events()
                self.logger.debug("--- visitor ok")
                if self.is_aborted():
                    return 0 # number of processed images

            # save all the data of the position, no aborts from here on
            # want all processed data saved
            if self.settings('Output', 'export_object_counts') and \
                    self.settings('EventSelection', 'supervised_event_selection'):
                # no object counts in case of unsupervised event selection
                self.export_object_counts()
            if self.settings('Output', 'export_object_details'):
                self.export_object_details()
            if self.settings('Output', 'export_file_names'):
                self.export_image_names()

            if self.settings('Processing', 'tracking'):
                self.export_tracks_hdf5()
                self.update_status({'text': 'export events...'})
                if self.settings('Processing', 'eventselection'):
                    self.export_events()
                if self.settings('EventSelection', 'unsupervised_event_selection'):
                    self.export_tc3()
                if self.settings('Output', 'export_track_data'):
                    self.export_full_tracks()
                if self.settings('Output', 'export_tracking_as_dot'):
                    self.export_graphviz()

            self.update_status({'text': 'export events...',
                                'max': 1,
                                'progress': 1})

            # remove all features from all channels to free memory
            # for the generation of gallery images
            self.timeholder.purge_features()
            if self.settings.get('Output', 'events_export_gallery_images') and \
                    self.settings.get('Processing', 'eventselection'):
                self.export_gallery_images()

        try:
            intval = stopwatch.stop()/n_images*1000
        except ZeroDivisionError:
            pass
        else:
            self.logger.info(" - %d image sets analyzed, %3d ms per image set" %
                             (n_images, intval))

        self.touch_finished()
        self.clear()
        return n_images

    @property
    def hdf5_filename(self):
        return self.timeholder.hdf5_filename

    def touch_finished(self, times=None):
        """Writes an empty file to mark this position as finished"""
        fname = join(self._finished_dir, '%s__finished.txt' % self.position)
        with open(fname, "w") as f:
            os.utime(fname, times)

    def clear(self):
        # closes hdf5
        if self.timeholder is not None:
            self.timeholder.close_all()
        # close and remove handlers from logging object
        self.close()

    def _analyze(self, cellanalyzer):
        super(PositionAnalyzer, self)._analyze()
        n_images = 0
        stopwatch = StopWatch(start=True)
        crd = Coordinate(self.plate_id, self.position,
                         self._frames, list(set(self.ch_mapping.values())))

        for frame, channels in self._imagecontainer( \
            crd, interrupt_channel=True, interrupt_zslice=True):

            if self.is_aborted():
                self.clear()
                return 0
            else:
                txt = 'T %d (%d/%d)' %(frame, self._frames.index(frame)+1,
                                       len(self._frames))
                self.update_status({'progress': self._frames.index(frame)+1,
                                    'text': txt,
                                    'interval': stopwatch.interim()})

            stopwatch.reset(start=True)
            cellanalyzer.initTimepoint(frame)
            self.register_channels(cellanalyzer, channels)

            cellanalyzer.process()
            n_images += 1
            images = []

            if self.settings('Processing', 'tracking'):
                region = self.settings('Tracking', 'tracking_regionname')
                samples = self.timeholder[frame][PrimaryChannel.NAME].get_region(region)
                self._tracker.track_next_frame(frame, samples)

                if self.settings('Tracking', 'tracking_visualization'):
                    size = cellanalyzer.getImageSize(PrimaryChannel.NAME)
                    nframes = self.settings('Tracking', 'tracking_visualize_track_length')
                    radius = self.settings('Tracking', 'tracking_centroid_radius')
                    img_conn, img_split = self._tracker.render_tracks(
                        frame, size, nframes, radius)
                    images += [(img_conn, '#FFFF00', 1.0),
                               (img_split, '#00FFFF', 1.0)]

            for clf in self.classifiers.itervalues():
                cellanalyzer.classify_objects(clf)

            ##############################################################
            # FIXME - part for browser
            if 0:
                self.render_browser(cellanalyzer)
            ##############################################################

            self.settings.set_section('General')
            # want emit all images at once
            imgs = {}
            imgs.update(self.render_classification_images(cellanalyzer, images, frame))
            imgs.update(self.render_contour_images(cellanalyzer, images, frame))
            msg = 'PL %s - P %s - T %05d' %(self.plate_id, self.position, frame)
            self.set_image(imgs, msg, 50)

            if self.settings('Output', 'rendering_channel_gallery'):
                self.render_channel_gallery(cellanalyzer, frame)

            if self.settings('Output', 'rendering_labels_discwrite'):
                cellanalyzer.exportLabelImages(self._labels_dir)

            self.logger.info(" - Frame %d, duration (ms): %3d" \
                                 %(frame, stopwatch.interim()*1000))
            cellanalyzer.purge(features=self.export_features)

        return n_images

    def render_channel_gallery(self, cellanalyzer, frame):
        for channel in cellanalyzer.virtual_channels.itervalues():
            chgal = ChannelGallery(channel, frame, self._channel_gallery_dir)
            chgal.make_gallery()

    def render_contour_images(self, ca, images, frame):
        images_ = dict()
        for region, render_par in self.settings.get2('rendering').iteritems():
            out_dir = join(self._images_dir, region)
            write = self.settings('Output', 'rendering_contours_discwrite')

            if region not in self.CHANNELS.keys():
                img, _ = ca.render(out_dir, dctRenderInfo=render_par,
                                       writeToDisc=write, images=images)


                images_[region] = img
            # gallery images are treated differenty
            else:
                ca.render(out_dir, dctRenderInfo=render_par, writeToDisc=True)
        return images_

    def render_classification_images(self, cellanalyzer, images, frame):
        images_ = dict()
        for region, render_par in self.settings.get2('rendering_class').iteritems():
            out_images = join(self._images_dir, region)
            write = self.settings('Output', 'rendering_class_discwrite')
            image, _ = cellanalyzer.render(out_images,
                                                 dctRenderInfo=render_par,
                                                 writeToDisc=write,
                                                 images=images)
            images_[region] = image
        return images_

    def render_browser(self, cellanalyzer):
        d = {}
        for name in cellanalyzer.get_channel_names():
            channel = cellanalyzer.get_channel(name)
            d[channel.strChannelId] = channel.meta_image.image
            self._myhack.show_image(d)

        channel_name, region_name = self._myhack._object_region
        channel = cellanalyzer.get_channel(channel_name)
        if channel.has_region(region_name):
            region = channel.get_region(region_name)
            coords = {}
            for obj_id, obj in region.iteritems():
                coords[obj_id] = obj.crack_contour
            self._myhack.set_coords(coords)
            
            
class PositionAnalyzerForBrowser(PositionCore):
    @property
    def _hdf_options(self):
        self.settings.set_section('Output')
        h5opts = {"hdf5_include_tracking": False,
                  "hdf5_include_events": False,
                  "hdf5_compression": False,
                  "hdf5_create": False,
                  "hdf5_reuse": False,
                  "hdf5_include_raw_images": False,
                  "hdf5_include_label_images": False,
                  "hdf5_include_features": False,
                  "hdf5_include_crack": False,
                  "hdf5_include_classification": False}

        return h5opts
    
    def __init__(self, *args, **kw):
        super(PositionAnalyzerForBrowser, self).__init__(*args, **kw)
        
    def setup_classifiers(self):
        sttg = self.settings
        # processing channel, color channel
        for p_channel, c_channel in self.ch_mapping.iteritems():
            self.settings.set_section('Processing')
            if sttg.get2(self._resolve_name(p_channel, 'classification')):
                sttg.set_section('Classification')
                clf_dir = sttg.get2(self._resolve_name(p_channel, 'classification_envpath'))
                if not os.path.exists(clf_dir):
                    continue
                clf = CommonClassPredictor(
                    clf_dir=clf_dir,
                    name=p_channel,
                    channels=self._channel_regions(p_channel),
                    color_channel=c_channel)
                clf.importFromArff()
                clf.loadClassifier()
                self.classifiers[p_channel] = clf
                
    def __call__(self):

        self.timeholder = TimeHolder(self.position, self._all_channel_regions,
                                     None,
                                     self.meta_data, self.settings,
                                     self._frames,
                                     self.plate_id,
                                     **self._hdf_options)


        stopwatch = StopWatch(start=True)
        ca = CellAnalyzer(timeholder=self.timeholder,
                          position = self.position,
                          create_images = True,
                          binning_factor = 1,
                          detect_objects = self.settings.get('Processing', 'objectdetection'))

        #self.setup_classifiers()
        #self.export_features = self.define_exp_features()
        self._analyze(ca)
        return ca

        
    
    def _analyze(self, cellanalyzer):
        n_images = 0
        stopwatch = StopWatch(start=True)
        crd = Coordinate(self.plate_id, self.position,
                         self._frames, list(set(self.ch_mapping.values())))
        print crd

        for frame, channels in self._imagecontainer( \
            crd, interrupt_channel=True, interrupt_zslice=True):

            if self.is_aborted():
                self.clear()
                return 0
            else:
                txt = 'T %d (%d/%d)' %(frame, self._frames.index(frame)+1,
                                       len(self._frames))
                self.update_status({'progress': self._frames.index(frame)+1,
                                    'text': txt,
                                    'interval': stopwatch.interim()})

            stopwatch.reset(start=True)
            cellanalyzer.initTimepoint(frame)
            self.register_channels(cellanalyzer, channels)

            cellanalyzer.process()

            self.setup_classifiers()


            for clf in self.classifiers.itervalues():
                try:
                    cellanalyzer.classify_objects(clf)
                    print 'classifying'
                    for label, obj in cellanalyzer.get_channel('Primary').get_region('primary').iteritems():
                        print label, obj.strHexColor
                except KeyError:
                    pass

         
                


        return n_images
    
    def clear(self):
        print 'Clean up'
