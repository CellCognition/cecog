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

from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import (StyledFrame,
                            StyledSideFrame,
                            StyledButton,
                            )

from cecog.plugins.masks.primary import Primary

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class MaskManager(object):

    NAME = 'MaskManager'
    TEXT = 'mask'

    def __init__(self):
        self.available_plugins = OrderedDict()
        self.active_plugins = OrderedDict()

    def register(self, plugin):
        self.available_plugins[plugin.NAME] = plugin

    def get(self, name):
        return self.available_plugins[name]

    def activate(self, name):
        plugin = self.get(name)
        idx = 2
        id_name = name
        while id_name in self.active_plugins:
            id_name = "%s - %d" % (name, idx)
            idx += 1
        self.active_plugins[id_name] = plugin
        return id_name, plugin

    @property
    def plugins(self):
        return self.available_plugins.iteritems()

mask_manager = MaskManager()
mask_manager.register(Primary)


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
            self.combo.addItem(name, name)

        button_ok = QPushButton('Ok', self)
        button_cancel = QPushButton('Cancel', self)

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


class MaskFrame(StyledFrame):

    def __init__(self, parent):
        super(StyledFrame, self).__init__(parent)

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

    def on_button_plus(self):
        selector = PluginSelector(self, mask_manager)
        if selector.exec_():
            name, plugin = mask_manager.activate(selector.selection)
            plugin_widget = PluginWidget(self.list_widget, plugin)
            idx = self.list_widget.addItem(plugin_widget, name)
            self.list_widget.setCurrentIndex(idx)

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

#-------------------------------------------------------------------------------
# main:
#

