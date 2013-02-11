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

from cecog.traits.settings import _Section
from cecog.gui.guitraits import StringTrait, BooleanTrait

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

class SectionFeatureExtraction(_Section):

    SECTION_NAME = SECTION_NAME_FEATURE_EXTRACTION

    OPTIONS = [

    ('primary_features',
     [('primary_featurecategory_%s' % name,
       BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)
      ]),

    ('secondary_features',
     [('secondary_featurecategory_%s' % name,
       BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)
      ]),

    ('tertiary_features',
     [('tertiary_featurecategory_%s' % name,
       BooleanTrait(True, label=desc))
       for name, desc in zip(FEATURE_CATEGORIES, FEATURE_CATEGORY_DESC)
      ]),

    ]
