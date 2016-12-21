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

__all__ = ['GeneralFrame']

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from cecog.gui.analyzer import BaseFrame


class GeneralFrame(BaseFrame):

    ICON = ":general.png"

    def __init__(self, settings, parent, name):
        super(GeneralFrame, self).__init__(settings, parent, name)

        self.add_group('version', [])
        self.add_input('pathin')
        self.add_input('has_multiple_plates')
        self.add_input('pathout')
        self.add_input('plate_layout')
        self.add_input('namingscheme')
        self.add_line()

        self.add_group(None, [('process_primary', (0, 0, 1, 1)),
                              ('process_secondary', (0, 1, 1, 1)),
                              ('process_tertiary', (0, 2, 1, 1)),
                              ('process_merged', (0, 3, 1, 1))],
                       link="channels", label='Color Channels')

        self.add_group('constrain_positions', [('positions',)])
        self.add_input('skip_finished')
        self.add_group('framerange', [('framerange_begin',),
                                      ('framerange_end',),
                                      ('frameincrement', )],
                       layout='flow')
        self.add_group('crop_image', [('crop_image_x0',),
                                      ('crop_image_y0',),
                                      ('crop_image_x1',),
                                      ('crop_image_y1',),],
                       layout='flow')


        self.add_expanding_spacer()

        buttonbar = QFrame(self)
        self.process_control.hide()
        self.layout().addWidget(buttonbar)

        layout = QHBoxLayout(buttonbar)
        layout.addStretch()

        btn = QPushButton('Scan Images', self)
        btn.setToolTip("Scan image directory")
        btn.clicked.connect(self.parent().main_window._on_load_input)
        layout.addWidget(btn)

        btn = QPushButton('Load Settings', buttonbar)
        layout.addWidget(btn)
        btn.clicked.connect(self.parent().main_window._on_file_open)
        self._btn_save = QPushButton('Save Settings', buttonbar)
        self._btn_save.setEnabled(False)
        layout.addWidget(self._btn_save)
        self._btn_save.clicked.connect(self.parent().main_window._on_file_save)
        btn = QPushButton('Save Settings as', buttonbar)
        layout.addWidget(btn)
        btn.clicked.connect(self.parent().main_window._on_file_save_as)

        self.parent().main_window.modified.connect(self._on_modified)
        layout.addStretch()

    def _on_modified(self, changed):
        self._btn_save.setEnabled(changed)
