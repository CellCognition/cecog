"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Qing Zhong'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['SectionPostProcessing']

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
                                 BooleanTrait,
                                 FloatTrait,
                                 IntTrait,
                                 SelectionTrait,
                                 SelectionTrait2,
                                 )
from cecog.analyzer import TRACKING_DURATION_UNITS_DEFAULT
from cecog.analyzer import TC3_ALGORITHMS
#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_EVENT_SELECTION = 'EventSelection'



#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionEventSelection(_Section):

    SECTION_NAME = SECTION_NAME_EVENT_SELECTION

    OPTIONS = [
      ('event_selection',
       [('event_selection',
            BooleanTrait(True, label='Event Selection')),
        ('tracking_backwardrange',
            FloatTrait(0, -1, 4000, label='Duration [pre]')),
        ('tracking_forwardrange',
            FloatTrait(0, -1, 4000, label='Duration [post]')),

        ('tracking_duration_unit',
            SelectionTrait2(TRACKING_DURATION_UNITS_DEFAULT[0],
                            TRACKING_DURATION_UNITS_DEFAULT,
                            label='Duration unit')),
        ('tracking_backwardrange_min',
            BooleanTrait(False, label='Min.')),
        ('tracking_forwardrange_min',
            BooleanTrait(False, label='Min.')),
        ]),
     
     ('supervised_event_selection',
       [('supervised_event_selection',
            BooleanTrait(True, label='Supervised', 
                                 widget_info=BooleanTrait.RADIOBUTTON)),
        ('tracking_labeltransitions',
            StringTrait('', 200, label='Class transition motif(s)',
                    mask='(\(\d+,\d+\),)*\(\d+,\d+\)')),
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
        ]),
      ('unsupervised_event_selection',
       [('unsupervised_event_selection',
            BooleanTrait(False, label='Unsupervised',
                                 widget_info=BooleanTrait.RADIOBUTTON)),
        ('min_event_duration',
            IntTrait(3, 3, 30, label='Min event duration')),
        ]),
      ('tc3_analysis',
        [('tc3_analysis',
            BooleanTrait(False, label='Temporal Clustering')),
         ('invert',
            BooleanTrait(False, label='Invert event/background')),
         ('num_clusters',
            IntTrait(6, 2, 10, label='Number of clusters',)), 
         ('min_cluster_size',
            IntTrait(2, 1, 10, label='Min cluster size',)),
         ('tc3_algorithms',
            SelectionTrait(TC3_ALGORITHMS[0],
                           TC3_ALGORITHMS,
                           label='Algorithms')),
         ]),
    ]
