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

__all__ = ['ColorBox',
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
from cecog.gui.util import StyledComboBox
from cecog.ccore import (read_lut,
                         lut_from_single_color,
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

class ColorBox(StyledComboBox):

    colorSelected = pyqtSignal('list')

    COLOR_SIZE = (50, 10)
    TEXT_MORE = 'more...'
    TEXT_LUT = 'LUT...'

    def __init__(self, parent, color, colors):
        super(ColorBox, self).__init__(parent)
        self.setIconSize(QSize(*self.COLOR_SIZE))
        self._popup_shown = False
        self._base_count = len(colors) + 1
        self._user_count = 0
        self._highlight_index = None

        self._luts = {}

        for col in colors:
            self.add_color(col)

        self.insertSeparator(self.count())
        self.insertItem(self.count(), self.TEXT_MORE, self.TEXT_MORE)
        self.insertItem(self.count(), self.TEXT_LUT, self.TEXT_LUT)

        #print "moo", color, colors
        #print color in colors
        rgb_values = map(lambda c: c.rgb(), colors)
        if color.rgb() in rgb_values:
            self.setCurrentIndex(rgb_values.index(color.rgb()))
        else:
            index = self.add_color(color, user=True)
            self.setCurrentIndex(index)

        self.connect(self, SIGNAL('activated(int)'), self.on_activated)
        self.connect(self, SIGNAL('highlighted(int)'), self.on_highlighted)
        self.current = self.currentIndex()

    def add_color(self, lut, user=False):
        pixmap = QPixmap(*self.COLOR_SIZE)

        if isinstance(lut, QColor):
            color = lut
            lut = lut_from_single_color((lut.red(), lut.green(), lut.blue()))
        else:
            color = lut[-1]

        f = 256. / self.COLOR_SIZE[0]
        painter = QPainter(pixmap)
        for w in range(self.COLOR_SIZE[0]):
            i = int(f * w)
            painter.fillRect(w, 0, w+1, self.COLOR_SIZE[1], QColor(*lut[i]))
        painter.end()
        icon = QIcon(pixmap)
        if user:
            index = self._base_count+self._user_count
            self.insertItem(index, icon, '', color)
            if self._user_count == 0:
                self.insertSeparator(index+1)
            self._user_count += 1
        else:
            index = self.count()
            self.insertItem(index, icon, '', color)
        self._luts[index] = lut
        return index

    def get_current_lut(self):
        return self._luts[self.current]

    def get_current_qcolor(self):
        return QColor(self.itemData(self.current))

    def emit_selection(self):
        self.colorSelected.emit(self.get_current_lut())

    def on_activated(self, index):
        if self.itemData(index).toString() == self.TEXT_MORE:
            dialog = QColorDialog(self.get_current_qcolor(), self)
            dialog.setOption(QColorDialog.ShowAlphaChannel)
            if dialog.exec_():
                color = dialog.selectedColor()
                #print color
                #print color.alpha()
                self.current = self.add_color(color, user=True)
                self.emit_selection()
            self.setCurrentIndex(self.current)

        # LUT...
        elif self.itemData(index).toString() == self.TEXT_LUT:
            dialog = QFileDialog(self)
            dialog.setFileMode(QFileDialog.ExistingFile)
            dialog.setNameFilters(['*.lut', '*.*'])
            try:
                if dialog.exec_():
                    filename = str(dialog.selectedFiles()[0])
                    lut = read_lut(filename)
                    self.current = self.add_color(lut, user=True)
                    self.emit_selection()
            except:
                QMessageBox.critical(self, 'Error opening LUT file.',
                                     traceback.format_exc())
            self.setCurrentIndex(self.current)

        # color selection
        elif self.current != self.currentIndex():
            self.current = self.currentIndex()
            self.emit_selection()

    def on_highlighted(self, index):
        self._highlight_index = index

    # protected method overload

    def showPopup(self):
        super(ColorBox, self).showPopup()
        self.grabKeyboard()
        self._popup_shown = True

    def hidePopup(self):
        self.releaseKeyboard()
        self._popup_shown = False
        super(ColorBox, self).hidePopup()

    def keyPressEvent(self, ev):
        if self._popup_shown and ev.key() == Qt.Key_Delete:
            ev.accept()
            if (self._user_count > 0 and
                self._highlight_index >= self._base_count):
                self.removeItem(self._highlight_index)
                del self._luts[self._highlight_index]
                self._user_count -= 1
                if self._user_count == 0:
                    self.removeItem(self._base_count)
                old = self.current
                self.current = self.currentIndex()
                while self.itemData(self.current).isNull():
                    self.current -= 1
                    self.setCurrentIndex(self.current)
                self.hidePopup()
                if old != self.current:
                    self.emit_selection()
        else:
            ev.ignore()


#-------------------------------------------------------------------------------
# main:
#

