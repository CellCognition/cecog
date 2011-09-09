"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__all__ = ['RegionInformation',
           'SegmentationPluginManager',
           '_SegmentationPlugin',
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
from cecog.plugin import (PluginManager,
                          _Plugin,
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
class RegionInformation(object):

    names = {'primary': [], 'secondary': [], 'tertiary': []}
    colors = {}


class SegmentationPluginManager(PluginManager):

    LABEL = 'Segmentation plugins'

    def notify_instance_modified(self, plugin_name, removed=False):
        #FIXME: should not be imported here
        from cecog.plugin.segmentation import REGION_INFO
        prefix = self.name.split('_')[0]

        REGION_INFO.names[prefix] = self.get_plugin_names()
        REGION_INFO.colors.update(dict([(name, self.get_plugin_instance(name).COLOR)
                                        for name in self.get_plugin_names()]))


class _SegmentationPlugin(_Plugin):

    COLOR = '#FFFFFF'
    REQUIRES = None

    def run(self, meta_image, channel=None):
        if not self.REQUIRES is None:
            required_container = channel.dctContainers[self.REQUIRES]
            result_container = self._run(meta_image, required_container)
        else:
            result_container =  self._run(meta_image)
        return result_container


#-------------------------------------------------------------------------------
# main:
#

