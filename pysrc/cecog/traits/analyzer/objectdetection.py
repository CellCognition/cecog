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

__all__ = ['SectionObjectdetection']

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
from cecog.gui.guitraits import (IntTrait,
                                 StringTrait,
                                 BooleanTrait,
                                 SelectionTrait,
                                 SelectionTrait2,
                                 )
from cecog.analyzer import (ZSLICE_PROJECTION_METHODS
                            )
from cecog.util.util import unlist

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_OBJECTDETECTION = 'ObjectDetection'


#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class SectionObjectdetection(_Section):

    SECTION_NAME = SECTION_NAME_OBJECTDETECTION

    OPTIONS = [
      ('primary_image',
       [('primary_channelid',
            SelectionTrait2(None, [], label='Primary channel ID')),
        ('primary_normalizemin',
            IntTrait(0, -2**16, 2**16, label='Min.')),
        ('primary_normalizemax',
            IntTrait(255, -2**16, 2**16, label='Max.')),
        ('primary_zslice_selection',
            BooleanTrait(True, label='Z-slice selection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('primary_flat_field_correction',
            BooleanTrait(False, label='Z-slice flat field correction',
                         widget_info=BooleanTrait.CHECKBOX)),
        ('primary_flat_field_correction_image_file',
            StringTrait('', 1000, label='Correction image',
                                   widget_info=StringTrait.STRING_FILE)),
        ('primary_zslice_selection_slice',
            IntTrait(1, 0, 1000, label='Slice')),
        ('primary_zslice_projection',
            BooleanTrait(False, label='Z-slice projection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('primary_zslice_projection_method',
            SelectionTrait(ZSLICE_PROJECTION_METHODS[0],
                           ZSLICE_PROJECTION_METHODS, label='Method')),
        ('primary_zslice_projection_begin',
            IntTrait(1, 0, 1000, label='Begin')),
        ('primary_zslice_projection_end',
            IntTrait(1, 0, 1000, label='End')),
        ('primary_zslice_projection_step',
            IntTrait(1, 1, 1000, label='Step')),
       ]),

      ] +\
      unlist(
      [[('%s_image' % prefix,
       [('%s_channelid' % prefix,
            SelectionTrait2(None, [], label='%s channel ID' % name)),
        ('%s_normalizemin' % prefix,
            IntTrait(0, -2**16, 2**16, label='Min.')),
        ('%s_normalizemax' % prefix,
            IntTrait(255, -2**16, 2**16, label='Max.')),

        ('%s_zslice_selection' % prefix,
            BooleanTrait(True, label='Z-slice selection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('%s_flat_field_correction' % prefix,
            BooleanTrait(False, label='Z-slice flat field correction',
                         widget_info=BooleanTrait.CHECKBOX)),
        ('%s_flat_field_correction_image_file' % prefix,
            StringTrait('', 1000, label='Correction image',
                                   widget_info=StringTrait.STRING_FILE)),
        ('%s_zslice_selection_slice' % prefix,
            IntTrait(1, 0, 1000, label='Slice')),
        ('%s_zslice_projection' % prefix,
            BooleanTrait(False, label='Z-slice projection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('%s_zslice_projection_method' % prefix,
            SelectionTrait(ZSLICE_PROJECTION_METHODS[0],
                           ZSLICE_PROJECTION_METHODS, label='Method')),
        ('%s_zslice_projection_begin' % prefix,
            IntTrait(1, 0, 1000, label='Begin')),
        ('%s_zslice_projection_end' % prefix,
            IntTrait(1, 0, 1000, label='End')),
        ('%s_zslice_projection_step' % prefix,
            IntTrait(1, 1, 1000, label='Step')),
       ]),

      ('%s_registration' % prefix,
       [('%s_channelregistration_x' % prefix,
            IntTrait(0, -99999, 99999, label='Shift X')),
        ('%s_channelRegistration_y' % prefix,
            IntTrait(0, -99999, 99999, label='Shift Y')),
       ]),

       ]
       for name, prefix in [('Secondary', 'secondary'),
                            ('Tertiary', 'tertiary'),
                            ]]
      ) + \
      [('merged_image', [('merged_channelid',
                          SelectionTrait2(None, [], label='Merged channel ID'))])
       ]
