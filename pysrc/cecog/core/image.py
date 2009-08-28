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

__all__ = []

#------------------------------------------------------------------------------
# standard library imports:
#

#------------------------------------------------------------------------------
# extension module imports:
#
#from cecog.core.ccore import PIXEL_TYPECODES
import pyvigra
#------------------------------------------------------------------------------
# cecog imports:
#


#------------------------------------------------------------------------------
# constants:
#
PIXEL_TYPECODES = ccore.PIXEL_TYPECODES

#------------------------------------------------------------------------------
# functions:
#

def read_image(filename, pixel_type, index=-1):
    if pixel_type == PIXEL_TYPECODES.UINT8:
        try:
            image = ccore.readImageUInt8(filename, index)
        except:
            raise ImageImportError(filename, index)
    elif pixel_type == 'UINT16':
        try:
            image = ccore.readImageUInt16(filename, index)
        except:
            raise ImageImportError(filename, index)
    else:
        raise ValueError('Pixel-type %s not supported.' % pixel_type)
    return image

#------------------------------------------------------------------------------
# classes:
#


class ImageImportError(Exception):
    
    pass


class _Image(object):
    
    PIXEL_TYPE = None


class ImageUInt8(ccore.ImageUInt8, _Image):
    
    PIXEL_TYPE = PIXEL_TYPECODES.UINT8
    
    
class ImageUInt16(ccore.ImageUInt16, _Image):
    
    PIXEL_TYPE = PIXEL_TYPECODES.UINT16
    
    
class ImageInt16(ccore.ImageInt16, _Image):
    
    PIXEL_TYPE = PIXEL_TYPECODES.INT16
    
    
class ImageUInt32(ccore.ImageUInt32, _Image):
    
    PIXEL_TYPE = PIXEL_TYPECODES.UINT32
    
    
class ImageInt32(ccore.ImageInt32, _Image):
    
    PIXEL_TYPE = PIXEL_TYPECODES.INT32
    
    
class ImageFloat(ccore.ImageFloat, _Image):
    
    PIXEL_TYPE = PIXEL_TYPECODES.FLOAT
    