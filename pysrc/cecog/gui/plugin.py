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

__all__ = []

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
from cecog.gui.util import (StyledFrame,
                            StyledSideFrame,
                            StyledButton,
                            )
from cecog.gui.dynamicwidget import PhenoStyledSideFrame, PhenoFrame
from cecog.core.workflow import workflow_manager
from cecog.core.plugin import PluginManager

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class GuiPluginManagerMixin:

    DISPLAY_CLASS = None

    @classmethod
    def create_widget(cls, plugin_item, parent):
        frame = QSplitter(Qt.Vertical, parent)
        plugin, entity = plugin_item.plugin, plugin_item.entity

        if not plugin is None:
            scroll_area = QScrollArea(frame)
            plugin_frame = PhenoFrame(plugin, scroll_area)
            #plugin_frame.setBackgroundRole(QPalette.Dark)
            scroll_area.setWidget(plugin_frame)
        else:
            plugin_frame = None


        display_frame = cls.DISPLAY_CLASS(entity, frame)
        entity.register_display(display_frame)

        frame.addWidget(display_frame)
        #frame.plugin_frame = plugin_frame
        #frame.display_frame = display_frame
        return frame

    def register_gui_handler(self, gui_handler):
        self._gui_handler = gui_handler



class ActionSelectorFrame(StyledFrame):

    def __init__(self, manager_name, parent):
        super(ActionSelectorFrame, self).__init__(parent)

        self._manager_name = manager_name
        manager = workflow_manager.get_manager(self._manager_name)
        manager.register_gui_handler(self)

        self.layout = QGridLayout()

        self.list_widget = QToolBox(self)
        self.button_plus = StyledButton('+', self)
        self.button_minus = StyledButton('-', self)
        self.button_up = StyledButton('up', self)
        self.button_down = StyledButton('down', self)
        self.button_help = StyledButton('help', self)

        self.connect(self.button_plus, SIGNAL('clicked()'),
                     self.on_button_plus)
        self.connect(self.button_minus, SIGNAL('clicked()'),
                     self.on_button_minus)
        self.connect(self.button_up, SIGNAL('clicked()'),
                     self.on_button_up)
        self.connect(self.button_down, SIGNAL('clicked()'),
                     self.on_button_down)

        self.layout.addWidget(self.list_widget, 0, 0, 1, 5)
        self.layout.addWidget(self.button_plus, 1, 0)
        self.layout.addWidget(self.button_minus, 1, 1)
        self.layout.addWidget(self.button_up, 1, 2)
        self.layout.addWidget(self.button_down, 1, 3)
        self.layout.addWidget(self.button_help, 1, 4)

        self.setLayout(self.layout)

    def add_plugin(self, name):
        manager = workflow_manager.get_manager(self._manager_name)
        name, plugin_item = manager.activate(name)
        widget = manager.create_widget(plugin_item,
                                       self.list_widget)
        idx = self.list_widget.addItem(widget, name)
        self.list_widget.setCurrentIndex(idx)


    def on_button_plus(self):
        manager = workflow_manager.get_manager(self._manager_name)
        selector = PluginSelector(self, manager)
        if selector.exec_():
            self.add_plugin(selector.selection)

    def on_button_minus(self):
        pass

    def on_button_up(self):
        idx = self.list_widget.currentIndex()
        if idx > 0:
            widget = self.list_widget.currentWidget()
            text = self.list_widget.itemText(idx)
            self.list_widget.removeItem(idx)
            idx -= 1
            self.list_widget.insertItem(idx, widget, text)
            self.list_widget.setCurrentIndex(idx)

    def on_button_down(self):
        idx = self.list_widget.currentIndex()
        if idx < self.list_widget.count()-1:
            widget = self.list_widget.currentWidget()
            text = self.list_widget.itemText(idx)
            self.list_widget.removeItem(idx)
            idx += 1
            self.list_widget.insertItem(idx, widget, text)
            self.list_widget.setCurrentIndex(idx)


class PluginSelector(QDialog):

    def __init__(self, parent, manager):
        super(PluginSelector, self).__init__(parent, Qt.Sheet)

        self.manager = manager
        self.selection = None

        self.setModal(True)
        self.setWindowTitle('Select %s plugin...' % self.manager.TEXT)

        layout = QGridLayout()

        self.combo = QComboBox(self)
        for name, plugin in self.manager.plugins:
            if not plugin is None:
                self.combo.addItem(name, name)

        button_ok = QPushButton('Ok', self)
        button_cancel = QPushButton('Cancel', self)

        if len(self.manager.plugins) == 0:
            button_ok.setEnabled(False)

        layout.addWidget(self.combo, 0, 0, 1, 2)
        layout.addWidget(button_ok, 1, 0)
        layout.addWidget(button_cancel, 1, 1)
        self.setLayout(layout)

        self.connect(button_ok, SIGNAL('clicked()'), self.on_ok)
        self.connect(button_cancel, SIGNAL('clicked()'), self.on_cancel)

    def on_ok(self):
        self.selection =\
            str(self.combo.itemData(self.combo.currentIndex()).toString())
        self.accept()

    def on_cancel(self):
        self.reject()


class PluginWidget(StyledSideFrame):

    def __init__(self, parent, plugin):
        super(PluginWidget, self).__init__(parent)

#-------------------------------------------------------------------------------
# main:
#

