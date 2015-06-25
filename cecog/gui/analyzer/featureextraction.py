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

__all__ = ['FeatureExtractionFrame']

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from cecog.gui.analyzer import BaseFrame

class FeatureExtractionFrame(BaseFrame):

    DISPLAY_NAME = 'Feature Extraction'
    TABS = ['Primary Channel', 'Secondary Channel', 'Tertiary Channel']

    def __init__(self, settings, parent, name):
        super(FeatureExtractionFrame, self).__init__(settings, parent, name)
        self._result_frames = {}

        feature_families = ['intensity', 'haralick', 'stat_geom', 'granugrey',
                            'basicshape', 'convhull', 'distance', 'moments',
                            'spotfeatures']

        for tab_name, prefix in [('Primary Channel', 'primary'),
                                 ('Secondary Channel', 'secondary'),
                                 ('Tertiary Channel',  'tertiary')
                                 ]:

            self.set_tab_name(tab_name)            
            #feature_list = [('%s_featurecategory_%s' % (prefix, f), (i, 0, 1, 1)) for i,f in enumerate(feature_families)]
#            self.add_group(None,
#                           feature_list,
#                           layout='grid',
#                           link='%s_featureextraction' % prefix,
#                           label='Feature extraction')
            
            self.add_group(None,
                           [('%s_featurecategory_intensity' % prefix,
                             (0, 0, 1, 1) ),
                            ('%s_featurecategory_haralick' % prefix,
                             (1, 0, 1, 1) ),
                            ('%s_dist_haralick' % prefix,
                             (1, 1, 1, 1) ),                            
                            ('%s_featurecategory_stat_geom' % prefix,
                             (2, 0, 1, 1) ),
                            ('%s_featurecategory_granugrey' % prefix,
                             (3, 0, 1, 1)),
                            ('%s_se_granugrey' % prefix,
                             (3, 1, 1, 1) ),                            
                            ('%s_featurecategory_basicshape' % prefix,
                             (4, 0, 1, 1) ),
                            ('%s_featurecategory_convhull' % prefix,
                             (5, 0, 1, 1)),
                            ('%s_featurecategory_distance' % prefix,
                             (6, 0, 1, 1)),
                            ('%s_featurecategory_moments' % prefix,
                             (7, 0, 1, 1) ),
                            ('%s_featurecategory_spotfeatures' % prefix,
                             (8, 0, 1, 1) ),
                            ('%s_spotfeature_diameter' % prefix,
                             (8, 1, 1, 1) ),
                            ('%s_spotfeature_thresh' % prefix,
                             (8, 2, 1, 1) ),
                            ],
                           layout='grid',
                           link='%s_featureextraction' % prefix,
                           label='Feature extraction')
            self.add_expanding_spacer()
