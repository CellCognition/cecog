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

#-------------------------------------------------------------------------------
# constants:
#
CONTROL_1 = 'CONTROL_1'
CONTROL_2 = 'CONTROL_2'

FEATURE_CATEGORIES = ['roisize',
                      'circularity',
                      'irregularity',
                      'irregularity2',
                      'axes',
                      'normbase',
                      'normbase2',
                      'levelset',
                      'convexhull',
                      'dynamics',
                      'granulometry',
                      'distance',
                      'moments',
                      ]
REGION_NAMES_PRIMARY = ['primary']
REGION_NAMES_SECONDARY = ['expanded', 'inside', 'outside', 'rim', 'propagate']

REGION_NAMES = {'primary'   : REGION_NAMES_PRIMARY,
                'secondary' : REGION_NAMES_SECONDARY,
                'tertiary'  : REGION_NAMES_SECONDARY,
                }

SECONDARY_COLORS = {'inside' : '#FFFF00',
                    'outside' : '#00FF00',
                    'expanded': '#00FFFF',
                    'rim' : '#FF00FF',
                    'propagate': '#FFFF99',
                    }

SECONDARY_REGIONS = {'secondary_regions_expanded' : 'expanded',
                     'secondary_regions_inside' : 'inside',
                     'secondary_regions_outside' : 'outside',
                     'secondary_regions_rim' : 'rim',
                     'secondary_regions_propagate' : 'propagate',
                     }

ZSLICE_PROJECTION_METHODS = ['maximum', 'average']

COMPRESSION_FORMATS = ['raw', 'bz2', 'gz']
TRACKING_METHODS = ['ClassificationCellTracker',]

R_LIBRARIES = ['hwriter', 'RColorBrewer', 'igraph']
