"""
metadata.py

"""
from __future__ import absolute_import
from __future__ import print_function
import six

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = 'LGPL'




__all__ = ('MetaData', 'MetaDataError', 'MetaImage')

from collections import OrderedDict

import numpy
import vigra

from cecog import ccore
from cecog.io.constants import PixelType
from cecog.io.constants import MetaInfo
from cecog.io.xmlserializer import XmlSerializer


class MetaDataError(ValueError):
    pass


class MetaData(XmlSerializer):

    def __init__(self):
        super(MetaData, self).__init__()

        self.dim_x = None
        self.dim_y = None
        self.dim_z = None
        self.dim_c = None
        self.dim_t = None
        self.dim_p = None

        self.real_image_width = None
        self.real_image_height = None

        self.has_timelapse = False
        self.has_timestamp_info = False
        self.has_condition_info = False
        self.has_well_info = False

        self.zslices = None
        self.channels = None
        self.times = None
        self.positions = None
        self.plateids = None

        self.image_files = 0

        self._timestamps_relative = {}
        self._timestamps_absolute = {}
        self._timestamp_summary = {}

        self.plate_timestamp_info = None

        self._position_well_map = {}

        self.pixel_type = None

    @property
    def pixel_range(self):
        return PixelType.range(self.pixel_type)

    def set_image_info(self, info):
        self.dim_x = info.width
        self.dim_y = info.height
        self.real_image_width = info.width
        self.real_image_height = info.height

        # ccore returns upper case type names, numpy is lower case
        ptype = info.pixel_type.lower()
        if not PixelType.is_valid(ptype):
            raise TypeError('Pixel type is not understood')
        self.pixel_type = ptype

    def get_timestamp_info(self, position):
        try:
            info = self._timestamp_summary[position]
        except KeyError:
            info = None
        return info

    def get_timestamp_relative(self, coordinate):
        try:
            timestamp = self._timestamps_relative[coordinate.position] \
                                                 [coordinate.time]
        except KeyError:
            timestamp = float('NAN')
        return timestamp

    def get_timestamp_absolute(self, coordinate):
        try:
            timestamp = self._timestamps_absolute[coordinate.position] \
                                                 [coordinate.time]
        except KeyError:
            timestamp = float('NAN')
        return timestamp

    def append_absolute_time(self, position, time, timestamp):
        if not position in self._timestamps_absolute:
            self._timestamps_absolute[position] = OrderedDict()
        self._timestamps_absolute[position][time] = timestamp
        self.has_timestamp_info = True

    def append_well_subwell_info(self, position, well, subwell):
        if not position in self._position_well_map:
            self._position_well_map[position] = {MetaInfo.Well: well,
                                                 MetaInfo.Subwell: subwell}

        self.has_well_info = True

    def get_well_and_subwell(self, position):
        if position in self._position_well_map:
            result = (self._position_well_map[position][MetaInfo.Well],
                      self._position_well_map[position][MetaInfo.Subwell])
        else:
            result = (None, None)
        return result

    def get_well_and_subwell_dict(self):
        wells_subwell_pairs = [(self._position_well_map[x][MetaInfo.Well],
                                self._position_well_map[x][MetaInfo.Subwell])
                                for x in list(self._position_well_map.keys())]
        well_map = {}
        for well, subwell in wells_subwell_pairs:
            if well in ['', None]:
                continue
            if not well in well_map:
                well_map[well] = []
            if not subwell in ['', None]:
                well_map[well].append(subwell)

        return well_map

    def setup(self):
        for pos, od in six.iteritems(self._timestamps_absolute):
            sorted_od = OrderedDict(sorted(six.iteritems(od), key=lambda o: o[0]))
            self._timestamps_absolute[pos] = sorted_od
        for position, timestamps in six.iteritems(self._timestamps_absolute):
            base_time = list(timestamps.values())[0]
            self._timestamps_relative[position] = OrderedDict()
            for frame, timestamp in six.iteritems(timestamps):
                self._timestamps_relative[position][frame] = \
                    timestamp - base_time
        for position, timestamps in six.iteritems(self._timestamps_absolute):
            values = numpy.array(list(timestamps.values()))
            diff = numpy.diff(values)
            self._timestamp_summary[position] = (numpy.mean(diff),
                                                 numpy.std(diff))

        if self.has_timestamp_info:
            values = numpy.array(list(self._timestamp_summary.values()))
            mean = numpy.mean(values, axis=0)
            std = numpy.std(values, axis=0)
            self.plate_timestamp_info = (mean[0], std[0] + mean[1])

        self.dim_p = len(self.positions)
        self.dim_t = len(self.times)
        self.dim_c = len(self.channels)
        self.dim_z = len(self.zslices)
        self.has_timelapse = self.dim_t > 1

    def h(self, a):
        if len(a) == 0:
            s = '[ - ]'
        elif len(a) == 1:
            s = '[ %s ]' % a[0]
        elif len(a) > 1:
            s = '[ %s ... %s ]' % (a[0], a[-1])
        return s

    def format(self):
        strings = []
        head = "*   Imaging MetaData   *"
        line = "*"*len(head)
        strings += [line]
        strings += [head]
        strings += [line]
        strings += ["* Positions: %s %s" %
                    (self.dim_p, self.h(self.positions))]
        if len(self.times) > 0:
            strings += ["* Time-points: %s (%d - %d)" %
                        (self.dim_t, min(self.times), max(self.times))]
        else:
            strings += ["* Time-points: %s" % self.dim_t]
        strings += ["* Channels: %s %s" % (self.dim_c, self.channels)]
        strings += ["* Z-slices: %s %s" % (self.dim_z, self.zslices)]
        strings += ["* Height: %s" % self.dim_y]
        strings += ["* Width: %s" % self.dim_x]
        strings += ["* Wells: %s" % len(self.get_well_and_subwell_dict())]
        strings += [line]
        return "\n".join(strings)

    def get_frames_of_position(self, pos):
        return list(self._timestamps_absolute[pos].keys())

    def __str__(self):
        return self.format()


class MetaImage(object):
    """
    Simple container to hold an image and its dimensions.
    Image reading is implemented lazy.
    """
    _crop_coordinates = None

    @classmethod
    def get_crop_coordinates(cls):
        return cls._crop_coordinates

    def __init__(self, image_container=None, coordinate=None,
                 height=None, width=None):
        self.coordinate = coordinate
        self.img_height = height
        self.img_width = width
        self.image_container = image_container
        self._img = None
        self._img_c = None

    @property
    def format(self):
        try:
            image = self.image
        except:
            print('MetaImage.format(): No image loaded')
            raise
        if isinstance(image, (ccore.UInt16Image,)):
            return numpy.uint16
        elif isinstance(image, (ccore.Image,)):
            return numpy.uint8
        else:
            raise RuntimeError('MetaImage.format(): Unknown pixel type')

    @property
    def width(self):
        return self.image.width

    @property
    def height(self):
        return self.image.height

    @property
    def raw_width(self):
        return self._raw_image.width

    @property
    def raw_height(self):
        return self._raw_image.height

    @property
    def image(self):
        if MetaImage._crop_coordinates is None:
            return self._raw_image
        else:
            return self._cropped_image

    @property
    def _raw_image(self):
        if self._img is None:
            self._img = self.image_container.get_image(self.coordinate)
        return self._img

    @property
    def _cropped_image(self):
        if self._img_c is None:
            self._img_c = ccore.subImage(
                self._raw_image, ccore.Diff2D(MetaImage._crop_coordinates[0],
                                              MetaImage._crop_coordinates[1]),
                ccore.Diff2D(MetaImage._crop_coordinates[2],
                             MetaImage._crop_coordinates[3]))
        return self._img_c

    def set_raw_image(self, img):
        self._img = img

    def set_cropped_image(self, img):
        self._img_c = img

    def set_image(self, img):
        if self._crop_coordinates is None:
            self.set_raw_image(img)
        else:
            self.set_cropped_image(img)

    @classmethod
    def _check_crop_coordinates(cls, x0, y0, width, height):
        ok = True
        if x0 < 0 or y0 < 0 or width < 0 or height < 0:
            ok = False
        return ok

    @classmethod
    def enable_cropping(cls, x0, y0, width, height):
        if cls._check_crop_coordinates(x0, y0, width, height):
            cls._crop_coordinates = (x0, y0, width, height)
        else:
            raise RuntimeError('wrong crop coordinates')

    @classmethod
    def disable_cropping(cls):
        MetaImage._crop_coordinates = None

    @property
    def vigra_image(self):
        ar = self.image.toArray()
        return vigra.Image(ar, dtype=ar.dtype)
