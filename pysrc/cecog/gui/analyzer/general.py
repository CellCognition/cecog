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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from cecog import VERSION
from cecog.gui.analyzer import BaseFrame

class GeneralFrame(BaseFrame):

    def __init__(self, settings, parent, name):
        super(GeneralFrame, self).__init__(settings, parent, name)

        self.add_group('version', [])
        self.add_input('pathin')
        self.add_input('has_multiple_plates')
        self.add_input('pathout')
        # original: self.add_input('namingscheme')
        self.add_group('image_import_namingschema', [('namingscheme',),],
                       layout='flow')
        self.add_group('image_import_structurefile', [('structure_filename',)])
        self.add_group(None,
                       [('structure_file_pathin', (0,0,1,1)),
                        ('structure_file_pathout', (0,1,1,1)),
                        ('structure_file_extra_path', (0,2,1,1)),
                        ('structure_file_extra_path_name', (1,0,1,8)),
                        ], label='Structure file location')

        self.add_line()
        self.add_group('constrain_positions', [('positions',)])
        self.add_input('redofailedonly')
        self.add_line()
        self.add_group('framerange', [('framerange_begin',),
                                      ('framerange_end',)],
                       layout='flow')
        self.add_input('frameincrement')
        self.add_line()
        self.add_group('crop_image', [('crop_image_x0',),
                                      ('crop_image_y0',),
                                      ('crop_image_x1',),
                                      ('crop_image_y1',),],
                       layout='flow')


        self.add_expanding_spacer()

        layout = QHBoxLayout(self._control)
        layout.addStretch()
        btn = QPushButton('Load image data', self._control)
        layout.addWidget(btn)
        btn.clicked.connect(self.parent().main_window._on_load_input)
        btn = QPushButton('Load settings...', self._control)
        layout.addWidget(btn)
        btn.clicked.connect(self.parent().main_window._on_file_open)
        self._btn_save = QPushButton('Save settings', self._control)
        self._btn_save.setEnabled(False)
        layout.addWidget(self._btn_save)
        self._btn_save.clicked.connect(self.parent().main_window._on_file_save)
        btn = QPushButton('Save settings as...', self._control)
        layout.addWidget(btn)
        btn.clicked.connect(self.parent().main_window._on_file_save_as)
        layout.addStretch()
        self.parent().main_window.modified.connect(self._on_modified)

        help_button = QToolButton(self._control)
        help_button.setIcon(QIcon(':question_mark'))
        handler = lambda x: lambda : self._on_show_help(x)
        layout.addWidget(help_button)
        help_button.clicked.connect(handler('controlpanel'))

    def _on_modified(self, changed):
        self._btn_save.setEnabled(changed)
