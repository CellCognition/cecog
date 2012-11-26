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

__all__ = ['SECTION_REGISTRY']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.settings import SectionRegistry
from cecog.traits.analyzer.general import SectionGeneral
from cecog.traits.analyzer.objectdetection import SectionObjectdetection
from cecog.traits.analyzer.featureextraction import SectionFeatureExtraction
from cecog.traits.analyzer.classification import SectionClassification
from cecog.traits.analyzer.tracking import SectionTracking
from cecog.traits.analyzer.errorcorrection import SectionErrorcorrection
from cecog.traits.analyzer.output import SectionOutput
from cecog.traits.analyzer.processing import SectionProcessing
from cecog.traits.analyzer.cluster import SectionCluster
from cecog.traits.analyzer.postprocessing import SectionPostProcessing

from cecog.extensions.graphLib import Graph

#-------------------------------------------------------------------------------
# constants:
#
SECTION_REGISTRY = SectionRegistry()
SECTION_REGISTRY.register_section(SectionGeneral())
SECTION_REGISTRY.register_section(SectionObjectdetection())
SECTION_REGISTRY.register_section(SectionFeatureExtraction())
SECTION_REGISTRY.register_section(SectionClassification())
SECTION_REGISTRY.register_section(SectionTracking())
SECTION_REGISTRY.register_section(SectionErrorcorrection())
SECTION_REGISTRY.register_section(SectionPostProcessing())
SECTION_REGISTRY.register_section(SectionOutput())
SECTION_REGISTRY.register_section(SectionProcessing())
SECTION_REGISTRY.register_section(SectionCluster())

class UpdateDependency(object):

    def __init__(self):
        graph = Graph()
        name = SectionObjectdetection.SECTION_NAME
        graph.add_node(1, (name, 'primary_image',
                           ('raw_images_finished', [1])))
        graph.add_node(2, (name, 'primary_segmentation',
                           ('raw_images_finished', 1)))
        graph.add_node(3, (name, 'secondary_image',
                           ('raw_images_finished', [2])))
        graph.add_node(4, (name, 'secondary_segmentation'))
        graph.add_node(5, (name, 'secondary_registration'))

        name = SectionClassification.SECTION_NAME
        graph.add_node(6, (name, 'primary_features'))
        graph.add_node(7, (name, 'primary_classification'))

        graph.add_node(11, (name, 'secondary_features'))
        graph.add_node(12, (name, 'secondary_classification'))

        graph.add_edge(1, 2)
        graph.add_edge(3, 4)
        graph.add_edge(2, 4)
        graph.add_edge(5, 1)
        graph.add_edge(5, 3)

        graph.add_edge(2, 6)
        graph.add_edge(6, 7)
        graph.add_edge(4, 11)
        graph.add_edge(11, 12)

        self._graph = graph
        self._start = 5

    def check(self, settings, settings_new, node_id=None):

        if node_id is None:
            node_id = self._start
        section_name, grp_name = self._graph.node_data(node_id)

        # compare current section/group settings in graph
        if not settings.compare(settings_new, section_name, grp_name):
            # perform invalidation down the graph
            pass
        else:
            # recursively traverse the graph and compare further
            for edge_id in self._graph.out_arcs(self._start):
                tail_id = self._graph.tail(edge_id)
                self.check(settings, settings_new, tail_id)
