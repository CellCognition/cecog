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
from os.path import join, abspath, dirname
import sys
import glob
from ctypes.util import find_library

sys.path.append(abspath('scripts'))

from distutils.core import setup, Extension
import py2exe
import build_helpers

pyrcc_opts = {'qrc': {'cecog.qrc' : join('cecog', 'cecog_rc.py'), },
              'pyrccbin': join('C:\\', 'Python27', 'Lib', 'site-packages',
                               'PyQt5', 'pyrcc5.exe')}

help_opts = {'infile': join('doc', 'manual.qhcp'),
             'outfile': join('resources', 'doc', 'manual.qhc'),
             'qcollectiongeneator': 'qcollectiongenerator'}

DLL_EXCLUDES = ['w9xpopen.exe',
                'MSVCP90.dll',
                'HID.DLL'] # is not excluded for some reasion

py2exe_opts = {'includes': build_helpers.INCLUDES,
               'excludes': build_helpers.EXCLUDES,
               'dll_excludes': DLL_EXCLUDES,
               'optimize': 1,
               'compressed': True,
               'skip_archive': False,
               'bundle_files': 3,
               'packages' : ['h5py','sklearn', 'skimage']}

# ccore build paths
# or write these paths to setup.cfg
includes = ['c:/python27/include',
            'c:/Python27/Lib/site-packages/numpy/core/include',
            './csrc/include']
libraries = ['libtiff', 'vigraimpex']
library_dirs = []

ccore = Extension('cecog.ccore._cecog',
                  sources = [join('csrc','src', 'cecog.cxx')],
                  include_dirs = includes,
                  libraries = libraries,
                  library_dirs = library_dirs,
                  extra_compile_args = ["/bigobj", "/EHsc"],
                  language = 'c++')

# python package to distribute
packages = build_helpers.find_submodules("./cecog", "cecog")

# special casing for system installation or py2exe bundle
if "py2exe" in sys.argv:
    dfiles = build_helpers.get_data_files(build_helpers.TARGET_BUNDLE)
    uifiles = build_helpers.find_uifiles('./cecog', build_helpers.TARGET_BUNDLE)
    dfiles.append(uifiles)
else:
    build_helpers.metadata['name'] = 'cellcognition'
    dfiles = build_helpers.get_data_files(build_helpers.TARGET_SYS,
                                          mpl_data=False)

if "bdist_wininst" in sys.argv:
    from distutils.sysconfig import get_python_lib
    dllpath = find_library("vigraimpex")
    # assuming all dlls in the same directory,
    # lib/site-packages is also windows specific
    dlls = (join("lib", "site-packages", "cecog", "ccore"),
            glob.glob(dllpath.replace("vigraimpex", "*")))
    dfiles.append(dlls)


setup(options = {'py2exe': py2exe_opts,
                 'build_rcc': pyrcc_opts,
                 'build_help': help_opts},
      cmdclass = {'build_rcc': build_helpers.BuildRcc,
                  'build_help': build_helpers.BuildHelp,
                  'build': build_helpers.Build},
      packages = packages,
      package_data = {'cecog': [join('gui', '*.ui'),
                                join('gui', 'helpbrowser', '*.ui')]},
      data_files = dfiles,
      # switch between console and window to debug
      windows = [{'script': join('scripts', 'CecogAnalyzer.py'),
                  'icon_resources': [(1, 'resources\cecog_analyzer_icon.ico')]
                  }],
      ext_modules = [ccore],
      **build_helpers.metadata)
