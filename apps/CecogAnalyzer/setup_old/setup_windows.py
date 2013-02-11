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

import pkginfo
from datafiles import get_data_files

if sys.platform != 'win32':
    raise RuntimeError("%s runs only on Windows machine's"
                       % os.path.basename(__file__))

PACKAGES = [ 'cecog', 'h5py', 'vigra', 'matplotlib' ]

INCLUDES = [ 'sip',
             'scipy.sparse.csgraph._validation',
             'scipy.spatial.kdtree',
             'scipy.sparse.csgraph._shortest_path' ]

EXCLUDES = [ 'PyQt4.QtDesigner', 'PyQt4.QtNetwork',
             'PyQt4.QtOpenGL', 'PyQt4.QtScript',
             'PyQt4.QtSql', 'PyQt4.QtTest',
             'PyQt4.QtWebKit', 'PyQt4.QtXml',
             'PyQt4.phonon',
             'rpy',
             '_gtkagg', '_tkagg', '_agg2', '_cairo', '_cocoaagg',
             '_fltkagg', '_gtk', '_gtkcairo',
             'Tkconstants', 'Tkinter', 'tcl' ]

DLL_EXCLUDES = [ 'libgdk-win32-2.0-0.dll',
                 'libgobject-2.0-0.dll',
                 'libgdk_pixbuf-2.0-0.dll',
                 'w9xpopen.exe' ] # is not excluded for some reasion

setup( options = {"py2exe": { 'includes': INCLUDES,
                              'excludes': EXCLUDES,
                              'packages': PACKAGES,
                              'dll_excludes': DLL_EXCLUDES,
                              # optimize 2 would strip doc-strings
                              'optimize': 1,
                              'compressed': True,
                              'skip_archive': False,
                              'bundle_files': 3 }},
       data_files = get_data_files(),
       zipfile = "data.zip",
       windows = [{'script': "CecogAnalyzer.py",
                   'icon_resources': [(1, 'resources\cecog_analyzer_icon.ico')]
                   }],
       **pkginfo.metadata)

try:
    os.remove(join('dist', 'w9xpopen.exe'))
except:
    pass
