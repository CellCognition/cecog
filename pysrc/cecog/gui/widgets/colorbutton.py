"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
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

__all__ = ['ColorButton']

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
class ColorButton(QToolButton):

    color_changed = pyqtSignal(QColor)

    def __init__(self, current_color, parent, show_alpha=True):
        QToolButton.__init__(self, parent)
        self.current_color = current_color
        self.show_alpha = show_alpha
        self.clicked.connect(self._on_clicked)

    def set_color(self, color):
        self.current_color = color
        # restrict the css to this class, otherwise the QColorDialog background
        # is changed as well (on Windows only)
        self.setStyleSheet(
            'ColorButton { background-color: rgba(%d, %d, %d, %d) }' %
             (color.red(), color.green(), color.blue(), color.alpha()))
        self.color_changed.emit(color)

    def _on_clicked(self):
        dlg = QColorDialog(self)
        if self.show_alpha:
            dlg.setOption(QColorDialog.ShowAlphaChannel)
        if not self.current_color is None:
            dlg.setCurrentColor(self.current_color)
        if dlg.exec_():
            col = dlg.currentColor()
            self.set_color(col)
            self.color_changed.emit(col)

