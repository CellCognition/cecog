# pylint: disable-msg=F0401
# PyLint shouldn't fail if not on Windows
"""
Core pdk utilities.

FOG 10.2002
"""

__docformat__ = "epytext"

__author__ = "F Oliver Gathmann"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['get_os_name',
           'on_linux',
           'on_mac',
           'on_posix',
           'on_windows',
           'app_is_frozen',
           'get_main_dir',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import imp
import os
import sys

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# helper functions:
#

#------------------------------------------------------------------------------
# classes:
#

#------------------------------------------------------------------------------
# functions:
#

def on_windows():
    """
    Checks if the current machine runs MS Windows.

    @return: check result (Boolean)
    """
    return sys.platform[:3] == 'win'


def on_linux():
    """
    Checks if the current machine runs Linux.

    @return: check result (Boolean)
    """
    return sys.platform[:5] == 'linux'


def on_mac():
    """
    Checks if the current machine runs Mac OS-X.

    @return: check result (Boolean)
    """
    return sys.platform == 'darwin'


def on_posix():
    """
    Checks if the current machine runs a posix OS.

    @return: check result (Boolean)
    """
    return os.name == 'posix'


def get_os_name():
    """
    Returns a generic OS name string ("windows", "linux", or "mac").

    @return: OS name (string) or C{None}, if the current OS is not supported
    """
    os_name = None
    if on_windows():
        os_name = 'windows'
    elif on_linux():
        os_name = 'linux'
    elif on_mac():
        os_name = 'mac'
    return os_name


def app_is_frozen():
    """
    Checks if the app is stadalone

    @return: True / False
    @rtype: bool
    """
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") # old py2exe
            or imp.is_frozen("__main__")) # tools/freeze


def get_main_dir():
    """
    Returns the directory of the standalone or the python script

    @return: a directory path
    @rtype: string
    """
    main_dir = os.path.dirname(sys.argv[0])
    if app_is_frozen():
        strExePath = os.path.dirname(sys.executable)
        if on_windows():
            main_dir = strExePath
        elif on_mac:
            main_dir = os.path.sep + \
                         os.path.join(*strExePath.split(os.path.sep)[:-3]) # pylint: disable-msg=W0142
    return main_dir
