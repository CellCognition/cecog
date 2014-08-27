"""
constants.py

Symbolic constants for pixel (integer) types, dimensions and meta data


"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ('PixelType', 'DimensionName', 'MetaInfo')


import numpy as np


class PixelType(object):

    Uint8 = np.uint8
    Uint16 = np.uint16
    Int8 = np.int8
    Int16 = np.int16
    Types = (Uint8, Int16, Int8, Int16)

    _names = [t.__name__ for t in Types]

    @classmethod
    def is_valid(cls, type_name):
        """Returns True if the pixel type name is valid i.e. supported by this
        class. Validation is required if the type_name is  provided by an
        external library or module.

        All type names must be lower case (numpy convention)."""
        return type_name in cls._names

    @staticmethod
    def range(pixel_type):
        iinfo = np.iinfo(pixel_type)
        return iinfo.min, iinfo.max

    @staticmethod
    def name(pixel_type):
        return pixel_type.__name__


class Dimensions(object):

    Position = "position"
    Time = "time"
    Channel = "channel"
    ZSlice = "zslice"
    Height = "height"
    Width = "width"


class MetaInfo(object):

    Timestamp = "timestamp"
    Well = "well"
    Subwell = "subwell"
