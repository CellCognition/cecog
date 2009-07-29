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

__all__ = ['DisplayFrame',
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
from cecog.gui.util import StyledSideFrame

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class DisplayFrame(StyledSideFrame):

    def __init__(self, parent, viewer):
        super(DisplayFrame, self).__init__(parent)
        self._viewer = viewer

        self.layout = QGridLayout()

        self.button_fit = QPushButton('Fit', self)
        self.button_orig = QPushButton('100', self)

        self.connect(self.button_fit, SIGNAL('clicked()'),
                     self.on_button_fit)
        self.connect(self.button_orig, SIGNAL('clicked()'),
                     self.on_button_orig)

        self.slider_zoom = QSlider(Qt.Horizontal, self)
        self.slider_zoom.setRange(10, 500)
        self.slider_zoom.setValue(100)
        self.slider_zoom.setTracking(True)
        self.slider_zoom.setTickPosition(QSlider.TicksBelow)
        self.slider_zoom.setTickInterval(1)
        self.slider_zoom.setFocusPolicy(Qt.StrongFocus)
        self.slider_zoom.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                   QSizePolicy.Minimum))
        self.connect(self.slider_zoom, SIGNAL('valueChanged(int)'),
                     self.on_slider_zoom)

        self.layout.addWidget(self.button_fit, 0, 0)
        self.layout.addWidget(self.button_orig, 0, 1)
        self.layout.addWidget(self.slider_zoom, 1, 0, 1, 2)

        self.setLayout(self.layout)

    def on_slider_zoom(self, value):
        self._viewer.scale_to_value(value / 100.)

    def on_button_fit(self):
        self.slider_zoom.setValue(self._viewer.scale_to_fit() * 100)

    def on_button_orig(self):
        self.slider_zoom.setValue(self._viewer.scale_to_original() * 100)


#-------------------------------------------------------------------------------
# main:
#

