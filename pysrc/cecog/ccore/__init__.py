"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland
                            www.cellcognition.org

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL:: $'


# import all wrapped C++ classes and functions and make them part of this package
from _mito import *

import os

strFontBasePath = os.path.realpath(os.path.join(__path__[0], "resources"))

# set font filename and path relative to the location of this package (must be a realpath for C++)
Config.strFontFilepath = os.path.join(strFontBasePath, "font12.png")

assert os.path.isfile(Config.strFontFilepath)

oFont12 = Font(os.path.join(strFontBasePath, "font12.png"))
oFont14 = Font(os.path.join(strFontBasePath, "font14.png"))
oFont16 = Font(os.path.join(strFontBasePath, "font16.png"))
