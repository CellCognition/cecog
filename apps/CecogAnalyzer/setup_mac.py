"""
setup_mac.py

Setup script for MacOSX.

Usage:
   python setup_mac.py py2app

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import os
import sys
import py2app
sys.path.append(os.path.join(os.pardir, os.pardir, "pysrc"))

from distutils.core import setup

import pkginfo
from datafiles import get_data_files

INCLUDES = [ 'sip',
             'scipy.sparse.csgraph._validation',
             'scipy.spatial.kdtree',
             'scipy.sparse.csgraph._shortest_path']

EXCLUDES = ['QtDesigner', 'QtNetwork',
            'QtOpenGL', 'QtScript',
            'QtSql', 'QtTest',
            'QtWebKit', 'QtXml',
            'phonon']

PACKAGES = ['cecog', 'pdk', 'h5py', 'vigra', 'sklearn']

# setting argv_emulation causes the app to get stuck in the splash screen
py2app_opts = {'argv_emulation': False,
               'excludes': EXCLUDES,
               'strip' : True,
               'packages': PACKAGES,
               # don't use 2, some packages use
               # __doc__ += PCA.__doc__, that causes the bundle to crash
               'optimize': 1,
               'iconfile': 'resources/cecog_analyzer_icon.icns'}


setup(app=['CecogAnalyzer.py'],
      data_files=get_data_files(),
      options={"py2app": py2app_opts},
      setup_requires=['py2app'],
      **pkginfo.metadata)
