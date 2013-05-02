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
import numpy.distutils

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

pyrcc_opts = {'infile': 'cecog.qrc',
              'outfile': join('pysrc', 'cecog', 'cecog_rc.py'),
              'pyrccbin': 'pyrcc4'}

# cc_includes = ['/usr/include',
#                '/biosw/debian5-x86_64/vigra/1.8.0/include',
#                '/biosw/debian5-x86_64/boost/1.51.0/include',
# 	       'csrc/include'] + \
#                numpy.distutils.misc_util.get_numpy_include_dirs()
# library_dirs = ['/biosw/debian5-x86_64/vigra/1.8.0/lib',
# 	        '/biosw/debian5-x86_64/boost/1.51.0/lib']
# libraries = ['boost_python', 'tiff', 'vigraimpex']


cc_includes = ['/Users/hoefler/sandbox/lib-static/include',
               '/cecoglibs/vigra/include/',
               'csrc/include'] + \
               numpy.distutils.misc_util.get_numpy_include_dirs()
library_dirs = ['/Users/hoefler/sandbox/lib-static/lib',
                '/cecoglibs/vigra/lib']
libraries = ['boost_python', 'tiff', 'vigraimpex']


ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'wrapper','cecog.cxx')],
                  include_dirs = cc_includes,
                  libraries = libraries,
                  library_dirs = library_dirs,
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

scripts = [join('scripts', 'CecogAnalyzer.py'), join('scripts', 'batch.py')]

setup(scripts = scripts,
      data_files = build_helpers.get_data_files(mpl_data=False),
      cmdclass = {'pyrcc': build_helpers.PyRcc,
                  'build': build_helpers.Build},
      packages = packages,
      package_dir = {'cecog': join('pysrc', 'cecog'),
                     'pdk': join('pysrc', 'pdk')},
      options = {"pyrcc": pyrcc_opts},
      ext_modules = [ccore],
      **build_helpers.metadata)
