"""
setup_windows.py

Setup script for Windows.

Usage:
   python setup_windows.py py2exe

"""
__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import os
from os.path import join, abspath
import sys
import glob

sys.path.append(abspath("pysrc"))
sys.path.append(abspath('scripts'))

from distutils.core import setup, Extension
import py2exe
import build_helpers

pyrcc_opts = {'infile': 'cecog.qrc',
              'outfile': join('pysrc', 'cecog', 'cecog_rc.py'),
              'pyrccbin': join('C:\\', 'Python27', 'Lib', 'site-packages',
                               'PyQt4', 'pyrcc4.exe')}

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

py2exe_opts = {'includes': build_helpers.INCLUDES,
               'excludes': build_helpers.EXCLUDES,
               'dll_excludes': DLL_EXCLUDES}

# ccore build paths
# or write these paths to setup.cfg
includes = ['c:/python27/include',
            'c:/Python27/Lib/site-packages/numpy/core/include',
            'c:/lib/include',
            'c:/vigra/include',
            './csrc/include']
libraries = ['boost_python-vc100-mt-1_45', 'libtiff', 'vigraimpex']
library_dirs = ['c:/lib/lib', 'c:/vigra/lib']

ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'wrapper','cecog.cxx')],
                  include_dirs = includes,
                  libraries = libraries,
                  library_dirs = library_dirs,
                  extra_compile_args = ["/bigobj", "/EHsc"],
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

setup(options = {"py2exe": py2exe_opts,
                 'pyrcc': pyrcc_opts},
      cmdclass = {'pyrcc': build_helpers.PyRcc,
                  'build': build_helpers.Build},
      packages = packages,
      package_dir = {'cecog': join('pysrc', 'cecog'),
                     'pdk': join('pysrc', 'pdk')},
      data_files = build_helpers.get_data_files(),
      # zipfile = "data.zip",
      windows = [{'script': join('scripts', 'CecogAnalyzer.py'),
                  'icon_resources': [(1, 'resources\cecog_analyzer_icon.ico')]
                  }],
      console = [{'script': join('scripts', 'cecog_batch.py')}],
      ext_modules = [ccore],
      **build_helpers.metadata)
