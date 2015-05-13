"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

Translated to Python and adopted from Qxt (http://www.libqxt.org/)
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['QxtGroupBox']

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

class QxtGroupBox(QGroupBox):

    def __init__(self, title=None, parent=None):
        super(QxtGroupBox, self).__init__(parent)
        if not title is None:
            self.setTitle(title)
        self.setCheckable(True)
        self.setChecked(True)
        self._collapsive = True
        self._flat = False
        self.toggled.connect(self.setExpanded)
        #self.setStyleSheet('spacing-left: 50px;')

    def isCollapsive(self):
        return self._collapsive

    def setCollapsive(self, enable=True):
        if self._collapsive != enable:
            self._collapsive = enable
            if not enable:
                self.setExpanded(True)
            elif not self.isChecked():
                self.setExpanded(False)

    @pyqtSlot(bool)
    def setCollapsed(self, collapsed=True):
        self.setExpanded(not collapsed)

    @pyqtSlot(bool)
    def setExpanded(self, expanded=True):
        if self._collapsive or expanded:
            for child in self.children():
                if child.isWidgetType():
                    child.setVisible(expanded)
            if expanded:
                self.setFlat(self._flat)
            else:
                self._flat = self.isFlat()
                self.setFlat(True)
            #self.parent().layout().update()

    def childEvent(self, event):
        child = event.child()
        if event.added() and child.isWidgetType():
            if self._collapsive and not self.isChecked():
                child.hide()
