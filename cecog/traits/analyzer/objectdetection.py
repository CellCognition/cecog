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

from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import IntTrait, StringTrait, BooleanTrait, \
    SelectionTrait, SelectionTrait2


from cecog.util.util import unlist

PROJECTION_METHODS = ('maximum', 'average')

SECTION_NAME_OBJECTDETECTION = 'ObjectDetection'

class SectionObjectdetection(SectionCore):

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
        ('primary_flat_field_correction_image_dir',
            StringTrait('', 1000, label='Correction image directory',
                                   widget_info=StringTrait.STRING_PATH)),
        ('primary_zslice_selection_slice',
            IntTrait(1, 0, 1000, label='Slice')),
        ('primary_zslice_projection',
            BooleanTrait(False, label='Z-slice projection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('primary_zslice_projection_method',
            SelectionTrait(PROJECTION_METHODS[0],
                           PROJECTION_METHODS, label='Method')),
        ('primary_zslice_projection_begin',
            IntTrait(1, 0, 1000, label='Begin')),
        ('primary_zslice_projection_end',
            IntTrait(1, 0, 1000, label='End')),
        ('primary_zslice_projection_step',
         IntTrait(1, 1, 1000, label='Step')),
        # these two options are nopes, just to have no
        # special casing in channel classes
        ('primary_channelregistration_x',
         IntTrait(0, -99999, 99999, label='Shift X')),
        ('primary_channelregistration_y',
         IntTrait(0, -99999, 99999, label='Shift Y')),
        ]),
      ] + \
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
        ('%s_flat_field_correction_image_dir' % prefix,
            StringTrait('', 1000, label='Correction image directory',
                                   widget_info=StringTrait.STRING_PATH)),
        ('%s_zslice_selection_slice' % prefix,
            IntTrait(1, 0, 1000, label='Slice')),
        ('%s_zslice_projection' % prefix,
            BooleanTrait(False, label='Z-slice projection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('%s_zslice_projection_method' % prefix,
            SelectionTrait(PROJECTION_METHODS[0],
                           PROJECTION_METHODS, label='Method')),
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
        ('%s_channelregistration_y' % prefix,
            IntTrait(0, -99999, 99999, label='Shift Y')),
       ]),

       ]
       for name, prefix in [('Secondary', 'secondary'),
                            ('Tertiary', 'tertiary'),
                            # moste merged channel options are nopes
                            # to avoid special casing
                            ('Merged', 'merged')
                            ]]
      )
