"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                           See LICENSE.txt for details.
                    See AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import os

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

import cellh5

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import warning

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#

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
        btn.toggled.connect(lambda x: self.on_tab_changed(name))
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

    def on_tab_changed(self, name):
        if not self.current_widget is None:
            self.current_widget.deactivate()
        self.current_widget = self.get_widget(name)
        self.current_widget.activate()
        self.stacked_frame.setCurrentWidget(self.current_widget)


class Module(QFrame, object):

    NAME = ''

    def __init__(self, module_manager, browser):
        self.module_manager = module_manager
        self.browser = browser
        super(Module, self).__init__(self.module_manager.stacked_frame)
        self.is_initialized = False
        self.module_manager.register_tab(self)
        self.setStyleSheet(
"""
 QWidget {
     font-size: 11px;
 }

 QGroupBox {
     background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #E0E0E0, stop: 1 #FFFFFF);
     border: 2px solid #999999;
     border-radius: 5px;
     margin-top: 1ex; /* leave space at the top for the title */
     font-size: 13px;
     color: black;
 }

 QGroupBox::title {
     subcontrol-origin: margin;
     subcontrol-position: top center; /* position at the top center */
     padding: 0 3px;
     font-size: 13px;
     color: black;
 }

 QTableView {
     font-size: 10px;
     alternate-background-color: #EEEEFF;
 }

 QPushButton {
     font-size: 11px; min-width: 10px;
 }

 ColorButton::enabled {
     border: 1px solid #444444;
 }

 ColorButton::disabled {
     border: 1px solid #AAAAAA;
 }

""")

    def initialize(self):
        pass

    def activate(self):
        if not self.is_initialized:
            self.initialize()
            self.is_initialized = True

    def deactivate(self):
        pass
    
    
class CH5BasedModule(Module):
    def __init__(self, module_manager, browser, settings, imagecontainer):
        super(CH5BasedModule, self).__init__(module_manager, browser)
        self._imagecontainer = imagecontainer
        
        self._settings = settings
        self._init_ch5()
    
    def _init_ch5(self):
        self.hdf_file = os.path.join(self._settings.get('General', 'pathout'), 'hdf5', '_all_positions.ch5')
        
        if not os.path.exists(self.hdf_file):
            warning(self, "Invalid CellH5 files",
                        info="%s does not exist!" % self.hdf_file)
            
            self.ch5file = None
        else:
        
            self.ch5file = cellh5.CH5File(self.hdf_file)
            
    @property
    def coordinates(self):
        return self.ch5file.get_coordinates()
        
    
    def close(self):
        if self.ch5file is not None:
            self.ch5file.close()
    
