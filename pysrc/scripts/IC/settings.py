import os, sys, time, re

from collections import OrderedDict
#from utilities import *

class Settings(object):
    """
    Simple container to hold all settings from an external python file as own
    class attributes.
    Should be made singleton.
    """

    def __init__(self, filename=None, dctGlobals=None):
        self.strFilename = filename
        if not filename is None:
            self.load(filename, dctGlobals)


    def load(self, filename, dctGlobals=None):
        self.strFilename = filename
        if dctGlobals is None:
            dctGlobals = globals()

        #self.settings_dir = os.path.abspath(os.path.dirname(self.strFilename))
        execfile(self.strFilename, dctGlobals, self.__dict__)

    def update(self, dctNew, bExcludeNone=False):
        for strKey, oValue in dctNew.iteritems():
            if not bExcludeNone or not oValue is None:
                self.__dict__[strKey] = oValue

    def __getattr__(self, strName):
        if strName in self.__dict__:
            return self.__dict__[strName]
        else:
            raise SettingsError("Parameter '%s' not found in settings file '%s'." %
                                (strName, self.strFilename))

    def __call__(self, strName):
        return getattr(self, strName)

    def all(self, copy=True):
        return self.__dict__.copy()


class SettingsError(StandardError):
    pass

