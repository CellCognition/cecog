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

__all__ = ['ChannelFrame',
           ]

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
from cecog.gui.util import (StyledSideFrame,
                            StyledFrame,
                            )
from cecog.gui.widgets.colorframe import ColorFrame

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class ChannelFrame(StyledSideFrame):

    def __init__(self, parent, viewer, default_colors):
        super(ChannelFrame, self).__init__(parent)
        self.viewer = viewer
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop|Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.default_colors = default_colors
        self._widgets = []

    def clear(self):
        # this looks more like hack :-(
        for widget in self._widgets:
            self.layout.removeWidget(widget)
            widget.deleteLater()
        self._widgets = []

    def set_channels(self, channels):
        self.clear()
        for idx, (name, color) in enumerate(channels):
            if idx > 0:
                line = StyledFrame(self)
                line.setFrameShape(QFrame.HLine)
                self.layout.addWidget(line)
                self._widgets.append(line)
            self._add_color_frame(name, color, self.default_colors)

    def _add_color_frame(self, name, color, colors):
        color_frame = ColorFrame(self, name, color, colors)
        color_frame.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                              QSizePolicy.Minimum))
        color_frame.colorSelected.connect(self.on_update_color)
        self.layout.addWidget(color_frame)
        self._widgets.append(color_frame)

    def on_update_color(self, name, lut, alpha):
        self.viewer.update_lut_by_name(name, lut, alpha)


#-------------------------------------------------------------------------------
# main:
#

