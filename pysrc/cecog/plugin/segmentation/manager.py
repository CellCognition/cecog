"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__all__ = ['SegmentationPluginManager', '_SegmentationPlugin']

from cecog.plugin import PluginManager, _Plugin


class _SegmentationPlugin(_Plugin):

    COLOR = '#FFFFFF'
    QRC_PREFIX = 'segmentation'


class SegmentationPluginManager(PluginManager):

    LABEL = 'Segmentation plugins'

    def __init__(self, region_info, *args, **kw):
        super(SegmentationPluginManager, self).__init__(*args, **kw)
        self.region_info = region_info

    def init_from_settings(self, *args, **kw):
        prefix = self.name.split('_')[0]
        self.region_info.delete_channel(prefix)
        super(SegmentationPluginManager, self).init_from_settings(*args, **kw)

    def notify_instance_modified(self, plugin_name, removed=False):
        super(SegmentationPluginManager, self).notify_instance_modified( \
            plugin_name, removed)

        prefix = self.name.split('_')[0]
        self.region_info.names[prefix] = self.get_plugin_names()
        self.region_info.colors.update( \
            dict([(name, self.get_plugin_instance(name).COLOR)
                  for name in self.get_plugin_names()]))

