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

__all__ = ['OutputFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.analyzer import (_BaseFrame,
                                )
from cecog.traits.guitraits import (BooleanTrait,
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

class OutputFrame(_BaseFrame):

    SECTION = 'Output'

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)

        self.add_group('Export result images', None,
                       [
                        ('rendering_labels_discwrite',
                         BooleanTrait(False, label='Label images'),
                         (0,0,1,1)),
                        ('rendering_contours_discwrite',
                         BooleanTrait(False, label='Contour images'),
                         (1,0,1,1)),
                        ('rendering_contours_showids',
                         BooleanTrait(False, label='Show object IDs'),
                         (1,1,1,1)),
                        ('rendering_class_discwrite',
                         BooleanTrait(False, label='Classification images'),
                         (2,0,1,1)),
                        ('rendering_class_showids',
                         BooleanTrait(False, label='Show object IDs'),
                         (2,1,1,1)),
                        ], link='export_result_images')

        self.add_group('Statistics', None,
                       [
                        ('export_object_counts',
                         BooleanTrait(False, label='Export object counts'),
                         (0,0,1,1)),
                        ('export_object_details',
                         BooleanTrait(False, label='Export detailed object data'),
                         (1,0,1,1)),
                        ('export_track_data',
                         BooleanTrait(False, label='Export track data'),
                         (2,0,1,1)),
                        ], link='statistics')

#        self.add_input('rendering',
#                       DictTrait({}, label='Rendering',
#                                 tooltip='abc...'))
#        self.add_input('rendering_discwrite',
#                       BooleanTrait(True, label='Write images to disc',
#                                    tooltip='abc...'))
#        self.add_input('rendering_class',
#                       DictTrait({}, label='Rendering class',
#                                 tooltip='abc...'))
#        self.add_input('rendering_class_discwrite',
#                       BooleanTrait(True, label='Write images to disc',
#                                    tooltip='abc...'))
#
#
#        self.add_group('Filter feature values', None,
#                       [
#                        ('primary_featureExtraction_exportFeatureNames',
#                         ListTrait([], label='Primary channel',
#                                   tooltip='abc...')),
#                        ('secondary_featureExtraction_exportFeatureNames',
#                         ListTrait([], label='Secondary channel',
#                                   tooltip='abc...')),
#                        ], layout='flow')

        self.add_expanding_spacer()
