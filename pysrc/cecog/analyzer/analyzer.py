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
       logging, \
       zlib, \
       base64

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
import h5py

#-------------------------------------------------------------------------------
# cecog module imports:
#

from cecog import ccore

from cecog.util.util import hexToRgb
from cecog.analyzer import (REGION_NAMES,
                            REGION_NAMES_PRIMARY,
                            REGION_NAMES_SECONDARY,
                            )
from cecog.io.imagecontainer import (Coordinate,
                                     MetaImage,
                                     )

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

    HDF5_GRP_DEFINITIONS = "/definitions"
    HDF5_GRP_RELATIONS = "/relations"
    HDF5_GRP_IMAGES = "/images"
    HDF5_GRP_FRAMES = "/frames"
    HDF5_GRP_REGIONS = "regions"
    HDF5_GRP_REGION_CHANNEL = "region_and_channel"

    def __init__(self, P, channels, filename_hdf5, meta_data, settings,
                 analysis_frames,
                 hdf5_create=True, hdf5_compression='gzip',
                 hdf5_include_raw_images=True,
                 hdf5_include_label_images=True, hdf5_include_features=True,
                 hdf5_include_classification=True, hdf5_include_crack=True,
                 hdf5_include_tracking=True, hdf5_include_events=True):
        super(TimeHolder, self).__init__()
        self.P = P
        self._iCurrentT = None
        self.channels = channels
        self._meta_data = meta_data
        self._settings = settings

        self._hdf5_create = hdf5_create
        self._hdf5_include_raw_images = hdf5_include_raw_images
        self._hdf5_include_label_images = hdf5_include_label_images
        self._hdf5_include_features = hdf5_include_features
        self._hdf5_include_classification = hdf5_include_classification
        self._hdf5_include_crack = hdf5_include_crack
        self._hdf5_include_tracking = hdf5_include_tracking
        self._hdf5_include_events = hdf5_include_events
        self._hdf5_compression = hdf5_compression

        self._logger = logging.getLogger(self.__class__.__name__)
        # frames get an index representation with the NC file, starting at 0
        frames = sorted(analysis_frames)
        self._frames_to_idx = dict([(f,i) for i, f in enumerate(frames)])
        self._idx_to_frames = dict([(i,f) for i, f in enumerate(frames)])

        self._channel_info = [('primary',
                               settings.get('ObjectDetection',
                                            'primary_channelid'))]
        self._region_infos = [('primary', 'primary__primary', 'primary')]
        settings.set_section('ObjectDetection')
        for prefix in ['secondary', 'tertiary']:
            if settings.get('Processing', '%s_processchannel' % prefix):
                name = settings.get('ObjectDetection', '%s_channelid' % prefix)
                self._channel_info.append((prefix, name))
                for name in REGION_NAMES_SECONDARY:
                    if settings.get2('%s_regions_%s' % (prefix, name)):
                        self._region_infos.append((prefix,
                                                   '%s__%s' % (prefix, name),
                                                   name))

        self._channels_to_idx = OrderedDict([(n[0], i) for i, n in
                                             enumerate(self._channel_info)])
        self._regions_to_idx = OrderedDict([(n[1], i) for i, n in
                                            enumerate(self._region_infos)])
        self._edge_to_idx = {}

        if self._hdf5_create:
            f = h5py.File(filename_hdf5, 'w')
            self._hdf5_file = f

            if self._meta_data.has_timelapse:
                f.create_group(self.HDF5_GRP_FRAMES)
            else:
                f.create_group(self.HDF5_GRP_REGIONS)

            if self._hdf5_include_raw_images or self._hdf5_include_label_images:
                f.create_group(self.HDF5_GRP_IMAGES)
            f.create_group(self.HDF5_GRP_RELATIONS)
            grp_def = f.create_group(self.HDF5_GRP_DEFINITIONS)

            if self._meta_data.has_timelapse:
                dtype = numpy.dtype([('frame', 'i'), ('timestamp_abs', 'i'),
                                     ('timestamp_rel', 'i')])
                nr_frames = len(frames)
                var = grp_def.create_dataset('frames', (nr_frames,),
                                             dtype,
                                             chunks=(1,),
                                             compression=self._hdf5_compression)
                for frame in frames:
                    idx = self._frames_to_idx[frame]
                    coord = Coordinate(position=self.P, time=frame)
                    ts_abs = meta_data.get_timestamp_absolute(coord)
                    ts_rel = meta_data.get_timestamp_relative(coord)
                    var[idx] = (frame, ts_abs, ts_rel)

            dtype = numpy.dtype([('channel_name', '|S50'),
                                 ('description', '|S100'),
                                 ('is_physical', bool)])

            nr_channels = len(self._channel_info)
            var = grp_def.create_dataset('channels', (nr_channels,), dtype)
            for idx in self._channels_to_idx.values():
                data = (self._channel_info[idx][0],
                        self._channel_info[idx][1],
                        True)
                var[idx] = data

            dtype = numpy.dtype([('region_name', '|S50'),
                                 ('channel_idx', 'i')])
            nr_labels = len(self._regions_to_idx)
            var = grp_def.create_dataset('regions', (nr_labels,),
                                         dtype)
            for tpl in self._region_infos:
                channel_name, combined = tpl[:2]
                idx = self._regions_to_idx[combined]
                channel_idx = self._channels_to_idx[channel_name]
                var[idx] = (combined, channel_idx)

            if self._hdf5_include_features or self._hdf5_include_classification:
                dt = numpy.dtype([('region_idx', 'int32'),
                                  ('channel_idx', 'int32')])
                grp_region_channel = \
                    grp_def.create_group(self.HDF5_GRP_REGION_CHANNEL)
                self._region_channel_idx = {}
                for idx, tpl in enumerate(self._region_infos):
                    name = str(idx)
                    channel_name, combined, region_name = tpl
                    grp_current = grp_region_channel.create_group(name)
                    var_region_channel = \
                        grp_current.create_dataset('relation', (1,), dt)
                    var_region_channel[:] = \
                        (self._regions_to_idx[combined],
                         self._channels_to_idx[channel_name])
                    if not channel_name in self._region_channel_idx:
                        self._region_channel_idx[channel_name] = {}
                    self._region_channel_idx[channel_name][region_name] = name

    def close_all(self):
        if self._hdf5_create:
            self._hdf5_file.close()

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

    def _convert_region_name(self, channel_name, region_name):
        return '%s__%s' % (channel_name.lower(), region_name)

    def apply_channel(self, oChannel):
        iT = self._iCurrentT
        if not iT in self:
            self[iT] = OrderedDict()
        self[iT][oChannel.NAME] = oChannel
        self[iT].sort(key = lambda x: self[iT][x])

    def apply_segmentation(self, channel, primary_channel=None):
        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)
        channel.apply_segmentation(primary_channel)

        if self._hdf5_create and self._hdf5_include_label_images:
            meta = self._meta_data
            w = meta.real_image_width
            h = meta.real_image_height
            z = meta.dim_z
            t = len(self._frames_to_idx)
            f = self._hdf5_file
            var_name = 'regions'
            grp = f[self.HDF5_GRP_IMAGES]
            if var_name in grp:
                var_labels = grp[var_name]
            else:
                nr_labels = len(self._regions_to_idx)
                var_labels = \
                    grp.create_dataset(var_name,
                                       (nr_labels, t, z, h, w),
                                       'int32',
                                       chunks=(1, 1, z, h, w),
                                       compression=self._hdf5_compression)

            frame_idx = self._frames_to_idx[self._iCurrentT]
            for region_name in channel.lstAreaSelection:
                idx = self._regions_to_idx[
                        self._convert_region_name(channel.PREFIX, region_name)]
                container = channel.dctContainers[region_name]
                array = container.img_labels.toArray(copy=False)
                var_labels[idx, frame_idx, 0] = numpy.require(array, 'int32')


    def prepare_raw_image(self, channel):
        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)
        channel.apply_zselection()
        channel.normalize_image()
        channel.apply_registration()

        if self._hdf5_create and self._hdf5_include_raw_images:
            meta = self._meta_data
            w = meta.real_image_width
            h = meta.real_image_height
            z = meta.dim_z
            t = len(self._frames_to_idx)
            f = self._hdf5_file
            nr_channels = len(self._channel_info)
            var_name = 'channels'
            grp = f[self.HDF5_GRP_IMAGES]
            if var_name in grp:
                var_images = grp[var_name]
            else:
                var_images = \
                    grp.create_dataset(var_name,
                                       (nr_channels, t, z, h, w),
                                       'uint8',
                                       chunks=(1, 1, 1, h, w),
                                       compression=self._hdf5_compression)

            frame_idx = self._frames_to_idx[self._iCurrentT]
            channel_idx = self._channels_to_idx[channel.PREFIX]
            img = channel.meta_image.image
            array = img.toArray(copy=False)
            var_images[channel_idx, frame_idx, 0] = array

    def _get_regions_group(self):
        f = self._hdf5_file
        if self._meta_data.has_timelapse:
            grp_frames = f[self.HDF5_GRP_FRAMES]
            var_name = str(self._frames_to_idx[self._iCurrentT])
            if not var_name in grp_frames:
                grp_current = grp_frames.create_group(var_name)
            else:
                grp_current = grp_frames[var_name]
        else:
            grp_current = f

        if not self.HDF5_GRP_REGIONS in grp_current:
            grp_region = grp_current.create_group(self.HDF5_GRP_REGIONS)
        else:
            grp_region = grp_current[self.HDF5_GRP_REGIONS]

        return grp_region


    def apply_features(self, channel):
        desc = '[P %s, T %05d, C %s]' % (self.P, self._iCurrentT,
                                         channel.strChannelId)

        name = channel.NAME.lower()
        channel.apply_features()

        if self._hdf5_create:
            f = self._hdf5_file

            grp_def = f[self.HDF5_GRP_DEFINITIONS]
            grp_region = self._get_regions_group()

            for region_name in channel.region_names():
                idx = self._regions_to_idx[
                        self._convert_region_name(name, region_name)]
                grp_name = str(idx)
                grp_current_region = grp_region.create_group(grp_name)

                region = channel.get_region(region_name)
                feature_names = region.getFeatureNames()
                nr_features = len(feature_names)
                nr_objects = len(region)

                dtype = numpy.dtype([('obj_id', 'int32'),
                                     ('upper_left', 'int32', 2),
                                     ('lower_right', 'int32', 2),
                                     ('center', 'int32', 2)])
                var_objects = \
                    grp_current_region.create_dataset('objects',
                                             (nr_objects,),
                                             dtype,
                                             chunks=(nr_objects,),
                                             compression=self._hdf5_compression)

                if (self._hdf5_include_features or
                    self._hdf5_include_classification):

                    name = self._region_channel_idx[channel.PREFIX][region_name]

                    grp_region_channel = \
                        grp_current_region.create_group(
                                                self.HDF5_GRP_REGION_CHANNEL)
                    grp_current_region_channel = \
                        grp_region_channel.create_group(name)

                    if self._hdf5_include_features:
                        grp_current_region_channel2 = \
                            grp_def[self.HDF5_GRP_REGION_CHANNEL][name]
                        var_name = "feature_names"
                        if not var_name in grp_current_region_channel2:
                            dt = h5py.new_vlen(str)
                            var_fnames = \
                                grp_current_region_channel2.create_dataset(
                                                 var_name, (nr_features,), dt)
                            var_fnames[:] = feature_names

                        var_features = \
                            grp_current_region_channel.create_dataset(
                                            'features',
                                            (nr_objects, nr_features),
                                            'float',
                                            chunks=(nr_objects, nr_features),
                                            compression=self._hdf5_compression)

                if self._hdf5_include_crack:
                    dt = h5py.new_vlen(str)
                    var_crack = \
                        grp_current_region.create_dataset('crack_contours',
                                            (nr_objects, ), dt,
                                            chunks=(1, ),
                                            compression=self._hdf5_compression)
                for idx, obj_id in enumerate(region):
                    obj = region[obj_id]

                    var_objects[idx] = (obj_id,
                                        obj.oRoi.upperLeft, obj.oRoi.lowerRight,
                                        obj.oCenterAbs)

                    if self._hdf5_include_features:
                        var_features[idx] = region[obj_id].aFeatures

                    if self._hdf5_include_crack:
                        data = ','.join(map(str, flatten(obj.crack_contour)))
                        # FIXME: VLEN(str) compression seems not to work in
                        #        h5py. 'external' compression is not nice
                        var_crack[idx] = base64.b64encode(zlib.compress(data))

    def serialize_tracking(self, tracker):
        graph = tracker.get_graph()
        channel_name = tracker._channelId
        region_name = tracker._regionName
        if self._hdf5_create and self._hdf5_include_tracking:
            grp = self._hdf5_file[self.HDF5_GRP_RELATIONS]
            nr_edges = graph.number_of_edges()
            dtype = numpy.dtype([('region_idx1', 'int32'),
                                 ('frame_idx1', 'int32'),
                                 ('obj_idx1', 'int32'),
                                 ('region_idx2', 'int32'),
                                 ('frame_idx2', 'int32'),
                                 ('obj_idx2', 'int32')])
            var = grp.create_dataset('tracking',
                                     (nr_edges, ),
                                     dtype,
                                     chunks=(1,),
                                     compression=self._hdf5_compression)

            region_idx = self._regions_to_idx[
                self._convert_region_name(channel_name.lower(), region_name)]

            for idx, edge in enumerate(graph.edges.itervalues()):
                head_id, tail_id = edge[:2]
                self._edge_to_idx[(head_id, tail_id)] = idx
                head_frame, head_obj_id = \
                    tracker.getComponentsFromNodeId(head_id)[:2]
                tail_frame, tail_obj_id = \
                    tracker.getComponentsFromNodeId(tail_id)[:2]
                head_frame_idx = self._frames_to_idx[head_frame]
                tail_frame_idx = self._frames_to_idx[tail_frame]

                head_region = \
                    self[head_frame][channel_name].get_region(region_name)
                tail_region = \
                    self[tail_frame][channel_name].get_region(region_name)
                head_obj_idx = head_region.index(head_obj_id)
                tail_obj_idx = tail_region.index(tail_obj_id)
                var[idx] = (region_idx, head_frame_idx, head_obj_idx,
                            region_idx, tail_frame_idx, tail_obj_idx)

    def serialize_events(self, tracker):
        if self._hdf5_create and self._hdf5_include_events:
            grp = self._hdf5_file[self.HDF5_GRP_RELATIONS]
            grp_events = grp.create_group('events')

            nr_events = 0
            nr_edges = None
            nr_daughters = 0
            daughters = {}
            for events in tracker.dctVisitorData.itervalues():
                for start_id, event in events.iteritems():
                    if start_id[0] != '_':
                        frame, obj_id = \
                            tracker.getComponentsFromNodeId(start_id)[:2]
                        new_id = tracker.getNodeIdFromComponents(frame, obj_id)
                        if not new_id in daughters:
                            daughters[new_id] = []
                            nr_daughters += 1
                        daughters[new_id].append(start_id)
                        nr_events += 1
                        if nr_edges is None:
                            nr_edges = event['maxLength']-1

            #dtype = numpy.dtype([('tracking_idx', 'i')])
            var_edges = \
                grp_events.create_dataset('edges',
                                          (nr_events, nr_edges),
                                          'int32',
                                          chunks=(1, nr_edges),
                                          compression=self._hdf5_compression)
            dtype = numpy.dtype([('daughter_idx1', 'int32'),
                                 ('daughter_idx2', 'int32'),
                                 ('has_daughter', bool),
                                 ('event_idx', 'int32'),
                                 ('split_idx', 'int32'),
                                 ('has_split', bool),
                                 ])
            var_dau = \
                grp_events.create_dataset('daughters',
                                          (nr_daughters, ),
                                          dtype,
                                          chunks=(1,),
                                          compression=self._hdf5_compression)

            event_idx = 0
            edges_to_idx = {}
            for events in tracker.dctVisitorData.itervalues():
                for start_id, event in events.iteritems():
                    if start_id[0] != '_':
                        track = event['tracks'][0]
                        event_id, split_id = -1, -1
                        for idx, (head_id, tail_id) in \
                            enumerate(zip(track, track[1:])):
                            edge_idx = self._edge_to_idx[(head_id, tail_id)]
                            var_edges[event_idx, idx] = edge_idx
                            if head_id == event['splitId']:
                                split_id = idx
                            if head_id == event['eventId']:
                                event_id = idx
                        edges_to_idx[start_id] = (event_idx, event_id, split_id)
                        event_idx += 1
            for idx, node_ids in enumerate(daughters.itervalues()):
                d1_info = edges_to_idx[node_ids[0]]
                if len(node_ids) > 1:
                    d2_info = edges_to_idx[node_ids[1]]
                    assert d1_info[1] == d2_info[1]
                    assert d1_info[2] == d2_info[2]
                    d2_idx = d2_info[0]
                    has_daughter = True
                else:
                    d2_idx = -1
                    has_daughter = False
                var_dau[idx] = (d1_info[0], d2_idx, has_daughter,
                                d1_info[1], d1_info[2], d1_info[2] > -1)

    def serialize_region_hierarchy(self, channel_name, region_name):

        if self._hdf5_create:# and self._hdf5_include_tracking:
            grp = self._hdf5_file[self.HDF5_GRP_RELATIONS]

            nr_values = 0
            for frame, channels in self.iteritems():
                channel = channels[channel_name]
                region = channel.get_region(region_name)
                nr_values += len(region)
            nr_regions = len(self._region_infos) - 1
            nr_values *= nr_regions
            dtype = numpy.dtype([('region_idx1', 'i'),
                                 ('frame_idx1', 'i'),
                                 ('obj_idx1', 'i'),
                                 ('region_idx2', 'i'),
                                 ('frame_idx2', 'i'),
                                 ('obj_idx2', 'i')])
            if nr_regions > 0:
                var = grp.create_dataset('region_hierarchy',
                                         (nr_values,),
                                         dtype,
                                         chunks=(nr_regions,),
                                         compression=self._hdf5_compression)

                region_idx1 = self._regions_to_idx[
                    self._convert_region_name(channel_name.lower(),
                                              region_name)]

                idx = 0
                for frame, channels in self.iteritems():
                    frame_idx = self._frames_to_idx[frame]
                    channel = channels[channel_name]
                    region = channel.get_region(region_name)
                    for obj_id in region:
                        # get the index of the obj_id in the OrderedDict
                        obj_idx = region.index(obj_id)
                        for info in self._region_infos[1:]:
                            region_idx2 = self._regions_to_idx[info[1]]
                            var[idx] = (region_idx1, frame_idx, obj_idx,
                                        region_idx2, frame_idx, obj_idx)
                            idx += 1

    def serialize_classification(self, channel_name, region_name, class_info):
        if self._hdf5_create and self._hdf5_include_classification:
            channel = self[self._iCurrentT][channel_name]
            region = channel.get_region(region_name)
            nr_classes = len(class_info)

            grp_def = self._hdf5_file[self.HDF5_GRP_DEFINITIONS]
            region_channel = \
                self._region_channel_idx[channel.PREFIX][region_name]
            grp_current_region_channel = \
                grp_def[self.HDF5_GRP_REGION_CHANNEL][region_channel]
            var_name = 'classes'
            if not var_name in grp_current_region_channel:
                dtype = numpy.dtype([('label', 'i'),
                                     ('name', '|S50')])
                var = \
                    grp_current_region_channel.create_dataset(var_name,
                                                              (nr_classes,),
                                                              dtype)
                var[:] = class_info

            var_name_region = str(self._regions_to_idx[
                        self._convert_region_name(channel_name, region_name)])
            grp_region = self._get_regions_group()
            grp = grp_region[var_name_region] \
                            [self.HDF5_GRP_REGION_CHANNEL] \
                            [region_channel]
            nr_objects = len(region)
            var_class_probs = \
                grp.create_dataset('classification_probs',
                                   (nr_objects, nr_classes),
                                   'float',
                                   chunks=(nr_objects, nr_classes),
                                   compression=self._hdf5_compression)
            var_class = \
                grp.create_dataset('classification',
                                   (nr_objects, ),
                                   'int16',
                                   chunks=(nr_objects, ),
                                   compression=self._hdf5_compression)

            label_to_idx = dict([(tpl[0], i)
                                 for i, tpl in enumerate(class_info)])
            for idx, obj_id in enumerate(region):
                obj = region[obj_id]
                var_class[idx] = label_to_idx[obj.iLabel]
                var_class_probs[idx] = obj.dctProb.values()


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


    def classify_objects(self, predictor):
        channel_name = predictor.strChannelId
        region_name = predictor.strRegionId
        channel = self._channel_registry[channel_name]
        region = channel.get_region(region_name)
        for obj in region.itervalues():
            label, probs = predictor.predict(obj.aFeatures,
                                             region.getFeatureNames())
            obj.iLabel = label
            obj.dctProb = probs
            obj.strClassName = predictor.dctClassNames[label]
            obj.strHexColor = predictor.dctHexColors[obj.strClassName]

        class_info = zip(predictor.lstClassLabels, predictor.lstClassNames)
        self.time_holder.serialize_classification(channel_name, region_name,
                                                  class_info)
