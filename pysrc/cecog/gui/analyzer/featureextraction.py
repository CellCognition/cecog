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
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
from cecog.gui.util import (information,
                            exception,
                            )
from cecog.gui.analyzer import (_BaseFrame,
                                _ProcessorMixin,
                                AnalzyerThread,
                                TrainingThread,
                                )
from cecog.analyzer import SECONDARY_REGIONS
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.learning.learning import (CommonClassPredictor,
                                     )
from cecog.util.util import (hexToRgb,
                             convert_package_path,
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

class FeatureExtractionFrame(_BaseFrame, _ProcessorMixin):

    SECTION_NAME = SECTION_NAME_FEATURE_EXTRACTION
    DISPLAY_NAME = 'Feature Extraction'
    TABS = ['PrimaryChannel', 'SecondaryChannel']

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)
        self._result_frames = {}

        self.set_tab_name('PrimaryChannel')

        self.add_group(None,
                       [('primary_featurecategory_intensity', (0, 0, 1, 1) ),
                        ('primary_featurecategory_haralick', (1, 0, 1, 1) ),
                        ('primary_featurecategory_stat_geom', (2, 0, 1, 1) ),
                        ('primary_featurecategory_granugrey', (3, 0, 1, 1)),
                        ('primary_featurecategory_basicshape', (0, 1, 1, 1) ),
                        ('primary_featurecategory_convhull', (1, 1, 1, 1)),
                        ('primary_featurecategory_distance', (2, 1, 1, 1)),
                        ('primary_featurecategory_moments', (3, 1, 1, 1) ),
                        ],
                       layout='grid',
                       link='primary_featureextraction',
                       label='Feature extraction')
        self.add_expanding_spacer()

        self.set_tab_name('SecondaryChannel')

        self.add_group(None,
                       [('secondary_featurecategory_intensity', (0, 0, 1, 1) ),
                        ('secondary_featurecategory_haralick', (1, 0, 1, 1) ),
                        ('secondary_featurecategory_stat_geom', (2, 0, 1, 1) ),
                        ('secondary_featurecategory_granugrey', (3, 0, 1, 1)),
                        ('secondary_featurecategory_basicshape', (0, 1, 1, 1) ),
                        ('secondary_featurecategory_convhull', (1, 1, 1, 1)),
                        ('secondary_featurecategory_distance', (2, 1, 1, 1)),
                        ('secondary_featurecategory_moments', (3, 1, 1, 1) ),
                        ],
                       layout='grid',
                       link='secondary_featureextraction',
                       label='Feature extraction')
        self.add_expanding_spacer()
        #self._init_control()

