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

__all__ = ["SectionGeneral"]

from cecog import VERSION
from cecog.traits.analyzer.section_core import SectionCore

from cecog.gui.guitraits import (StringTrait,
                                 IntTrait,
                                 BooleanTrait,
                                 SelectionTrait,
                                 DictTrait,
                                 ListTrait
                                 )
from cecog.environment import CecogEnvironment

SECTION_NAME_GENERAL = 'General'

class SectionGeneral(SectionCore):

    SECTION_NAME = SECTION_NAME_GENERAL

    OPTIONS = [
      ('general',
       [('pathin',
            StringTrait('', 1000, label='Input directory',
                                   widget_info=StringTrait.STRING_PATH)),
        ('has_multiple_plates',
            BooleanTrait(False, label='Multiple plates')),

        ('pathout',
            StringTrait('', 1000, label='Output directory',
                                   widget_info=StringTrait.STRING_PATH)),
        ('image_import_namingschema',
            BooleanTrait(True, label='Import via naming schema',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('image_import_structurefile',
            BooleanTrait(False, label='Import via coordinate file',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('namingscheme',
            SelectionTrait(CecogEnvironment.naming_schema.sections()[0],
                           CecogEnvironment.naming_schema.sections(),
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

        ('framerange',
            BooleanTrait(False, label='Timelapse')),
        ('framerange_begin',
            IntTrait(1, 0, 10000, label='first')),
        ('framerange_end',
            IntTrait(1, 0, 1000, label='last')),
        ('frameincrement',
            IntTrait(1, 1, 100, label='increment')),


        ('redofailedonly',
            BooleanTrait(False, label='Skip finished positions')),
        ('constrain_positions', BooleanTrait(False, label='Positions')),
        ('positions',
         StringTrait('', 1000, label="", mask='(\w+,)*\w+')),

        ('process_primary', BooleanTrait(True, label='primary')),
        ('process_secondary', BooleanTrait(False, label='secondary')),
        ('process_tertiary', BooleanTrait(False, label='tertiary')),
        ('process_merged', BooleanTrait(False, label='merged')),


        ('crop_image',
            BooleanTrait(False, label='Image cropping')),
        ('crop_image_x0',
            IntTrait(-1, -1, 4000, label='upper left x:')),
        ('crop_image_y0',
            IntTrait(-1, -1, 4000, label='upper left y')),
        ('crop_image_x1',
            IntTrait(-1, -1, 4000, label='lower right x')),
        ('crop_image_y1',
            IntTrait(-1, -1, 4000, label='lower right y')),

        ('crop_image',
            BooleanTrait(False, label='Image cropping')),


        ('rendering', DictTrait({}, label='Rendering')),
        ('version', StringTrait('', 6, label='Cecog %s, file version:'
                                %VERSION, widget_info=StringTrait.STRING_GRAYED)),
        ('rendering_class', DictTrait({}, label='Rendering class')),
        ('primary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Primary channel')),
        ('secondary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Secondary channel')),
        ('tertiary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Tertiary channel')),

      ])
    ]
