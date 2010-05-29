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
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['GeneralFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.analyzer import _BaseFrame
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class GeneralFrame(_BaseFrame):

    SECTION_NAME = SECTION_NAME_GENERAL

    def __init__(self, settings, parent):
        super(GeneralFrame, self).__init__(settings, parent)

        self.add_input('pathin')
        self.add_input('pathout')
        self.add_input('namingscheme')
        self.add_line()
        self.add_group('constrain_positions', [('positions',)])
        self.add_input('redofailedonly')
        self.add_line()
        self.add_group('framerange', [('framerange_begin',),
                                      ('framerange_end',)],
                       layout='flow')
        self.add_input('frameincrement')
        self.add_expanding_spacer()

        layout = QHBoxLayout(self._control)
        btn1 = QPushButton('Load settings...', self._control)
        btn2 = QPushButton('Save settings', self._control)
        btn3 = QPushButton('Save settings as...', self._control)
        layout.addStretch()
        layout.addWidget(btn1)
        layout.addWidget(btn2)
        layout.addWidget(btn3)
        layout.addStretch()
        self.connect(btn1, SIGNAL('clicked()'),
                     self.parent().main_window._on_file_open)
        self.connect(btn2, SIGNAL('clicked()'),
                     self.parent().main_window._on_file_save)
        self.connect(btn3, SIGNAL('clicked()'),
                     self.parent().main_window._on_file_save_as)

        help_button = QToolButton(self._control)
        help_button.setIcon(QIcon(':question_mark'))
        handler = lambda x: lambda : self._on_show_help(x)
        self.connect(help_button, SIGNAL('clicked()'), handler('controlpanel'))
        layout.addWidget(help_button)


