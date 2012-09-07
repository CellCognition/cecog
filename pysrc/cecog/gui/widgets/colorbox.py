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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

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
class ColorBox(QComboBox):

    selection_changed = pyqtSignal(str)

    COLOR_SIZE = (60, 10)
    TEXT_MORE = 'more...'
    TEXT_LUT = 'LUT...'

    def __init__(self, current, palettes, parent):
        super(ColorBox, self).__init__(parent)
        self.setIconSize(QSize(*self.COLOR_SIZE))

        self.setStyleSheet('font-size: 10px;')

        self._popup_shown = False
        self._base_count = len(palettes) + 1
        self._user_count = 0
        self._highlight_index = None

        for name, palette in palettes.iteritems():
            self.add_palette(name, palette)

#        self.insertSeparator(self.count())
#        self.insertItem(self.count(), self.TEXT_MORE,
#                        QVariant(self.TEXT_MORE))

        self.setCurrentIndex(self.findData(current))
        self.currentIndexChanged[int].connect(self._on_current_changed)


    def add_palette(self, name, palette, user=False):
        pixmap = QPixmap(*self.COLOR_SIZE)
        lut = palette.lut
        f = 256. / self.COLOR_SIZE[0]
        painter = QPainter(pixmap)
        for w in range(self.COLOR_SIZE[0]):
            i = int(f * w)
            painter.fillRect(w, 0, w+1, self.COLOR_SIZE[1], QColor(*lut[i]))
        painter.end()
        icon = QIcon(pixmap)
        index = self._base_count+self._user_count
        self.insertItem(index, icon, '  '+name.capitalize(), name)
#            if self._user_count == 0:
#                self.insertSeparator(index+1)
#            self._user_count += 1
#        else:
#            index = self.count()
#            self.insertItem(index, icon, '', QVariant(color))
#        self._luts[index] = lut
        return index

    def _on_current_changed(self, idx):
        name = self.itemData(idx)
        self.selection_changed.emit(name)

#    def on_activated(self, index):
#        if self.itemData(index).toString() == self.TEXT_MORE:
#            dialog = QColorDialog(self.get_current_qcolor(), self)
#            dialog.setOption(QColorDialog.ShowAlphaChannel)
#            if dialog.exec_():
#                color = dialog.selectedColor()
#                #print color
#                #print color.alpha()
#                self.current = self.add_color(color, user=True)
#                self.emit_selection()
#            self.setCurrentIndex(self.current)
#
#        # LUT...
#        elif self.itemData(index).toString() == self.TEXT_LUT:
#            dialog = QFileDialog(self)
#            dialog.setFileMode(QFileDialog.ExistingFile)
#            dialog.setNameFilters(['*.lut', '*.*'])
#            try:
#                if dialog.exec_():
#                    filename = str(dialog.selectedFiles()[0])
#                    lut = read_lut(filename)
#                    self.current = self.add_color(lut, user=True)
#                    self.emit_selection()
#            except:
#                QMessageBox.critical(self, 'Error opening LUT file.',
#                                     traceback.format_exc())
#            self.setCurrentIndex(self.current)
#
#        # color selection
#        elif self.current != self.currentIndex():
#            self.current = self.currentIndex()
#            self.emit_selection()
#    def on_highlighted(self, index):
#        self._highlight_index = index
#
#    # protected method overload
#
#    def showPopup(self):
#        super(ColorBox, self).showPopup()
#        self.grabKeyboard()
#        self._popup_shown = True
#
#    def hidePopup(self):
#        self.releaseKeyboard()
#        self._popup_shown = False
#        super(ColorBox, self).hidePopup()
#
#    def keyPressEvent(self, ev):
#        if self._popup_shown and ev.key() == Qt.Key_Delete:
#            ev.accept()
#            if (self._user_count > 0 and
#                self._highlight_index >= self._base_count):
#                self.removeItem(self._highlight_index)
#                del self._luts[self._highlight_index]
#                self._user_count -= 1
#                if self._user_count == 0:
#                    self.removeItem(self._base_count)
#                old = self.current
#                self.current = self.currentIndex()
#                while self.itemData(self.current).isNull():
#                    self.current -= 1
#                    self.setCurrentIndex(self.current)
#                self.hidePopup()
#                if old != self.current:
#                    self.emit_selection()
#        else:
#            ev.ignore()


#-------------------------------------------------------------------------------
# main:
#

