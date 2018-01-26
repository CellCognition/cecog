"""
analysis.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("PositionCore", "PositionAnalyzer")


import numpy as np

from os.path import join, basename, dirname
from collections import OrderedDict, defaultdict

from PyQt5.QtCore import QThread

from cecog.gui.preferences import AppPreferences
from cecog.io.imagecontainer import Coordinate
from cecog.plugin.metamanager import MetaPluginManager
from cecog.units.time import TimeConverter

from cecog.analyzer.tracker import Tracker
from cecog.analyzer.timeholder import TimeHolder
from cecog.analyzer.analyzer import CellAnalyzer
from cecog.analyzer.eventselection import EventSelection

from cecog.analyzer.channel import PrimaryChannel
from cecog.analyzer.channel import SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel
from cecog.analyzer.channel import MergedChannel

from cecog.classifier import SupportVectorClassifier

from cecog.logging import LoggerObject
from cecog.util.stopwatch import StopWatch
from cecog.util.ctuple import COrderedDict

from cecog.features import FEATURE_MAP
from cecog.io import Ch5File


class PositionCore(LoggerObject):

    PRIMARY_CHANNEL = PrimaryChannel.NAME
    SECONDARY_CHANNEL = SecondaryChannel.NAME
    TERTIARY_CHANNEL = TertiaryChannel.NAME
    MERGED_CHANNEL = MergedChannel.NAME

    CHANNELS = OrderedDict()
    CHANNELS['primary'] = PrimaryChannel
    CHANNELS['secondary'] = SecondaryChannel
    CHANNELS['tertiary'] = TertiaryChannel
    CHANNELS['merged'] = MergedChannel

    def __init__(self, plate_id, position, datafile, settings, frames,
                 sample_readers, sample_positions, learner,
                 image_container, layout, writelogs=False):
        super(PositionCore, self).__init__()

        self.datafile = datafile
        self.settings = settings
        self._imagecontainer = image_container
        self.plate_id = plate_id
        self.position = position
        self.layout = layout

        self._frames = frames # frames to process
        self._writelogs = writelogs
        self.sample_readers = sample_readers
        self.sample_positions = sample_positions
        self.learner = learner

        self._tracker = None
        self.timeholder = None
        self.classifiers = OrderedDict()

        self._tes = None

    def _analyze(self, *args, **kw):
        raise NotImplementedError

    def _posinfo(self):
        i = np.where(self.layout["File"]==self.position)[0][0]
        return self.layout["Well"][i], self.layout["Site"][i]

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
            if self.settings('General','process_%s' %prefix):
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
        fgroups = defaultdict(dict)

        for group, features in FEATURE_MAP.iteritems():
            if self.settings.get('FeatureExtraction',
                                 self._resolve_name(ch_name, group)):

                for feature, params in features.iteritems():

                    if params is not None:
                        for pname, value in params.iteritems():
                            # special case, same parameters for haralick features
                            if feature.startswith("haralick"):
                                option = "%s_%s" %(self._resolve_name(ch_name, pname), "haralick")
                            else:
                                option = "%s_%s" %(self._resolve_name(ch_name, pname), feature)

                            option = self.settings("FeatureExtraction", option)

                            if isinstance(value, (list, tuple)) and \
                               isinstance(option, basestring):
                                fgroups[feature][pname] = eval(option)
                            else:
                                fgroups[feature][pname] = option

                    else:
                        fgroups[feature] = params # = None

        return fgroups


    def setup_channel(self, proc_channel, col_channel, zslice_images,
                      check_for_plugins=True):

        if not proc_channel == 'Merged':
            # determine the list of features to be calculated from each object
            # and their parameters
            f_params = self.feature_params(proc_channel)
        else:
            # there are no feature parameter settings for the merged channel
            # as this is a simple concatennation of features from other channels
            f_params = None

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
                         strBackgroundImagePath = self.settings.get2(
                             '%s_flat_field_correction_image_dir' %proc_channel),
                         feature_groups = f_params,
                         check_for_plugins = check_for_plugins)

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
            if self.settings('General', 'process_%s' % name.lower()):
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
            if not chm[channel]:
                chm[channel] = None

        return chm

    def isAborted(self):

        # in case of multiprocessing
        try:
            return QThread.currentThread().is_aborted()
        except AttributeError:
            pass

    def interruptionPoint(self):
        # in case of multiprocessing
        try:
            QThread.currentThread().interruption_point()
        except AttributeError:
            pass

    def statusUpdate(self, *args, **kw):
        # in case of multiprocessing
        try:
            QThread.currentThread().statusUpdate(*args, **kw)
        except AttributeError:
            pass

    def setImage(self, images, message, stime=0):
        """Propagate a rendered image to QThread."""
        assert isinstance(images, dict)
        assert isinstance(message, basestring)

        thread = QThread.currentThread()
        if images:
            try:
                thread.show_image(images, message, stime)
            except AttributeError:
                pass


    def _channel_regions(self, p_channel):
        """Return a dict of of channel region pairs according to the classifier"""
        regions = COrderedDict()
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
            chreg[chname] = region
        return chreg


class PositionAnalyzer(PositionCore):

    def __init__(self, *args, **kw):
        super(PositionAnalyzer, self).__init__(*args, **kw)

        if not self.has_timelapse:
            self.settings.set('Processing', 'tracking', False)

        if self._writelogs:
            logfile = join(
                dirname(dirname(self.datafile)), "log", "%s.log" %self.position)
            self.add_file_handler(logfile, self.Levels.DEBUG)
        self.logger.setLevel(self.Levels.DEBUG)

    def setup_classifiers(self):
        sttg = self.settings

        # processing channel, color channel
        for p_channel, c_channel in self.ch_mapping.iteritems():
            self.settings.set_section('Processing')
            if sttg.get2(self._resolve_name(p_channel, 'classification')):
                chreg = self._channel_regions(p_channel)

                sttg.set_section('Classification')
                cpath = sttg.get2(self._resolve_name(p_channel, 'classification_envpath'))
                cpath = join(cpath, basename(cpath)+".hdf")
                svc = SupportVectorClassifier(
                    cpath, load=True, channels=chreg, color_channel=c_channel)
                svc.close()
                self.classifiers[p_channel] = svc

    @property
    def _transitions(self):
        try:
            transitions = np.array(
                eval(self.settings.get('EventSelection', 'labeltransitions')))
            transitions.reshape((-1, 2))
        except Exception as e:
            raise RuntimeError(("Make sure that transitions are of the form "
                                "'int, int' or '(int, int), (int, int)' i.e "
                                "2-int-tuple  or a list of 2-int-tuples"))

        return transitions

    def setup_eventselection(self, graph):
        """Setup the method for event selection."""

        opts = {'transitions': self._transitions,
                'backward_range': self._convert_tracking_duration('backwardrange'),
                'forward_range': self._convert_tracking_duration('forwardrange'),
                'max_in_degree': self.settings.get('EventSelection', 'maxindegree'),
                'max_out_degree': self.settings.get('EventSelection', 'maxoutdegree')}

        opts.update({'backward_labels': [int(i) for i in self.settings.get(
            'EventSelection', 'backwardlabels').split(',')],
                     'forward_labels': [int(i) for i in self.settings.get(
                         'EventSelection', 'forwardlabels').split(',')],
                     'backward_range_min': self.settings.get('EventSelection', 'backwardrange_min'),
                     'forward_range_min': self.settings.get('EventSelection', 'forwardrange_min'),
                     'backward_check': self._convert_tracking_duration('backwardCheck'),
                     'forward_check': self._convert_tracking_duration('forwardCheck')})
        es = EventSelection(graph, **opts)

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
                if name is self.MERGED_CHANNEL:
                    continue

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
                region_features[self._all_channel_regions[name].values()] = mftrs
                features[name] = region_features

        return features

    def save_tracks(self):
        """Save tracking data to hdf file"""
        self.logger.info("Save tracking data")
        self.timeholder.serialize_tracking(self._tracker.graph)

    def save_events(self):
        self.logger.info("Save Event data")
        self.timeholder.serialize_events(self._tes)

    def save_classification(self):
        """Save classlabels of each object to the hdf file."""
        # function works for supervised and unuspervised case
        for channels in self.timeholder.itervalues():
            for chname, classifier in self.classifiers.iteritems():
                holder = channels[chname].get_region(classifier.regions)
                if classifier.feature_names is None:
                    # special for unsupervised case
                    classifier.feature_names = holder.feature_names
                self.timeholder.save_classlabels(channels[chname],
                                                 holder, classifier)

    def __call__(self):

        thread = QThread.currentThread()
        well, site = self._posinfo()

        self.timeholder = TimeHolder(self.position, self._all_channel_regions,
                                     self.datafile,
                                     self.meta_data, self.settings,
                                     self._frames,
                                     self.plate_id,
                                     well, site,
                                     **self._hdf_options)

        self.settings.set_section('Tracking')
        self.setup_classifiers()

        # setup tracker
        if self.settings('Processing', 'tracking'):
            tropts = (self.settings('Tracking', 'tracking_maxobjectdistance'),
                      self.settings('Tracking', 'tracking_maxsplitobjects'),
                      self.settings('Tracking', 'tracking_maxtrackinggap'))
            self._tracker = Tracker(*tropts)

        stopwatch = StopWatch(start=True)
        ca = CellAnalyzer(timeholder=self.timeholder,
                          position = self.position,
                          create_images = True,
                          binning_factor = 1,
                          detect_objects = self.settings('Processing',
                                                         'objectdetection'))

        self.export_features = self.define_exp_features()
        self._analyze(ca)


        # invoke event selection
        if self.settings('Processing', 'eventselection') and \
           self.settings('Processing', 'tracking'):

            evchannel = self.settings('EventSelection', 'eventchannel')
            region = self.classifiers[evchannel].regions

            if  evchannel != PrimaryChannel.NAME or region != self.settings("Tracking", "region"):
                graph = self._tracker.clone_graph(self.timeholder, evchannel, region)
            else:
                graph = self._tracker.graph

            self._tes = self.setup_eventselection(graph)
            self.logger.info("Event detection")
            self._tes.find_events()
            if self.isAborted():
                return 0 # number of processed images

        # save all the data of the position, no aborts from here on
        # want all processed data saved
        if self.settings('Processing', 'tracking'):
            self.statusUpdate(text="Saving Tracking Data to cellh5...")
            self.save_tracks()

            if self.settings('Output', 'hdf5_include_events') and \
               self.settings('Processing', "eventselection"):
                self.statusUpdate(text="Saving Event Data to cellh5...")
                self.save_events()

            self.save_classification()
            self.timeholder.purge()

        try:
            n = len(self._frames)
            intval = stopwatch.stop()/n*1000
        except ZeroDivisionError:
            pass
        else:
            self.logger.info("%d images analyzed, %3d ms per image set" %(n, intval))

        self.clear()

        with Ch5File(self.datafile, mode="r+") as ch5:
            ch5.savePlateLayout(self.layout, self.plate_id)

    def clear(self):
        if self.timeholder is not None:
            self.timeholder.close_all()
        # close and remove handlers from logging object
        self.close()

    def _analyze(self, cellanalyzer):

        thread = QThread.currentThread()

        stopwatch = StopWatch(start=True)
        crd = Coordinate(self.plate_id, self.position,
                         self._frames, list(set(self.ch_mapping.values())))

        for frame, channels in self._imagecontainer( \
            crd, interrupt_channel=True, interrupt_zslice=True):

            self.interruptionPoint()
            txt = '%s, %s, T %d (%d/%d)' \
                  %(self.plate_id, self.position, frame,
                    self._frames.index(frame)+1, len(self._frames))

            self.statusUpdate(text=txt, interval=stopwatch.interim(), increment=True)

            stopwatch.reset(start=True)
            cellanalyzer.initTimepoint(frame)
            self.register_channels(cellanalyzer, channels)

            cellanalyzer.process()

            self.logger.debug(" - Frame %d, cellanalyzer.process (ms): %3d" \
                             %(frame, stopwatch.interval()*1000))

            images = []

            if self.settings('Processing', 'tracking'):
                apc = AppPreferences()
                region = self.settings('Tracking', 'region')
                samples = self.timeholder[frame][PrimaryChannel.NAME].get_region(region)
                self._tracker.track_next_frame(frame, samples)

                if apc.display_tracks:
                    size = cellanalyzer.getImageSize(PrimaryChannel.NAME)
                    img_conn, img_split = self._tracker.render_tracks(
                        frame, size, apc.track_length, apc.cradius)
                    images += [(img_conn, '#FFFF00', 1.0),
                               (img_split, '#00FFFF', 1.0)]

            self.logger.debug(" - Frame %d, Tracking (ms): %3d" \
                             %(frame, stopwatch.interval()*1000))

            # can't cluster on a per frame basis
            if self.settings("EventSelection", "supervised_event_selection"):
                for channel, clf in self.classifiers.iteritems():
                    cellanalyzer.classify_objects(clf, channel)

            self.logger.debug(" - Frame %d, Classification (ms): %3d" \
                             % (frame, stopwatch.interval()*1000))

            self.settings.set_section('General')
            # want emit all images at once

            imgs = {}
            imgs.update(self.render_classification_images(cellanalyzer, images, frame))
            imgs.update(self.render_contour_images(cellanalyzer, images, frame))
            msg = 'PL %s - P %s - T %05d' %(self.plate_id, self.position, frame)
            self.setImage(imgs, msg, 50)

            cellanalyzer.purge(features=self.export_features)
            self.logger.debug(" - Frame %d, duration (ms): %3d" \
                              %(frame, stopwatch.interim()*1000))


    def render_contour_images(self, ca, images, frame):
        images_ = dict()
        for region, render_par in self.settings.get2('rendering').iteritems():
            img = ca.render(dctRenderInfo=render_par, images=images)
            images_[region] = img

        return images_

    def render_classification_images(self, cellanalyzer, images, frame):
         images_ = dict()
         for region, render_par in self.settings.get2('rendering_class').iteritems():
             image = cellanalyzer.render(dctRenderInfo=render_par, images=images)
             images_[region] = image
         return images_
