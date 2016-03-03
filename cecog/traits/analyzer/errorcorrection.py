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

from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import StringTrait, FloatTrait, BooleanTrait, IntTrait

SECTION_NAME_ERRORCORRECTION = 'ErrorCorrection'

class SectionErrorcorrection(SectionCore):

    SECTION_NAME = SECTION_NAME_ERRORCORRECTION

    OPTIONS = [
      ('error_correction',
       [('primary', BooleanTrait(True, label='primary')),
        ('secondary', BooleanTrait(False, label='secondary')),
        ('tertiary', BooleanTrait(False, label='tertiary')),
        ('merged', BooleanTrait(False, label='merged')),

        ('constrain_graph',
            BooleanTrait(True, label='Constrain graph')),
        ('primary_graph',
         StringTrait('', 1000, label='Primary file',
                     widget_info=StringTrait.STRING_FILE)),
        ('secondary_graph',
         StringTrait('', 1000, label='Secondary file',
                     widget_info=StringTrait.STRING_FILE)),
        ('tertiary_graph',
         StringTrait('', 1000, label='Tertiary file',
                     widget_info=StringTrait.STRING_FILE)),
        ('merged_graph',
         StringTrait('', 1000, label='Merged ch. file',
                     widget_info=StringTrait.STRING_FILE)),
        ('groupby_position',
         BooleanTrait(True, label='Position',
                      widget_info=BooleanTrait.RADIOBUTTON)),
        ('groupby_oligoid',
         BooleanTrait(False, label='Oligo ID',
                      widget_info=BooleanTrait.RADIOBUTTON)),
        ('hmm_smoothing',
         BooleanTrait(True, label='Smoothing Model',
                      widget_info=BooleanTrait.RADIOBUTTON)),
        ('hmm_baumwelch',
         BooleanTrait(False, label='Baum-Welch',
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
         FloatTrait(-1, -1, 2000, digits=2,
                    label='Max. time in plot [min]')),
        ('ignore_tracking_branches',
         BooleanTrait(False, label='Ignore tracking branches')),
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
        ('resampling_factor',
         FloatTrait(0.4, 0.01, 1.0, label="Resampling factor")),
        ('size_gallery_image',
         IntTrait(60, 1, 1000, label='Size of gallery images (px)'))
        ])
      ]
