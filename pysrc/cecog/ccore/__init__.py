"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
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

import os
import sys

from cecog.traits.config import FONT12_FILENAME

# import all wrapped C++ classes and functions and make them part of this package
from _cecog import *

# set font filename and path relative to the location of this package
# (must be a realpath for C++)
Config.strFontFilepath = os.path.realpath(FONT12_FILENAME)
#assert os.path.isfile(Config.strFontFilepath)
