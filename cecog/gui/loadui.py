"""
loadui.py

Helper function to load qt5-ui files either from sandbox or from
a frozen environment.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ('loadUI', )


from os.path import join
from os.path import isfile
from os.path import basename
from PyQt5 import uic

from cecog.environment import CecogEnvironment


def loadUI(filename, widget):
    """Helper function to load qt5-ui files either from sandbox or from
    a frozen environment.
    """

    if isfile(filename):
        return uic.loadUi (filename, widget)
    else:
        return uic.loadUi(
            join(CecogEnvironment.UI_DIR, basename(filename)), widget)
