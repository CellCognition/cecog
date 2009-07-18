"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
              See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['hex_to_rgb',
           'rgb_to_hex']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#


#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#

def hex_to_rgb(hex_string):
    """
    Converts the hex representation of a RGB value (8bit per channel) to
    its integer components.

    Example: hex_to_rgb('#559988') = (85, 153, 136)
             hex_to_rgb('559988') = (85, 153, 136)

    @param hexString: the RGB value
    @type hexString: string
    @return: RGB integer components (tuple)
    """
    if hex_string[:2] == '0x':
        hex_value = eval(hex_string)
    elif hex_string[0] == '#':
        hex_value = eval('0x'+hex_string[1:])
    else:
        hex_value = eval('0x'+hex_string)
    b = hex_value & 0xff
    g = hex_value >> 8 & 0xff
    r = hex_value >> 16 & 0xff
    return (r, g, b)


def rgb_to_hex(r, g, b, prefix='#', upper=False):
    """
    Converts the 8bit integer components of a RGB value its hex representation
    leading some prefix characters.

    Example: rgb_to_hex(85, 153, 136) = '#559988'
             rgb_to_hex(85, 153, 136, '0x') = '0x559988'

    @param r: red component
    @type r: integer
    @param g: green component
    @type g: integer
    @param b: blue component
    @type b: integer
    @param prefix: hex prefix, e.g. '#' or '0x'
    @type prefix: string
    @return: hex representation (string)
    """
    hex_string = "".join([hex(c)[2:].zfill(2) for c in (r, g, b)])
    if upper:
        hex_string = hex_string.upper()
    return prefix + hex_string


#-------------------------------------------------------------------------------
# classes:
#


#-------------------------------------------------------------------------------
# main:
#

