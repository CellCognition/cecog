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

#-------------------------------------------------------------------------------
# standard library imports:
#
import functools

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# cecog imports:
#

#-------------------------------------------------------------------------------
# constants:
#
TAB_STYLE = \
'''
    QPushButton#tab {
        border: 1px solid #8f8f91;
        border-radius: 2px;
        padding: 3px;
        min-width: 120px;
    }

    QPushButton#tab:checked, QPushButton#tab:pressed {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #9a9b9e, stop: 1 #babbbe);
    }

    QStackedWidget#stacked {
        border: 1px solid #8f8f91;
    }
'''

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class TabControl(QFrame):

    """
    General tab control: list of buttons at the top and stacked widget below
    Should be merged with cecog.gui.modules.module.ModuleManager
    """

    current_changed = pyqtSignal(int)

    def __init__(self, parent, hide_one=True):
        QFrame.__init__(self, parent)

        self.setStyleSheet(TAB_STYLE)

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

        btn = QPushButton(name, self._btn_frame)
        btn.setObjectName('tab')
        btn.setFlat(True)
        btn.setCheckable(True)
        btn.toggled.connect(functools.partial(self._on_btn_toggled, name))
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
        if (self._hide_one and len(self._tabs) <= 1) or (not self._hide_one and len(self._tabs) == 0):
            self._btn_frame.hide()

    def set_active(self, name, toggle=True):
        scroll_area = self._tabs[name][0]
        if toggle:
            btn = self._tabs[name][2]
            btn.setChecked(True)
        self._stacked_frame.setCurrentWidget(scroll_area)
        self._current_name = name
        self.current_changed.emit(self._tabs.index(name))

    def set_active_index(self, index):
        name = self._tabs.keys()[index]
        self.set_active(name)

    def _on_btn_toggled(self, name):
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
        return self._tabs.index(self._current_name)

#-------------------------------------------------------------------------------
# main:
#

