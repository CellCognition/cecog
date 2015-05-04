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


import logging
import zlib
import base64
import csv
from os.path import join, exists
from collections import OrderedDict
from  matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_agg import FigureCanvasAgg

import h5py
import numpy

# only temporary
import pdb

from cellh5 import CH5Const, CH5File, CH5Position

from cecog import ccore
from cecog.colors import Colors
from cecog.util.stopwatch import StopWatch
from cecog.io.imagecontainer import Coordinate
from cecog.io.imagecontainer import MetaImage
from cecog.analyzer.channel import PrimaryChannel
from cecog.plugin.metamanager import MetaPluginManager
from cecog.analyzer.tracker import Tracker
from cecog.analyzer.object import ImageObject, ObjectHolder, Orientation, Region

from cecog.analyzer.feature_groups import FeatureGroups


def chunk_size(shape):
    """Helper function to compute chunk size for image data cubes."""
    c = shape[0]
    t = 1
    z = 1
    y = shape[3] / 4
    x = shape[4] / 4
    return (c, t, z, y, x)

def max_shape(shape):
    """Helper function to compute chunk size for image data cubes."""
    c = 8 # 8 is kind of arbitrary, but better than None to help h5py to reserve the space
    t = shape[1]
    z = 1
    y = shape[3]
    x = shape[4]
    return (c, t, z, y, x)


class TimeHolder(OrderedDict):

    # label for unlabled objects
    UNPREDICTED_LABEL = CH5Const.UNPREDICTED_LABEL
    UNPREDICTED_PROB = CH5Const.UNPREDICTED_PROB

    HDF5_GRP_DEFINITION = "definition"
    HDF5_GRP_RELATION = "relation"
    HDF5_GRP_IMAGE = "image"
    HDF5_GRP_TIME = "time_lapse"
    HDF5_GRP_ZSLICE = "zslice"
    HDF5_GRP_OBJECT = "object"
    HDF5_OTYPE_RELATION = 'relation'
    HDF5_GRP_FEATURE = "feature"
    HDF5_GRP_FEATURE_SET = "feature_set"
    HDF5_GRP_CLASSIFICATION = "classification"
    HDF5_GRP_ANNOTATION = "annotation"
    HDF5_GRP_CLASSIFIER = "classifier"
    HDF5_GRP_REGION = "region"
    HDF5_NAME_ID = "id"
    HDF5_NAME_EDGE = "edge"
    HDF5_ATTR_DESCRIPTION = "description"
    HDF5_OTYPE_REGION = 'region'
    HDF5_OTYPE_OBJECT = 'object'

    HDF5_DTYPE_RELATION = \
         numpy.dtype([('obj_idx1', 'uint32'),
                      ('obj_idx2', 'uint32'),])

    HDF5_DTYPE_TERMINAL_RELATION = \
         numpy.dtype([('obj_id1', 'uint32'),
                      ('obj_idx1', 'uint32', 2),
                      ('obj_id2', 'uint32'),
                      ('obj_idx2', 'uint32', 2),])

    HDF5_DTYPE_EDGE = \
        numpy.dtype([('obj_id', 'uint32'),
                     ('idx1', 'uint32'),
                     ('idx2', 'uint32'),
                     ])

    HDF5_DTYPE_ID = \
        numpy.dtype([('obj_id', 'uint32'),
                     ('edge_idx1', 'uint32'),
                     ('edge_idx2', 'uint32'),])

    def __init__(self, P, channel_regions, filename_hdf5, meta_data, settings,
                 analysis_frames, plate_id,
                 hdf5_create=True, hdf5_reuse=True, hdf5_compression='gzip',
                 hdf5_include_raw_images=True,
                 hdf5_include_label_images=True, hdf5_include_features=True,
                 hdf5_include_classification=True, hdf5_include_crack=True,
                 hdf5_include_tracking=True, hdf5_include_events=True,
                 hdf5_include_annotation=True):
        super(TimeHolder, self).__init__()
        try:
            import pydevd
            pydevd.connected = True
            pydevd.settrace(suspend=False)
            print 'Thread enabled interactive eclipse debuging...'
        except:
            pass
        self.P = P
        self.plate_id = plate_id
        self._iCurrentT = None
        self.channel_regions = channel_regions
        self._meta_data = meta_data
        self._settings = settings
        self._analysis_frames = analysis_frames
        self.reginfo = MetaPluginManager().region_info

        self._hdf5_create = hdf5_create
        self._hdf5_include_raw_images = hdf5_include_raw_images
        self._hdf5_include_label_images = hdf5_include_label_images
        self._hdf5_include_features = hdf5_include_features
        self._hdf5_include_classification = hdf5_include_classification
        self._hdf5_include_crack = hdf5_include_crack
        self._hdf5_include_tracking = hdf5_include_tracking
        self._hdf5_include_events = hdf5_include_events
        self._hdf5_include_annotation = hdf5_include_annotation
        self._hdf5_compression = hdf5_compression
        self._hdf5_reuse = hdf5_reuse

        self._hdf5_features_complete = False
        self.hdf5_filename = filename_hdf5

        self.minimal_effort = False
        try:
            # minimal_effort is read from the settings
            self.minimal_effort = self._settings.get('Output', 'minimal_effort') and self._hdf5_reuse
        except:
            # for backwards compatibility
            self.minimal_effort = False

        self._logger = logging.getLogger(self.__class__.__name__)
        frames = sorted(analysis_frames)
        all_frames = meta_data.get_frames_of_position(self.P)
        self._frames_to_idx = dict([(f, i) for i, f in enumerate(all_frames)])
        self._idx_to_frames = dict([(i ,f) for i, f in enumerate(all_frames)])
        self._object_coord_to_id = {}
        self._object_coord_to_idx = {}

        channels = sorted(list(meta_data.channels))
        self._region_names = []

        self._region_names = self.reginfo.names['primary'] + \
            self.reginfo.names['secondary'] + \
            self.reginfo.names['tertiary']

        if len(self.reginfo.names['merged']):
            self._region_names.append(str(self.reginfo.names['merged']))

        self._channel_info = OrderedDict()
        self._region_infos = []
        region_names2 = []

        for prefix in self.channel_regions.keys():
            for name in self.reginfo.names[prefix.lower()]:
                self._channel_info[prefix.lower()] = \
                    settings.get('ObjectDetection', '%s_channelid' %prefix)
                self._region_infos.append((prefix.lower(),
                                           self._convert_region_name(prefix.lower(), name),
                                           name))
                region_names2.append((prefix.capitalize(), name))

        self._feature_to_idx = OrderedDict()

        self._hdf5_found = False
        if self.hdf5_filename is not None and exists(self.hdf5_filename):
            if self._hdf5_check_file():
                self._hdf5_found = True
                if self._hdf5_prepare_reuse() > 0:
                    self._hdf5_found = False

        self._regions_to_idx = dict([(n,i) for i, n in enumerate(self._region_names)])

        _cmap = dict()
        self._channels_to_idx = OrderedDict()
        for i, (k, v) in enumerate(self._channel_info.iteritems()):
            if not _cmap.has_key(v):
                _cmap[v] = len(_cmap)
            self._channels_to_idx[k] = _cmap[v]

        self._regions_to_idx2 = OrderedDict([(n,i) for i, n in enumerate(region_names2)])

        if self._hdf5_create:
            label_image_cpy = None
            label_image_str = None
            label_image_valid = None

            raw_image_cpy = None
            raw_image_str = None
            raw_image_valid = None

            feature_dict=None
            object_dict=None

            if self._hdf5_found and self._hdf5_reuse:
                # file already there AND opened
                try:
                    feature_dict = {}
                    object_dict = {}
                    self._grp_cur_position[self.HDF5_GRP_IMAGE]
                    # check if label images are there and if reuse is enabled
                    if 'region' in self._grp_cur_position[self.HDF5_GRP_IMAGE]:
                        label_image_cpy = self._grp_cur_position[self.HDF5_GRP_IMAGE]['region'].value
                        label_image_valid = self._grp_cur_position[self.HDF5_GRP_IMAGE]['region'].attrs['valid']
                        label_image_str = self._grp_cur_position[self.HDF5_GRP_IMAGE].name + '/region'

                    if 'channel' in self._grp_cur_position[self.HDF5_GRP_IMAGE]:
                        raw_image_cpy = self._grp_cur_position[self.HDF5_GRP_IMAGE]['channel'].value
                        raw_image_valid = self._grp_cur_position[self.HDF5_GRP_IMAGE]['channel'].attrs['valid']
                        raw_image_str = self._grp_cur_position[self.HDF5_GRP_IMAGE].name + '/channel'

                    for region in self._grp_cur_position[self.HDF5_GRP_FEATURE]:
                        region_grp = self._grp_cur_position[self.HDF5_GRP_FEATURE][region]
                        object_grp = self._grp_cur_position[self.HDF5_OTYPE_OBJECT][region]
                        for obj_feat in ["object_features", "crack_contour",
                                         "center", "bounding_box", "orientation"]:
                            if obj_feat in region_grp:
                                key_data = region_grp.name + "/" + obj_feat
                                value_data = region_grp[obj_feat].value


                                key_desc = self._grp_def[self.HDF5_GRP_FEATURE][region][obj_feat].name
                                value_desc = self._grp_def[self.HDF5_GRP_FEATURE][region][obj_feat].value

                                feature_dict[(key_desc, key_data)] = (value_desc, value_data)

                        key_data = object_grp.name
                        value_data = object_grp.value


                        key_desc = self._grp_def[self.HDF5_OTYPE_OBJECT][region].name
                        value_desc = self._grp_def[self.HDF5_OTYPE_OBJECT][region].value

                        object_dict[(key_desc, key_data)] = (value_desc, value_data)



                except Exception as e:
                    print 'Loading of Hdf5 failed... '
                    self._logger.info('Loading of Hdf5 failed... ')
                    self._hdf5_reuse = False
                    label_image_cpy = None
                    label_image_str = None
                    label_image_valid = None

                    raw_image_cpy = None
                    raw_image_str = None
                    raw_image_valid = None

                    feature_dict=None
                    object_dict=None

            self._hdf5_create_file_structure(self.hdf5_filename, (label_image_str, label_image_cpy, label_image_valid),
                                                                 (raw_image_str, raw_image_cpy, raw_image_valid), feature_dict, object_dict)

            self._hdf5_write_global_definition()

    def get_well_position(self):
        meta_data = self._meta_data

        # Check for being wellbased or old style (B01_03 vs. 0037)
        if meta_data.has_well_info:
            well, subwell = meta_data.get_well_and_subwell(self.P)
            position = str(subwell)
        else:
            well = "0"
            position = self.P
        return well, position

    def _hdf5_prepare_reuse(self):
        self.cellh5_file = CH5File(self.hdf5_filename, 'r')
        self._hdf5_file = self.cellh5_file.get_file_handle()
        try:
            well, position = self.get_well_position()


            self._grp_cur_position = self._hdf5_file['/sample/0/plate/%s/experiment/%s/position/%s' % (self.plate_id,
                                                                                                       well,
                                                                                                       position)]
            self._grp_def = self._hdf5_file[self.HDF5_GRP_DEFINITION]
            return 0
        except:
            self.cellh5_file.close()
            return 1

    def _hdf5_check_file(self):
        try:
            f = h5py.File(self.hdf5_filename, 'r')
        except:
            return False

        try:
            meta_data = self._meta_data
            # Check for being wellbased or old style (B01_03 vs. 0037)
            if meta_data.has_well_info:
                well, subwell = meta_data.get_well_and_subwell(self.P)
                position = str(subwell)
            else:
                well = "0"
                position = self.P

            label_image_str = '/sample/0/plate/%s/experiment/%s/position/%s/%s/region' % (self.plate_id,
                                                                                      well,
                                                                                      position,
                                                                                      self.HDF5_GRP_IMAGE)

            raw_image_str = '/sample/0/plate/%s/experiment/%s/position/%s/%s/channel' % (self.plate_id,
                                                                                      well,
                                                                                      position,
                                                                                      self.HDF5_GRP_IMAGE)
            # we check if the label image and raw image are in the cellh5 file
            if label_image_str in f and raw_image_str in f:
                return True
            else:
                # if this is not the case, we would return False unless
                # minimal_effort is set to True (in which case we might not need the segmentation)
                return self.minimal_effort
                #return False
        except:
            return False
        finally:
            f.close()

    def _hdf5_write_global_definition(self):

        # global channel description
        dtype = numpy.dtype([('channel_name', '|S50'),
                             ('description', '|S100'),
                             ('is_physical', bool),
                             ('voxel_size', 'float', 3),
                             ('color', "|S7")])

        nr_channels = len(self._channel_info)
        global_channel_desc = self._grp_def[self.HDF5_GRP_IMAGE].create_dataset( \
            'channel', (nr_channels,), dtype)

        for i, (ch, col) in enumerate(self._channel_info.iteritems()):
            is_physical = bool(col is not None)
            data = (ch, col, is_physical, (0, 0, 0), Colors.channel_hexcolor(col))
            global_channel_desc[i] = data

        # global region description
        dtype = numpy.dtype([('region_name', '|S50'), ('channel_idx', 'i')])
        nr_labels = len(self._region_infos)
        global_region_desc = self._grp_def[self.HDF5_GRP_IMAGE].create_dataset(\
            self.HDF5_GRP_REGION, (nr_labels,), dtype)

        for tpl in self._region_infos:
            channel_name, combined, region_name = tpl
            idx = self._regions_to_idx2[(channel_name.title(), region_name)]
            channel_idx = self._channels_to_idx[channel_name]
            global_region_desc[idx] = (combined, channel_idx)

        # time-lapse definition
        # global definition
        if self._meta_data.has_timelapse:
            var = self._grp_def[self.HDF5_GRP_IMAGE].create_dataset(self.HDF5_GRP_TIME,
                                        (3,), '|S12')
            var[:] = ['frame', 'timestamp_abs', 'timestamp_rel']

            # actual values
            dtype = numpy.dtype([('frame', 'i'), ('timestamp_abs', 'i'),
                                 ('timestamp_rel', 'i')])
            frames = sorted(self._analysis_frames)
            all_frames = sorted(self._meta_data.get_frames_of_position(self.P))
            nr_frames = len(all_frames)
            var = self._grp_cur_position[self.HDF5_GRP_IMAGE].create_dataset(self.HDF5_GRP_TIME,
                                        (nr_frames,), dtype,
                                        chunks=(nr_frames,),
                                        compression=self._hdf5_compression)
            for frame in all_frames:
                idx = self._frames_to_idx[frame]
                coord = Coordinate(position=self.P, time=frame)
                ts_abs = self._meta_data.get_timestamp_absolute(coord)
                ts_rel = self._meta_data.get_timestamp_relative(coord)
                var[idx] = (frame, ts_abs, ts_rel)

        ### global object definition
        # add the basic regions
        global_object_dtype = numpy.dtype([('name', '|S512'), ('type', '|S512'), ('source1', '|S512'), ('source2', '|S512')])

        for channel_name, combined, region_name in self._region_infos:
            obj_name = self._convert_region_name(channel_name, region_name, prefix='')
            if obj_name not in self._grp_def[self.HDF5_GRP_OBJECT]:
                global_object_desc = self._grp_def[self.HDF5_GRP_OBJECT].create_dataset(obj_name, (1,), global_object_dtype)
                global_object_desc[0] = (obj_name, self.HDF5_OTYPE_REGION, '', '')

        # add basic relation objects (primary -> secondary etc)
        prim_obj_name = self._convert_region_name(self._region_infos[0][0], self._region_infos[0][2], prefix='')
        for channel_name, combined, region_name in self._region_infos[1:]:
            # relation between objects from different regions
            # (in cecog 1:1 from primary only)
            if channel_name != PrimaryChannel.PREFIX:
                obj_name = self._convert_region_name(channel_name, region_name, prefix='')
                obj_name = '%s___to___%s' % (prim_obj_name, obj_name)
                global_object_desc = self._grp_def[self.HDF5_GRP_OBJECT].create_dataset(obj_name, (1,), global_object_dtype)
                global_object_desc[0] =  (obj_name, self.HDF5_OTYPE_RELATION,
                                          prim_obj_name,
                                          obj_name)

        # relations for virtual channels
        for channel_name, combined, region_name in self._virtual_region_infos():
            obj_name = self._convert_region_name(channel_name, region_name, prefix='')

            chreg = self.channel_regions[channel_name.title()]
            dtype = [('name', 'S512'), ('type', 'S512')]
            dtype += [('region%d' %i, 'S512') for i in range(len(chreg))]

            dset = self._grp_def[self.HDF5_GRP_OBJECT].create_dataset( \
                obj_name, (1,), numpy.dtype(dtype))

            data = (obj_name, self.HDF5_OTYPE_RELATION)
            for ch, reg in chreg.iteritems():
                data += (("%s__%s" %(ch, reg)).lower(), )
            dset[0] = data

        # add special relation objects (events, tracking, etc)
        if self._hdf5_include_tracking:
            obj_name = 'tracking'
            global_object_desc = self._grp_def[self.HDF5_GRP_OBJECT].create_dataset(obj_name, (1,), global_object_dtype)
            global_object_desc[0] = (obj_name, self.HDF5_OTYPE_RELATION, prim_obj_name, prim_obj_name)

        if self._hdf5_include_events:
            obj_name = 'event'
            global_object_desc = self._grp_def[self.HDF5_GRP_OBJECT].create_dataset(obj_name, (1,), global_object_dtype)
            global_object_desc[0] = (obj_name, self.HDF5_OTYPE_OBJECT, prim_obj_name, prim_obj_name)

    def _virtual_region_infos(self):
        """Return a tuple of channel name (lower case), combined identifier
        and region name as for virtual channels, as it is stored in
        self._region_info.
        """
        chnames = [rinfo[0] for rinfo in self._region_infos]

        for channel_name, regions in self.channel_regions.iteritems():
            if channel_name.lower() not in chnames:
                combined = "region__%s__%s" %(channel_name.lower(), regions.values())
                yield channel_name.lower(), combined, '-'.join(regions.values())

        raise StopIteration

    def _hdf5_create_file_structure(self, filename, label_info=(None, None, None), raw_info=(None, None, None), feature_dict=None, object_dict=None):
        label_image_str, label_image_cpy, label_image_valid = label_info
        raw_image_str, raw_image_cpy, raw_image_valid = raw_info

        if hasattr(self, "cellh5_file") and self.cellh5_file is not None:
            try:
                self.cellh5_file.close()
            except:
                print '_hdf5_create_file_structure(): Closing already opended file for rewrite'

        # TODO: This should be replaced with cellh5 API functions
        f = h5py.File(filename, 'w')
        self._hdf5_file = f

        grp_sample = f.create_group('sample')
        grp_cur_sample = grp_sample.create_group('0')
        grp_plate = grp_cur_sample.create_group('plate')
        grp_cur_plate = grp_plate.create_group(self.plate_id)

        meta_data = self._meta_data

        # Check for being wellbased or old style (B01_03 vs. 0037)
        if meta_data.has_well_info:
            well, subwell = meta_data.get_well_and_subwell(self.P)
            position = str(subwell)
        else:
            well = "0"
            position = self.P
        grp_experiment = grp_cur_plate.create_group('experiment')
        grp_cur_experiment = grp_experiment.create_group(well)
        grp_position = grp_cur_experiment.create_group('position')
        grp_cur_position = grp_position.create_group(position)

        self._grp_cur_position = grp_cur_position

        self._grp_cur_position.create_group(self.HDF5_GRP_IMAGE)
        self._grp_cur_position.create_group(self.HDF5_GRP_FEATURE)
        self._grp_cur_position.create_group(self.HDF5_GRP_OBJECT)

        self._grp_def = f.create_group(self.HDF5_GRP_DEFINITION)

        self._grp_def.create_group(self.HDF5_GRP_IMAGE)
        self._grp_def.create_group(self.HDF5_GRP_FEATURE)
        self._grp_def.create_group(self.HDF5_GRP_OBJECT)

        if label_image_cpy is not None:
            self._hdf5_file.create_dataset(label_image_str,
                                           label_image_cpy.shape,
                                           'uint16',
                                           chunks=chunk_size(label_image_cpy.shape),
                                           data=label_image_cpy,
                                           maxshape=max_shape(label_image_cpy.shape),
                                           compression=self._hdf5_compression)
            self._hdf5_file[label_image_str].attrs['valid'] = label_image_valid

            if self._hdf5_file[label_image_str].shape[0] != len(self._regions_to_idx):
                self._hdf5_file[label_image_str].resize(len(self._regions_to_idx), axis=0)


        if raw_image_cpy is not None:
            self._hdf5_file.create_dataset(raw_image_str,
                                           raw_image_cpy.shape,
                                           'uint8',
                                           chunks=chunk_size(raw_image_cpy.shape),
                                           data=raw_image_cpy,
                                           maxshape=max_shape(raw_image_cpy.shape),
                                           compression=self._hdf5_compression)
            self._hdf5_file[raw_image_str].attrs['valid'] = raw_image_valid

            if self._hdf5_file[raw_image_str].shape[0] != len(self._regions_to_idx):
                self._hdf5_file[raw_image_str].resize(len(self._regions_to_idx), axis=0)

        if feature_dict is not None:
            if object_dict is not None:
                for (key_desc, key_data), (value_desc, value_data) in feature_dict.items():
                    self._hdf5_file.create_dataset(key_desc, data=value_desc, compression=self._hdf5_compression)
                    if not value_data.dtype == numpy.dtype('O'):
                        d = self._hdf5_file.create_dataset(key_data, data=value_data, compression=self._hdf5_compression)
                        d.attrs["reused"] = True
                    else:
                        d = self._hdf5_file.create_dataset(key_data, data=value_data, compression=self._hdf5_compression, dtype=h5py.new_vlen(str))
                        d.attrs["reused"] = True

                for (key_desc, key_data), (value_desc, value_data) in object_dict.items():
                    d = self._hdf5_file.create_dataset(key_desc, data=value_desc, compression=self._hdf5_compression)
                    d.attrs["reused"] = True
                    d = self._hdf5_file.create_dataset(key_data, data=value_data, compression=self._hdf5_compression)
                    d.attrs["reused"] = True




        self.cellh5_file = CH5File(self._hdf5_file)

    def close_all(self):
        try:
            self.cellh5_file.close()
        except:
            pass

    def initTimePoint(self, iT):
        # HDF5 feature definition is complete after first frame
        if not self._iCurrentT is None:
            self._hdf5_features_complete = True
        self._iCurrentT = iT

    def getCurrentTimePoint(self):
        return self._iCurrentT

    def getCurrentChannels(self):
        return self[self._iCurrentT]

    def purge_features(self):
        for channels in self.itervalues():
            for channel in channels.itervalues():
                channel.purge(features={})

    def _convert_region_name(self, channel_name, region_name, prefix='region'):
        s = '%s__%s' % (channel_name.lower(), region_name)
        if not prefix is None and len(prefix) > 0:
            s = '%s___%s' % (prefix, s)
        return s

    def _convert_feature_name(self, feature_name, channel_name, region_name):
        return '__'.join([feature_name, channel_name, region_name])

    # isn't it add channel
    def apply_channel(self, channel):
        iT = self._iCurrentT
        if not iT in self:
            self[iT] = OrderedDict()
        self[iT][channel.NAME] = channel

    def hdf_channel_frame_valid(self):
        try:
            frame_idx = self._frames_to_idx[self._iCurrentT]
            if self._grp_cur_position[self.HDF5_GRP_IMAGE]['channel'].attrs['valid'][frame_idx]:
                return True
        except:
            pass
        return False

    def apply_segmentation(self, channel, *args):
        stop_watch = StopWatch(start=True)

        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)

        channel_name = channel.NAME.lower()
        label_images_valid = False
        if self._hdf5_found and self._hdf5_reuse:
            ### Try to load them
            frame_idx = self._frames_to_idx[self._iCurrentT]
            for region_name in self.reginfo.names[channel_name]:
                if 'region' in self._grp_cur_position[self.HDF5_GRP_IMAGE]:
                    dset_label_image = self._grp_cur_position[self.HDF5_GRP_IMAGE]['region']
                    frame_valid = dset_label_image.attrs['valid'][frame_idx]
                    if frame_valid:
                        region_idx = self._regions_to_idx2[(channel.NAME, region_name)]
                        if not (region_idx < dset_label_image.shape[0]):
                            label_images_valid = False
                            break
                        image_data = dset_label_image[region_idx, frame_idx, 0, :, :].astype('int16')
                        img_label = ccore.numpy_to_image(image_data, copy=True)
                        img_xy = channel.meta_image.image
                        container = ccore.ImageMaskContainer(img_xy, img_label, False, True, True)
                        channel.containers[region_name] = container
                        label_images_valid = True
                    else:
                        label_images_valid = False
                        break
                else:
                    label_images_valid = False
                    break

        if label_images_valid:
            self._logger.info('Label images %s loaded from hdf5 file in %s.'
                              % (desc, stop_watch.interim()))

        # only True if hdf_create and reuse and label_images are valid!
        if not label_images_valid:

            # in this case, we do not necessarily calculate a segmentation
            # this is not ideal if the data is to be browsed.
            if self.minimal_effort:
                self._logger.info('No segmentation calculated or loaded for %s (overhead: %s)'
                                  % (desc, stop_watch.interim()))
                for region_name in self.reginfo.names[channel_name]:
                    channel.containers[region_name] = None
            else:
                # compute segmentation (not loading from file)
                channel.apply_segmentation(*args)

                self._logger.info('Label images %s computed in %s.'
                              %(desc, stop_watch.interim()))
                # write segmentation back to file
                if self._hdf5_create and self._hdf5_include_label_images:
                    meta = self._meta_data
                    w = meta.real_image_width
                    h = meta.real_image_height

                    # CellCognition is always working on one z-slice for know and thus saves only one
                    #z = meta.dim_z
                    z = 1

                    t = len(self._frames_to_idx)
                    var_name = 'region'
                    grp = self._grp_cur_position[self.HDF5_GRP_IMAGE]
                    # create new group if it does not exist yet!
                    if var_name in grp and grp[var_name].shape[0] == len(self._regions_to_idx2):
                        var_labels = grp[var_name]
                    else:
                        nr_labels = len(self._regions_to_idx2)
                        var_labels = \
                            grp.create_dataset(var_name,
                                               (nr_labels, t, z, h, w),
                                               'uint16',
                                               chunks=chunk_size((nr_labels, t, z, h, w)),
                                               compression=self._hdf5_compression)
                        var_labels.attrs['valid'] = numpy.zeros(t)

                    frame_idx = self._frames_to_idx[self._iCurrentT]
                    for region_name in self.reginfo.names[channel_name]:
                        if channel.is_virtual():
                            continue
                        idx = self._regions_to_idx2[(channel.NAME, region_name)]
                        container = channel.containers[region_name]
                        array = container.img_labels.toArray(copy=False)
                        var_labels[idx, frame_idx, 0] = numpy.require(array, 'uint16')
                        ### Workaround... h5py attributes do not support transparent list types...
                        tmp = var_labels.attrs['valid']
                        tmp[frame_idx] = 1
                        var_labels.attrs['valid'] = tmp
        return

    def prepare_raw_image(self, channel):
        if channel.is_virtual():
            # no raw image in a merged channel
            return

        stop_watch = StopWatch(start=True)
        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)
        frame_valid = False
        if self._hdf5_found and self._hdf5_reuse:
            if 'channel' in self._grp_cur_position[self.HDF5_GRP_IMAGE]:
                frame_idx = self._frames_to_idx[self._iCurrentT]
                dset_raw_image = self._grp_cur_position[self.HDF5_GRP_IMAGE]['channel']
                frame_valid = dset_raw_image.attrs['valid'][frame_idx]
                if frame_valid:
                    # Double check if image_data contains data
                    coordinate = Coordinate(position=self.P, time=self._iCurrentT,
                                    channel=channel.strChannelId, zslice=1)
                    meta_image = MetaImage(image_container=None, coordinate=coordinate)
                    channel_idx = self._channels_to_idx[channel.PREFIX]
                    if not (channel_idx < dset_raw_image.shape[0]):
                        frame_valid = False

        if self._hdf5_found and frame_valid:
            coordinate = Coordinate(position=self.P, time=self._iCurrentT,
                                    channel=channel.strChannelId, zslice=1)
            meta_image = MetaImage(image_container=None, coordinate=coordinate)
            channel_idx = self._channels_to_idx[channel.PREFIX]

            img = ccore.numpy_to_image(dset_raw_image[channel_idx, frame_idx, 0, :, :], copy=True)
            meta_image.set_image(img)
            meta_image.set_raw_image(img)
            channel.meta_image = meta_image
            self._logger.info('Raw image %s loaded from hdf5 file in %s.'
                              % (desc, stop_watch.interim()))
        else:
            channel.apply_zselection()
            channel.normalize_image(self.plate_id)
            channel.apply_registration()
            self._logger.info('Raw image %s prepared in %s.' % (desc, stop_watch.interim()))

            if self._hdf5_create and self._hdf5_include_raw_images:
                meta = self._meta_data
                w = meta.real_image_width
                h = meta.real_image_height

                # CellCognition is always working on one z-slice for know and thus saves only one
                # z = meta.dim_z
                z = 1

                t = len(self._frames_to_idx)
                ncolors = len(set(self._channels_to_idx.values()))
                var_name = 'channel'
                grp = self._grp_cur_position[self.HDF5_GRP_IMAGE]
                if var_name in grp:
                    var_images = grp[var_name]
                else:
                    var_images = \
                        grp.create_dataset(var_name,
                                           (ncolors, t, z, h, w),
                                           'uint8',
                                           chunks=chunk_size((ncolors, t, z, h, w)),
                                           compression=self._hdf5_compression)
                    var_images.attrs['valid'] = numpy.zeros(t)

                frame_idx = self._frames_to_idx[self._iCurrentT]
                channel_idx = self._channels_to_idx[channel.PREFIX]
                img = channel.meta_image.image
                array = img.toArray(copy=False)
                var_images[channel_idx, frame_idx, 0] = array
                tmp = var_images.attrs['valid']
                tmp[frame_idx] = 1
                var_images.attrs['valid'] = tmp
                self._logger.info('Raw image %s written to hdf5 file.' % desc)

    def _get_feature_group(self):
        grp_object_features = self._grp_cur_position.require_group(self.HDF5_GRP_FEATURE)
        return grp_object_features

    def _apply_features_from_hdf5(self, channel):
        channel._features_calculated = True
        channel_name = channel.NAME.lower()
        for region_name, container in channel.containers.iteritems():
            well, position = self.get_well_position()
            frame_idx = self._frames_to_idx[self._iCurrentT]

            combined_region_name = self._convert_region_name(channel_name, region_name, '')

            cur_pos = self.cellh5_file.get_position(well, position)

            # cast to tuple to enable cashing
            current_object_idx = tuple(cur_pos.get_object_idx(combined_region_name, frame_idx))

            object_holder = ObjectHolder(region_name)

            object_features = cur_pos.get_object_features(combined_region_name, current_object_idx)

            object_feature_names = list(self.cellh5_file.object_feature_def(combined_region_name))
            try:
                eccentricity_idx = self.cellh5_file.get_object_feature_idx_by_name(combined_region_name, 'eccentricity')
            except ValueError:
                eccentricity_idx = None

            try:
                crack_contours = cur_pos.get_crack_contour(current_object_idx, combined_region_name, bb_corrected=False)
            except:
                crack_contours = None

            if not container is None:
                # in this case a container is present (segmentation and images have been found/computed)
                for j, (obj_id, c_obj) in enumerate(container.getObjects().iteritems()):
                    # build a new ImageObject
                    obj = ImageObject(c_obj)
                    obj.iId = obj_id
                    if len(crack_contours) > 0:
                        obj.crack_contour = crack_contours[j]
                    else:
                        # Fallback if cracks are not safed in cellh5
                        ul = obj.oRoi.upperLeft
                        crack = [(pos[0] + ul[0], pos[1] + ul[1])
                                 for pos in
                                 container.getCrackCoordinates(obj_id)]
                        obj.crack_contour = crack

                    if 'moments' in channel.lstFeatureCategories and eccentricity_idx is not None:
                        obj.orientation = Orientation(angle = c_obj.orientation,
                                                      eccentricity = object_features[j, eccentricity_idx])

                    # assign feature values in sorted order as NumPy array
                    obj.aFeatures = object_features[j, :]
                    object_holder[obj_id] = obj

                channel.lstFeatureNames = object_feature_names
                object_holder.feature_names = channel.lstFeatureNames

            elif len(object_feature_names) > 0 and object_features.shape[1] == len(object_feature_names):
                # TODO: additional check whether features are in the cellh5 file

                # in this case, we would take the values from the cellh5 file
                orientation = cur_pos.get_orientation(current_object_idx, combined_region_name)
                bounding_box = cur_pos.get_bounding_box(current_object_idx, combined_region_name)
                center = cur_pos.get_center(current_object_idx, combined_region_name)

                # get_object_feature_by_name gives back all feature values for the specified feature (for all timepoints)
                #bounding_box = cur_pos.get_object_feature_by_name("bounding_box")
                #center = cur_pos.get_object_feature_by_name("center")

                # loop over detected objects
                for j, index in enumerate(current_object_idx):

                    # label of the object (corresponding to the label value in the label image)
                    obj_id = cur_pos.get_obj_label_id(index)

                    bb = bounding_box[j]
                    #ul = (bb[0], bb[1])
                    #lr = (bb[0] + bb[2], bb[1] + bb[3])
                    c = center[j]

                    # region
                    reg = Region(tplCoords=(bb[0], bb[2], bb[1], bb[3]))

                    # build object
                    obj = ImageObject(iId = obj_id)
                    obj.oRoi = reg
                    obj.oCenterAbs = c

                    # if crack contours are saved in the cellh5, we read them.
                    # otherwise, we would just leave this None.
                    if not crack_contours is None and len(crack_contours) > 0:
                        obj.crack_contour = crack_contours[j]

                    # set orientation
                    if eccentricity_idx is not None:
                        obj.orientation = Orientation(angle = orientation[j],
                                                      eccentricity = object_features[j, eccentricity_idx])

                    # assign feature values in sorted order as NumPy array
                    obj.aFeatures = object_features[j, :]
                    object_holder[obj_id] = obj

                channel.lstFeatureNames = object_feature_names
                object_holder.feature_names = channel.lstFeatureNames

            else:
                print 'no features found in cellh5 file'
            channel._regions[region_name] = object_holder

    def _write_object_feature_table(self, feature_names, global_def_group):
        n_feature_groups = len(FeatureGroups)
        n_features = len(feature_names)
        feature_dtype = [('name', '|S256')] + [('group_%02d' % i, '|S256') for i in range(n_feature_groups)]
        dset_tmp = global_def_group.create_dataset('object_features', (n_features, ), feature_dtype)

        assign_table = numpy.zeros((n_features, ), feature_dtype)

        for i, f in enumerate(feature_names):
            assign_table[i][0] = f
            for j in range(n_feature_groups):
                assign_table[i][j+1] = CH5Const.NOT_DEFINED

        for j, feat_name in enumerate(feature_names):
            for i, feat_group_name in enumerate(FeatureGroups):
                for feat_group_assignment in FeatureGroups[feat_group_name]:
                    if feat_name in FeatureGroups[feat_group_name][feat_group_assignment]:
                        assign_table[j][i+1] = feat_group_assignment

        dset_tmp[:] = assign_table
        dset_tmp.attrs["feature_groups"] = numpy.array([("group_%02d" % i, FeatureGroups.values()[i].group_name) for i in range(n_feature_groups)], dtype='|S64')

    def apply_features(self, channel):
        stop_watch = StopWatch(start=True)
        channel_name = channel.NAME.lower()
        if self._hdf5_found and self._hdf5_reuse and (self.hdf_channel_frame_valid() or self.minimal_effort):

            self._apply_features_from_hdf5(channel)
            how = "loaded"
        else:
            channel.apply_features()
            how = "computed"
        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)
        self._logger.info('object %s %s in %s.'
                              %(desc, how, stop_watch.interim()))


        if self._hdf5_create:
            grp_cur_pos = self._grp_cur_position
            grp_feature = self._get_feature_group()
            for region_name in channel.region_names():
                combined_region_name = self._convert_region_name(channel_name, region_name, '')

                region = channel.get_region(region_name)
                feature_names = region.feature_names
                nr_features = len(feature_names)
                nr_objects = len(region)

                ### write global definition
                self._grp_def[self.HDF5_GRP_FEATURE]
                global_feature_group = self._grp_def.require_group(self.HDF5_GRP_FEATURE)
                global_def_group = global_feature_group.require_group(combined_region_name)
                if 'bounding_box' not in global_def_group:
                    dset_tmp = global_def_group.create_dataset('bounding_box', (4,), [('name', '|S16')])
                    dset_tmp[:] = ['left', 'right', 'top', 'bottom']
                if 'center' not in global_def_group:
                    dset_tmp = global_def_group.create_dataset('center', (2,), [('name', '|S16')])
                    dset_tmp[:] = ['x', 'y']
                if 'orientation' not in global_def_group:
                    dset_tmp = global_def_group.create_dataset('orientation', (2,), [('name', '|S16')])
                    dset_tmp[:] = ['angle', 'eccentricity']
                if 'object_features' not in global_def_group:
                    if nr_features > 0:
                        self._write_object_feature_table(feature_names, global_def_group)
                elif ('object_features' in global_def_group) and (len(global_def_group['object_features']) == 0):
                    if nr_features > 0:
                        del global_def_group['object_features']
                        self._write_object_feature_table(feature_names, global_def_group)

                if 'crack_contour' not in global_def_group:
                    dset_tmp = global_def_group.create_dataset('crack_contour', (1,), [('name', '|S512')])
                    dset_tmp[:] = ('contour_polygon',)


                ### write bounding-box, center, etc per object

                grp_region_features = grp_feature.require_group(combined_region_name)

                # create object mapping tables
                if combined_region_name not in grp_cur_pos[self.HDF5_GRP_OBJECT]:
                    dtype = numpy.dtype([('time_idx', 'int32'),
                                         ('obj_label_id', 'int32'),
                                         ])

                    dset_idx_relation = grp_cur_pos[self.HDF5_GRP_OBJECT].create_dataset(combined_region_name,
                                                          (nr_objects,),
                                                          dtype,
                                                          chunks=(nr_objects if nr_objects > 0 else 1,),
                                                          compression=self._hdf5_compression,
                                                          maxshape=(None,))
                    offset = 0
                else:
                    if not "reused" in grp_cur_pos[self.HDF5_GRP_OBJECT][combined_region_name].attrs.keys():
                        dset_idx_relation = grp_cur_pos[self.HDF5_GRP_OBJECT][combined_region_name]
                        offset = len(dset_idx_relation)
                        dset_idx_relation.resize((nr_objects + offset,))
                    else:
                        offset = 0


                # create mapping from primary to secondary, tertiary, etc
                if channel_name != PrimaryChannel.PREFIX:
                    prim_obj_name = self._convert_region_name(self._region_infos[0][0], self._region_infos[0][2], prefix='')
                    obj_name = self._convert_region_name(channel_name, region_name, prefix='')
                    obj_name = '%s___to___%s' % (prim_obj_name, obj_name)
                    if obj_name not in grp_cur_pos[self.HDF5_GRP_OBJECT]:
                        dt = [('idx1', 'int32'),('idx2', 'int32')]
                        dset_cross_rel = grp_cur_pos[self.HDF5_GRP_OBJECT].create_dataset(obj_name,
                                                                                      (nr_objects,),
                                                                                      dt,
                                                                                      chunks=(nr_objects if nr_objects > 0 else 1,),
                                                                                      compression=self._hdf5_compression,
                                                                                      maxshape=(None,))

                    else:
                        dset_cross_rel = grp_cur_pos[self.HDF5_GRP_OBJECT][obj_name]
                        dset_cross_rel.resize((nr_objects + offset,))

                # Create dataset for bounding box
                if 'bounding_box' not in grp_region_features:
                    dtype = numpy.dtype([('left', 'int32'),
                                         ('right', 'int32'),
                                         ('top', 'int32'),
                                         ('bottom', 'int32'),
                                         ])

                    dset_bounding_box = grp_region_features.create_dataset('bounding_box',
                                                          (nr_objects,),
                                                          dtype,
                                                          chunks=(nr_objects if nr_objects > 0 else 1,),
                                                          compression=self._hdf5_compression,
                                                          maxshape=(None,))
                else:
                    if not "reused" in grp_region_features['bounding_box'].attrs.keys():
                        dset_bounding_box = grp_region_features['bounding_box']
                        dset_bounding_box.resize((nr_objects + offset,))

                # Create dataset for orientation
                if 'orientation' not in grp_region_features:
                    dtype = numpy.dtype([('angle', 'float'),
                                         ('eccentricity', 'float'),])

                    dset_orientation = grp_region_features.create_dataset('orientation',
                                                      (nr_objects,),
                                                      dtype,
                                                      chunks=(nr_objects if nr_objects > 0 else 1,),
                                                      compression=self._hdf5_compression,
                                                      maxshape=(None,))
                else:
                    if not "reused" in grp_region_features['orientation'].attrs.keys():
                        dset_orientation = grp_region_features['orientation']
                        dset_orientation.resize((nr_objects + offset,))

                # Create dataset for center
                if 'center' not in grp_region_features:
                    dtype = numpy.dtype([('x', 'int32'),
                                         ('y', 'int32'),])

                    dset_center = grp_region_features.create_dataset('center',
                                                          (nr_objects,),
                                                          dtype,
                                                          chunks=(nr_objects if nr_objects > 0 else 1,),
                                                          compression=self._hdf5_compression,
                                                          maxshape=(None,))
                else:
                    if not "reused" in grp_region_features['center'].attrs.keys():
                        dset_center = grp_region_features['center']
                        dset_center.resize((nr_objects + offset,))

                if (self._hdf5_include_features or self._hdf5_include_classification):
                    # Create dataset for center
                    if 'object_features' not in grp_region_features:
                        dset_object_features = grp_region_features.create_dataset('object_features',
                                                          (nr_objects, nr_features),
                                                          dtype='float',
                                                          compression=self._hdf5_compression,
                                                          maxshape=(None, nr_features))
                    elif nr_objects > 0:
                        if not "reused" in grp_region_features['object_features'].attrs.keys():
                            dset_object_features = grp_region_features['object_features']
                            dset_object_features.resize(nr_objects + offset, axis=0)
                            # This I do not understand: if you set this to false,
                            # features are not written for the following frames !
                            # self._hdf5_include_features = False

                if self._hdf5_include_crack:
                    if 'crack_contour' not in grp_region_features:
                        dt = h5py.new_vlen(str)
                        dset_crack_contour = grp_region_features.create_dataset('crack_contour',
                                                (nr_objects, ), dt,
                                                chunks=(nr_objects if nr_objects > 0 else 1, ),
                                                maxshape=(None,))
                    else:
                        if not "reused" in grp_region_features['crack_contour'].attrs.keys():
                            dset_crack_contour = grp_region_features['crack_contour']
                            dset_crack_contour.resize((nr_objects + offset, ))


                frame_idx = self._frames_to_idx[self._iCurrentT]
                for idx, obj_id in enumerate(region):
                    obj = region[obj_id]

                    ### Important: save unified objects and relations lookup into _object_coord_to_id
                    idx_new = offset + idx
                    new_obj_id = idx_new + 1
                    coord = frame_idx, obj_id

                    self._object_coord_to_id[(channel.PREFIX, coord)] = new_obj_id
                    self._object_coord_to_idx[(channel.PREFIX, coord)] = idx_new

                    if not "reused" in grp_region_features['bounding_box'].attrs.keys():
                        dset_bounding_box[idx + offset] = obj.oRoi.upperLeft[0], obj.oRoi.lowerRight[0], obj.oRoi.upperLeft[1], obj.oRoi.lowerRight[1]
                    if not "reused" in grp_region_features['center'].attrs.keys():
                        dset_center[idx + offset] = obj.oCenterAbs

                    # is case one don't wants nan's written to the hdf5 file
                    # if np.isnan(obj.orientation.angle)
                    if not "reused" in grp_region_features['orientation'].attrs.keys():
                        dset_orientation[idx + offset] = obj.orientation.angle, obj.orientation.eccentricity
                    if not "reused" in grp_cur_pos[self.HDF5_GRP_OBJECT][combined_region_name].attrs.keys():
                        dset_idx_relation[idx + offset] = frame_idx, obj_id

                    if self._hdf5_include_features:
                        if len(obj.aFeatures) > 0:
                            if not "reused" in grp_region_features['object_features'].attrs.keys():
                                dset_object_features[idx + offset] = obj.aFeatures

                    if self._hdf5_include_crack:
                        if not "reused" in grp_region_features['crack_contour'].attrs.keys():
                            data = ','.join(map(str, numpy.array(obj.crack_contour).flatten()))
                            dset_crack_contour[idx + offset] = base64.b64encode(zlib.compress(data))

                    if channel_name != PrimaryChannel.PREFIX:
                        dset_cross_rel[idx + offset] = (idx, idx)

    def serialize_tracking(self, graph):

        # export full graph structure to .dot file
        if self._hdf5_create and self._hdf5_include_tracking:
            grp = self._grp_cur_position[self.HDF5_GRP_OBJECT]

            head_nodes = [node_id for node_id in graph.node_list()
                          if graph.in_degree(node_id) == 0 and graph.out_degree(node_id) > 0]
            nr_edges = graph.number_of_edges()
            nr_objects = len(head_nodes)

            var_rel = grp.create_dataset('tracking',
                                         (nr_edges, ),
                                         self.HDF5_DTYPE_RELATION,
                                         chunks=(nr_edges if nr_edges > 0 else 1,),
                                         compression=self._hdf5_compression)

            prefix = PrimaryChannel.PREFIX
            data = []
            for idx, edge in enumerate(graph.edges.itervalues()):
                head_id, tail_id = edge[:2]
                head_frame, head_obj_id = \
                    Tracker.split_nodeid(head_id)[:2]
                head_frame_idx = self._frames_to_idx[head_frame]
                tail_frame, tail_obj_id = \
                    Tracker.split_nodeid(tail_id)[:2]
                tail_frame_idx = self._frames_to_idx[tail_frame]

                head_obj_idx_meta = self._object_coord_to_idx[(prefix, (head_frame_idx, head_obj_id))]
                tail_obj_idx_meta = self._object_coord_to_idx[(prefix, (tail_frame_idx, tail_obj_id))]

                data.append((head_obj_idx_meta,
                             tail_obj_idx_meta))
            if len(data) > 0:
                var_rel[:] = data

    def serialize_events(self, tracker):
        if self._hdf5_create and self._hdf5_include_events:
            event_lookup = {}
            for events in tracker.visitor_data.itervalues():
                for start_id, event in events.iteritems():
                    if start_id[0] != '_':
                        key = Tracker.split_nodeid(start_id)[:2]
                        event_lookup.setdefault(key, []).append(event)
            nr_events = len(event_lookup)
            nr_edges = 0
            for events in event_lookup.itervalues():
                if len(events) == 1:
                    nr_edges += events[0]['maxLength'] - 1
                elif len(events) == 2:
                    splt = events[0]['splitIdx']
                    nr_edges += events[0]['maxLength'] + events[1]['maxLength'] - splt - 1
                else:
                    raise ValueError("More than two daughter cell are not supported.")

            object_group = self._grp_cur_position[self.HDF5_GRP_OBJECT]

            if nr_events > 0:
                var_event = object_group.create_dataset('event', (nr_edges,), self.HDF5_DTYPE_EDGE, maxshape=(None,))

                obj_idx = 0
                rel_idx = 0
                for events in event_lookup.itervalues():
                    obj_id = obj_idx
                    track = events[0]['tracks'][0]
                    for head_id, tail_id in zip(track, track[1:]):
                        head_frame, head_obj_id = Tracker.split_nodeid(head_id)[:2]
                        haed_frame_idx = self._frames_to_idx[head_frame]
                        head_id_ = self._object_coord_to_idx[('primary', (haed_frame_idx, head_obj_id))]

                        tail_frame, tail_obj_id = Tracker.split_nodeid(tail_id)[:2]
                        tail_frame_idx = self._frames_to_idx[tail_frame]
                        tail_id_ = self._object_coord_to_idx[('primary', (tail_frame_idx, tail_obj_id))]

                        var_event[rel_idx] = (obj_id, head_id_, tail_id_)
                        rel_idx += 1
                    if len(events) == 2:
                        splt = events[1]['splitIdx']
                        track = events[1]['tracks'][0][splt-1:]
                        for head_id, tail_id in zip(track, track[1:]):
                            head_frame, head_obj_id = Tracker.split_nodeid(head_id)[:2]
                            haed_frame_idx = self._frames_to_idx[head_frame]
                            head_id_ = self._object_coord_to_idx[('primary', (haed_frame_idx, head_obj_id))]

                            tail_frame, tail_obj_id = Tracker.split_nodeid(tail_id)[:2]
                            tail_frame_idx = self._frames_to_idx[tail_frame]
                            tail_id_ = self._object_coord_to_idx[('primary', (tail_frame_idx, tail_obj_id))]
                            var_event[rel_idx] = (obj_id, head_id_, tail_id_)
                            rel_idx += 1
                    obj_idx += 1
            else:
                var_event = object_group.create_dataset('event', (0,),
                                                      self.HDF5_DTYPE_EDGE,
                                                      chunks=(1,), maxshape=(None,))


    def exportObjectCounts(self, filename, pos, meta_data, ch_info,
                           sep='\t', has_header=False):

        with open(filename, 'w') as fp:
            for frame, channels in self.iteritems():
                line1 = []
                line2 = []
                line3 = []
                line4 = []
                items = []
                coordinate = Coordinate(position=pos, time=frame)
                prefix = [frame, meta_data.get_timestamp_relative(coordinate)]
                prefix_names = ['frame', 'time']

                for chname, (region_name, class_names, _) in ch_info.iteritems():
                    channel = channels[chname]

                    if not has_header:
                        keys = ['total'] + class_names
                        line4 += keys
                        line3 += ['total'] + ['class']*len(class_names)
                        line1 += [chname.upper()]*len(keys)
                        line2 += [str(region_name)]*len(keys)

                    region = channel.get_region(region_name)
                    total = len(region)
                    count = dict([(x, 0) for x in class_names])
                    # in case just total counts are needed
                    if len(class_names) > 0:
                        for obj in region.values():
                            count[obj.strClassName] += 1
                    items += [total] + [count[x] for x in class_names]

                if not has_header:
                    has_header = True
                    prefix_str = [''] * len(prefix)
                    fp.write('%s\n' % sep.join(prefix_str + line1))
                    fp.write('%s\n' % sep.join(prefix_str + line2))
                    fp.write('%s\n' % sep.join(prefix_str + line3))
                    fp.write('%s\n' % sep.join(prefix_names + line4))
                fp.write('%s\n' % sep.join(map(str, prefix + items)))

    def getObjectCounts(self, ch_info):

        all_counts = {}
        for chname, (region_name, class_names, _) in ch_info.iteritems():
            all_counts[(chname, region_name)] = {}

        for frame, channels in self.iteritems():

            for chname, (region_name, class_names, _) in ch_info.iteritems():

                if len(all_counts[(chname, region_name)])==0:
                    all_counts[(chname, region_name)] = OrderedDict([(x, [])
                                                                     for x in ['total'] + class_names])
                channel = channels[chname]
                region = channel.get_region(region_name)
                total = len(region)
                count = dict([(x, 0) for x in class_names])
                # in case just total counts are needed
                if len(class_names) > 0:
                    for obj in region.values():
                        count[obj.strClassName] += 1
                for class_name in class_names:
                    all_counts[(chname, region_name)][class_name].append(count[class_name])
                all_counts[(chname, region_name)]['total'].append(total)

        return all_counts

    def exportPopulationPlots(self, ch_info, pop_plot_output_dir, plate, pos,
                              ymax=None,
                              all_counts=None, grid=True, legend=True,
                              relative=True):
        if all_counts is None:
            all_counts = self.getObjectCounts(ch_info)

        if relative:
            ylab = 'class percentage'
        else:
            ylab = 'class counts (raw)'

        for chname, (region_name, class_names, colors) in ch_info.iteritems():
            if len(class_names) < 2:
                continue

            X = numpy.array([all_counts[(chname, region_name)][x] for x in class_names])
            timevec = range(X.shape[1])

            if len(timevec) > 1:
                if relative:
                    total = numpy.array(all_counts[(chname, region_name)]['total'])
                    X = X.astype('float') / total.astype('float')

                fig = Figure(figsize=(10, 8))
                ax = fig.add_subplot(1,1,1)

                # in this case we have more than one time point and we can visualize the time series
                for i, lb, color in zip(range(len(class_names)), class_names, colors):
                    ax.plot(timevec, X[i,:], color=color, label=lb, linewidth=2.0)

                if not ymax is None and ymax > -1:
                    ax.axis([min(timevec), max(timevec), 0, ymax])
                ax.set_title('Population time series: %s %s %s %s' % (plate, pos, chname, region_name), size='medium')
                ax.set_xlim((min(timevec), max(timevec)))
                ax.set_xlabel('time (frames)', size='medium')
                ax.set_ylabel(ylab, size='medium')

                if legend:
                    fprop = FontProperties()
                    fprop.set_size('small')

                    handles, labels = ax.get_legend_handles_labels()
                    ax.legend(handles[::-1], labels[::-1], frameon=False, loc=9,
                              ncol=len(class_names), mode="expand", prop=fprop)

                if grid:
                    ax.grid(b=True, which='major', alpha=0.5)

                canvas = FigureCanvasAgg(fig)
                fig.savefig(join(pop_plot_output_dir, '%s__%s__%s__%s.pdf'
                                 %(plate, pos, chname, region_name)))

            else:
                # in this case we have only one timepoint.
                # We can visualize a barplot instead.
                width = 0.7
                nb_bars = X.shape[0]

                fig = Figure(figsize=(int(0.8*nb_bars + 1),10))
                ax = fig.add_subplot(1,1,1)

                ind = numpy.arange(nb_bars)

                if relative:
                    X = X.astype('float') / numpy.sum(X.astype('float'))

                ax.bar(ind-width/2., X[:,0], width=width, color=colors,
                       edgecolor='none')
                ax.set_xlim((ind.min()-0.5, ind.max()+0.5))
                ax.set_xticks(ind)
                ax.set_xticklabels(class_names, rotation=45, fontsize='small',
                                   ha='center')

                ax.set_title('Classification results:\n%s %s\n%s %s'
                             %(plate, pos, chname, region_name), size='medium')
                ax.set_xlabel('')
                ax.set_ylabel(ylab, size='medium')

                if grid:
                    ax.grid(b=True, axis='y', which='major', alpha=0.5)

                canvas = FigureCanvasAgg(fig)
                fig.savefig(join(pop_plot_output_dir, '%s__%s__%s__%s.pdf' % (plate, pos, chname, region_name)))
        return

    def exportObjectDetails(self, filename, sep='\t'):
        f = file(filename, 'w')

        feature_lookup = OrderedDict()
        feature_lookup['mean'] = 'n2_avg'
        feature_lookup['sd'] = 'n2_stddev'
        feature_lookup['size'] = 'roisize'

        has_header = False
        line1 = []
        line2 = []
        line3 = []

        for frame, channels in self.iteritems():

            items = []
            prim_region = channels.values()[0].get_region(self.reginfo.names['primary'][0])

            for obj_id in prim_region:

                prefix = [frame, obj_id]
                prefix_names = ['frame', 'objID']
                items = []

                for channel in channels.values():

                    for rname in channel.region_names():

                        region = channel.get_region(rname)
                        if obj_id in region:
                            #FIXME:
                            feature_lookup2 = feature_lookup.copy()
                            for k,v in feature_lookup2.items():
                                if not region.has_feature(v):
                                    del feature_lookup2[k]

                            if not has_header:
                                keys = ['classLabel', 'className']
                                if channel.NAME == 'Primary':
                                    keys += ['centerX', 'centerY']
                                keys += feature_lookup2.keys()

                                line1 += ['%s_%s_%s' % (channel.NAME.upper(),
                                                        rname, key)
                                          for key in keys]

                            obj = region[obj_id]
                            features = region.features_by_name(obj_id, feature_lookup2.values())
                            values = [x if not x is None else '' for x in [obj.iLabel, obj.strClassName]]
                            if channel.NAME == 'Primary':
                                values += [obj.oCenterAbs[0], obj.oCenterAbs[1]]
                            values += list(features)
                            items.extend(values)

                if not has_header:
                    has_header = True
                    prefix_str = [''] * len(prefix)

                    line1 = prefix_names + line1
                    f.write('%s\n' % sep.join(line1))
                f.write('%s\n' % sep.join(map(str, prefix + items)))
        f.close()

    def exportImageFileNames(self, outdir, position, importer, ch_mapping):
        fname = join(outdir, 'P%s__image_files.csv' %position)

        with open(fname, 'wb') as fp:
            writer = csv.DictWriter(fp, ch_mapping.keys(), lineterminator='\n')
            writer.writeheader()
            for frame in self.keys():
                table = dict()
                for chname, color in ch_mapping.iteritems():
                    # no color channel in merged channel
                    if color is None:
                        continue
                    for zslice in importer.dimension_lookup[position][frame][color]:
                        file_ = importer.dimension_lookup[position][frame][color][zslice]
                        table[chname] = join(importer.path, file_)
                writer.writerow(table)

    def save_classlabels(self, channel, region, predictor):
        """Save class labels and preditions to hdf5."""
        if not (self._hdf5_create and self._hdf5_include_classification):
            return

        channel_region = ("%s__%s" %(channel.NAME, region.name)).lower()

        nr_classes = predictor.n_classes
        nr_objects = len(region)

        # 1) write /definition - classifier definition
        global_def_group = self._grp_def[self.HDF5_GRP_FEATURE].require_group(channel_region)
        classification_group = global_def_group.require_group('object_classification')

        # class labels
        if 'class_labels' not in classification_group:
            dt = numpy.dtype([('label', 'int32'),
                              ('name', '|S100'),
                              ('color', '|S9')])
            var = classification_group.create_dataset('class_labels', (nr_classes,), dt)
            var.attrs["UNPREDICED_LABEL"] = numpy.int32(self.UNPREDICTED_LABEL)
            var.attrs['UNPREDICED_PROB'] = numpy.float32(self.UNPREDICTED_PROB)
            var[:] = zip(predictor.class_names.keys(),
                         predictor.class_names.values(),
                         [predictor.hexcolors[n] for n in predictor.class_names.values()])

            # classifier
            dt = numpy.dtype([('name', '|S512'),
                              ('method', '|S512'),
                              ('version', '|S512'),
                              ('parameter', '|S512'),
                              ('description', '|S512')])
            var = classification_group.create_dataset('classifier', (1,), dt)

            var[0] = (channel.NAME, predictor.classifier.METHOD,
                      predictor.classifier.NAME, '', '')

            # feature names
            feature_names = predictor.feature_names
            var = classification_group.create_dataset('features', (len(feature_names),), \
                                                          [('object_feautres','|S512'),])
            var[:] = feature_names

        # 2) write to /sample  prediction and probablilities
        current_classification_grp =  \
            self._grp_cur_position[self.HDF5_GRP_FEATURE].require_group(channel_region)
        current_classification_grp = current_classification_grp.require_group('object_classification')

        if 'prediction' not in current_classification_grp:
            dt = numpy.dtype([('label_idx', 'int32')])
            dset_prediction = current_classification_grp.create_dataset('prediction',
                                                                        (nr_objects, ), dt,
                                                                        chunks=(nr_objects if nr_objects > 0 else 1,),
                                                                        compression=self._hdf5_compression,
                                                                        maxshape=(None,))
            offset = 0
        else:
            dset_prediction = current_classification_grp['prediction']
            offset = len(dset_prediction)
            dset_prediction.resize((nr_objects + offset,))

        if predictor.SAVE_PROBS:
            var_name = 'probability'
            if not var_name in current_classification_grp:
                dset_probability = current_classification_grp.create_dataset(var_name, (nr_objects, nr_classes),
                                           'float',
                                           chunks=(nr_objects if nr_objects > 0 else 1, nr_classes),
                                           compression=self._hdf5_compression,
                                           maxshape=(None, nr_classes)
                                           )
            else:
                dset_probability = current_classification_grp[var_name]
                dset_probability.resize((offset+nr_objects, nr_classes))

        label2idx = dict([(l, i) for i, l in enumerate(predictor.class_names.keys())])

        for i, obj in enumerate(region.itervalues()):
            # replace default for unlabeld object with numerical values
            if obj.iLabel is None:
                dset_prediction[i+offset] = (self.UNPREDICTED_LABEL, )
                probs = [self.UNPREDICTED_PROB]*predictor.n_classes
            else:
                dset_prediction[i+offset] = (label2idx[obj.iLabel], )
                probs = obj.dctProb.values()

            if predictor.SAVE_PROBS:
                dset_probability[i+offset] = probs
