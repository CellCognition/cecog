"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__all__ = ['PLUGIN_MANAGERS',
           'PRIMARY_PLUGIN_MANAGER',
           'SECONDARY_PLUGIN_MANAGER',
           'TERTIARY_PLUGIN_MANAGER',
           'REGION_INFO',
           ]

from cecog import PLUGIN_MANAGERS
from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION

from cecog.plugin.segmentation.manager import (RegionInformation,
                                               SegmentationPluginManager,
                                               )
from cecog.plugin.segmentation.strategies import (SegmentationPluginPrimary,
                                                  SegmentationPluginExpanded,
                                                  SegmentationPluginInside,
                                                  SegmentationPluginOutside,
                                                  SegmentationPluginRim,
                                                  SegmentationPluginPropagate,
                                                  SegmentationPluginConstrainedWatershed,
                                                  )

REGION_INFO = RegionInformation()

PRIMARY_SEGMENTATION_MANAGER = SegmentationPluginManager('primary_segmentation',
                                                         SECTION_NAME_OBJECTDETECTION)
PRIMARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginPrimary)

SECONDARY_SEGMENTATION_MANAGER = SegmentationPluginManager('secondary_segmentation',
                                                           SECTION_NAME_OBJECTDETECTION)
SECONDARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginExpanded)
SECONDARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginInside)
SECONDARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginOutside)
SECONDARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginRim)
SECONDARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginPropagate)
SECONDARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginConstrainedWatershed)

TERTIARY_SEGMENTATION_MANAGER = SegmentationPluginManager('tertiary_segmentation',
                                                          SECTION_NAME_OBJECTDETECTION)
TERTIARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginExpanded)
TERTIARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginInside)
TERTIARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginOutside)
TERTIARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginRim)
TERTIARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginPropagate)
TERTIARY_SEGMENTATION_MANAGER.register_plugin(SegmentationPluginConstrainedWatershed)

PLUGIN_MANAGERS.extend([PRIMARY_SEGMENTATION_MANAGER, SECONDARY_SEGMENTATION_MANAGER, TERTIARY_SEGMENTATION_MANAGER])

