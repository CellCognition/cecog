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

__all__ = ['ColorFrame',
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
from cecog.gui.util import (StyledFrame,
                            StyledLabel,
                            )
from cecog.gui.widgets.colorbox import ColorBox

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class ColorFrame(StyledFrame):

    colorSelected = pyqtSignal('str', 'list', 'float')

    def __init__(self, parent, name, color, colors, show_label=True):
        super(ColorFrame, self).__init__(parent)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        if show_label:
            self._label = StyledLabel(name, self)
        self._box = ColorBox(self, color, colors)

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

        if show_label:
            self.layout.addWidget(self._label, 0, 0)
            self.layout.addWidget(self._box, 1, 0)
            self.layout.addWidget(self._alpha_slider, 2, 0)
        else:
            self.layout.addWidget(self._box, 0, 0)
            self.layout.addWidget(self._alpha_slider, 1, 0)
        self.setLayout(self.layout)

        self._name = name
        self._alpha = 1.0
        self._current_lut = self._box.get_current_lut()

        self._box.colorSelected.connect(self.on_color_selected)

    def on_color_selected(self, lut):
        self._current_lut = lut
        self.colorSelected.emit(self._name, self._current_lut, self._alpha)

    def on_alpha_changed(self, value):
        self._alpha = value / 100.
        self.colorSelected.emit(self._name, self._current_lut, self._alpha)
        self._alpha_slider.setToolTip('Alpha: %d%%' % value)

#-------------------------------------------------------------------------------
# main:
#

