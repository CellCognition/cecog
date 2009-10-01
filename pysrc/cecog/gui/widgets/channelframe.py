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

import numpy
import pyvigra

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
from cecog.ccore import (protected_linear_range_mapping,
                         )

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


class HistogramFrame(QFrame):

    SIZE = (250, 100)
    BINS = 256

    def __init__(self, parent):
        super(HistogramFrame, self).__init__(parent)
        self.layout = QGridLayout()

        self._histogram_label = QLabel(self)
        self._histogram_label.setStyleSheet("border: 1px solid #999999;")
        histogram_image = QPixmap(*self.SIZE)
        histogram_image.fill(Qt.transparent)
        self._histogram_label.setPixmap(histogram_image)

        self._xmin = StyledLabel(self)
        self._xmax = StyledLabel(self)
        self._ymin = StyledLabel(self)
        self._ymax = StyledLabel(self)
        self.layout.addWidget(self._histogram_label, 0, 1, 2, 2, Qt.AlignRight)
        self.layout.addWidget(self._ymin, 1, 0, Qt.AlignBottom|Qt.AlignRight)
        self.layout.addWidget(self._ymax, 0, 0, Qt.AlignTop|Qt.AlignRight)
        self.layout.addWidget(self._xmin, 2, 1, Qt.AlignLeft)
        self.layout.addWidget(self._xmax, 2, 2, Qt.AlignRight)
        self.setLayout(self.layout)

    def update_by_image(self, image):
        width, height = self.SIZE
        array = image.to_array()
        histogram, bin_edges = numpy.histogram(array,
                                               bins=self.BINS, normed=True)
        ymax_value = numpy.max(histogram)
        xmin_value = numpy.min(array)
        xmax_value = numpy.max(array)
        print xmin_value, xmax_value
        #print max_value
        #print bin_edges, len(bin_edges)
        histogram = histogram / float(ymax_value) * height
        #print histogram, len(histogram)
        histogram_image = QPixmap(*self.SIZE)
        histogram_image.fill(Qt.transparent)
        painter = QPainter(histogram_image)
        color = QColor('white')
        ratio = float(width) / self.BINS
        for idx, value in enumerate(histogram):
            w = bin_edges[idx+1] - bin_edges[idx]
            rect = QRectF(bin_edges[idx]*ratio, height-value, w*ratio, value)
            painter.fillRect(rect, color)
        painter.end()
        self._histogram_label.setPixmap(histogram_image)
        self._ymin.setText(str(0))
        self._ymax.setText('%.1f%%' % (ymax_value * 100.))
        self._xmin.setText(str(xmin_value))
        self._xmax.setText(str(xmax_value))

        return xmin_value, xmax_value


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

        self._histogram_frame = HistogramFrame(self)

        self._min_spin = QSpinBox(self)
        self._max_spin = QSpinBox(self)
        self._min_spin.setMinimum(-1000)
        self._min_spin.setMaximum(+1000)
        self._max_spin.setMinimum(-1000)
        self._max_spin.setMaximum(+1000)
        self.connect(self._min_spin, SIGNAL('valueChanged(int)'),
                     self._on_min_intensity_changed)
        self.connect(self._max_spin, SIGNAL('valueChanged(int)'),
                     self._on_max_intensity_changed)
        self._has_min = False
        self._has_max = False

        self.layout.addWidget(self._box, 0, 0, 1, 6)
        self.layout.addWidget(StyledLabel('alpha:', self), 1, 0, Qt.AlignRight)
        self.layout.addWidget(self._alpha_slider, 1, 1, 1, 5)
        self.layout.addWidget(self._histogram_frame, 2, 0, 1, 6, Qt.AlignCenter)
        self.layout.addWidget(self._min_spin, 3, 0, 1, 2, Qt.AlignCenter)
        self.layout.addWidget(self._max_spin, 3, 2, 1, 2, Qt.AlignCenter)
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

    def update(self, image):
        #new_image = image
        minv, maxv = self._histogram_frame.update_by_image(image)
        if not self._has_min:
            self._min_spin.setValue(minv)
            self._has_min = True
        elif self._min_spin.value() >= minv:
            minv = self._min_spin.value()
        if not self._has_max:
            self._max_spin.setValue(maxv)
            self._has_max = True
        elif self._max_spin.value() <= maxv:
            maxv = self._max_spin.value()
        new_image = protected_linear_range_mapping(image, int(minv), int(maxv),
                                                   0, 255)
        return new_image

    def _on_min_intensity_changed(self, value):
        #if value >= self._max_spin.value():
        self._channel.update()

    def _on_max_intensity_changed(self, value):
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

