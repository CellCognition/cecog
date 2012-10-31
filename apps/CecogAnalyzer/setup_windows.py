# -*- coding: utf-8 -*-
"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See LICENSE.txt for details.
                 See AUTHORS.txt for author contributions.

setup_windows.py - windows specific instructions for distuils
"""

__author__ = 'rudolf.hoefler@gmail.com'

import os, sys, glob
from distutils.core import setup
import py2exe

from datafiles import get_data_files

if sys.platform != 'win32':
    raise RuntimeError("%s runs only on Windows machine's"
                       % os.path.basename(__file__))

INCLUDES = ['sip', 'netCDF4_utils', 'netcdftime']
EXCLUDES = ['PyQt4.QtDesigner', 'PyQt4.QtNetwork',
            'PyQt4.QtOpenGL', 'PyQt4.QtScript',
            'PyQt4.QtSql', 'PyQt4.QtTest',
            'PyQt4.QtWebKit', 'PyQt4.QtXml',
            'PyQt4.phonon',
            'scipy', 'rpy',
            'Tkconstants', 'Tkinter', 'tcl' ]

setup( options = {"py2exe": { 'includes': INCLUDES,
                              'excludes': EXCLUDES,
                              'packages': ['cecog'],
                              'optimize': 2,
                              'compressed': True,
                              'bundle_files': 3 }},
       data_files = get_data_files(),
       zipfile = "data.zip",
       windows = [{'script': "CecogAnalyzer.py",
                   'icon_resources': [(1, 'resources\cecog_analyzer_icon.ico')]
                   }]
       )

# why removing w9xpopen.exe anyway?
try:
    os.remove(join('dist', 'w9xpopen.exe'))
except:
    pass
