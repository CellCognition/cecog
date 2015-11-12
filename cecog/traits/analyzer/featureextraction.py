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
from cecog.gui.guitraits import BooleanTrait, StringTrait, IntTrait

SECTION_NAME_FEATURE_EXTRACTION = 'FeatureExtraction'

FEATURE_CATEGORIES = ['basicshape', 'intensity', 'haralick', 'stat_geom',
                      'convhull', 'distance', 'granugrey', 'moments', 'spotfeatures', 'lbp']

FEATURE_CATEGORY_DESC = ['Basic shape features',
                         'Basic intensity features',
                         'Haralick features',
                         'Statistical geometric features',
                         'Convex hull features',
                         'Distance map features',
                         'Granulometry features',
                         'Moments', 
                         'Spot Features',
                         'LBP features']

class SectionFeatureExtraction(SectionCore):

    SECTION_NAME = SECTION_NAME_FEATURE_EXTRACTION

    OPTIONS = [

    ('primary_features',
     [('primary_featurecategory_%s' % name, BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)]
   + [('primary_dist_haralick', 
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
      ('primary_se_granugrey', 
       StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)')),
      ('primary_diameter_spotfeatures', 
       IntTrait(5, 1, 30, label="Diameter")),
      ('primary_thresh_spotfeatures', 
       IntTrait(8, 1, 255, label="Threshold")),
      ('primary_r_lbp', 
       StringTrait('1,2,4,8', 200, label='LBP: Circle range')),
      ]
     ),
     
    ('secondary_features',
     [('secondary_featurecategory_%s' % name, BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)] +
     [('secondary_dist_haralick', 
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
       ('secondary_se_granugrey', 
        StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)')),
      ('secondary_diameter_spotfeatures', 
       IntTrait(5, 1, 30, label="Diameter")),
      ('secondary_thresh_spotfeatures', 
       IntTrait(8, 1, 255, label="Threshold")),
      ('secondary_r_lbp', 
       StringTrait('1,2,4,8', 200, label='LBP: Circle range')),
      ]
     ),

    ('tertiary_features',
     [('tertiary_featurecategory_%s' % name, BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)] + 
     [('tertiary_dist_haralick', 
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
      ('tertiary_se_granugrey', 
       StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)')),
      ('tertiary_diameter_spotfeatures', 
       IntTrait(5, 1, 30, label="Diameter")),
      ('tertiary_thresh_spotfeatures', 
       IntTrait(8, 1, 255, label="Threshold")),
      ('tertiary_r_lbp', 
       StringTrait('1,2,4,8', 200, label='LBP: Circle range')),
      ]
     ),

    ]