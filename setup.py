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
sys.path.append(abspath("pysrc"))

from distutils.core import setup, Extension
import build_helpers

pyrcc_opts = {'infile': 'cecog.qrc',
              'outfile': join('pysrc', 'cecog', 'cecog_rc.py'),
              'pyrccbin': 'pyrcc4'}

ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'wrapper','cecog.cxx')],
                  include_dirs=build_helpers.CC_INCLUDES,
                  libraries=['boost_python', 'tiff', 'vigraimpex'],
                  extra_compile_args = ['-O3', '-fPIC'],
                  language = 'c++')

# python packages to distribute
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

scripts = [join('scripts', 'CecogAnalyzer.py'), join('scripts', 'cecog_batch.py')]
datadir = join(sys.prefix, 'share', 'cellcognition')

setup(scripts = scripts,
      data_files = build_helpers.get_data_files(mpl_data=False),
      cmdclass = {'pyrcc': build_helpers.PyRcc,
                  'build': build_helpers.Build},
      packages = packages,
      package_dir = {'cecog': join('pysrc', 'cecog'),
                     'pdk': join('pysrc', 'pdk')},
      options = {'pyrcc': pyrcc_opts,
                 'install': {'install_data': datadir}},
      ext_modules = [ccore],
      **build_helpers.metadata)
