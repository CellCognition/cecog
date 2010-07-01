"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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
from cecog.traits.config import _Section
from cecog.gui.guitraits import (StringTrait,
                                 IntTrait,
                                 BooleanTrait,
                                 SelectionTrait,
                                 DictTrait,
                                 ListTrait
                                 )
from cecog.traits.config import NAMING_SCHEMAS

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
            StringTrait('', 1000, label='Data folder',
                                   widget_info=StringTrait.STRING_PATH)),
        ('pathout',
            StringTrait('', 1000, label='Output folder',
                                   widget_info=StringTrait.STRING_PATH)),
        ('image_import_namingschema',
            BooleanTrait(True, label='Import via naming schema',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('image_import_structurefile',
            BooleanTrait(False, label='Import via structure file',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('namingscheme',
            SelectionTrait(NAMING_SCHEMAS.sections()[0],
                           NAMING_SCHEMAS.sections(),
                           label='Naming scheme')),
        ('structure_filename',
            StringTrait('', 1000, label='Folder to structure files',
                                   widget_info=StringTrait.STRING_PATH)),

#        ('primary_zslice_selection_slice',
#            IntTrait(1, 0, 1000, label='Slice')),
#        ('primary_zslice_projection',
#            BooleanTrait(False, label='Z-slice projection',
#                         widget_info=BooleanTrait.RADIOBUTTON)),
#

#        ('namingScheme',
#            SelectionTrait(NAMING_SCHEMAS.sections()[0],
#                           NAMING_SCHEMAS.sections(),
#                           label='Naming scheme')),
        ('constrain_positions',
            BooleanTrait(False, label='Constrain positions')),
        ('positions',
            StringTrait('', 1000, label='Positions',
                                   mask='(\w+,)*\w+')),
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
        ('createimagecontainer', BooleanTrait(True)),
        ('preferimagecontainer', BooleanTrait(False)),
        ('binningfactor', IntTrait(1,1,10)),
        ('timelapsedata', BooleanTrait(True)),
        ('qualitycontrol', BooleanTrait(False)),
        ('debugmode', BooleanTrait(False)),
        ('createimages', BooleanTrait(True)),
        ('imageoutcompression',
            StringTrait('98', 5,
                        label='Image output compresion')),
        ('rendering', DictTrait({}, label='Rendering')),
        ('rendering_class', DictTrait({}, label='Rendering class')),
        ('primary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Primary channel')),
        ('secondary_featureextraction_exportfeaturenames',
            ListTrait(['n2_avg', 'n2_stddev', 'roisize'], label='Secondary channel')),

      ])
    ]


