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

__all__ = ['SectionFeatureExtraction']

from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import BooleanTrait, StringTrait

SECTION_NAME_FEATURE_EXTRACTION = 'FeatureExtraction'

FEATURE_CATEGORIES = ['basicshape', 'intensity', 'haralick', 'stat_geom',
                      'convhull', 'distance', 'granugrey', 'moments']

FEATURE_CATEGORY_DESC = ['Basic shape features',
                         'Basic intensity features',
                         'Haralick features',
                         'Statistical geometric features',
                         'Convex hull features',
                         'Distance map features',
                         'Granulometry features',
                         'Moments']

class SectionFeatureExtraction(SectionCore):

    SECTION_NAME = SECTION_NAME_FEATURE_EXTRACTION

    OPTIONS = [

    ('primary_features',
     [('primary_featurecategory_%s' % name, BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)]
   + [('primary_dist_haralick', 
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
      ('primary_se_granugrey', 
       StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)'))
      ]
     ),
     
    ('secondary_features',
     [('secondary_featurecategory_%s' % name, BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)] +
     [('secondary_dist_haralick', 
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
       ('secondary_se_granugrey', 
        StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)'))
      ]
     ),

    ('tertiary_features',
     [('tertiary_featurecategory_%s' % name, BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)] + 
     [('tertiary_dist_haralick', 
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
      ('tertiary_se_granugrey', 
       StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)'))
      ]
     ),

    ]
