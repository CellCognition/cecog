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
import types

#------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict
from pdk.datetimeutils import StopWatch

#------------------------------------------------------------------------------
# cecog imports:
#

#------------------------------------------------------------------------------
# constants:
#

DIMENSION_NAME_POSITION = 'position'
DIMENSION_NAME_TIME = 'time'
DIMENSION_NAME_CHANNEL = 'channel'
DIMENSION_NAME_ZSLICE = 'zslice'
DIMENSION_NAME_HEIGHT = 'height'
DIMENSION_NAME_WIDTH = 'width'

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

        self.timestamps_relative = {}
        self.timestamps_absolute = {}

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
            timestamp = self.timestamps_relative[position][frame]
        except KeyError:
            return float('NAN')
        else:
            return timestamp

    def get_timestamp_absolute(self, position, frame):
        try:
            timestamp = self.timestamps_absolute[position][frame]
        except KeyError:
            return float('NAN')
        else:
            return timestamp

    def append_absolute_time(self, position, time, timestamp):
        if not position in self.timestamps_absolute:
            self.timestamps_absolute[position] = OrderedDict()
        self.timestamps_absolute[position][time] = timestamp

    def setup(self):
        for position in self.timestamps_absolute:
            self.timestamps_absolute[position].sort()
        for position, timestamps in self.timestamps_absolute.iteritems():
            base_time = timestamps.values()[0]
            self.timestamps_relative[position] = OrderedDict()
            for time, timestamp in timestamps.iteritems():
                self.timestamps_relative[position][time] = \
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

    def __init__(self, image_container, position, time, channel, zslice,
                 height, width):
        self.position = position
        self.time = time
        self.channel = channel
        self.zslice = zslice
        self.height = height
        self.width = width
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
                yield self.image_container.get_meta_image(*params)


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

