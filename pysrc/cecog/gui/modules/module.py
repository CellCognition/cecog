"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

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

class Module(QFrame):

    NAME = ''

    def __init__(self, parent, browser):
        QFrame.__init__(self, parent)
        self._is_initialized = False
        self._browser = browser
        self.setStyleSheet(
"""
 QWidget {
     font-size: 11px;
 }

 QGroupBox {
     background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #E0E0E0, stop: 1 #FFFFFF);
     border: 2px solid #999999;
     border-radius: 5px;
     margin-top: 1ex; /* leave space at the top for the title */
     font-size: 13px;
 }

 QGroupBox::title {
     subcontrol-origin: margin;
     subcontrol-position: top center; /* position at the top center */
     padding: 0 3px;
 }

 QTableView {
     font-size: 10px;
     alternate-background-color: #EEEEFF;
 }

 QPushButton {
     font-size: 11px;
 }

 ColorButton::enabled {
     border: 1px solid #444444;
 }

 ColorButton::disabled {
     border: 1px solid #AAAAAA;
 }

""")

    def initialize(self):
        pass

    def activate(self):
        if not self._is_initialized:
            self.initialize()
            self._is_initialized = True
