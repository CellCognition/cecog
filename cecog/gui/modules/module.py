"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                           See LICENSE.txt for details.
                    See AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'


import os

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

import cellh5


class ModuleManager(object):

    def __init__(self, toolbar, stacked_frame):
        self.toolbar = toolbar
        self.stacked_frame = stacked_frame
        self._tabs = {}
        self.current_widget = None
        self._toolbar_grp = QButtonGroup(self.toolbar)
        self._toolbar_grp.setExclusive(True)

    def register_tab(self, widget):
        idx = len(self._tabs)
        name = widget.NAME
        btn = QPushButton(name, self.toolbar)
        btn.toggled.connect(lambda state: self.on_tab_changed(name, state))
        btn.setFlat(True)
        btn.setCheckable(True)
        self.toolbar.addWidget(btn)
        self._toolbar_grp.addButton(btn, idx)
        self.stacked_frame.addWidget(widget)
        self._tabs[name] = (widget, idx)

    def activate_tab(self, name):
        self.current_widget, idx = self._tabs[name]
        btn = self._toolbar_grp.button(idx)
        btn.setChecked(True)
        self.current_widget.activate()

    def get_widget(self, name):
        return self._tabs[name][0]

    def on_tab_changed(self, name, state=True):
        if not state:
            return
        if not self.current_widget is None:
            self.current_widget.deactivate()
        self.current_widget = self.get_widget(name)
        self.current_widget.activate()
        self.stacked_frame.setCurrentWidget(self.current_widget)


class Module(QFrame):

    NAME = ''

    def __init__(self, module_manager, browser):
        self.module_manager = module_manager
        self.browser = browser
        super(Module, self).__init__(self.module_manager.stacked_frame)
        self.is_initialized = False
        self.module_manager.register_tab(self)

    def initialize(self):
        pass

    def activate(self):
        if not self.is_initialized:
            try:
                self.initialize()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            else:
                self.is_initialized = True

    def deactivate(self):
        pass


class CH5BasedModule(Module):
    def __init__(self, module_manager, browser, settings, imagecontainer):
        super(CH5BasedModule, self).__init__(module_manager, browser)
        self._imagecontainer = imagecontainer
        self._settings = settings

    def initialize(self):
        super(CH5BasedModule, self).initialize()
        self.hdf_file = os.path.join(
            self._settings.get('General', 'pathout'), 'hdf5',
            '_all_positions.ch5')

        if not os.path.exists(self.hdf_file):
            raise IOError(("CellH5 files not yet created. Interactive viewing "
                           "of selected events will not be possible."))
            self.ch5file = None
        else:
            try:
                self.ch5file = cellh5.CH5File(self.hdf_file, mode="r")
            except Exception as e:
                raise RuntimeError(("Invalid CellH5 files. Interactive viewing "
                                    "of selected events will not be possible.\n "
                                    "%s is corrupt!\n\n%s"
                                    %(self.hdf_file, str(e))))

    @property
    def coordinates(self):
        return self.ch5file.get_coordinates()


    def close(self):
        if self.ch5file is not None:
            self.ch5file.close()
