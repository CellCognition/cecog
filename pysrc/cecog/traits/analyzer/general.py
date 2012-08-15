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

__all__ = []

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
                                 IntTrait,
                                 BooleanTrait,
                                 SelectionTrait,
                                 DictTrait,
                                 ListTrait
                                 )
from cecog.config import NAMING_SCHEMAS

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_GENERAL = 'General'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class SectionGeneral(_Section):

    SECTION_NAME = SECTION_NAME_GENERAL

    OPTIONS = [
      ('general',
       [('pathin',
            StringTrait('', 1000, label='Image folder',
                                   widget_info=StringTrait.STRING_PATH)),
        ('has_multiple_plates',
            BooleanTrait(False, label='Multiple plates')),

        ('pathout',
            StringTrait('', 1000, label='Analysis folder',
                                   widget_info=StringTrait.STRING_PATH)),
        ('image_import_namingschema',
            BooleanTrait(True, label='Import via naming schema',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('image_import_structurefile',
            BooleanTrait(False, label='Import via coordinate file',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('namingscheme',
            SelectionTrait(NAMING_SCHEMAS.sections()[0],
                           NAMING_SCHEMAS.sections(),
                           label='Naming scheme')),
        ('structure_filename',
            StringTrait('', 1000, label='Coordinate filename',
                                   widget_info=StringTrait.STRING_FILE)),

        ('structure_file_pathin',
            BooleanTrait(True, label='Image folder',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('structure_file_pathout',
            BooleanTrait(False, label='Analysis folder',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('structure_file_extra_path',
            BooleanTrait(False, label='Different location',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('structure_file_extra_path_name',
            StringTrait('', 1000, label='Path',
                        widget_info=StringTrait.STRING_PATH)),

        ('constrain_positions',
            BooleanTrait(False, label='Constrain positions')),
        ('positions',
            StringTrait('', 1000, label='Positions',
                                   mask='(\w+,)*\w+')),
        ('crop_image',
            BooleanTrait(False, label='Crop image')),
        ('crop_image_x0',
            IntTrait(-1, -1, 4000, label='Upper left X')),
        ('crop_image_y0',
            IntTrait(-1, -1, 4000, label='Upper left Y')),
        ('crop_image_x1',
            IntTrait(-1, -1, 4000, label='Lower right X')),
        ('crop_image_y1',
            IntTrait(-1, -1, 4000, label='Lower right Y')),
        
        ('crop_image',
            BooleanTrait(False, label='Crop image')),
        
        
        ('redofailedonly',
            BooleanTrait(True, label='Skip processed positions')),
        ('framerange',
            BooleanTrait(False, label='Constrain timepoints')),
        ('framerange_begin',
            IntTrait(1, 0, 10000, label='Begin')),
        ('framerange_end',
            IntTrait(1, 0, 1000, label='End')),
        ('frameincrement',
            IntTrait(1, 1, 100, label='Timepoint increment')),

        ('rendering', DictTrait({}, label='Rendering')),
        ('version', StringTrait('1.3.0', 6, label='Version')),
        ('rendering_class', DictTrait({}, label='Rendering class')),
        ('primary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Primary channel')),
        ('secondary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Secondary channel')),
        ('tertiary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Tertiary channel')),

      ])
    ]


