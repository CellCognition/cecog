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

__all__ = ['EventSelectionFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.eventselection import SECTION_NAME_EVENT_SELECTION
from cecog.gui.analyzer import (BaseProcessorFrame,
                                AnalzyerThread,
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

class EventSelectionFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_EVENT_SELECTION
    DISPLAY_NAME = 'Event Selection'
    PROCESS_SYNCING = 'PROCESS_SYNCING'

    def __init__(self, settings, parent):
        super(EventSelectionFrame, self).__init__(settings, parent)

        # IMPORTANT LINE HERE: DESIGN NEW EVENT SELECTION PROCESSING
        # THREAD BY TEARING APPART THE OLD TRACKING
        self.register_control_button(self.PROCESS_SYNCING,
                                     AnalzyerThread,
                                     ('Start', 'Stop'))

        self.add_line()
        self.add_group(None,
                       [('tracking_backwardrange', (0,0,1,1)),
                        ('tracking_forwardrange', (0,1,1,1)),
                        ('tracking_duration_unit', (0,2,1,1)),
                        ], link='tracking_eventselection', label='Event selection')
        self.add_group('supervised_event_selection',
                       [('tracking_labeltransitions', (0,0,1,1)),
                         ('tracking_backwardlabels', (1,0,1,1)),
                        ('tracking_forwardlabels', (1,1,1,1)),
                        ('tracking_backwardcheck', (3,0,1,1)),
                        ('tracking_forwardcheck', (3,1,1,1)),
                       ], layout='grid')
        self.add_group('unsupervised_event_selection',
                       [('min_event_duration',),
                       ], layout='flow')
        self.add_line()
        self.add_group('tc3_analysis', [
                ('num_clusters', (0,0,1,1)),
                ('min_cluster_size', (0,1,1,1)),
                ('tc3_algorithms', (0,2,1,1)),
                ],
                layout='grid', link='tc3_analysis')
        self.add_expanding_spacer()

        self._init_control(has_images=False)
