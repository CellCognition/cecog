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


from cecog.threads.hmm import HmmThread
from cecog.threads.pyhmm import PyHmmThread
from cecog.gui.analyzer import BaseProcessorFrame

class ErrorCorrectionFrame(BaseProcessorFrame):

    DISPLAY_NAME = 'Error Correction'

    def __init__(self, settings, parent, name):
        super(ErrorCorrectionFrame, self).__init__(settings, parent, name)

        self.register_control_button( 'pyhmm', PyHmmThread,
            ('start error correction', 'stop error correction'))

        self.add_group(None, [('primary', (0, 0, 1, 1)),
                              ('secondary', (0, 1, 1, 1)),
                              ('tertiary', (0, 2, 1, 1)),
                              ('merged', (0, 3, 1, 1))], label='Channels')

        self.add_group(None,
                       [('hmm_simple', ),
                        ('hmm_baumwelch', )],
                       layout='flow', link='hmm_learning',
                       label='HMM learning algorithm')

        self.add_input('ignore_tracking_branches')
        self.add_line()
        self.add_group('constrain_graph',
                       [('primary_graph',),
                        ('secondary_graph',),
                        ('tertiary_graph',),
                        ('merged_graph',)])

        self.add_group('position_labels',
                       [('mappingfile_path',)])
        self.add_group(None,
                       [('groupby_position',),
                        ('groupby_oligoid',),
                        ('groupby_genesymbol',),
                        ], layout='flow', link='groupby', label='Group by')
        self.add_line()
        self.add_group(None, [('max_time',), ], layout='flow',
                       link='plot_parameter', label='Plot parameter')
        self.add_group('overwrite_time_lapse',
                       [('timelapse',),], layout='flow')
        self.add_group('enable_sorting',
                       [('sorting_sequence',),], layout='flow')
        self.add_line()
        self.add_group('compose_galleries',
                       [('compose_galleries_sample', ),
                        ('resampling_factor', ),
                        ('size_gallery_image', )],
                       layout='flow', label="Gallery images",
                       link='compose_galleries')
        self.add_expanding_spacer()
        self._init_control(has_images=False)

    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings( \
            self, name, has_timelapse)
        settings.set_section('Processing')
        if settings.get2('primary_classification'):
            settings.set2('primary_errorcorrection', True)
        if not settings.get2('secondary_processchannel'):
            settings.set2('secondary_classification', False)
            settings.set2('secondary_errorcorrection', False)
        elif settings.get2('secondary_classification'):
            settings.set2('secondary_errorcorrection', True)
        return settings
