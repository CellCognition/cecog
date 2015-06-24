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
from cecog.gui.guitraits import IntTrait, BooleanTrait, SelectionTrait, \
    SelectionTrait2

from cecog.analyzer import COMPRESSION_FORMATS

SECTION_NAME_TRACKING = 'Tracking'

class SectionTracking(SectionCore):

    SECTION_NAME = SECTION_NAME_TRACKING

    OPTIONS = [
        ('tracking',
         [('region',
           SelectionTrait2(None, [], label='Region name')),
          ]),

        ('visualization',
         [('tracking_visualization',
           BooleanTrait(False, label='Visualization')),
          ('tracking_visualize_track_length',
           IntTrait(5, -1, 10000, label='Max. time-points')),
          ('tracking_centroid_radius',
           IntTrait(3, -1, 50, label='Centroid radius')),
          ]),
        ]
