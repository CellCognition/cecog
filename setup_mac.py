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
from os.path import join, abspath
import numpy.distutils

import py2app
sys.path.append(abspath("pysrc"))

from distutils.core import setup, Extension
import build_helpers

INCLUDES = [ 'sip',
             'scipy.sparse.csgraph._validation',
             'scipy.spatial.kdtree',
             'scipy.sparse.csgraph._shortest_path']

EXCLUDES = ['PyQt4.QtDesigner', 'PyQt4.QtNetwork',
            'PyQt4.QtOpenGL', 'PyQt4.QtScript', 'PyQt4.QtSql',
            'PyQt4.QtTest', 'PyQt4.QtWebKit', 'PyQt4.QtXml', 'PyQt4.phonon']

# setting argv_emulation causes the app to get stuck in the splash screen
py2app_opts = {'argv_emulation': False,
               'excludes': EXCLUDES,
               'strip' : True,
               'packages': ['h5py', 'vigra'],
               'optimize': 2,
               'iconfile': 'resources/cecog_analyzer_icon.icns'}

pyrcc_opts = {'infile': 'cecog.qrc',
              'outfile': join('pysrc', 'cecog', 'cecog_rc.py'),
              'pyrccbin': 'pyrcc4'}

cc_includes = ['/Users/hoefler/sandbox/lib-static/include',
               '/cecoglibs/vigra/include/',
               'csrc/include'] + \
               numpy.distutils.misc_util.get_numpy_include_dirs()
library_dirs = ['/Users/hoefler/sandbox/lib-static/lib',
                '/cecoglibs/vigra/lib']
libraries = ['boost_python', 'vigraimpex']


ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'wrapper','cecog.cxx')],
                  include_dirs = cc_includes,
                  libraries = libraries,
                  library_dirs = library_dirs,
                  extra_object = ['tiff'],
                  extra_compile_args = ['-O3', '-fPIC', '-arch x86_64'],
                  language = 'c++')

# python package to distribute
packages = ['cecog',
            'cecog.analyzer',
            'cecog.ccore',
            'cecog.experiment',
            'cecog.export',
            'cecog.extensions',
            'cecog.gui',
            'cecog.gui.analyzer',
            'cecog.gui.modules',
            'cecog.gui.widgets',
            'cecog.io',
            'cecog.learning',
            'cecog.multiprocess',
            'cecog.plugin',
            'cecog.plugin.segmentation',
            'cecog.threads',
            'cecog.traits',
            'cecog.traits.analyzer',
            'cecog.util',
            'pdk']

scripts = [join('scripts', 'CecogAnalyzer.py')]

setup(app = scripts,
      scripts = scripts,
      data_files = build_helpers.get_data_files(),
      cmdclass = {'pyrcc': build_helpers.PyRcc,
                  'build': build_helpers.Build},
      packages = packages,
      package_dir = {'cecog': join('pysrc', 'cecog'),
                     'pdk': join('pysrc', 'pdk')},
      options = {"py2app": py2app_opts,
                 "pyrcc": pyrcc_opts},
      setup_requires=['py2app'],
      ext_modules = [ccore],
      **build_helpers.metadata)
