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

__all__ = ['FeatureExtractionFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
from cecog.gui.analyzer import (BaseFrame,
                                )

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class FeatureExtractionFrame(BaseFrame):

    SECTION_NAME = SECTION_NAME_FEATURE_EXTRACTION
    DISPLAY_NAME = 'Feature Extraction'
    TABS = ['Primary Channel', 'Secondary Channel', 'Tertiary Channel']

    def __init__(self, settings, parent):
        super(FeatureExtractionFrame, self).__init__(settings, parent)
        self._result_frames = {}

        for tab_name, prefix in [('Primary Channel', 'primary'),
                                 ('Secondary Channel', 'secondary'),
                                 ('Tertiary Channel',  'tertiary')
                                 ]:

            self.set_tab_name(tab_name)
            self.add_group(None,
                           [('%s_featurecategory_intensity' % prefix,
                             (0, 0, 1, 1) ),
                            ('%s_featurecategory_haralick' % prefix,
                             (1, 0, 1, 1) ),
                            ('%s_featurecategory_stat_geom' % prefix,
                             (2, 0, 1, 1) ),
                            ('%s_featurecategory_granugrey' % prefix,
                             (3, 0, 1, 1)),
                            ('%s_featurecategory_basicshape' % prefix,
                             (0, 1, 1, 1) ),
                            ('%s_featurecategory_convhull' % prefix,
                             (1, 1, 1, 1)),
                            ('%s_featurecategory_distance' % prefix,
                             (2, 1, 1, 1)),
                            ('%s_featurecategory_moments' % prefix,
                             (3, 1, 1, 1) ),
                            ],
                           layout='grid',
                           link='%s_featureextraction' % prefix,
                           label='Feature extraction')
            self.add_expanding_spacer()

        #self._init_control()

