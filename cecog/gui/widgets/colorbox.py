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


import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

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
        return index

    def _on_current_changed(self, idx):
        name = self.itemData(idx)
        self.selection_changed.emit(name)
