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

__all__ = ['ErrorCorrectionFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.analyzer import (_BaseFrame,
                                _ProcessorMixin,
                                HmmThread
                                )
from cecog.traits.guitraits import (StringTrait,
                                    FloatTrait,
                                    BooleanTrait,
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
class ErrorCorrectionFrame(_BaseFrame, _ProcessorMixin):

    SECTION = 'ErrorCorrection'
    NAME = 'Error Correction'

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

        self.register_control_button('hmm',
                                     HmmThread,
                                     ('Correct errors', 'Stop correction'))

        self.add_input('filename_to_R',
                       StringTrait('', 1000, label='R-project executable',
                                   widget_info=StringTrait.STRING_FILE))

        self.add_line()

        self.add_group('constrain_graph',
                       BooleanTrait(True, label='Constrain graph'),
                       [('primary_graph',
                         StringTrait('', 1000, label='Primary file',
                                     widget_info=StringTrait.STRING_FILE)),
                        ('secondary_graph',
                         StringTrait('', 1000, label='Secondary file',
                                     widget_info=StringTrait.STRING_FILE)),
                        ])

        self.add_group('position_labels',
                       BooleanTrait(False, label='Position labels'),
                       [('mappingfile',
                         StringTrait('', 1000, label='File',
                                     widget_info=StringTrait.STRING_FILE)),
                        ])
        self.add_group('Group by', None,
                       [('groupby_position',
                         BooleanTrait(True, label='Position',
                                      widget_info=BooleanTrait.RADIOBUTTON)),
                        ('groupby_oligoid',
                         BooleanTrait(False, label='Oligo ID',
                                      widget_info=BooleanTrait.RADIOBUTTON)),
                        ('groupby_genesymbol',
                         BooleanTrait(False, label='Gene symbol',
                                      widget_info=BooleanTrait.RADIOBUTTON)),
                        ], layout='flow', link='groupby')

        self.add_line()

        self.add_group('Plot parameter', None,
                       [('timelapse',
                         FloatTrait(1, 0, 2000, digits=2,
                                    label='Time-lapse [min]')),
                        ('max_time',
                         FloatTrait(100, 1, 2000, digits=2,
                                    label='Max. time in plot [min]')),
                        ], layout='flow', link='plot_parameter')

        self.register_trait('primary_sort',
                            StringTrait('', 100))
        self.register_trait('secondary_sort',
                            StringTrait('', 100))

        self.add_expanding_spacer()

        self._init_control(has_images=False)

    def _get_modified_settings(self, name):
        settings = _ProcessorMixin._get_modified_settings(self, name)
        settings.set_section('Processing')
        if settings.get2('primary_classification'):
            settings.set2('primary_errorcorrection', True)
        if not settings.get2('secondary_processchannel'):
            settings.set2('secondary_classification', False)
            settings.set2('secondary_errorcorrection', False)
        elif settings.get2('secondary_classification'):
            settings.set2('secondary_errorcorrection', True)
        return settings
