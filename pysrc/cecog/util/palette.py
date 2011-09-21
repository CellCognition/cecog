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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import os, \
       struct
import numpy

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.util.color import hex_to_rgb

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#
def unpack_at(fmt, string, offset):
    """
    unpack that supports offset and does not require exact string length
    """
    string = string[offset:]
    size = struct.calcsize(fmt)
    assert len(string) >= size, 'Data string is too short'
    return struct.unpack(fmt, string[:size])


#-------------------------------------------------------------------------------
# classes:
#

class MyStruct(struct.Struct):

    def unpack_at(self, string, offset):
        """
        unpack that supports offset and does not require exact string length
        """
        string = string[offset:]
        assert len(string) >= self.size, 'Data string is too short'
        return self.unpack(string[:self.size])


class _Palette(object):

    """
    Abstract lookup table class providing a 3x256 uint8 numpy array and a name.
    """

    def __init__(self, name):
        self.lut = numpy.zeros((256,3), dtype=numpy.uint8)
        self.name = name

    def apply_to_numpy(self, array):
        '''
        Apply the lut to a numpy ndarray.
        The result is a new ndarray with a new (r,g,b) array as the innermost
        dimension (24 bit RGB 8-8-8 format).
        '''
        return self.lut[array,:]


class _FilePalette(_Palette):

    @classmethod
    def from_file(cls, filename, size=50000):
        f = file(filename, 'rb')
        data = f.read(size)
        f.close()
        name = os.path.splitext(os.path.split(filename)[1])[0]
        return cls(name, data)


class NucMedPalette(_FilePalette):

    """
    Importer for NucMed / ImageJ lookup table files.
    """

    def __init__(self, name, data):
        super(NucMedPalette, self).__init__(name)

        if data.find('ICOL') != 0:
            raise ValueError('Not a valid NucMed/ImageJ LUT definition file.')

        s = MyStruct('B' * 256)
        for c in range(3):
            self.lut[:,c] = s.unpack_at(data, 32 + c*256)


class ZeissPalette(_FilePalette):

    """
    Importer for Zeiss AIM / ZEN lookup table files.
    Inspired from http://imagejdocu.tudor.lu/doku.php?id=macro:importzeisslut
    """

    def __init__(self, name, data):
        super(ZeissPalette, self).__init__(name)

        if data.find('CZ - LSM510 Color Palette , Version 1.00') != 0:
            raise ValueError('Not a valid Zeiss LUT definition.')

        size = unpack_at('i', data, 41)[0]
        self.name = data[45:(45+size)]
        offset = 46 + size

        s = MyStruct('h')
        # one value occupies 32 byte * 256 values = 8192
        # 8192 bytes x red, 8192 bytes x green, 8192 bytes x blue
        # values are shifted by 4 bit right (division by 16)
        for c in range(3):
            for i in range(256):
                self.lut[i, c] = s.unpack_at(data, offset+i*32+8192*c)[0] >> 4


class SingleColorPalette(_Palette):

    """
    Named lookup table from a single rgb color, (r,g,b) tuple.
    """

    def __init__(self, name, color):
        super(SingleColorPalette, self).__init__(name)
        self.name = name

        assert len(color) == 3, 'RGB color tuple is not valid.'

        for c in range(3):
            self.lut[:,c] = numpy.array(range(256)) / 255. * color[c]

    @classmethod
    def from_hex_color(cls, name, string):
        return cls(name, hex_to_rgb(string))


#-------------------------------------------------------------------------------
# main:
#
if __name__ == "__main__":

    z = ZeissPalette.from_file('/Users/miheld/src/cecog_svn/trunk/apps/CecogAnalyzer/resources/palettes/Zeiss/004_Magenta.lut')
    print '"%s"' % z.name
    print z.lut

    z = NucMedPalette.from_file('/Users/miheld/src/cecog_svn/trunk/apps/CecogAnalyzer/resources/palettes/NucMed/gray.lut')
    print '"%s"' % z.name
    print z.lut

    z = SingleColorPalette('test', (255,18,100))
    print '"%s"' % z.name
    print z.lut

