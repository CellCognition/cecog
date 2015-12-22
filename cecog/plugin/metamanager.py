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

# primary plugins
from cecog.plugin.segmentation.primary_plugins import GlobalThreshold
from cecog.plugin.segmentation.primary_plugins import Ilastik
from cecog.plugin.segmentation.primary_plugins import LoadFromFile
from cecog.plugin.segmentation.primary_plugins import LocalAdaptiveThreshold
from cecog.plugin.segmentation.primary_plugins import LocalAdaptiveThreshold2
from cecog.plugin.segmentation.primary_plugins import LocalAdaptiveThreshold3
from cecog.plugin.segmentation.primary_plugins import LocalAdaptiveThreshold4
# watershed
from cecog.plugin.segmentation.watershed import ConstrainedWatershed
from cecog.plugin.segmentation.watershed import WatershedAndThresholdLocalThreshold
from cecog.plugin.segmentation.watershed import WatershedAndMultiThreshold
# secondary and tertiary
from cecog.plugin.segmentation.secondary_plugins import Expanded
from cecog.plugin.segmentation.secondary_plugins import Inside
from cecog.plugin.segmentation.secondary_plugins import Outside
from cecog.plugin.segmentation.secondary_plugins import Rim
from cecog.plugin.segmentation.secondary_plugins import Propagate
from cecog.plugin.segmentation.secondary_plugins import Difference

from cecog import CHANNEL_PREFIX


class RegionInformation(object):

    def __init__(self):
        self.names = dict([(p, list()) for p in CHANNEL_PREFIX])
        self.colors = dict()

    def delete_channel(self, channel):
        try:
            self.names[channel] = list()
            del self.colors[channel]
        except KeyError:
            pass

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


        self.managers['primary'].register_plugin(LocalAdaptiveThreshold)
        self.managers['primary'].register_plugin(GlobalThreshold)
        self.managers['primary'].register_plugin(Ilastik)
        self.managers['primary'].register_plugin(LoadFromFile)
        self.managers['primary'].register_plugin(LocalAdaptiveThreshold2)
        self.managers['primary'].register_plugin(LocalAdaptiveThreshold3)
        self.managers['primary'].register_plugin(LocalAdaptiveThreshold4)

        self.managers['secondary'].register_plugin(Expanded)
        self.managers['secondary'].register_plugin(Inside)
        self.managers['secondary'].register_plugin(Outside)
        self.managers['secondary'].register_plugin(Rim)
        self.managers['secondary'].register_plugin(Propagate)
        self.managers['secondary'].register_plugin(ConstrainedWatershed)
        self.managers['secondary'].register_plugin(WatershedAndMultiThreshold)
        self.managers['secondary'].register_plugin(WatershedAndThresholdLocalThreshold)

        self.managers['tertiary'].register_plugin(Expanded)
        self.managers['tertiary'].register_plugin(Inside)
        self.managers['tertiary'].register_plugin(Outside)
        self.managers['tertiary'].register_plugin(Rim)
        self.managers['tertiary'].register_plugin(Difference)
        self.managers['tertiary'].register_plugin(Propagate)
        self.managers['tertiary'].register_plugin(ConstrainedWatershed)
        self.managers['tertiary'].register_plugin(WatershedAndMultiThreshold)
        self.managers['tertiary'].register_plugin(WatershedAndThresholdLocalThreshold)

    def __getitem__(self, key):
        return self.managers[key]

    def __iter__(self):
        for mgr in self.managers.itervalues():
            yield mgr
