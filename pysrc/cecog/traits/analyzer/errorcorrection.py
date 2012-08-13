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

__all__ = ['SectionErrorcorrection']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.settings import _Section
from cecog.gui.guitraits import (StringTrait,
                                 FloatTrait,
                                 BooleanTrait,
                                 IntTrait,
                                 )

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_ERRORCORRECTION = 'ErrorCorrection'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionErrorcorrection(_Section):

    SECTION_NAME = SECTION_NAME_ERRORCORRECTION

    OPTIONS = [
      ('error_correction',
       [('filename_to_r',
            StringTrait('', 1000, label='R-project executable',
                        widget_info=StringTrait.STRING_FILE)),
        ('constrain_graph',
            BooleanTrait(True, label='Constrain graph')),
        ('primary_graph',
            StringTrait('', 1000, label='Primary file',
                        widget_info=StringTrait.STRING_FILE)),
        ('secondary_graph',
            StringTrait('', 1000, label='Secondary file',
                        widget_info=StringTrait.STRING_FILE)),
        ('skip_processed_plates',
            BooleanTrait(False, label='Skip processed plates')),
        ('position_labels',
            BooleanTrait(False, label='Position labels')),
        ('mappingfile_path',
            StringTrait('', 1000, label='Path',
                        widget_info=StringTrait.STRING_PATH)),
        ('groupby_position',
            BooleanTrait(True, label='Position',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('groupby_oligoid',
            BooleanTrait(False, label='Oligo ID',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('groupby_genesymbol',
            BooleanTrait(False, label='Gene symbol',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('overwrite_time_lapse',
            BooleanTrait(False, label='Overwrite time-lapse')),
        ('timelapse',
            FloatTrait(1, 0, 2000, digits=2,
                       label='Time-lapse [min]')),
        ('max_time',
            FloatTrait(100, 1, 2000, digits=2,
                       label='Max. time in plot [min]')),
        ('ignore_tracking_branches',
            BooleanTrait(False, label='Ignore tracking branches')),
        ('show_html',
            BooleanTrait(True, label='Open in browser')),
        ('enable_sorting',
            BooleanTrait(False, label='Sort by phase duration')),
        ('sorting_sequence',
            StringTrait('', 1000, label='Label sequence',
                                   mask='(\w+,)*\w+')),
        ('primary_sort',
            StringTrait('', 100)),
        ('secondary_sort',
            StringTrait('', 100)),
        ('compose_galleries',
            BooleanTrait(False, label='Compose gallery images')),
        ('compose_galleries_sample',
            IntTrait(-1, -1, 10000, label='Max. number of random samples')),
        ])
      ]