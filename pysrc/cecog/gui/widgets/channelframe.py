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
                            StyledLabel,
                            DEFAULT_COLORS
                            )
from cecog.gui.widgets.colorframe import ColorFrame
from cecog.gui.widgets.colorbox import ColorBox
from cecog.gui.plugin import (ActionSelectorFrame,
                              GuiPluginManagerMixin,
                              )
from cecog.util.color import hex_to_rgb
from cecog.core.workflow import CHANNEL_MANAGER
from cecog.core.channel import ChannelManager

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class ChannelFrameBrowser(StyledSideFrame):

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


class ChannelDisplay(StyledSideFrame):

    #colorSelected = pyqtSignal('str', 'list', 'float')

    def __init__(self, channel, parent):
        super(ChannelDisplay, self).__init__(parent)
        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)

        self._channel = channel
        channel.color = QColor(*hex_to_rgb(channel.hex_color))

        colors = [QColor(*hex_to_rgb(col)) for col in DEFAULT_COLORS]
        self._box = ColorBox(self, channel.color, colors)

        self._alpha_slider = QSlider(Qt.Horizontal, self)
        self._alpha_slider.setRange(0,100)
        self._alpha_slider.setValue(100)
        self._alpha_slider.setTracking(True)
        self._alpha_slider.setTickPosition(QSlider.TicksBelow)
        self._alpha_slider.setTickInterval(10)
        self._alpha_slider.setSingleStep(5)
        self._alpha_slider.setToolTip('Alpha: 100%')
        self.connect(self._alpha_slider, SIGNAL('valueChanged(int)'),
                     self.on_alpha_changed)

        self.layout.addWidget(self._box, 0, 0, 1, 6)
        self.layout.addWidget(StyledLabel('alpha:', self), 1, 0, Qt.AlignRight)
        self.layout.addWidget(self._alpha_slider, 1, 1, 1, 5)
        self.setLayout(self.layout)

        #self._name = name
        #self._alpha = 1.0
        #self._current_lut = self._box.get_current_lut()

        self._box.colorSelected.connect(self.on_color_selected)

    def on_color_selected(self, lut):
        self._channel.lut = lut
        self._channel.update()
        #self._current_lut = lut
        #self.colorSelected.emit(self._name, self._current_lut, self._alpha)

    def on_alpha_changed(self, value):
        #alpha = value / 100.
        #self.colorSelected.emit(self._name, self._current_lut, self._alpha)
        self._alpha_slider.setToolTip('Alpha: %d%%' % value)
        self._channel.alpha = value / 100.
        self._channel.update()


class ChannelFrame(ActionSelectorFrame):

    def __init__(self, parent):
        super(ChannelFrame, self).__init__(CHANNEL_MANAGER, parent)



class GuiChannelManager(ChannelManager, GuiPluginManagerMixin):

    DISPLAY_CLASS = ChannelDisplay

    def set_experiment_channels(self, channels):
        ChannelManager.set_experiment_channels(self, channels)

        for name in channels:
            self._gui_handler.add_plugin(name)


#-------------------------------------------------------------------------------
# main:
#

