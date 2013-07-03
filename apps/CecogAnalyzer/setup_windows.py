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

import os, sys
from os.path import join
from distutils.core import setup
import py2exe

import pkginfo
from datafiles import get_data_files


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
             '_gtkagg', '_cairo', '_gtkcairo', '_fltkagg',
             '_tkagg',
             'Tkinter']

DLL_EXCLUDES = [ 'libgdk-win32-2.0-0.dll',
                 'libgobject-2.0-0.dll',
                 'libgdk_pixbuf-2.0-0.dll',
                 'KERNELBASE.dll',
                 'MSIMG32.dll',
                 'NSI.dll',
                 'USP10.dll',
                 'intl.dll',
                 'freetype6.dll',
                 'libcairo-2.dll',
                 'libexpat-1.dll',
                 'libglib-2.0-0.dll',
                 'libgmodule-2.0-0.dll',
                 # 'libifcoremd.dll',
                 # 'libiomp5md.dll',
                 # 'libmmd.dll',
                 'libpango-1.0-0.dll',
                 'sqlite3.dll',
                 'DNSAPI.dll',
                 'API-MS-Win-Core-SysInfo-L1-1-0.dll',
                 'API-MS-Win-Core-Misc-L1-1-0.dll',
                 'API-MS-Win-Core-IO-L1-1-0.dll',
                 'API-MS-Win-Core-File-L1-1-0.dll',
                 'API-MS-Win-Core-Debug-L1-1-0.dll',
                 'API-MS-Win-Core-Handle-L1-1-0.dll',
                 'API-MS-Win-Core-Localization-L1-1-0.dll',
                 'API-MS-Win-Core-Profile-L1-1-0.dll',
                 'API-MS-Win-Core-Heap-L1-1-0.dll',
                 'API-MS-Win-Core-Synch-L1-1-0.dll',
                 'API-MS-Win-Core-String-L1-1-0.dll',
                 'API-MS-Win-Core-DelayLoad-L1-1-0.dll',
                 'API-MS-Win-Core-LibraryLoader-L1-1-0.dll',
                 'API-MS-Win-Core-ErrorHandling-L1-1-0.dll',
                 'API-MS-Win-Core-ProcessThreads-L1-1-0.dll',
                 'API-MS-Win-Core-ProcessEnvironment-L1-1-0.dll',
                 'API-MS-Win-Core-LocalRegistry-L1-1-0.dll',
                 'w9xpopen.exe'] # is not excluded for some reasion

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
       console = [{'script': join("..", "..", "pysrc", "cecog",
                                  "batch", "batch.py")}],
       **pkginfo.metadata)

try:
    os.remove(join('dist', 'w9xpopen.exe'))
except:
    pass
