"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import

__author__ = 'Michael Held'
__date__ = '$Date: $'
__revision__ = '$Rev:  $'
__source__ = '$URL: $'

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class CollapsibleFrame(QFrame):

    def __init__(self, parent, label, state=False):
        QFrame.__init__(self, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        frame2 = QFrame(self)
        layout.addWidget(frame2)

        layout = QHBoxLayout(frame2)
        layout.setContentsMargins(0, 0, 0, 0)
        self.btn = QPushButton(label, frame2)
        self.btn.setCheckable(True)
        self.btn.setChecked(state)
        layout.addWidget(self.btn)
        layout.addStretch(1)

    def set_frame(self, frame):
        layout = self.layout()
        frame.setVisible(self.btn.isChecked())
        fct = lambda x: frame.setVisible(x)
        self.btn.toggled.connect(fct)
        layout.addWidget(frame)

#-------------------------------------------------------------------------------
# main:
#

