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
import os

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# cecog imports:
#

# import all wrapped C++ classes and functions and make them part of this package
from cecog.core._cecog import *

#------------------------------------------------------------------------------
# constants:
#


#------------------------------------------------------------------------------
# functions:
#


#------------------------------------------------------------------------------
# classes:
#
resource_path = os.path.realpath(os.path.join(os.path.split(__file__)[0], 
                                              'resources'))

# set font filename and path relative to the location of this package 
# (must be a realpath for C++)
Config.strFontFilepath = os.path.join(resource_path, "font12.png")

assert os.path.isfile(Config.strFontFilepath)

oFont12 = Font(os.path.join(resource_path, "font12.png"))
oFont14 = Font(os.path.join(resource_path, "font14.png"))
oFont16 = Font(os.path.join(resource_path, "font16.png"))
