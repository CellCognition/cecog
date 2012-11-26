"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__all__ = ['RegionInformation', 'SegmentationPluginManager', '_SegmentationPlugin']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog import CHANNEL_PREFIX
from cecog.plugin import PluginManager, _Plugin

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class RegionInformation(object):

    names = dict([(p, list()) for p in CHANNEL_PREFIX])
    colors = {}

class SegmentationPluginManager(PluginManager):

    LABEL = 'Segmentation plugins'

    def __init__(self, region_info, *args, **kw):
        super(SegmentationPluginManager, self).__init__(*args, **kw)
        self.region_info = region_info

    def notify_instance_modified(self, plugin_name, removed=False):
        super(SegmentationPluginManager, self).notify_instance_modified( \
            plugin_name, removed)
        prefix = self.name.split('_')[0]

        self.region_info.names[prefix] = self.get_plugin_names()
        self.region_info.colors.update( \
            dict([(name, self.get_plugin_instance(name).COLOR)
                  for name in self.get_plugin_names()]))


class _SegmentationPlugin(_Plugin):

    COLOR = '#FFFFFF'
    QRC_PREFIX = 'segmentation'


#-------------------------------------------------------------------------------
# main:
#
