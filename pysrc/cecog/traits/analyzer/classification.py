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

__all__ = ['SectionClassification']

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
                                 SelectionTrait,
                                 )
from cecog.analyzer import (REGION_NAMES_PRIMARY,
                            REGION_NAMES_SECONDARY,
                            )
from cecog.util.util import unlist

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_CLASSIFICATION = 'Classification'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionClassification(_Section):

    SECTION_NAME = SECTION_NAME_CLASSIFICATION

    OPTIONS = [

    ('primary_classification',
     [('primary_classification_envpath',
        StringTrait('', 1000, label='Classifier folder',
                    widget_info=StringTrait.STRING_PATH)),
      ('primary_classification_regionname',
        SelectionTrait(REGION_NAMES_PRIMARY[0], REGION_NAMES_PRIMARY,
                       label='Region name')),
      ('primary_classification_annotationfileext',
        StringTrait('.xml', 50, label='Annotation ext.')),
      ]),

    ] + \
    unlist(
    [[('%s_classification' % x,
     [('%s_classification_envpath' % x,
       StringTrait('', 1000, label='Classifier folder',
                   widget_info=StringTrait.STRING_PATH)),
      ('%s_classification_regionname' % x,
       SelectionTrait(REGION_NAMES_SECONDARY[0], REGION_NAMES_SECONDARY,
                      label='Region name')),
      ('%s_classification_annotationfileext' % x,
       StringTrait('.xml', 50, label='Annotation ext.')),
      ])]
      for x in ['secondary', 'tertiary']]

      ) + \
      [
      ('collectsamples',
       [('collectsamples',
            BooleanTrait(False)),
        ('collectsamples_prefix',
            StringTrait('',100)),
        ])
      ]
