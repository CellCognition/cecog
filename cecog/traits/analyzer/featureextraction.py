"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import
import six

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['SectionFeatureExtraction']

from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import BooleanTrait, StringTrait, IntTrait

SECTION_NAME_FEATURE_EXTRACTION = 'FeatureExtraction'


GUI_LABELS = {
    'featurecategory_intensity': 'Basic intensity features',
    'featurecategory_haralick': 'Haralick features',
    'featurecategory_stat_geom': 'Statistical geometric features',
    'featurecategory_granugrey': 'Granulometry features',
    'featurecategory_basicshape': 'Basic shape features',
    'featurecategory_convhull': 'Convex Hull features',
    'featurecategory_distance': 'Distance Map features',
    'featurecategory_moments': 'Moments',
    'featurecategory_spotfeatures': 'Spot Features'
}


class SectionFeatureExtraction(SectionCore):

    SECTION_NAME = SECTION_NAME_FEATURE_EXTRACTION

    OPTIONS = [

    ('primary_features',
     [('primary_%s' %name, BooleanTrait(True, label=desc))
       for name, desc in six.iteritems(GUI_LABELS)]
   + [('primary_dist_haralick',
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
      ('primary_se_granulometry',
       StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)')),
      ('primary_diameter_spotfeatures',
       IntTrait(5, 1, 30, label="Diameter")),
      ('primary_thresh_spotfeatures',
       IntTrait(8, 1, 255, label="Threshold")),
      ]
     ),

    ('secondary_features',
     [('secondary_%s' %name, BooleanTrait(True, label=desc))
       for name, desc in six.iteritems(GUI_LABELS)] +
     [('secondary_dist_haralick',
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
       ('secondary_se_granulometry',
        StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)')),
      ('secondary_diameter_spotfeatures',
       IntTrait(5, 1, 30, label="Diameter")),
      ('secondary_thresh_spotfeatures',
       IntTrait(8, 1, 255, label="Threshold")),
      ]
     ),

    ('tertiary_features',
     [('tertiary_%s' % name, BooleanTrait(True, label=desc))
       for name, desc in six.iteritems(GUI_LABELS)] +
     [('tertiary_dist_haralick',
       StringTrait('1,2,4,8', 200, label='Haralick: Distances for cooccurence')),
      ('tertiary_se_granulometry',
       StringTrait('1,2,3,5,7', 200, label='Granulometry Sizes (Structuring Element)')),
      ('tertiary_diameter_spotfeatures',
       IntTrait(5, 1, 30, label="Diameter")),
      ('tertiary_thresh_spotfeatures',
       IntTrait(8, 1, 255, label="Threshold")),
      ]
     ),

    ]
