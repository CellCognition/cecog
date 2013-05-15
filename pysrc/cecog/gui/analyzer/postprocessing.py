"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Christoph Sommer'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['PostProcessingFrame']

import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from cecog.gui.util import information, exception

from cecog.gui.analyzer import BaseProcessorFrame,  PostProcessingThread
from cecog.analyzer.channel import PrimaryChannel
from cecog.analyzer.channel import SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel

from cecog.learning.learning import CommonClassPredictor
from cecog.util.util import hexToRgb


class PostProcessingFrame(BaseProcessorFrame):

    DISPLAY_NAME = 'Plots and Postprocessing'

    def __init__(self, settings, parent, name):
        super(PostProcessingFrame, self).__init__(settings, parent, name)
        self.register_control_button('post_processing',
                                     PostProcessingThread,
                                     ('Start', 'Stop'))

        self.add_group(None, [('mappingfile_path',)], label='Mapping file path')

        self.add_line()

        self.add_group('ibb_analysis', [
                        ('ibb_ratio_signal_threshold', (0,0,1,1)),
                        ('ibb_range_signal_threshold', (0,1,1,1)),
                        ('ibb_onset_factor_threshold', (1,0,1,1)),
                        ('nebd_onset_factor_threshold', (1,1,1,1)),
                        ],
                       layout='grid', link='ibb_analysis_params', label='Group by')

        self.add_group(None, [
                        ('group_by_position', (0,0,1,1)),
                        ('group_by_oligoid', (0,1,1,1)),
                        ('group_by_genesymbol', (0,2,1,1)),
                        ('group_by_group', (0,3,1,1)),
                        ],
                       layout='grid', link='groupby', label='Group by')
        self.add_group(None, [
                        ('color_sort_by_position', (0,0,1,1)),
                        ('color_sort_by_oligoid', (0,1,1,1)),
                        ('color_sort_by_genesymbol', (0,2,1,1)),
                        ('color_sort_by_group', (0,3,1,1)),
                        ],
                       layout='grid', link='color_sort', label='Color sort')
        self.add_group(None, [
                        ('single_plot', (0,0,1,1)),
                        ('single_plot_max_plots', (0,1,1,1)),
                        ('single_plot_ylim_low', (0,2,1,1)),
                        ('single_plot_ylim_high', (0,3,1,1)),
                        ('plot_ylim1_low', (1,0,1,1)),
                        ('plot_ylim1_high', (1,1,1,1)),
                        ],
                       layout='grid', link='plot_params', label='Plotting')

        self.add_line()
        self.add_group('securin_analysis',[])
        self.add_expanding_spacer()

        self._init_control(has_images=False)
