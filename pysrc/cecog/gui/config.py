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

__all__ = ['GuiConfigSettings']

#-------------------------------------------------------------------------------
# standard library imports:
#
import copy

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.settings import ConfigSettings
#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class GuiConfigSettings(ConfigSettings):
    '''
    Extended ConfigSettings to set the window modified flag of the parent
    window upon all setting changes via set.
    '''

    def __init__(self, parent, section_registry):
        self._parent = parent
        self._notify_change = True
        ConfigSettings.__init__(self, section_registry)

    def copy(self):
        new = copy.copy(self)
        new._parent = None
        # some deepcopy problem introduced with Python 2.7
        # ConfigParser cannot be deepcopied due to a new regex stored in self
        try:
            new._optcre = None
        except AttributeError:
            pass
        new2 = copy.deepcopy(new)
        try:
            new2._optcre = self._optcre
        except AttributeError:
            pass
        return new2

    def set_notify_change(self, state):
        self._notify_change = state

    def set(self, section_name, trait_name, value):
        ConfigSettings.set(self, section_name, trait_name, value)
        if not self._parent is None and self._notify_change:
            self._parent.settings_changed(True)


#-------------------------------------------------------------------------------
# main:
#

