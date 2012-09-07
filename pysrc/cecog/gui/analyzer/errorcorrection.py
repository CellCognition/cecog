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
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION
from cecog.gui.analyzer import (BaseProcessorFrame,
                                HmmThread,
                                HmmThreadPython
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
class ErrorCorrectionFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_ERRORCORRECTION
    DISPLAY_NAME = 'Error Correction'

    def __init__(self, settings, parent):
        super(ErrorCorrectionFrame, self).__init__(settings, parent)

        self.register_control_button('hmm',
                                     HmmThread,
                                     ('Correct errors', 'Stop correction'))
        
        self.register_control_button('hmm2',
                                     HmmThreadPython,
                                     ('Correct errors (python)', 'Stop correction (python)'))

        self.add_input('filename_to_r')
        self.add_line()
        self.add_group('constrain_graph',
                       [('primary_graph',),
                        ('secondary_graph',),
                        ])
        self.add_group('position_labels',
                       [('mappingfile_path',),
                        ])
        self.add_group(None,
                       [('groupby_position',),
                        ('groupby_oligoid',),
                        ('groupby_genesymbol',),
                        ], layout='flow', link='groupby', label='Group by')
        self.add_line()
        self.add_input('skip_processed_plates')
        self.add_group('overwrite_time_lapse',
                       [('timelapse',),
                        ], layout='flow')
        self.add_group('enable_sorting',
                       [('sorting_sequence',),
                        ], layout='flow')
        self.add_group(None,
                       [('max_time',),
                        ], layout='flow', link='plot_parameter',
                        label='Plot parameter')
        self.add_input('ignore_tracking_branches')
        self.add_input('show_html')
        self.add_line()
        self.add_group('compose_galleries',
                       [('compose_galleries_sample',),
                        ], layout='flow')
        self.add_expanding_spacer()
        self._init_control(has_images=False)

    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings(self, name, has_timelapse)
        settings.set_section('Processing')
        if settings.get2('primary_classification'):
            settings.set2('primary_errorcorrection', True)
        if not settings.get2('secondary_processchannel'):
            settings.set2('secondary_classification', False)
            settings.set2('secondary_errorcorrection', False)
        elif settings.get2('secondary_classification'):
            settings.set2('secondary_errorcorrection', True)
        return settings
