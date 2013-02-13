# -*- coding: utf-8 -*-
"""
setup_ccore.py - distutuils setup for ccore extension module

This setup file is currently for testing purpose. The goal is to remove
the separate compilation of the extension module. The script builds just the
c++ extension module so far, without the need of cmake

Missing stuff:
-) platform independent search routines for includes andl libs
-) platform specific compiler opttions such as optimization etc..

If your msvc is part of the Microsoft SDKs run:
1) c:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd /x64
2) set VS90COMNTOOLS=%VS100COMNTOOLS%
3) python setup_ccore.py build

1) and 2) can be skipped if you are using VS 2010 Professional
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = 'WTFL'

import sys
from os.path import join
from distutils.core import setup, Extension

import numpy.distutils

if sys.platform.startswith('win32'):
    includes = ['c:/python27/include',
                'C:/Python27/Lib/site-packages/numpy/core/include',
                'c:/lib/include',
                'c:/vigra/include',
                'csrc/include']
    compiler_opts = ["/bigobj", "/EHsc"]
    libraries = ['boost_python-vc100-mt-1_45',
                 'libtiff',
                 'vigraimpex']
    library_dirs = ['c:/lib/lib']

else: #currently just linux.
    includes = [#'/usr/include/python2.7',
                '/Users/hoefler/sandbox/lib-static/include',
                '/cecoglibs/vigra/include/',
                'csrc/include'] + \
                numpy.distutils.misc_util.get_numpy_include_dirs()
    library_dirs = ['/Users/hoefler/sandbox/lib-static/lib',
                    '/cecoglibs/vigra/lib']
    compiler_opts = ['-O3', '-fPIC', '-arch x86_64']
    libraries = ['boost_python', 'tiff', 'vigraimpex']


sources = [join('csrc','src', 'wrapper','cecog.cxx')]

cecog = Extension('cecog.ccore._cecog',
                  sources=sources,
                  include_dirs=includes,
                  libraries=libraries,
                  library_dirs=library_dirs,
                  language='c++')

try:
    cecog.extra_compile_args.extend(compiler_opts)
except NameError:
    pass

setup (name = 'cecog',
       version = '1.4.0',
       description = 'This is a demo package',
       author = 'Rudolf Hoefler',
       author_email = 'rudolf.hoefler@gmail.com',
       url = 'http://cellcognition.com',
       ext_modules = [cecog])
