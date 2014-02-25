"""
eventselection.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ['SectionEventSelection']

from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import BooleanTrait, StringTrait, FloatTrait, \
    IntTrait, SelectionTrait2

from cecog.units.time import TimeConverter


SECTION_NAME_EVENT_SELECTION = 'EventSelection'

class SectionEventSelection(SectionCore):

    SECTION_NAME = SECTION_NAME_EVENT_SELECTION

    OPTIONS = [
        ('event_selection',
         [('event_selection',
           BooleanTrait(True, label='Event Selection')),
          ('backwardrange',
           FloatTrait(0, -1, 4000, label='Duration [pre]')),
          ('forwardrange',
           FloatTrait(0, -1, 4000, label='Duration [post]')),

          ('duration_unit',
           SelectionTrait2(TimeConverter.FRAMES,
                           TimeConverter.units,
                           label='Duration unit')),
          ('backwardrange_min', BooleanTrait(False, label='Min.')),
          ('forwardrange_min', BooleanTrait(False, label='Min.')),
          ('maxindegree', IntTrait(1, 0, 4000, label='Max in-degree')),
          ('maxoutdegree', IntTrait(2, 0, 4000, label='Max out-degree')),
          ]),

        ('supervised_event_selection',
         [('supervised_event_selection',
           BooleanTrait(True, label='Supervised',
                        widget_info=BooleanTrait.RADIOBUTTON)),
          ('labeltransitions',
           StringTrait('', 200, label='Class transition motif(s)',
                       mask='(\(\d+,\d+\),)*\(\d+,\d+\)')),
          ('backwardlabels',
           StringTrait('', 200, label='Class filter [pre]',
                       mask='(\d+,)*\d+')),
          ('forwardlabels',
           StringTrait('', 200, label='Class filter [post]',
                       mask='(\d+,)*\d+')),
          ('backwardcheck',
           FloatTrait(2, 0, 4000, label='Filter duration [pre]')),
          ('forwardcheck',
           FloatTrait(2, 0, 4000, label='Filter duration [post]')),
          ]),

        ('unsupervised_event_selection',
         [('unsupervised_event_selection',
           BooleanTrait(False, label='Unsupervised',
                        widget_info=BooleanTrait.RADIOBUTTON)),
          ('min_event_duration',
           IntTrait(3, 1, 100, label='Min. event duration')),
          ('num_clusters',
           IntTrait(6, 2, 15, label='Number of clusters',)),
          ('min_cluster_size',
           IntTrait(2, 1, 10, label='Min. cluster size',)),
          ])
        ]
