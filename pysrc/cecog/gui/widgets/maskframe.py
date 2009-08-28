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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys
import os

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import StyledSideFrame
from cecog.gui.plugin import (ActionSelectorFrame,
                              GuiPluginManagerMixin
                              )
from cecog.core.workflow import MASK_MANAGER
from cecog.core.mask import MaskManager

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class MaskDisplay(StyledSideFrame):

    def __init__(self, mask, parent):
        super(MaskDisplay, self).__init__(parent)


class MaskFrame(ActionSelectorFrame):

    def __init__(self, parent):
        super(MaskFrame, self).__init__(MASK_MANAGER, parent)


class GuiMaskManager(MaskManager, GuiPluginManagerMixin):

    DISPLAY_CLASS = MaskDisplay


#-------------------------------------------------------------------------------
# main:
#

