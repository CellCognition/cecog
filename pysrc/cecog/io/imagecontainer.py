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
       os, \
       copy
import numpy
import cPickle as pickle

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
from cecog import ccore

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

IMAGECONTAINER_FILENAME = 'cecog_imagecontainer___PL%s.pkl'
IMAGECONTAINER_FILENAME_OLD = '.cecog_imagecontainer___PL%s.pkl'

#------------------------------------------------------------------------------
# functions:
#
def importer_pickle(obj, filename):
    f = open(filename, 'wb')
    pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    f.close()

def importer_unpickle(filename):
    f = open(filename, 'rb')
    obj = pickle.load(f)
    f.close()
    return obj

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
    _crop_coordinates = None
    
    @classmethod
    def get_crop_coordinates(cls):
        return cls._crop_coordinates

    def __init__(self, image_container=None, coordinate=None,
                 height=None, width=None, format=UINT8):
        self.coordinate = coordinate
        self.img_height = height
        self.img_width = width
        self.format = format
        self.image_container = image_container
        self._img = None
        self._img_c = None

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
            self._img_c = ccore.subImage(self._raw_image,
                                    ccore.Diff2D(MetaImage._crop_coordinates[0], MetaImage._crop_coordinates[1]),
                                    ccore.Diff2D(MetaImage._crop_coordinates[2], MetaImage._crop_coordinates[3]))
        return self._img_c

    def set_raw_image(self, img):
        self._img = img
        
    def set_cropped_image(self, img):
        self._img_c = img
        
    def set_image(self, img):
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

    def copy(self):
        return copy.deepcopy(self)


class ImageContainer(object):

    def __init__(self):
        self._plates = OrderedDict()
        self._path_in = OrderedDict()
        self._path_out = OrderedDict()
        self._importer = None
        self.current_plate = None
        self.has_timelapse = None

    def register_plate(self, plate_id, path_in, path_out, filename):
        self._plates[plate_id] = filename
        self._path_in[plate_id] = path_in
        self._path_out[plate_id] = path_out
        # FIXME: check some dimensions!!!

    def iterator(self, coordinate,
                 interrupt_time=False,
                 interrupt_channel=False,
                 interrupt_zslice=False):
        meta_data = self.get_meta_data()
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
        return iter_position()

    __call__ = iterator

    def set_plate(self, plate):
        if plate != self.current_plate:
            self.current_plate = plate
            filename = self._plates[plate]
            self._importer = importer_unpickle(filename)
            self._importer.path = self._path_in[plate]

    def check_dimensions(self):
        self.has_timelapse = self._importer.meta_data.has_timelapse

    def get_meta_image(self, coordinate):
        meta_data = self.get_meta_data()
        return MetaImage(self, coordinate, meta_data.dim_y, meta_data.dim_x)

    def get_image(self, coordinate):
        return self._importer.get_image(coordinate)

    def get_meta_data(self):
        return self._importer.meta_data

    def get_path_out(self, plate=None):
        if plate is None:
            plate = self.current_plate
        return self._path_out[plate]

    @property
    def plates(self):
        return sorted(self._plates.keys())

    @property
    def has_multiple_plates(self):
        return len(self.plates) > 1

    @property
    def channels(self):
        meta_data = self.get_meta_data()
        return sorted(meta_data.channels)

    @classmethod
    def _get_structure_filename(cls, settings, plate_id,
                                path_plate_in, path_plate_out, use_old=False):
        if settings.get2('structure_file_pathin'):
            path_structure = path_plate_in
        elif settings.get2('structure_file_pathout'):
            path_structure = path_plate_out
        else:
            path_structure = \
                settings.get2('structure_file_extra_path_name')
        if use_old:
            filename_container = IMAGECONTAINER_FILENAME_OLD % plate_id
        else:
            filename_container = IMAGECONTAINER_FILENAME % plate_id
        return os.path.join(path_structure, filename_container)

    @classmethod
    def iter_check_plates(cls, settings):
        settings.set_section(SECTION_NAME_GENERAL)
        path_in = convert_package_path(settings.get2('pathin'))
        path_out = convert_package_path(settings.get2('pathout'))
        has_multiple_plates = settings.get2('has_multiple_plates')

        if has_multiple_plates:
            plate_folders = [x for x in os.listdir(path_in)
                             if os.path.isdir(os.path.join(path_in, x))]
        else:
            plate_folders = [os.path.split(path_in)[1]]

        for plate_id in plate_folders:

            if has_multiple_plates:
                path_plate_in = os.path.join(path_in, plate_id)
                path_plate_out = os.path.join(path_out, plate_id)
            else:
                path_plate_in = path_in
                path_plate_out = path_out

            # check if structure file exists
            filename = cls._get_structure_filename(settings, plate_id, path_plate_in, path_plate_out)
            if not os.path.isfile(filename):
                # check old (hidden) filename for compatibility reasons
                filename = cls._get_structure_filename(settings, plate_id, path_plate_in, path_plate_out, use_old=True)
                if not os.path.isfile(filename):
                    filename = None
            yield plate_id, path_plate_in, path_plate_out, filename

    def iter_import_from_settings(self, settings, scan_plates=None):
        from cecog.io.importer import (IniFileImporter,
                                       FlatFileImporter,
                                       )
        settings.set_section(SECTION_NAME_GENERAL)

        for info in self.iter_check_plates(settings):
            plate_id, path_plate_in, path_plate_out, filename = info

            # check whether this plate has to be rescanned
            if not scan_plates is None:
                scan_plate = scan_plates[plate_id]
            else:
                scan_plate = False

            # if no structure file was found scan the plate
            if filename is None:
                scan_plate = True

            # (re)scan the file structure
            if scan_plate:
                if settings.get2('image_import_namingschema'):
                    config_parser = NAMING_SCHEMAS
                    section_name = settings.get2('namingscheme')
                    importer = IniFileImporter(path_plate_in,
                                               config_parser, section_name)
                # read file structure according to dimension/structure file
                elif settings.get2('image_import_structurefile'):
                    filename = settings.get2('structure_filename')
                    importer = FlatFileImporter(path_plate_in, filename)

                # scan the file structure
                importer.scan()

                # serialize importer and register plate only upon successful scan
                if importer.is_valid:
                    filename = self._get_structure_filename(settings, plate_id,
                                                            path_plate_in,
                                                            path_plate_out)

                    importer_pickle(importer, filename)
                    self.register_plate(plate_id, path_plate_in,
                                        path_plate_out, filename)
            else:
                self.register_plate(plate_id, path_plate_in,
                                    path_plate_out, filename)

            yield info

    def import_from_settings(self, settings, scan_plates=None):
        list(self.iter_import_from_settings(settings, scan_plates))
