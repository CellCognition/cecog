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
__date__ = '$Date: $'
__revision__ = '$Rev:  $'
__source__ = '$URL: $'

__all__ = ['TabControl']

import functools

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from collections import OrderedDict


class TabButton(QPushButton):
    pass

class TabControl(QFrame):
    """General tab control: list of buttons at the top and stacked widget below"""

    currentChanged = pyqtSignal(int)

    def __init__(self, parent, hide_one=True):
        super(TabControl, self).__init__(parent)

#         self.setStyleSheet(TAB_STYLE)

        self._hide_one = hide_one
        self._tabs = OrderedDict()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._btn_frame = QFrame(self)
        self._btn_grp = QButtonGroup(self._btn_frame)
        self._btn_grp.setExclusive(True)
        self._btn_layout = QHBoxLayout(self._btn_frame)
        self._btn_layout.insertStretch(0, 1)
        self._btn_layout.insertStretch(1, 1)
        self._stacked_frame = QStackedWidget(self)
        self._stacked_frame.setObjectName('stacked')
        layout.addWidget(self._btn_frame)
        layout.addWidget(self._stacked_frame)
        self._btn_frame.hide()
        self._current_name = None

    def add_tab(self, name, frame):
        scroll_area = QScrollArea(self)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(frame)

        btn = TabButton(name, self._btn_frame)
        btn.setObjectName('tab')
        btn.setFlat(True)
        btn.setCheckable(True)
        btn.clicked.connect(functools.partial(self._on_clicked, name))
        self._btn_grp.addButton(btn)
        self._tabs[name] = (scroll_area, frame, btn)
        self._stacked_frame.addWidget(scroll_area)
        self._btn_layout.insertWidget(len(self._tabs), btn)
        if not self._hide_one or len(self._tabs) > 1:
            self._btn_frame.show()

        self._current_name = name

    def remove_tab(self, name):
        scroll_area = self._tabs[name][0]
        btn = self._tabs[name][1]
        self._btn_layout.removeWidget(btn)
        self._stacked_frame.removeWidget(scroll_area)
        if (self._hide_one and len(self._tabs) <= 1) or \
                (not self._hide_one and len(self._tabs) == 0):
            self._btn_frame.hide()

    def set_active(self, name, toggle=True):
        if name == self._current_name:
            return

        scroll_area = self._tabs[name][0]
        if toggle:
            btn = self._tabs[name][2]
            btn.setChecked(True)
        self._stacked_frame.setCurrentWidget(scroll_area)

        self._current_name = name
        self.currentChanged.emit(self._tabs.keys().index(name))


    def set_active_index(self, index):
        name = self._tabs.keys()[index]
        self.set_active(name)

    def _on_clicked(self, name):
        self.set_active(name, toggle=False)

    def enable_non_active(self, state=True):
        for name in self._tabs:
            frame, btn = self._tabs[name][1:]
            if frame != self._stacked_frame.currentWidget():
                btn.setEnabled(state)

    def get_frame(self, name):
        return self._tabs[name][1]

    @property
    def current_name(self):
        return self._current_name

    @property
    def current_index(self):
        return self._tabs.keys().index(self._current_name)
