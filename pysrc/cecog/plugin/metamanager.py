"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

from collections import OrderedDict

from cecog.util.pattern import Singleton
from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION
from cecog.plugin.segmentation.manager import SegmentationPluginManager

from cecog.plugin.segmentation.strategies import SegmentationPluginPrimary
from cecog.plugin.segmentation.strategies import SegmentationPluginExpanded
from cecog.plugin.segmentation.strategies import SegmentationPluginInside
from cecog.plugin.segmentation.strategies import SegmentationPluginOutside
from cecog.plugin.segmentation.strategies import SegmentationPluginRim
from cecog.plugin.segmentation.strategies import SegmentationPluginPropagate
from cecog.plugin.segmentation.strategies import SegmentationPluginConstrainedWatershed
from cecog.plugin.segmentation.strategies import SegmentationPluginDifference
from cecog.plugin.segmentation.strategies import SegmentationPluginIlastik
from cecog.plugin.segmentation.strategies import SegmentationPluginPrimaryLoadFromFile
from cecog import CHANNEL_PREFIX


class RegionInformation(object):

    names = dict([(p, list()) for p in CHANNEL_PREFIX])
    colors = {}


class MetaPluginManager(object):

    # must be a process save Singleton, otherwise multiprocessing is broken
    __metaclass__ = Singleton

    def __init__(self):
        super(MetaPluginManager, self).__init__()
        self.region_info = RegionInformation()
        self.managers = OrderedDict()
        self.managers['primary'] =  SegmentationPluginManager(self.region_info,
                                                              self,
                                                              'Primary segmentation',
                                                              'primary_segmentation',
                                                              SECTION_NAME_OBJECTDETECTION)

        self.managers['secondary'] = SegmentationPluginManager(self.region_info,
                                                               self,
                                                               'Secondary segmentation',
                                                               'secondary_segmentation',
                                                               SECTION_NAME_OBJECTDETECTION)

        self.managers['tertiary'] = SegmentationPluginManager(self.region_info,
                                                              self,
                                                              'Tertiary segmentation',
                                                              'tertiary_segmentation',
                                                              SECTION_NAME_OBJECTDETECTION)
        self._register_plugins()

    def _register_plugins(self):

        self.managers['primary'].register_plugin(SegmentationPluginPrimary)
        self.managers['primary'].register_plugin(SegmentationPluginIlastik)
        self.managers['primary'].register_plugin(SegmentationPluginPrimaryLoadFromFile)

        self.managers['secondary'].register_plugin(SegmentationPluginExpanded)
        self.managers['secondary'].register_plugin(SegmentationPluginInside)
        self.managers['secondary'].register_plugin(SegmentationPluginOutside)
        self.managers['secondary'].register_plugin(SegmentationPluginRim)
        self.managers['secondary'].register_plugin(SegmentationPluginPropagate)
        self.managers['secondary'].register_plugin(SegmentationPluginConstrainedWatershed)

        self.managers['tertiary'].register_plugin(SegmentationPluginExpanded)
        self.managers['tertiary'].register_plugin(SegmentationPluginInside)
        self.managers['tertiary'].register_plugin(SegmentationPluginOutside)
        self.managers['tertiary'].register_plugin(SegmentationPluginRim)
        self.managers['tertiary'].register_plugin(SegmentationPluginPropagate)
        self.managers['tertiary'].register_plugin(SegmentationPluginConstrainedWatershed)
        self.managers['tertiary'].register_plugin(SegmentationPluginDifference)

    def __getitem__(self, key):
        return self.managers[key]

    def __iter__(self):
        for mgr in self.managers.itervalues():
            yield mgr
