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
from cecog.traits.guitraits import (StringTrait,
                                    IntTrait,
                                    BooleanTrait,
                                    SelectionTrait,
                                    DictTrait,
                                    ListTrait
                                    )

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

    SECTION = 'General'

    def __init__(self, settings, parent):
        super(GeneralFrame, self).__init__(settings, parent)

        self.add_input('pathIn',
                       StringTrait('', 1000, label='Data folder',
                                   widget_info=StringTrait.STRING_PATH))
        self.add_input('pathOut',
                       StringTrait('', 1000, label='Output folder',
                                   widget_info=StringTrait.STRING_PATH))

        naming_schemes = settings.naming_schemes.sections()
        self.add_input("namingScheme",
                       SelectionTrait(naming_schemes[0], naming_schemes,
                                      label="Naming scheme"))

        self.add_line()

        self.add_group('constrain_positions',
                       BooleanTrait(False, label='Constrain positions'),
                       [('positions',
                        StringTrait('', 1000, label='Positions',
                                   mask='(\w+,)*\w+'))
                       ])

        self.add_input('redoFailedOnly',
                       BooleanTrait(True, label='Skip processed positions'))

        self.add_line()

        self.add_group('frameRange',
                       BooleanTrait(False, label='Constrain timepoints'),
                       [('frameRange_begin',
                         IntTrait(1, 0, 10000, label='Begin')),
                        ('frameRange_end',
                         IntTrait(1, 0, 1000, label='End'))
                        ], layout='flow')

        self.add_input('frameIncrement',
                       IntTrait(1, 1, 100, label='Timepoint increment'))

#        self.add_input('imageOutCompression',
#                       StringTrait('98', 5, label='Image output compresion',
#                                   tooltip='abc...'))

        self.register_trait('preferimagecontainer', BooleanTrait(False))
        self.register_trait('binningFactor', IntTrait(1,1,10))
        self.register_trait('timelapseData', BooleanTrait(True))
        self.register_trait('qualityControl', BooleanTrait(False))
        self.register_trait('debugMode', BooleanTrait(False))
        self.register_trait('createImages', BooleanTrait(True))
        self.register_trait('imageOutCompression',
                            StringTrait('98', 5,
                                        label='Image output compresion'))


        self.add_expanding_spacer()

        self.register_trait('rendering',
                            DictTrait({}, label='Rendering'))
#        self.register_trait('rendering_discwrite',
#                       BooleanTrait(True, label='Write images to disc'))
        self.register_trait('rendering_class',
                       DictTrait({}, label='Rendering class'))
#        self.register_trait('rendering_class_discwrite',
#                       BooleanTrait(True, label='Write images to disc'))


        self.register_trait('primary_featureExtraction_exportFeatureNames',
                            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Primary channel'))
        self.register_trait('secondary_featureExtraction_exportFeatureNames',
                            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Secondary channel'))


        layout = QHBoxLayout(self._control)
        btn1 = QPushButton('Load settings...', self._control)
        btn2 = QPushButton('Save settings', self._control)
        btn3 = QPushButton('Save settings as...', self._control)
        layout.addStretch()
        layout.addWidget(btn1)
        layout.addWidget(btn2)
        layout.addWidget(btn3)
        layout.addStretch()
        self.connect(btn1, SIGNAL('clicked()'), self.parent().main_window._on_file_open)
        self.connect(btn2, SIGNAL('clicked()'), self.parent().main_window._on_file_save)
        self.connect(btn3, SIGNAL('clicked()'), self.parent().main_window._on_file_save_as)

        help_button = QToolButton(self._control)
        help_button.setIcon(QIcon(':question_mark'))
        handler = lambda x: lambda : self._on_show_help(x)
        self.connect(help_button, SIGNAL('clicked()'), handler('controlpanel'))
        layout.addWidget(help_button)


