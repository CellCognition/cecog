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

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.core.entity import Entity
from cecog.core.plugin import PluginManager

from cecog.ccore import (apply_lut,
                         lut_from_single_color,
                         )
from cecog.util.color import hex_to_rgb

#-------------------------------------------------------------------------------
# constants:
#
CHANNEL_MANAGER = 'ChannelManager'
DEFAULT_CHANNEL_MAPPING = {'rfp' : '#FF0000',
                           'gfp' : '#00FF00',
                           }

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class _Channel(Entity):

    def __init__(self, name, manager, hex_color=None):
        super(_Channel, self).__init__(name, manager)
        self.hex_color = hex_color
        self.color = None
        self.lut = lut_from_single_color(hex_to_rgb(self.hex_color))
        self.alpha = 1.0

    def __call__(self, plugin, data):
        results = []
        print plugin, data
        for manager_id, items in data.iteritems():
            if manager_id == CHANNEL_MANAGER:
                for channel_id, image in items:
                    if channel_id == self.name:
                        return apply_lut(image, self.lut), self.alpha


class ExperimentChannel(_Channel):
    pass


class UserChannel(_Channel):
    pass


class ChannelManager(PluginManager):

    TEXT = 'channel'
    NAME = CHANNEL_MANAGER

    def set_experiment_channels(self, channels):
        #self._channels = channels
        for channel_name in channels:
            entity_options = {'hex_color' :
                              DEFAULT_CHANNEL_MAPPING[channel_name],
                              }
            self.register(channel_name, None,
                          ExperimentChannel,
                          entity_options=entity_options)


