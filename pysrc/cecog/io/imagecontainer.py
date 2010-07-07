"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__docformat__ = "epytext"
__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

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

#------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict
from pdk.datetimeutils import StopWatch
from pdk.fileutils import safe_mkdirs

#------------------------------------------------------------------------------
# cecog imports:
#

#------------------------------------------------------------------------------
# constants:
#
UINT8 = 'UINT8'
UINT16 = 'UINT16'
PIXEL_TYPES = [UINT8, UINT16]

DIMENSION_NAME_POSITION = 'position'
DIMENSION_NAME_TIME = 'time'
DIMENSION_NAME_CHANNEL = 'channel'
DIMENSION_NAME_ZSLICE = 'zslice'
DIMENSION_NAME_HEIGHT = 'height'
DIMENSION_NAME_WIDTH = 'width'
META_INFO_WELL = 'well'
META_INFO_SUBWELL = 'subwell'


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

        self.zslices = None
        self.channels = None
        self.times = None
        self.positions = None

        self._timestamps_relative = {}
        self._timestamps_absolute = {}

        self._position_well_map = {}

        self.pixel_type = None
#
#    def _analyzeTimestamps(self):
#        for iP, dctPosTimestamps in self.dctTimestamps.iteritems():
#            lstTKeys = dctPosTimestamps.keys()
#            lstTKeys.sort()
#            lstDeltas = [dctPosTimestamps[lstTKeys[iIdx+1]] - dctPosTimestamps[lstTKeys[iIdx]]
#                         for iIdx in range(len(lstTKeys)-1)]
#            self.dctTimestampDeltas[iP] = lstDeltas
#            if len(lstDeltas) > 1:
#                fMean = mean(lstDeltas)
#                fStd  = std(lstDeltas)
#                self.dctTimestampStrs[iP] = "%.2fmin (+/- %.3fmin)" % (fMean / 60.0, fStd / 60.0)
#            else:
#                self.dctTimestampStrs[iP] = "-"

    def get_timestamp_relative(self, position, frame):
        try:
            timestamp = self._timestamps_relative[position][frame]
        except KeyError:
            return float('NAN')
        else:
            return timestamp

    def get_timestamp_absolute(self, position, frame):
        try:
            timestamp = self._timestamps_absolute[position][frame]
        except KeyError:
            return float('NAN')
        else:
            return timestamp

    def append_absolute_time(self, position, time, timestamp):
        if not position in self._timestamps_absolute:
            self._timestamps_absolute[position] = OrderedDict()
        self._timestamps_absolute[position][time] = timestamp

    def append_well_subwell_info(self, position, well, subwell):
        if not position in self._position_well_map:
            self._position_well_map[position] = {META_INFO_WELL: well,
                                                 META_INFO_SUBWELL: subwell,
                                                 }

    def get_well_and_subwell(self, position):
        if position in self._position_well_map:
            return (self._position_well_map[position][META_INFO_WELL],
                    self._position_well_map[position][META_INFO_SUBWELL])
        else:
            return (None, None)

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
            for time, timestamp in timestamps.iteritems():
                self._timestamps_relative[position][time] = \
                    timestamp - base_time

        self.dim_p = len(self.positions)
        self.dim_t = len(self.times)
        self.dim_c = len(self.channels)
        self.dim_z = len(self.zslices)

    def format(self, time=True):
#        if len(self.dctTimestampStrs) == 0:
#            self._analyzeTimestamps()
#        printer = pprint.PrettyPrinter(indent=6, depth=6, width=1)
        strings = []
        head = "*   Imaging MetaData   *"
        line = "*"*len(head)
        strings += [line]
        strings += [head]
        strings += [line]
        strings += ["* Positions: %s" % self.dim_p]
        strings += ["* Time-points: %s" % self.dim_t]
        strings += ["* Channels: %s" % self.dim_c]
        strings += ["* Z-slices: %s" % self.dim_z]
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

    def __init__(self, image_container=None, position=None, time=None,
                 channel=None, zslice=None, height=None, width=None,
                 format=UINT8):
        self.position = position
        self.time = time
        self.channel = channel
        self.zslice = zslice
        self.height = height
        self.width = width
        self.format = format
        self.image_container = image_container
        self._img = None

    def __str__(self):
        return "%s(P=%s,T=%s,C=%s,Z=%s,H=%s,W=%s)" % \
               (self.__class__.__name__, self.position, self.time, self.channel,
                self.zslice, self.height, self.width)

    @property
    def image(self):
        if self._img is None:
            self._img = self.image_container.get_image(self.position,
                                                       self.time,
                                                       self.channel,
                                                       self.zslice)
        return self._img

    def set_image(self, img):
        self._img = img

    def format(self, suffix=None, show_position=True, show_time=True,
               show_channel=True, show_zslice=True, sep='_'):
        lstFormat = []
        if bP:
            lstFormat.append("P%s" % self.P)
        if bT:
            lstFormat.append("T%05d" % self.iT)
        if bC:
            lstFormat.append("C%s" % self.strC)
        if bZ:
            lstFormat.append("Z%02d" % self.iZ)
        if strSuffix is not None:
            lstFormat.append(strSuffix)
        return strSep.join(lstFormat)



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

    def __call__(self, current=None, dimensions=None):
        if dimensions is None:
            dimensions = []
        else:
            dimensions.append(current)
        if not self.next_iter is None:
            for value in self.values:
                # interrupt: stop the iteration and return the generator
                if self.interrupt:
                    # return the generator
                    yield value, self.next_iter(value, dimensions[:])
                else:
                    # iterate over the next generator: return elements of the
                    # next dimension
                    for next_iter in self.next_iter(value, dimensions[:]):
                        yield next_iter
        else:
            # end of generator-chain reached: return the MetaImages
            for value in self.values:
                params = tuple(dimensions) + (value,)
                # pylint: disable-msg=W0142
                yield value, self.image_container.get_meta_image(*params)


class ImageContainer(object):

    def __init__(self, importer):
        self.importer = importer
        self.meta_data = importer.meta_data

    def iterator(self, position=None, time=None, channel=None, zslice=None,
                 interrupt_time=False,
                 interrupt_channel=False,
                 interrupt_zslice=False):
        # FIXME: linking of iterators should adapt to any scan-order
        iter_zslice = AxisIterator(self, zslice, self.meta_data.zslices,
                                   'zslice')
        iter_channel = AxisIterator(self, channel, self.meta_data.channels,
                                    'channel', interrupt_zslice, iter_zslice)
        iter_time = AxisIterator(self, time, self.meta_data.times,
                                 'time', interrupt_channel, iter_channel)
        iter_position = AxisIterator(self, position, self.meta_data.positions,
                                     'position', interrupt_time, iter_time)
        return iter_position()

    __call__ = iterator

    def get_meta_image(self, position, time, channel, zslice):
        return MetaImage(self, position, time, channel, zslice,
                         self.meta_data.dim_y, self.meta_data.dim_x)

    def get_image(self, position, time, channel, zslice):
        return self.importer.get_image(position, time, channel, zslice)

    @classmethod
    def from_settings(cls, settings):
        from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
        from cecog.io.filetoken import (MetaMorphTokenImporter,
                                        FlatFileImporter,
                                        )
        import cPickle as pickle
        settings.set_section(SECTION_NAME_GENERAL)
        path_input = settings.get2('pathin')
        path_output = settings.get2('pathout')
        path_output_dump = os.path.join(path_output, 'dump')
        filename_pkl = os.path.join(path_output_dump, 'imagecontainer.pkl')

        if os.path.isfile(filename_pkl):
            f = file(filename_pkl, 'rb')
            imagecontainer = pickle.load(f)
            f.close()
        else:
            if settings.get2('image_import_namingschema'):
                importer = MetaMorphTokenImporter(path_input)
            elif settings.get2('image_import_structurefile'):
                filename = settings.get2('structure_filename')
                importer = FlatFileImporter(path_input, filename)
            imagecontainer = cls(importer)

            safe_mkdirs(path_output)
            safe_mkdirs(path_output_dump)

            f = file(filename_pkl, 'wb')
            pickle.dump(imagecontainer, f, 1)
            f.close()
        return imagecontainer

#-------------------------------------------------------------------------------
# main:
#
if __name__ ==  "__main__":
    from cecog.io.filetoken import MetaMorphTokenImporter
    from cecog.io.filetoken import FlatFileImporter

    path = '/Users/twalter/CecogPackage/H2B_aTubulin'
    filename = '/Users/twalter/cecog_test.txt'
    #image_container = ImageContainer(MetaMorphTokenImporter(path))
    s = StopWatch()
    #path = '/Volumes/mattaj/andri/laminB_data/040210'
    #filename = '/Users/twalter/040210.txt'
    #path = '/Users/twalter/data/Andri/Images/110210'
    #filename = '/Users/twalter/110210_part.txt'
    image_container = ImageContainer(FlatFileImporter(path, filename))
    print image_container.meta_data
    print s

