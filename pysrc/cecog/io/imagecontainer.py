"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held, Thomas Walter'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['DIMENSION_NAME_POSITION',
           'DIMENSION_NAME_TIME',
           'DIMENSION_NAME_CHANNEL',
           'DIMENSION_NAME_ZSLICE',
           'DIMENSION_NAME_HEIGHT',
           'DIMENSION_NAME_WIDTH',
           'AxisIterator',
           'ImageContainer',
           'MetaData',
           'MetaImage',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import types, \
       os
import numpy

#------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict
from pdk.datetimeutils import StopWatch
from pdk.fileutils import safe_mkdirs

#------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.config import NAMING_SCHEMAS
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.util.util import convert_package_path

#------------------------------------------------------------------------------
# constants:
#
UINT8 = 'UINT8'
UINT16 = 'UINT16'
INT8 = 'INT8'
INT16 = 'INT16'
PIXEL_TYPES = [UINT8, UINT16, INT8, INT16]
PIXEL_INFO = dict((n, n.lower()) for n in PIXEL_TYPES)

DIMENSION_NAME_POSITION = 'position'
DIMENSION_NAME_TIME = 'time'
DIMENSION_NAME_CHANNEL = 'channel'
DIMENSION_NAME_ZSLICE = 'zslice'
DIMENSION_NAME_HEIGHT = 'height'
DIMENSION_NAME_WIDTH = 'width'
META_INFO_TIMESTAMP = 'timestamp'
META_INFO_WELL = 'well'
META_INFO_SUBWELL = 'subwell'

IMAGECONTAINER_FILENAME = '.cecog_imagecontainer.txt.bz2'


#------------------------------------------------------------------------------
# functions:
#

#------------------------------------------------------------------------------
# classes:
#

class MetaData(object):

    def __init__(self):
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
    def pixel_info(self):
        return PIXEL_INFO[self.pixel_type]

    def set_image_info(self, info):
        self.dim_x = info.width
        self.dim_y = info.height
        self.pixel_type = info.pixel_type

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
            self._position_well_map[position] = {META_INFO_WELL: well,
                                                 META_INFO_SUBWELL: subwell,
                                                 }
        self.has_well_info = True

    def get_well_and_subwell(self, position):
        if position in self._position_well_map:
            result = (self._position_well_map[position][META_INFO_WELL],
                      self._position_well_map[position][META_INFO_SUBWELL])
        else:
            result = (None, None)
        return result

    def get_well_and_subwell_dict(self):
        wells_subwell_pairs = [(self._position_well_map[x][META_INFO_WELL],
                                self._position_well_map[x][META_INFO_SUBWELL])
                                for x in self._position_well_map.keys()]
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
        for position in self._timestamps_absolute:
            self._timestamps_absolute[position].sort()
        for position, timestamps in self._timestamps_absolute.iteritems():
            base_time = timestamps.values()[0]
            self._timestamps_relative[position] = OrderedDict()
            for frame, timestamp in timestamps.iteritems():
                self._timestamps_relative[position][frame] = \
                    timestamp - base_time
        for position, timestamps in self._timestamps_absolute.iteritems():
            values = numpy.array(timestamps.values())
            diff = numpy.diff(values)
            self._timestamp_summary[position] = (numpy.mean(diff),
                                                 numpy.std(diff))

        if self.has_timestamp_info:
            values = numpy.array(self._timestamp_summary.values())
            mean = numpy.mean(values, axis=0)
            std = numpy.std(values, axis=0)
            self.plate_timestamp_info = (mean[0],
                                         std[0] + mean[1])

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

    def format(self, time=True):
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
#        if time:
#            lstStr += ["* Timestamp(s):\n" + oPrinter.pformat(self.dctTimestampStrs) + "\n"]
#        lstChannels = ["%s: %s" % (key, value)
#                       for key, value in self.dctChannelMapping.iteritems()
#                       if key in self.setC]
#        lstStr += ["* Channel Mapping:\n" + oPrinter.pformat(lstChannels) + "\n"]
        strings += [line]
        return "\n".join(strings)

    def __str__(self):
        return self.format()




class MetaImage(object):
    """
    Simple container to hold an image and its dimensions.
    Image reading is implemented lazy.
    """

    def __init__(self, image_container=None, coordinate=None,
                 height=None, width=None, format=UINT8):
        self.coordinate = coordinate
        self.height = height
        self.width = width
        self.format = format
        self.image_container = image_container
        self._img = None

#    def __str__(self):
#        return "%s(P=%s,T=%s,C=%s,Z=%s,H=%s,W=%s)" % \
#               (self.__class__.__name__, self.position, self.time, self.channel,
#                self.zslice, self.height, self.width)

    @property
    def image(self):
        if self._img is None:
            self._img = self.image_container.get_image(self.coordinate)
        return self._img

    def set_image(self, img):
        self._img = img
        self.width = img.width
        self.height = img.height

#    def format_info(self, suffix=None, show_position=True, show_time=True,
#                    show_channel=True, show_zslice=True, sep='_'):
#        items = []
#        if show_position:
#            items.append("P%s" % self.position)
#        if show_time:
#            items.append("T%05d" % self.time)
#        if show_channel:
#            items.append("C%s" % self.channel)
#        if show_zslice:
#            items.append("Z%02d" % self.zslice)
#        if suffix is not None:
#            items.append(suffix)
#        return sep.join(items)



#class Axis(object):
#
#    NAME = None
#
#    def __init__(self, current=None):
#        self.values = OrderedSet()
#        self.

class AxisIterator(object):
    """
    Concept of iterator-generator chains, which are linked according the given
    experiment scan-order and result in nested loops of scan-order dimensions.

    e.g. for scan-order PTCZYX the generators are linked:
      P->T->C->Z where the last returns the XY image (here a MetaImage instance)

    The definition of break-points allows to yield a generator at any nd-space,
    which can yield a generator of the sub-space again or directly return the
    XY-images in the their scan-order.
    """

    def __init__(self, image_container, selected_values, possible_values,
                 name=None, interrupt=False, next_iter=None):
        self.image_container = image_container
        self.next_iter = next_iter
        self.interrupt = interrupt
        self.name = name
        # iterate on all possible values
        if selected_values is None:
            self.values = possible_values
        # iterate on the a given sequence of values
        elif type(selected_values) in [types.ListType, types.TupleType]:
            self.values = selected_values
        # iterate just on one given value
        elif selected_values in possible_values:
            self.values = [selected_values]
        else:
            raise ValueError("Dimension %s: "
                             "Value %s not available. Candidates are %s." %
                             (name, selected_values, possible_values))

    def __str__(self):
        return "%s (%s)" % (self.__class__.__name__, self.name)

    def __call__(self, name=None, current=None, dimensions=None):
        if dimensions is None:
            dimensions = []
        else:
            dimensions.append((name, current))
        if not self.next_iter is None:
            for value in self.values:
                # interrupt: stop the iteration and return the generator
                if self.interrupt:
                    # return the generator
                    yield value, self.next_iter(self.name, value, dimensions[:])
                else:
                    # iterate over the next generator: return elements of the
                    # next dimension
                    for next_iter in self.next_iter(self.name, value, dimensions[:]):
                        yield next_iter
        else:
            # end of generator-chain reached: return the MetaImages
            for value in self.values:
                params = dict(dimensions + [(self.name, value)])
                coordinate = Coordinate(**params)
                yield value, self.image_container.get_meta_image(coordinate)


class Coordinate(object):

    def __init__(self, plate=None, position=None, time=None, channel=None,
                 zslice=None):
        self.plate = plate
        self.position = position
        self.time = time
        self.channel = channel
        self.zslice = zslice


class ImageContainer(object):

    def __init__(self):
        self._plates = OrderedDict()
        self._meta_data = OrderedDict()
        self.has_timelapse = None

    def register_plate(self, plate_id, importer):
        self._plates[plate_id] = importer
        self._meta_data[plate_id] = importer.meta_data
        # FIXME: check some dimensions!!!
        self.has_timelapse = importer.meta_data.has_timelapse

    def iterator(self, coordinate,
                 interrupt_position=False,
                 interrupt_time=False,
                 interrupt_channel=False,
                 interrupt_zslice=False):
        meta_data = self.get_meta_data(coordinate.plate)
        # FIXME: linking of iterators should adapt to any scan-order
        iter_zslice = AxisIterator(self, coordinate.zslice,
                                   meta_data.zslices, 'zslice')
        iter_channel = AxisIterator(self, coordinate.channel,
                                    meta_data.channels, 'channel',
                                    interrupt_zslice, iter_zslice)
        iter_time = AxisIterator(self, coordinate.time,
                                 meta_data.times, 'time',
                                 interrupt_channel, iter_channel)
        iter_position = AxisIterator(self, coordinate.position,
                                     meta_data.positions, 'position',
                                     interrupt_time, iter_time)
        iter_plate = AxisIterator(self, coordinate.plate,
                                  self.plates, 'plate',
                                  interrupt_position, iter_position)
        return iter_plate()

    __call__ = iterator

    def get_meta_image(self, coordinate):
        meta_data = self.get_meta_data(coordinate.plate)
        return MetaImage(self, coordinate, meta_data.dim_y, meta_data.dim_x)

    def get_image(self, coordinate):
        importer = self._plates[coordinate.plate]
        return importer.get_image(coordinate)

    def get_meta_data(self, plate):
        return self._meta_data[plate]

    @property
    def plates(self):
        return self._plates.keys()

    @property
    def has_multiple_plates(self):
        return len(self.plates) > 1

    @property
    def channels(self):
        channels = []
        for plate in self.plates:
            print plate
            meta_data = self._meta_data[plate]
            channels += meta_data.channels
        return sorted(set(channels))

    @classmethod
    def check_container_file(cls, path_plate_in, path_plate_out, settings):
        filename = os.path.join(path_plate_out, IMAGECONTAINER_FILENAME)
        if not os.path.isfile(filename):
            filename = os.path.join(path_plate_in, IMAGECONTAINER_FILENAME)
            if not os.path.isfile(filename):
                filename = None
        return filename

    @classmethod
    def from_settings(cls, settings, force=False):
        #from cecog.traits.analyzer.output import SECTION_NAME_OUTPUT
        from cecog.io.importer import (IniFileImporter,
                                       FlatFileImporter,
                                       )

        settings.set_section(SECTION_NAME_GENERAL)
        path_in = convert_package_path(settings.get2('pathin'))
        path_out = convert_package_path(settings.get2('pathout'))
        has_multiple_plates = settings.get2('has_multiple_plates')

        if has_multiple_plates:
            plate_folders = [x for x in os.listdir(path_in)
                             if os.path.isdir(os.path.join(path_in, x))]
        else:
            plate_folders = [os.path.split(path_in)[1]]

        imagecontainer = cls()

        for plate_id in plate_folders:

            if has_multiple_plates:
                path_plate_in = os.path.join(path_in, plate_id)
                path_plate_out = os.path.join(path_out, plate_id)
            else:
                path_plate_in = path_in
                path_plate_out = path_out

            # check if structure file exists
            filename = cls.check_container_file(path_plate_in, path_plate_out,
                                                settings)

            if filename is None:
                force = True

            if force:
                if settings.get2('image_import_namingschema'):
                    config_parser = NAMING_SCHEMAS
                    section_name = settings.get2('namingscheme')
                    importer = IniFileImporter(path_plate_in,
                                               config_parser, section_name)
                # read file structure according to dimension/structure file
                elif settings.get2('image_import_structurefile'):
                    filename = settings.get2('structure_filename')
                    importer = FlatFileImporter(path_plate_in, filename)
            else:
                importer = FlatFileImporter(path_plate_in, filename)

            importer.load()
            if force:
                importer.export_to_flatfile(os.path.join(path_plate_in,
                                                         IMAGECONTAINER_FILENAME))
            imagecontainer.register_plate(plate_id, importer)

        return imagecontainer

