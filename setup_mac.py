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

import sys
from os.path import join, abspath
sys.path.append(abspath("pysrc"))
import py2app

from distutils.core import setup, Extension
import build_helpers

py2app_opts = {'excludes': build_helpers.EXCLUDES}

pyrcc_opts = {'infile': 'cecog.qrc',
              'outfile': join('pysrc', 'cecog', 'cecog_rc.py'),
              'pyrccbin': 'pyrcc4'}

ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'cecog.cxx')],
                  libraries = ['vigraimpex', 'boost_python'],
                  include_dirs = build_helpers.CC_INCLUDES,
                  extra_object = ['tiff'],
                  extra_compile_args = ['-O3', '-fPIC'],
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
