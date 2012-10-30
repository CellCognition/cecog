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

__all__ = ['SectionTracking']

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
                                 IntTrait,
                                 FloatTrait,
                                 BooleanTrait,
                                 SelectionTrait,
                                 SelectionTrait2,
                                 )
from cecog.analyzer import (COMPRESSION_FORMATS,
                            TRACKING_DURATION_UNITS_DEFAULT,
                            )

from cecog.analyzer import TC3_ALGORITHMS

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_TRACKING = 'Tracking'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionTracking(_Section):

    SECTION_NAME = SECTION_NAME_TRACKING

    OPTIONS = [
      ('tracking',
       [('tracking_maxobjectdistance',
            IntTrait(0, 0, 4000, label='Max object x-y distance')),
        ('tracking_maxtrackinggap',
            IntTrait(0, 0, 4000, label='Max time-point gap')),
        ('tracking_maxsplitobjects',
            IntTrait(0, 0, 4000, label='Max split events')),
        ('tracking_maxindegree',
            IntTrait(1, 0, 4000, label='Max in-degree')),
        ('tracking_maxoutdegree',
            IntTrait(2, 0, 4000, label='Max out-degree')),
        ('tracking_exporttrackfeatures',
            BooleanTrait(True, label='Export tracks')),
        ('tracking_compressiontrackfeatures',
            SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
                           label='Compression')),
        ]),

      ('event_selection',
       [('event_selection',
            BooleanTrait(False,label='Event selection')),
        ('tracking_labeltransitions',
            StringTrait('', 200, label='Class transition motif(s)',
                        mask='(\(\d+,\d+\),)*\(\d+,\d+\)')),
        ('tracking_backwardrange',
            FloatTrait(0, -1, 4000, label='Duration [pre]')),
        ('tracking_forwardrange',
            FloatTrait(0, -1, 4000, label='Duration [post]')),
        ('tracking_backwardlabels',
            StringTrait('', 200, label='Class filter [pre]',
                        mask='(\d+,)*\d+')),
        ('tracking_forwardlabels',
            StringTrait('', 200, label='Class filter [post]',
                        mask='(\d+,)*\d+')),
        ('tracking_backwardcheck',
            FloatTrait(2, 0, 4000, label='Filter duration [pre]')),
        ('tracking_forwardcheck',
            FloatTrait(2, 0, 4000, label='Filter duration [post]')),

        ('tracking_duration_unit',
            SelectionTrait2(TRACKING_DURATION_UNITS_DEFAULT[0],
                            TRACKING_DURATION_UNITS_DEFAULT,
                            label='Duration unit')),

        ('tracking_backwardrange_min',
            BooleanTrait(False, label='Min.')),
        ('tracking_forwardrange_min',
            BooleanTrait(False, label='Min.')),
        ]),

      ('visualization',
       [('tracking_visualization',
            BooleanTrait(False, label='Visualization')),
        ('tracking_visualize_track_length',
            IntTrait(5, -1, 10000, label='Max. time-points')),
        ('tracking_centroid_radius',
            IntTrait(3, -1, 50, label='Centroid radius')),
        ]),
               
      ('unsupervised_event_detection',
       [('unsupervised_event_detection',
            BooleanTrait(False, label='UES')),
        ('duration_pre',
            IntTrait(0, -1, 4000, label='Duration [pre]')),
        ('duration_post',
            IntTrait(0, -1, 4000, label='Duration [post]')),
        ('max_event_duration',
            IntTrait(3, 3, 30, label='Max event duration')),
        ('tracking_duration_unit2',
            SelectionTrait2(TRACKING_DURATION_UNITS_DEFAULT[0],
                            TRACKING_DURATION_UNITS_DEFAULT,
                            label='Duration unit')),
        ]),
      ('tc3_analysis',
        [('tc3_analysis',
            BooleanTrait(False, label='TC3 analysis')),
        ('num_clusters',
            IntTrait(6, 2, 10, label='Number of clusters',)), 
        ('min_cluster_size',
            IntTrait(2, 1, 10, label='Min Cluster Size',)),
        ('tc3_algorithms',
            SelectionTrait(TC3_ALGORITHMS[0],
                           TC3_ALGORITHMS,
                           label='TC3 algorithms')),
         ]),
      ]
