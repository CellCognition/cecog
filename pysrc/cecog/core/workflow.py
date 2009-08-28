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
from pyvigra import UInt8RgbImage

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.core.channel import (CHANNEL_MANAGER,
                                ChannelManager,
                                ExperimentChannel,
                                UserChannel,
                                )
from cecog.core.mask import (MASK_MANAGER,
                             MaskManager,
                             Mask,
                             )

from cecog.plugins.masks.primary import Primary
from cecog.ccore import (apply_blending,
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

class Renderer:
    pass

class ImageViewerRenderer(Renderer):

    def __init__(self, image_viewer):
        self._image_viewer = image_viewer

    def render(self, manager):

        if manager.NAME == CHANNEL_MANAGER:
            rgb_overlay = apply_blending([img for img, alp in manager.results],
                                         [alp for img, alp in manager.results])
            self._image_viewer.from_pyvigra(rgb_overlay)


class WorkflowManager(object):

    def __init__(self):
        self._managers = OrderedDict()
        self._renderers = []
        self._image_container = None

    def register_manager(self, manager):
        #FIXME: hack to solve recursive import
        manager.set_workflow_manager(self)
        self._managers[manager.NAME] = manager

    def register_renderer(self, renderer):
        self._renderers.append(renderer)

    def get_manager(self, name):
        return self._managers[name]

    def set_image_container(self, image_container):
        self._image_container = image_container

        channel_manager = self.get_manager(CHANNEL_MANAGER)
        meta_data = self._image_container.meta_data
        channel_manager.set_experiment_channels(meta_data.channels)

    #def get_render_result(self):
    #    return UInt8Image2dRgb((200,200))

    def process_experiment_channels(self, exp_channels):
        #FIXME: bad hack
        self._exp_channels = exp_channels

        data = {}
        for name, manager in self._managers.iteritems():

            if name == CHANNEL_MANAGER:
                data[name] = exp_channels
            manager.process(data)

            for renderer in self._renderers:
                renderer.render(manager)

    def update(self, manager_name):
        #manager = self.get_manager(manager_name)
        #for renderer in self._renderers:
        #    renderer.render(manager)
        self.process_experiment_channels(self._exp_channels)


    def process(self):

        previous = {}
        for name, manager in self._managers.iteritems():
            manager.process(previous)
            previous[name] = manager


HAS_GUI = True

workflow_manager = WorkflowManager()

if HAS_GUI:
    from cecog.gui.widgets.channelframe import GuiChannelManager
    channel_manager = GuiChannelManager()
else:
    channel_manager = ChannelManager()
workflow_manager.register_manager(channel_manager)

if HAS_GUI:
    from cecog.gui.widgets.maskframe import GuiMaskManager
    mask_manager = GuiMaskManager()
else:
    mask_manager = MaskManager()
mask_manager.register(Primary.NAME, Primary, Mask)
workflow_manager.register_manager(mask_manager)

