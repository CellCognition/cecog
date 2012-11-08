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

import os
import sys
from os.path import join
from cx_Freeze import setup, Executable

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
             'Tkconstants', 'tk', 'Tkinter', 'tcl' ]

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(  options = {"build_exe" : {"includes" : INCLUDES,
                                  "packages": PACKAGES,
                                  "excludes": EXCLUDES,
                                  "silent": False},
                   "install_exe" : {"install_dir": "dist"},
                   "install": {"prefix": "dist"}},
        data_files = get_data_files(),
        executables = [Executable("CecogAnalyzer.py",
                                  base=base,
                                  icon=join('resources',
                                            'cecog_analyzer_icon.ico'))],
        **pkginfo.metadata)
