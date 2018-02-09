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

from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import IntTrait, BooleanTrait, SelectionTrait2


SECTION_NAME_TRACKING = 'Tracking'


class SectionTracking(SectionCore):

    SECTION_NAME = SECTION_NAME_TRACKING

    OPTIONS = [
        ('tracking',
         [('region',
           SelectionTrait2(None, [], label='Region name')),
          ('tracking_maxobjectdistance',
           IntTrait(0, 0, 4000, label='Max object x-y distance')),
          ('tracking_maxtrackinggap',
           IntTrait(0, 0, 4000, label='Max time-point gap')),
          ('tracking_maxsplitobjects',
           IntTrait(0, 0, 4000, label='Max split events')),
          ]),
        ]
