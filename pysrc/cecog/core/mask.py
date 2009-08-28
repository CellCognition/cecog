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
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#------------------------------------------------------------------------------
# cecog imports:
#
from cecog.core.entity import Entity
from cecog.core.plugin import PluginManager

#------------------------------------------------------------------------------
# constants:
#
MASK_MANAGER = 'MaskManager'

#------------------------------------------------------------------------------
# functions:
#


#------------------------------------------------------------------------------
# classes:
#
class Mask(Entity):
    pass


class MaskManager(PluginManager):

    TEXT = 'mask'
    NAME = MASK_MANAGER


