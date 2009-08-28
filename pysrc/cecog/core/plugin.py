"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__docformat__ = "epytext"
__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import time
import sys
import os

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# cecog imports:
#


#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class PluginItem(object):

    def __init__(self, plugin_cls, entity_cls, entity_options):
        self._plugin_cls = plugin_cls
        self._entity_cls = entity_cls
        if entity_options is None:
            entity_options = {}
        self._entity_options = entity_options

    def activate(self, id_name, manager):
        if not self._plugin_cls is None:
            plugin = self._plugin_cls()
        else:
            plugin = None
        entity = self._entity_cls(id_name, manager, **self._entity_options)
        return PluginItemInstance(plugin, entity)


class PluginItemInstance(object):

    def __init__(self, plugin, entity):
        self.plugin = plugin
        self.entity = entity


class PluginManager(object):

    TEXT = ''
    NAME = None

    def __init__(self):
        self._workflow_manager = None
        self._available_plugins = OrderedDict()
        self._active_plugins = OrderedDict()
        self.results = []

    def register(self, name, plugin_cls, entity_cls, entity_options=None):
        item = PluginItem(plugin_cls, entity_cls, entity_options)
        self._available_plugins[name] = item

    def get(self, name):
        return self._available_plugins[name]

    def activate(self, name):
        item = self.get(name)
        idx = 2
        id_name = name
        while id_name in self._active_plugins:
            id_name = "%s - %d" % (name, idx)
            idx += 1
        plugin_instance = item.activate(id_name, self)
        self._active_plugins[id_name] = plugin_instance
        return id_name, plugin_instance

    @property
    def plugins(self):
        return self._available_plugins.items()

    def process(self, data):
        self.results = []
        for name, plugin_instance in self._active_plugins.iteritems():
            #if not plugin_instance.plugin is None:
            #    plugin_instance.plugin(plugin_instance.entity)
            result = plugin_instance.entity(plugin_instance.plugin, data)
            self.results.append(result)

    def set_workflow_manager(self, workflow_manager):
        self._workflow_manager = workflow_manager

    def update(self):
        self._workflow_manager.update(self.NAME)

