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

__all__ = ['SECTION_REGISTRY',
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.config import SectionRegistry
from cecog.traits.analyzer.general import SectionGeneral
from cecog.traits.analyzer.objectdetection import SectionObjectdetection
from cecog.traits.analyzer.classification import SectionClassification
from cecog.traits.analyzer.tracking import SectionTracking
from cecog.traits.analyzer.errorcorrection import SectionErrorcorrection
from cecog.traits.analyzer.output import SectionOutput
from cecog.traits.analyzer.processing import SectionProcessing
from cecog.traits.analyzer.cluster import SectionCluster

#-------------------------------------------------------------------------------
# constants:
#
SECTION_REGISTRY = SectionRegistry()
SECTION_REGISTRY.register_section(SectionGeneral())
SECTION_REGISTRY.register_section(SectionObjectdetection())
SECTION_REGISTRY.register_section(SectionClassification())
SECTION_REGISTRY.register_section(SectionTracking())
SECTION_REGISTRY.register_section(SectionErrorcorrection())
SECTION_REGISTRY.register_section(SectionOutput())
SECTION_REGISTRY.register_section(SectionProcessing())
SECTION_REGISTRY.register_section(SectionCluster())
