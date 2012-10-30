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

__all__ = ['SectionPostProcessing']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.config import _Section
from cecog.gui.guitraits import (StringTrait,
                                 BooleanTrait,
                                 FloatTrait,
                                 IntTrait,
                                 )

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_POST_PROCESSING = 'PostProcessing'



#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionPostProcessing(_Section):

    SECTION_NAME = SECTION_NAME_POST_PROCESSING

    OPTIONS = [
      ('post_processing',
       [
        ('ibb_analysis',
            BooleanTrait(False, label='IBB analysis')),
        ('mappingfile_path',
            StringTrait('', 1000, label='Mapping file path',
                                   widget_info=StringTrait.STRING_PATH)), 
        ('single_plot',
            BooleanTrait(True, label='Export single event',)),
        ('single_plot_max_plots',
            IntTrait(1, 1, 2000, label='Max. number',)),
        ('ibb_ratio_signal_threshold',
            FloatTrait(1.2, 0.5, 5, label='IBB minimum ratio signal threshold',)),    
        ('ibb_range_signal_threshold',
            FloatTrait(3, 0.5, 5, label='IBB minimum range threshold',)),   
        ('ibb_onset_factor_threshold',
            FloatTrait(1.2, 1, 5, label='IBB onset slope threshold',)),   
        ('nebd_onset_factor_threshold',
            FloatTrait(1.2, 1, 5, label='NEBD onset slope threshold',)),   
        ('plot_ylim1_low',
            IntTrait(0, 0, 2000, label='Y-axis limit (low)',)),  
        ('plot_ylim1_high',
            IntTrait(100, 1, 4000, label='Y-axis limit (high)',)),  
        ('single_plot_ylim_low',
            FloatTrait(1, 0, 10, label='Y-axis ratio range (low)',)),  
        ('single_plot_ylim_high',
            IntTrait(5, 1, 30, label='Y-axis ratio range (high)',)),  
        ('group_by_position',
            BooleanTrait(True, label='Position',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('group_by_oligoid',
            BooleanTrait(False, label='Oligo ID',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('group_by_genesymbol',
            BooleanTrait(False, label='Gene symbol',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('group_by_group',
            BooleanTrait(False, label='Group',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        
        ('color_sort_by_position',
            BooleanTrait(False, label='Position',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('color_sort_by_oligoid',
            BooleanTrait(True, label='Oligo ID',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('color_sort_by_genesymbol',
            BooleanTrait(False, label='Gene symbol',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('color_sort_by_group',
            BooleanTrait(False, label='Group',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        
        ('securin_analysis',
            BooleanTrait(True, label='Securin analysis')),
        
        ]
       )
    ]
