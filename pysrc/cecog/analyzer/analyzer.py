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

#-------------------------------------------------------------------------------
# standard library imports:
#

import os, \
       types, \
       logging

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.propertymanagers import PropertyManager
from pdk.properties import (BooleanProperty,
                            IntProperty,
                            StringProperty,
                            InstanceProperty,
                            )
from pdk.attributes import Attribute
from pdk.map import dict_append_list
from pdk.fileutils import safe_mkdirs
from pdk.iterator import flatten
from pdk.ordereddict import OrderedDict

import numpy
#import h5py
import netCDF4

#-------------------------------------------------------------------------------
# cecog module imports:
#

from cecog import ccore

from cecog.util.util import hexToRgb
from cecog.io.imagecontainer import (Coordinate,
                                     MetaImage,
                                     )
from cecog.plugin.segmentation import REGION_INFO

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class QualityControl(object):

    FILENAME_TOKEN = ['prefix', 'P', 'C', 'R', 'A']

    def __init__(self, strFilePath, meta_data, dctProcessInfos, dctPlotterInfos=None):
        super(QualityControl, self).__init__()

        self.dctProcessInfos = dctProcessInfos

        if dctPlotterInfos is None:
            dctPlotterInfos = {}
        #self._oPlotter = RPlotter(**dctPlotterInfos)
        #self._oPlate = oPlate
        self._strFilePath = strFilePath
        self._dctPositions = {}
        self._iCurrentP = None
        self._meta_data = meta_data

    def initPosition(self, iP, origP):
        self._iCurrentP = iP
        self._origP = origP
        self._dctPositions[iP] = {}

    def processPosition(self, time_holder):
        iP = self._iCurrentP
        for strChannelId, dctInfo in self.dctProcessInfos.iteritems():

            strRegionId = dctInfo['regionId']
            strTask = dctInfo['task']

            if strTask == 'proliferation':

                oTable = newTable(['Frame', 'Timestamp', 'Cellcount'],
                                  columnTypeCodes=['i','f','i'])

                for iT, dctChannels in time_holder.iteritems():
                    try:
                        oRegion = dctChannels[strChannelId].get_region(strRegionId)
                    except KeyError:
                        iCellcount = 0
                    else:
                        iCellcount = len(oRegion)

                    fTimestamp = self.__meta_data.getTimestamp(self._origP, iT)

                    oTable.append({'Frame'     : iT,
                                   'Timestamp' : fTimestamp,
                                   'Cellcount' : iCellcount,
                                   })

                #self._plotProliferation()
                exportTable(oTable,
                            os.path.join(self._strFilePath,
                                         "qc_P%s_C%s_R%s_A%s.tsv" % (iP, strChannelId, strRegionId, strTask)),
                            fieldDelimiter='\t',
                            writeRowLabels=False)



class TimeHolder(OrderedDict):

    NC_GROUP_RAW = 'raw'
    NC_GROUP_LABEL = 'label'
    NC_GROUP_FEATURE = 'feature'
    NC_ZLIB = True
    NC_SHUFFLE = True

    def __init__(self, P, channels, filename, filename_hdf5, meta_data, settings,
                 create_nc=True, reuse_nc=True,
                 hdf5_create=True, hdf5_include_raw_images=True,
                 hdf5_include_label_images=True, hdf5_include_features=True):
        super(TimeHolder, self).__init__()
        self.P = P
        self._iCurrentT = None
        self.channels = channels
        self._meta_data = meta_data
        self._settings = settings

        self._create_nc = create_nc
        self._reuse_nc = reuse_nc

        self._nc4_filename = filename
        self._dataset = None

        self._hdf5_create = hdf5_create
        self._hdf5_include_raw_images = hdf5_include_raw_images
        self._hdf5_include_label_images = hdf5_include_label_images
        self._hdf5_include_features = hdf5_include_features

        self._logger = logging.getLogger(self.__class__.__name__)
        # frames get an index representation with the NC file, starting at 0
        frames = sorted(list(meta_data.times))
        self._frames_to_idx = dict([(f,i) for i, f in enumerate(frames)])
        self._idx_to_frames = dict([(i,f) for i, f in enumerate(frames)])

        channels = sorted(list(meta_data.channels))
        self._region_names = REGION_INFO.names['primary'] + REGION_INFO.names['secondary']

        region_names2 = []
        for prefix in ['primary', 'secondary', 'tertiary']:
            for name in REGION_INFO.names[prefix]:
                region_names2.append((prefix.capitalize(), name))

        self._channels_to_idx = dict([(f,i) for i, f in enumerate(channels)])
        self._idx_to_channels = dict([(i,f) for i, f in enumerate(channels)])

        self._regions_to_idx = dict([(n,i) for i, n in enumerate(self._region_names)])
        self._regions_to_idx2 = OrderedDict([(n,i) for i, n in enumerate(region_names2)])

        if self._hdf5_create:
            f = h5py.File(filename_hdf5, 'w')
            self._hdf5_file = f

    def create_nc4(self):
        settings = self._settings
        if (self._create_nc and self._reuse_nc and self._dataset is None and
            os.path.isfile(self._nc4_filename)):
            dataset = netCDF4.Dataset(self._nc4_filename, 'a')

            # decide which parts need to be reprocessed based on changes
            # between the saved (from nc4) and the current settings

            # load settings from nc4 file
            #var = str(dataset.variables['settings'][:][0])
            #settings2 = settings.copy()
            #settings2.from_string(var)

            # compare current and saved settings and decide which data is to
            # process again by setting the *_finished variables to zero

#            valid = {'primary'   : [True, True],
#                     'secondary' : [True, True],
#                     }
#            for name in ['primary', 'secondary']:
#                channel_id = settings2.get(SECTION_NAME_OBJECTDETECTION,
#                                           '%s_channelid' % name)
#                idx = dataset.variables['channels_idx'][:] == channel_id
#                if (not settings.compare(settings2, SECTION_NAME_OBJECTDETECTION,
#                                         '%s_image' % name) or
#                    not settings.compare(settings2, SECTION_NAME_OBJECTDETECTION,
#                                         'secondary_registration') or
#                    not valid[name][0]):
#                    dataset.variables['raw_images_finished'][:,idx] = 0
#                    valid['primary'] = [False, False]
#                    valid['secondary'] = [False, False]
#                idx = dataset.variables['region_channels'][:] == name
#                if (not settings.compare(settings2, SECTION_NAME_OBJECTDETECTION,
#                                        '%s_segmentation' % name) or
#                    not valid[name][1]):
#                    dataset.variables['label_images_finished'][:,idx] = 0
#                    valid['primary'] = [False, False]
#                    valid['secondary'] = [False, False]

        elif self._create_nc and self._dataset is None:
            meta = self._meta_data
            dim_t = meta.dim_t
            dim_c = meta.dim_c
            w = meta.real_image_width
            h = meta.real_image_height

            channels = sorted(list(meta.channels))
            region_channels = ['primary']*len(REGION_INFO.names['primary']) + \
                              ['secondary']*len(REGION_INFO.names['primary'])

            dataset = netCDF4.Dataset(self._nc4_filename, 'w', format='NETCDF4')
            dataset.createDimension('frames', dim_t)
            dataset.createDimension('channels', dim_c)
            dataset.createDimension('height', h)
            dataset.createDimension('width', w)
            dataset.createDimension('regions', len(self._region_names))
            dataset.createDimension('one', 1)

            frames = sorted(list(meta.times))
            var = dataset.createVariable('frames_idx', 'u4', 'frames')
            var.description = 'Mapping from indices to frames.'
            var[:] = frames

            var = dataset.createVariable('settings', str, 'one')
            var.description = 'Cecog settings used for the generation of this '\
                              'netCDF file. Current cecog and this settings '\
                              'are compared hierarchically leading to a '\
                              'stepwise invalidation of preprocessed values.'

            raw_g = dataset.createGroup(self.NC_GROUP_RAW)
            raw_g.description = 'Converted raw images as processed by cecog '\
                                'after 8bit conversion, registration, and '\
                                'z-projection/selection.'
            label_g = dataset.createGroup(self.NC_GROUP_LABEL)
            label_g.description = 'Label images as a result of object '\
                                  'detection.'

            object_g = dataset.createGroup('object')
            object_g.description = 'General object values and mapping'
            feature_g = dataset.createGroup(self.NC_GROUP_FEATURE)
            feature_g.description = 'Feature values'

            for channel_id in meta.channels:
                var = raw_g.createVariable(channel_id, 'u1',
                                           ('frames', 'height', 'width'),
                                           zlib=self.NC_ZLIB,
                                           shuffle=self.NC_SHUFFLE,
                                           chunksizes=(1, h, w))
                # FIXME: not working for dim_t == 1 (no timelapse data)
                var.valid = [0] * dim_t
                #print channel_id, dim_t, var.valid

            for channel_name in REGION_INFO.names.keys():
                channel_g = label_g.createGroup(channel_name)
                grp1 = object_g.createGroup(channel_name)
                grp2 = feature_g.createGroup(channel_name)
                for region_name in REGION_INFO.names[channel_name]:
                    var = channel_g.createVariable(region_name, 'i2',
                                                   ('frames', 'height',
                                                    'width'),
                                                   zlib=self.NC_ZLIB,
                                                   shuffle=self.NC_SHUFFLE,
                                                   chunksizes=(1, h, w))
                    var.valid = [0] * dim_t
                    grp1.createGroup(region_name)
                    grp2.createGroup(region_name)

            var = dataset.createVariable('channels_idx', str, 'channels')
            var[:] = numpy.asarray(channels, 'O')

            var = dataset.createVariable('region_names', str, 'regions')
            var[:] = numpy.asarray(self._region_names, 'O')

            var = dataset.createVariable('region_channels', str, 'regions')
            var[:] = numpy.asarray(region_channels, 'O')

            dataset.createVariable('raw_images', 'u1',
                                   ('frames', 'channels', 'height', 'width'),
                                   zlib='True',
                                   shuffle=False,
                                   chunksizes=(1, 1, h, w)
                                   )
            finished = dataset.createVariable('raw_images_finished', 'i1',
                                              ('frames', 'channels'))
            finished[:] = 0

            dataset.createVariable('label_images', 'i2',
                                   ('frames', 'regions', 'height', 'width'),
                                   zlib='True',
                                   shuffle=False,
                                   chunksizes=(1, 1, h, w)
                                   )
            finished = dataset.createVariable('label_images_finished', 'i1',
                                              ('frames', 'regions'))

            finished[:] = 0
        else:
            dataset = None

        if not dataset is None:
            # update the settings to the current version
            var = dataset.variables['settings']
            var[:] = numpy.asarray(settings.to_string(), 'O')
            self._dataset = dataset

    @staticmethod
    def nc_valid_set(var, idx, value):
        helper = var.valid
        helper[idx] = value
        var.valid = helper

    def close_all(self):
        if not self._dataset is None:
            self._dataset.close()
            self._dataset = None
            self._create_nc = False
        if self._hdf5_create:
            self._hdf5_file.close()
            self._hdf5_create = False

    def __del__(self):
        self.close_all()

    def initTimePoint(self, iT):
        self._iCurrentT = iT

    def getCurrentTimePoint(self):
        return self._iCurrentT

    def getCurrentChannels(self):
        return self[self._iCurrentT]

    def purge_features(self):
        for channels in self.itervalues():
            for channel in channels.itervalues():
                channel.purge(features={})

    def apply_channel(self, oChannel):
        iT = self._iCurrentT
        if not iT in self:
            self[iT] = OrderedDict()
        self[iT][oChannel.NAME] = oChannel
        self[iT].sort(key = lambda x: self[iT][x])

    def apply_segmentation(self, channel, primary_channel=None):
        self.create_nc4()
        valid = False
        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)
        name = channel.NAME.lower()
        if self._create_nc or self._reuse_nc:
            grp = self._dataset.groups[self.NC_GROUP_LABEL]
            grp = grp.groups[name]
            frame_idx = self._frames_to_idx[self._iCurrentT]
        if self._reuse_nc:
            for region_name in channel.lstAreaSelection:
                var = grp.variables[region_name]
                if var.valid[frame_idx]:
                    img_label = ccore.numpy_to_image(var[frame_idx],
                                                     copy=True)
                    img_xy = channel.meta_image.image
                    container = ccore.ImageMaskContainer(img_xy, img_label,
                                                         False, True)
                    channel.dctContainers[region_name] = container
                    valid = True
                else:
                    valid = False
                    break
        if not valid:
            channel.apply_segmentation(primary_channel)
            if self._create_nc:
                for region_name in channel.lstAreaSelection:
                    var = grp.variables[region_name]
                    container = channel.dctContainers[region_name]
                    var[frame_idx] = \
                        container.img_labels.toArray(copy=False)
                    self.nc_valid_set(var, frame_idx, 1)
                self._logger.debug('Label images %s written to nc4 file.' %\
                                   desc)
        else:
            self._logger.debug('Label images %s loaded from nc4 file.' %\
                   desc)

        if self._hdf5_create and self._hdf5_include_label_images:
            meta = self._meta_data
            w = meta.real_image_width
            h = meta.real_image_height
            f = self._hdf5_file
            if 'labeled_images' in f:
                labeled_images = f['labeled_images']
            else:
                nr_labels = len(self._regions_to_idx2)
                dt = h5py.special_dtype(vlen=str)
                names = f.create_dataset('label_names', (nr_labels, 2), dt)
                for tpl, idx in self._regions_to_idx2.iteritems():
                    names[idx] = tpl
                labeled_images = f.create_dataset('label_images', (nr_labels, meta.dim_t, meta.dim_z, w, h),
                                                  'int32', compression='szip', chunks=(1,1,meta.dim_z,w,h))

            frame_idx = self._frames_to_idx[self._iCurrentT]
            for region_name in channel.lstAreaSelection:
                idx = self._regions_to_idx2[(channel.NAME, region_name)]
                container = channel.dctContainers[region_name]
                array = container.img_labels.toArray(copy=False)
                labeled_images[idx, frame_idx, 0] = numpy.require(array, 'int32')


    def prepare_raw_image(self, channel):
        self.create_nc4()

        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)
        if self._create_nc or self._reuse_nc:
            grp = self._dataset.groups[self.NC_GROUP_RAW]
            var = grp.variables[channel.strChannelId]
            frame_idx = self._frames_to_idx[self._iCurrentT]
        if self._reuse_nc and var.valid[frame_idx]:
            coordinate = Coordinate(position=self.P, time=self._iCurrentT,
                                    channel=channel.strChannelId, zslice=1)
            meta_image = MetaImage(image_container=None, coordinate=coordinate)

            img = ccore.numpy_to_image(var[frame_idx], copy=True)
            meta_image.set_image(img)
            channel.meta_image = meta_image
            self._logger.debug('Raw image %s loaded from nc4 file.' % desc)
        else:
            channel.apply_zselection()
            channel.normalize_image()
            channel.apply_registration()
            if self._create_nc:
                img = channel.meta_image.image
                grp = self._dataset.groups[self.NC_GROUP_RAW]
                var = grp.variables[channel.strChannelId]
                var[frame_idx] = img.toArray(copy=False)
                self.nc_valid_set(var, frame_idx, 1)
                self._logger.debug('Raw image %s written to nc4 file.' % desc)

        if self._hdf5_create and self._hdf5_include_raw_images:
            meta = self._meta_data
            w = meta.real_image_width
            h = meta.real_image_height
            f = self._hdf5_file
            if 'images' in f:
                images = f['images']
            else:
                images = f.create_dataset('pre_images', (meta.dim_c, meta.dim_t, meta.dim_z, w, h),
                                          'uint8', compression='szip', chunks=(1,1,meta.dim_z,w,h))
                dt = h5py.special_dtype(vlen=str)
                channels = f.create_dataset('channel_names', (meta.dim_c,), dt)
                for idx in range(meta.dim_c):
                    channels[idx] = self._idx_to_channels[idx]

            frame_idx = self._frames_to_idx[self._iCurrentT]
            channel_idx = self._channels_to_idx[channel.strChannelId]
            img = channel.meta_image.image
            array = img.toArray(copy=False)
            print array.shape, (meta.dim_c, meta.dim_t, meta.dim_z, w, h), frame_idx, channel_idx
            images[channel_idx, frame_idx, 0] = array

    def apply_features(self, channel):
        self.create_nc4()
        valid = False
        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)

        name = channel.NAME.lower()
        channel.apply_features()

        if self._hdf5_create and self._hdf5_include_features:
            meta = self._meta_data
            w = meta.real_image_width
            h = meta.real_image_height
            f = self._hdf5_file
            if 'features' in f:
                features = f['features']
            else:
                features = f.create_group('features')

            if 'objects' in f:
                objects = f['objects']
            else:
                objects = f.create_group('objects')

#        #nr_objects
#
#        data_f = features.create_dataset(str(self._iCurrentT), (), 'float32',
#                                         compression='szip', chunks=())
#        data_o = objects.create_dataset(str(self._iCurrentT), (), 'float32',
#                                         compression='szip', chunks=())
#
#            nr_labels = len(self._regions_to_idx2)
#            dt = h5py.special_dtype(vlen=str)
#            names = f.create_dataset('label_names', (nr_labels, 2), dt)
#            for tpl, idx in self._regions_to_idx2.iteritems():
#                names[idx] = tpl
#            labeled_images = f.create_dataset('labeled_images', (nr_labels, meta.dim_t, meta.dim_z, w, h),
#                                              'int32', compression='szip', chunks=(1,1,meta.dim_z,w,h))
#
#        frame_idx = self._frames_to_idx[self._iCurrentT]
#        for region_name in channel.lstAreaSelection:
#            idx = self._regions_to_idx2[(channel.NAME, region_name)]
#            container = channel.dctContainers[region_name]
#            array = container.img_labels.toArray(copy=False)
#            labeled_images[idx, frame_idx, 0] = numpy.require(array, 'int32')



    def extportObjectCounts(self, filename, P, meta_data, prim_info=None,
                            sec_info=None, sep='\t'):
        f = file(filename, 'w')
        has_header = False

        for frame, channels in self.iteritems():
            #channels.sort(key = lambda x: channels[x])

            line1 = []
            line2 = []
            line3 = []
            line4 = []
            items = []
            coordinate = Coordinate(position=P, time=frame)
            prefix = [frame, meta_data.get_timestamp_relative(coordinate)]
            prefix_names = ['frame', 'time']

            for channel in channels.values():
                if channel.NAME == 'Primary' and not prim_info is None:
                    region_info = prim_info
                elif channel.NAME == 'Secondary' and not sec_info is None:
                    region_info = sec_info
                else:
                    region_info = None

                if not region_info is None:
                    region_name, class_names = region_info
                    if not has_header:
                        keys = ['total'] + class_names
                        line4 += keys
                        line3 += ['total'] + ['class']*len(class_names)
                        line1 += [channel.NAME.upper()] * len(keys)
                        line2 += [region_name] * len(keys)

                    if channel.has_region(region_name):
                        region = channel.get_region(region_name)
                        total = len(region)
                        count = dict([(x, 0) for x in class_names])
                        # in case just total counts are needed
                        if len(class_names) > 0:
                            for obj in region.values():
                                count[obj.strClassName] += 1
                        items += [total] + [count[x] for x in class_names]
                    else:
                        items += [numpy.NAN] * (len(class_names) + 1)

            if not has_header:
                has_header = True
                prefix_str = [''] * len(prefix)
                f.write('%s\n' % sep.join(prefix_str + line1))
                f.write('%s\n' % sep.join(prefix_str + line2))
                f.write('%s\n' % sep.join(prefix_str + line3))
                f.write('%s\n' % sep.join(prefix_names + line4))

            f.write('%s\n' % sep.join(map(str, prefix + items)))

        f.close()


    def extportObjectDetails(self, filename, sep='\t', excel_style=False):
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
            prim_region = channels.values()[0].get_region('primary')

            for obj_id in prim_region:

                prefix = [frame, obj_id]
                prefix_names = ['frame', 'objID']
                items = []

                for channel in channels.values():

                    for region_id in channel.region_names():

                        region = channel.get_region(region_id)
                        if obj_id in region:
                            #FIXME:
                            feature_lookup2 = feature_lookup.copy()
                            for k,v in feature_lookup2.items():
                                if not region.hasFeatureName(v):
                                    del feature_lookup2[k]

                            if not has_header:
                                keys = ['classLabel', 'className']
                                if channel.NAME == 'Primary':
                                    keys += ['centerX', 'centerY']
                                keys += feature_lookup2.keys()
                                if excel_style:
                                    line1 += [channel.NAME.upper()] * len(keys)
                                    line2 += [region_id] * len(keys)
                                    line3 += keys
                                else:
                                    line1 += ['%s_%s_%s' % (channel.NAME.upper(),
                                                            region_id, key)
                                              for key in keys]

                            obj = region[obj_id]
                            #print feature_lookup2.keys(), feature_lookup2.values()
                            #fn = region.getFeatureNames()
                            #print zip(fn, obj.aFeatures)
                            features = region.getFeaturesByNames(obj_id, feature_lookup2.values())
                            values = [x if not x is None else '' for x in [obj.iLabel, obj.strClassName]]
                            if channel.NAME == 'Primary':
                                values += [obj.oCenterAbs[0], obj.oCenterAbs[1]]
                            values += list(features)
                            items.extend(values)

                if not has_header:
                    has_header = True
                    prefix_str = [''] * len(prefix)
                    if excel_style:
                        line1 = prefix_str + line1
                        line2 = prefix_str + line2
                        line3 = prefix_names + line3
                        f.write('%s\n' % sep.join(line1))
                        f.write('%s\n' % sep.join(line2))
                        f.write('%s\n' % sep.join(line3))
                    else:
                        line1 = prefix_names + line1
                        f.write('%s\n' % sep.join(line1))

                f.write('%s\n' % sep.join(map(str, prefix + items)))

        f.close()


class CellAnalyzer(PropertyManager):

    PROPERTIES = \
        dict(P =
                 StringProperty(True, doc=''),
             bCreateImages =
                 BooleanProperty(True, doc="Create output images"),
             iBinningFactor =
                 IntProperty(None,
                             is_mandatory=True,
                             doc=''),
             detect_objects =
                 BooleanProperty(True),


             time_holder =
                 InstanceProperty(None,
                                  TimeHolder,
                                  doc="Instance of TimeHolder.",
                                  is_mandatory=True),
            )

    __attributes__ = [Attribute('_channel_registry'),
                      Attribute('_iT'),
                      Attribute('_oLogger'),
                      ]

    def __init__(self, **dctOptions):
        super(CellAnalyzer, self).__init__(**dctOptions)
        self._oLogger = logging.getLogger(self.__class__.__name__)

    def initTimepoint(self, iT):
        self._channel_registry = OrderedDict()
        self._iT = iT
        self.time_holder.initTimePoint(iT)

    def register_channel(self, channel):
        self._channel_registry[channel.NAME] = channel

    def get_channel_names(self):
        return self._channel_registry.keys()

    def get_channel(self, name):
        return self._channel_registry[name]

    def process(self, apply=True, extract_features=True):
        # sort by Channel `RANK`
        channels = sorted(self._channel_registry.values())
        primary_channel = None
        for channel in channels:

            self.time_holder.prepare_raw_image(channel)

            if self.detect_objects:
                self.time_holder.apply_segmentation(channel, primary_channel)
                if extract_features:
                    self.time_holder.apply_features(channel)

                if primary_channel is None:
                    assert channel.RANK == 1
                    primary_channel = channel

        if apply:
            for channel in channels:
                self.time_holder.apply_channel(channel)

    def purge(self, features=None):
        for oChannel in self._channel_registry.values():
            if not features is None and oChannel.strChannelId in features:
                channelFeatures = features[oChannel.strChannelId]
            else:
                channelFeatures = None
            oChannel.purge(features=channelFeatures)

    def exportLabelImages(self, pathOut, compression='LZW'):
        for name, channel in self._channel_registry.iteritems():
            channel_id = channel.strChannelId
            for strRegion, oContainer in channel.dctContainers.iteritems():
                strPathOutImage = os.path.join(pathOut,
                                               channel_id,
                                               strRegion)
                safe_mkdirs(strPathOutImage)
                oContainer.exportLabelImage(os.path.join(strPathOutImage,
                                                         'P%s_T%05d.tif' % (self.P, self._iT)),
                                            compression)

    def getImageSize(self, name):
        oChannel = self._channel_registry[name]
        w = oChannel.meta_image.width
        h = oChannel.meta_image.height
        return (w,h)

    def render(self, strPathOut, dctRenderInfo=None,
               strFileSuffix='.jpg', strCompression='98', writeToDisc=True,
               images=None):
        lstImages = []
        if not images is None:
            lstImages += images

        if dctRenderInfo is None:
            for name, oChannel in self._channel_registry.iteritems():
                for strRegion, oContainer in oChannel.dctContainers.iteritems():
                    strHexColor, fAlpha = oChannel.dctAreaRendering[strRegion]
                    imgRaw = oChannel.meta_image.image
                    imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                    ccore.drawContour(oContainer.getBinary(), imgCon, 255, False)
                    lstImages.append((imgRaw, strHexColor, 1.0))
                    lstImages.append((imgCon, strHexColor, fAlpha))
        else:
            for channel_name, dctChannelInfo in dctRenderInfo.iteritems():
                if channel_name in self._channel_registry:
                    oChannel = self._channel_registry[channel_name]
                    if 'raw' in dctChannelInfo:
                        strHexColor, fAlpha = dctChannelInfo['raw']
                        lstImages.append((oChannel.meta_image.image, strHexColor, fAlpha))

                    if 'contours' in dctChannelInfo:
                        # transform the old dict-style to the new tuple-style,
                        # which allows multiple definitions for one region
                        if type(dctChannelInfo['contours']) == types.DictType:
                            lstContourInfos = [(k,)+v
                                               for k,v in dctChannelInfo['contours'].iteritems()]
                        else:
                            lstContourInfos = dctChannelInfo['contours']

                        for tplData in lstContourInfos:
                            strRegion, strNameOrColor, fAlpha, bShowLabels = tplData[:4]

                            # draw contours only if region is present
                            if oChannel.has_region(strRegion):
                                if len(tplData) > 4:
                                    bThickContours = tplData[4]
                                else:
                                    bThickContours = False
                                if strNameOrColor == 'class_label':
                                    oContainer = oChannel.dctContainers[strRegion]
                                    oRegion = oChannel.get_region(strRegion)
                                    dctLabels = {}
                                    dctColors = {}
                                    for iObjId, oObj in oRegion.iteritems():
                                        iLabel = oObj.iLabel
                                        if not iLabel is None:
                                            if not iLabel in dctLabels:
                                                dctLabels[iLabel] = []
                                            dctLabels[iLabel].append(iObjId)
                                            dctColors[iLabel] = oObj.strHexColor
                                    #print dctLabels
                                    imgRaw = oChannel.meta_image.image
                                    imgCon2 = ccore.Image(imgRaw.width, imgRaw.height)
                                    for iLabel, lstObjIds in dctLabels.iteritems():
                                        imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                                        oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, False)
                                        lstImages.append((imgCon, dctColors[iLabel], fAlpha))

                                        if type(bShowLabels) == types.BooleanType and bShowLabels:
                                        #    oContainer.drawTextsByIds(lstObjIds, lstObjIds, imgCon2)
                                        #else:
                                            oContainer.drawTextsByIds(lstObjIds, [str(iLabel)]*len(lstObjIds), imgCon2)
                                    lstImages.append((imgCon2, '#FFFFFF', 1.0))

                                else:
                                    oContainer = oChannel.dctContainers[strRegion]
                                    oRegion = oChannel.get_region(strRegion)
                                    lstObjIds = oRegion.keys()
                                    imgRaw = oChannel.meta_image.image
                                    imgCon = ccore.Image(imgRaw.width, imgRaw.height)
                                    if not strNameOrColor is None:
                                        oContainer.drawContoursByIds(lstObjIds, 255, imgCon, bThickContours, False)
                                    else:
                                        strNameOrColor = '#FFFFFF'
                                    lstImages.append((imgCon, strNameOrColor, fAlpha))
                                    if bShowLabels:
                                        imgCon2 = ccore.Image(imgRaw.width, imgRaw.height)
                                        oContainer.drawLabelsByIds(lstObjIds, imgCon2)
                                        lstImages.append((imgCon2, '#FFFFFF', 1.0))


        if len(lstImages) > 0:
            imgRgb = ccore.makeRGBImage([x[0].getView() for x in lstImages],
                                        [ccore.RGBValue(*hexToRgb(x[1])) for x in lstImages],
                                        [x[2] for x in lstImages])

            if writeToDisc:
                strFilePath = os.path.join(strPathOut, "P%s_T%05d%s" % (self.P, self._iT, strFileSuffix))
                safe_mkdirs(strPathOut)
                ccore.writeImage(imgRgb, strFilePath, strCompression)
                self._oLogger.debug("* rendered image written '%s'" % strFilePath)
            else:
                strFilePath = ''
            return imgRgb, strFilePath


    def collectObjects(self, plate_id, P, lstReader, oLearner, byTime=True):

        #channel_name = oLearner.strChannelId
        strRegionId = oLearner.strRegionId
        img_rgb = None

        self._oLogger.debug('* collecting samples...')

#        bSuccess = True
#        channels = sorted(self._channel_registry.values())
#        primary_cChannel = None
#        for channel2 in lstChannels:
#
#            self.time_holder.prepare_raw_image(channel)
#            self.time_holder.apply_segmentation(oChannel2, oPrimaryChannel)
#
#            if oPrimaryChannel is None:
#                assert oChannel2.RANK == 1
#                oPrimaryChannel = oChannel2
        self.process(apply = False, extract_features = False)

        # self._channel_registry
        oChannel = self._channel_registry[oLearner.channel_name]
        oContainer = oChannel.get_container(strRegionId)
        objects = oContainer.getObjects()

        object_lookup = {}
        for oReader in lstReader:
            lstCoordinates = None
            if (byTime and P == oReader.getPosition() and self._iT in oReader):
                lstCoordinates = oReader[self._iT]
            elif (not byTime and P in oReader):
                lstCoordinates = oReader[P]
            #print "moo", P, oReader.getPosition(), byTime, self._iT in oReader
            #print lstCoordinates, byTime, self.P, oReader.keys()

            if not lstCoordinates is None:
                #print self.iP, self._iT, lstCoordinates
                for dctData in lstCoordinates:
                    label = dctData['iClassLabel']
                    if (label in oLearner.dctClassNames and
                        dctData['iPosX'] >= 0 and
                        dctData['iPosX'] < oContainer.width and
                        dctData['iPosY'] >= 0 and
                        dctData['iPosY'] < oContainer.height):

                        center1 = ccore.Diff2D(dctData['iPosX'],
                                               dctData['iPosY'])

                        # test for obj_id "under" annotated pixel first
                        obj_id = oContainer.img_labels[center1]

                        # if not background: valid obj_id found
                        if obj_id > 0:
                            dict_append_list(object_lookup, label, obj_id)

                        # otherwise try to find nearest object in a search
                        # radius of 30 pixel (compatibility with CellCounter)
                        else:
                            dists = []
                            for obj_id, obj in objects.iteritems():
                                diff = obj.oCenterAbs - center1
                                dist_sq = diff.squaredMagnitude()
                                # limit to 30 pixel radius
                                if dist_sq < 900:
                                    dists.append((obj_id, dist_sq))
                            if len(dists) > 0:
                                dists.sort(lambda a,b: cmp(a[1], b[1]))
                                obj_id = dists[0][0]
                                dict_append_list(object_lookup, label, obj_id)

        object_ids = set(flatten(object_lookup.values()))
        objects_del = set(objects.keys()) - object_ids
        for obj_id in objects_del:
            oContainer.delObject(obj_id)

        self.time_holder.apply_features(oChannel)
        region = oChannel.get_region(strRegionId)

        learner_objects = []
        for label, object_ids in object_lookup.iteritems():
            class_name = oLearner.dctClassNames[label]
            hex_color = oLearner.dctHexColors[class_name]
            rgb_value = ccore.RGBValue(*hexToRgb(hex_color))
            for obj_id in object_ids:
                obj = region[obj_id]
                obj.iLabel = label
                obj.strClassName = class_name
                obj.strHexColor = hex_color

                if (obj.oRoi.upperLeft[0] >= 0 and
                    obj.oRoi.upperLeft[1] >= 0 and
                    obj.oRoi.lowerRight[0] < oContainer.width and
                    obj.oRoi.lowerRight[1] < oContainer.height):
                    iCenterX, iCenterY = obj.oCenterAbs

                    strPathOutLabel = os.path.join(oLearner.dctEnvPaths['samples'],
                                                   oLearner.dctClassNames[label])
                    safe_mkdirs(strPathOutLabel)

                    strFilenameBase = 'PL%s___P%s___T%05d___X%04d___Y%04d' % (plate_id, self.P, self._iT, iCenterX, iCenterY)

                    obj.sample_id = strFilenameBase
                    learner_objects.append(obj)

                    strFilenameImg = os.path.join(strPathOutLabel, '%s___img.png' % strFilenameBase)
                    strFilenameMsk = os.path.join(strPathOutLabel, '%s___msk.png' % strFilenameBase)
                    #print strFilenameImg, strFilenameMsk
                    oContainer.exportObject(obj_id,
                                            strFilenameImg,
                                            strFilenameMsk)

                    oContainer.markObjects([obj_id], rgb_value, False, True)

                    #print obj_id, obj.oCenterAbs, iCenterX, iCenterY
                    ccore.drawFilledCircle(ccore.Diff2D(iCenterX, iCenterY),
                                           3, oContainer.img_rgb, rgb_value)


        if len(learner_objects) > 0:
            oLearner.applyObjects(learner_objects)
            # we don't want to apply None for feature names
            oLearner.setFeatureNames(oChannel.lstFeatureNames)

        strPathOut = os.path.join(oLearner.dctEnvPaths['controls'])
        safe_mkdirs(strPathOut)
        oContainer.exportRGB(os.path.join(strPathOut,
                                          "P%s_T%05d_C%s_R%s.jpg" %\
                                           (self.P, self._iT, oLearner.strChannelId, oLearner.strRegionId)),
                            '90')
        img_rgb = oContainer.img_rgb
        return img_rgb


    def classifyObjects(self, oPredictor):
        channel_name = oPredictor.strChannelId
        strRegionId = oPredictor.strRegionId
        oChannel = self._channel_registry[channel_name]
        oRegion = oChannel.get_region(strRegionId)
        for iObjId, oObj in oRegion.iteritems():
            iLabel, dctProb = oPredictor.predict(oObj.aFeatures.copy(), oRegion.getFeatureNames())
            oObj.iLabel = iLabel
            oObj.dctProb = dctProb
            oObj.strClassName = oPredictor.dctClassNames[iLabel]
            oObj.strHexColor = oPredictor.dctHexColors[oObj.strClassName]

