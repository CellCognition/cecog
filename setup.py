"""
setup.py

Setup script for linux.

Usage:
   python setup.py --help

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

from distutils.core import setup, Extension
import build_helpers

pyrcc_opts = {'infile': 'cecog.qrc',
              'outfile': join('cecog', 'cecog_rc.py'),
              'pyrccbin': 'pyrcc5'}

pycssrcc_opt = {'pyrccbin': 'pyrcc5'}

help_opts = {'infile': join('doc', 'manual.qhcp'),
             'outfile': join('resources', 'doc', 'manual.qhc'),
             'qcollectiongeneator': 'qcollectiongenerator'}

ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'cecog.cxx')],
                  include_dirs=build_helpers.CC_INCLUDES,
                  libraries=['boost_python', 'tiff', 'vigraimpex'],
                  extra_compile_args = ['-O3', '-fPIC'],
                  language = 'c++')

# python packages to distribute
packages = build_helpers.find_submodules("./cecog", "cecog")
scripts = [join('scripts', 'CecogAnalyzer.py'),
           join('scripts', 'cecog_batch.py')]

setup(scripts = scripts,
      data_files = build_helpers.get_data_files(build_helpers.TARGET_SYS,
                                                mpl_data=False,
                                                qt_plugins=False),
      cmdclass = {'build_rcc': build_helpers.BuildRcc,
                  'build_css': build_helpers.BuildCSSRcc,
                  'build_help': build_helpers.BuildHelp,
                  'build': build_helpers.Build},
      packages = packages,
      package_data = {'cecog': [join('gui', '*.ui'),
                                join('gui', 'helpbrowser', '*.ui')]},
      options = {'build_rcc': pyrcc_opts,
                 'build_css': pycssrcc_opt,
                 'build_help': help_opts},
      ext_modules = [ccore],
      **build_helpers.metadata)
