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
REGION_NAMES_SECONDARY = ['expanded', 'inside', 'outside', 'rim', 'propagate', 'constrained_watershed']

REGION_NAMES = {'primary'   : REGION_NAMES_PRIMARY,
                'secondary' : REGION_NAMES_SECONDARY,
                'tertiary'  : REGION_NAMES_SECONDARY,
                }

SECONDARY_COLORS = {'inside' : '#FFFF00',
                    'outside' : '#00FF00',
                    'expanded': '#00FFFF',
                    'rim' : '#FF00FF',
                    'propagate': '#FFFF99',
                    'constrained_watershed': '#FF99FF',
                    }

SECONDARY_REGIONS = {'secondary_regions_expanded' : 'expanded',
                     'secondary_regions_inside' : 'inside',
                     'secondary_regions_outside' : 'outside',
                     'secondary_regions_rim' : 'rim',
                     'secondary_regions_propagate' : 'propagate',
                     'secondary_regions_constrained_watershed' : 'constrained_watershed',
                     }
TERTIARY_REGIONS  = {'tertiary_regions_expanded' : 'expanded',
                     'tertiary_regions_inside' : 'inside',
                     'tertiary_regions_outside' : 'outside',
                     'tertiary_regions_rim' : 'rim',
                     'tertiary_regions_propagate' : 'propagate',
                     'tertiary_regions_constrained_watershed' : 'constrained_watershed',
                     }

ZSLICE_PROJECTION_METHODS = ['maximum', 'average']

COMPRESSION_FORMATS = ['raw', 'bz2', 'gz']
TRACKING_METHODS = ['ClassificationCellTracker',]

TRACKING_DURATION_UNIT_FRAMES = 'frames'
TRACKING_DURATION_UNIT_MINUTES = 'minutes'
TRACKING_DURATION_UNIT_SECONDS = 'seconds'
TRACKING_DURATION_UNITS_DEFAULT = [TRACKING_DURATION_UNIT_FRAMES,
                                   ]
TRACKING_DURATION_UNITS_TIMELAPSE = [TRACKING_DURATION_UNIT_FRAMES,
                                     TRACKING_DURATION_UNIT_MINUTES,
                                     TRACKING_DURATION_UNIT_SECONDS,
                                     ]

R_LIBRARIES = ['hwriter', 'RColorBrewer', 'igraph']

TC3_ALGORITHMS = ['TC3', 'TC3+GMM', 'TC3+GMM+DHMM', 'TC3+GMM+CHMM']