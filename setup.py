"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
              See trunk/AUTHORS.txt for author contributions.
"""
# many thanks for inspiration to F. Oliver Gathmann from the pyVIGRA project

import ConfigParser
import copy
import glob
import os
import sys

from distutils.sysconfig import (get_config_vars,
                                 get_python_inc)
from build_ext import build_ext
from setuptools import (Extension,
                        Library)
from setuptools import setup

#
#
#

DEFAULT_VIGRA_VERSION = 'vigra1.6.0'
DEFAULT_BOOST_VERSION = 'boost_1_39_0'
DEFAULT_PYVIGRA_VERSION = 'pyvigra'

#
# Utility functions.
#

def tempsyspath(path):
    def decorate(f):
        def handler():
            sys.path.insert(0, path)
            value = f()
            del sys.path[0]
            return value
        return handler
    return decorate


def read_pkginfo_file(setup_file):
    path = os.path.dirname(setup_file)
    @tempsyspath(path)
    def _import_pkginfo_file():
        if '__pgkinfo__' in sys.modules:
            del sys.modules['__pkginfo__']
        return __import__('__pkginfo__')
    return _import_pkginfo_file()


def on_posix():
    return os.name.startswith('posix')


def on_windows():
    return sys.platform.startswith('win')


def parse_defines(macro_def_string):
    if macro_def_string != '':
        defs = set([(macro.strip(), 1) for macro in macro_def_string.split(',')])
    else:
        defs = set([])
    return defs


def get_home():
    if on_windows():
        home_path = os.getenv('USERPROFILE')
    else:
        home_path = os.getenv('HOME')
    return home_path


def prefix_home(path):
    return os.path.join(get_home(), path)


def get_include_dirs(option_name, parser):
    option_string = parser.get('build_ext', option_name)
    if option_string == '':
        include_dirs = [prefix_home('include')]
    else:
        include_dirs = option_string.split(os.pathsep)
    return include_dirs


def get_lib_dir(option_name, parser):
    option_string = parser.get('build_ext', option_name)
    if option_string == '':
        lib_dir = prefix_home('lib')
    else:
        lib_dir = option_string.strip()
    return lib_dir


def get_lib(option_name, parser, default_name):
    option_string = parser.get('build_ext', option_name)
    if option_string == '':
        if on_windows():
            lib = 'lib%s' % default_name
        else:
            lib = default_name
    else:
        lib = option_string
    return lib


# Don't continue unless we are on POSIX or on Windows.
if not (on_posix() or on_windows()):
    raise NotImplementedError('Unsupported OS (%s)' % os.name)

# Parse setup.cfg.
parser = ConfigParser.ConfigParser()
parser.read('setup.cfg')


# Get interpreter include directories.
python_include_dirs = set([get_python_inc()])
if not on_windows():
    python_library_dirs = set([get_config_vars()['LIBDIR']])
else:
    python_library_dirs = set([get_config_vars()['LIBDEST']])


pyvigra_root_dir = parser.get('build_ext', 'pyvigra_dir')
if pyvigra_root_dir == '':
    # Try with default VIGRA version prepended by <HOME>/src directory.
    pyvigra_root_dir = prefix_home(os.path.join('src', DEFAULT_PYVIGRA_VERSION))
pyvigra_source_dir = os.path.join(pyvigra_root_dir, 'csrc', 'src')
pyvigra_pysource_dir = os.path.join(pyvigra_root_dir, 'pysrc', 'pyvigra')
pyvigra_include_dirs = set([pyvigra_source_dir,
                            os.path.join(pyvigra_root_dir, 'csrc', 'include')])
pyvigra_library_dirs = set([pyvigra_pysource_dir,
                            get_lib_dir('tiff_library_dir', parser),
                            ])
pyvigra_libraries = set(['boost_python',
                         get_lib('tiff_lib', parser, 'tiff'),
                         ])
pyvigra_include_dirs.update(
                           get_include_dirs('tiff_include_dir', parser)
                           )

parser_pyvigra = ConfigParser.ConfigParser()
parser_pyvigra.read(os.path.join(pyvigra_root_dir, 'setup.cfg'))

# Check for numpy.
for flag in parser_pyvigra.get('build_ext', 'pyvigra_define').split(','):
    if flag == 'PYVIGRA_HAS_NUMPY':
        import numpy
        numpy_include_dir = numpy.lib.get_include()
        python_include_dirs.add(numpy_include_dir)

# Prepare VIGRA library.
vigra_root_dir = parser_pyvigra.get('build_ext', 'vigra_dir')
if vigra_root_dir == '':
    # Try with default VIGRA version prepended by <HOME>/src directory.
    vigra_root_dir = prefix_home(os.path.join('src', DEFAULT_VIGRA_VERSION))
vigra_source_dir = os.path.join(vigra_root_dir, 'src', 'impex')
vigra_include_dirs = set([vigra_source_dir,
                          os.path.join(vigra_root_dir, 'include')])
vigra_define_macros = parse_defines(parser_pyvigra.get('build_ext', 'vigra_define'))
print vigra_define_macros

# Prepare boost_python library.
boost_root_dir = parser_pyvigra.get('build_ext', 'boost_dir')
if boost_root_dir == '':
    # Try with default boost version prepended by <HOME>/src directory.
    boost_root_dir = prefix_home(os.path.join('src', DEFAULT_BOOST_VERSION))
boost_include_dirs = set([boost_root_dir]).union(python_include_dirs)
if on_posix():
    boost_library_dirs = set()
else:
    boost_library_dirs = python_library_dirs
boost_define_macros =  parse_defines(parser_pyvigra.get('build_ext', 'boost_define'))
if on_posix():
    boost_extra_link_args = set()
else:
    boost_extra_link_args = set(['/SUBSYSTEM:CONSOLE',
                                 '/NODEFAULTLIB:"libc"',
                                 ])
    boost_define_macros.update(set([('BOOST_ALL_DYN_LINK', '1'),
                                    ('BOOST_PYTHON_SOURCE', '1'),
#                                    ('BOOST_PYTHON_NO_LIB', '1'),
                                    ('BOOST_AUTO_LINK_NOMANGLE', '1'),
                                    ('_CRT_SECURE_NO_DEPRECATE', '1')
                                    ]))

# Prepare cecog python wrapper library.
cecog_root_dir = 'csrc'
cecog_source_dir = os.path.join(cecog_root_dir, 'src')
cecog_python_source_dir = os.path.join(cecog_source_dir, 'python')
cecog_sources = glob.glob(os.path.join(cecog_source_dir, '*.cxx')) +\
                glob.glob(os.path.join(cecog_python_source_dir, 'cecog*.cxx'))
cecog_libraries = pyvigra_libraries.copy()
cecog_include_dirs = python_include_dirs.union(
                        vigra_include_dirs).union(
                            boost_include_dirs).union(
                                pyvigra_include_dirs).union(
                                    [os.path.join(cecog_root_dir, 'include')])
cecog_define_macros = parse_defines(parser.get('build_ext',
                                               'cecog_define')).union(
                           parse_defines(parser_pyvigra.get('build_ext',
                                                            'pyvigra_define'))).union(
                               vigra_define_macros).union(
                                   [('DEBUG', '1'),
                                    ('BOOST_PYTHON_DYNAMIC_LIB', 1)])

if on_posix():
    cecog_library_dirs = pyvigra_library_dirs.copy()
    cecog_extra_link_args = set()
else:
    cecog_library_dirs = \
                    pyvigra_library_dirs.copy().union(python_library_dirs)
#    pyvigra_libraries.add('kernel32')
    cecog_extra_link_args = set(['/SUBSYSTEM:CONSOLE',
                                 '/NODEFAULTLIB:"libc"',
                                ])
#    cecog_define_macros.update(set([('BOOST_ALL_DYN_LINK', '1'),
#                                     ('BOOST_PYTHON_SOURCE', '1'),
#                                     ('BOOST_AUTO_LINK_NOMANGLE', '1'),
#                                     ('_CRT_SECURE_NO_DEPRECATE', '1')
#                                     ]))
cecog_lib = Library('cecog.ccore.cecog',
                    sources=cecog_sources,
                    libraries=list(cecog_libraries),
                    include_dirs=list(cecog_include_dirs),
                    library_dirs=list(cecog_library_dirs),
                    extra_link_args=list(cecog_extra_link_args),
                    define_macros=list(cecog_define_macros))


# Prepare _pyvigra extension.
cecog_ext_sources = [os.path.join(cecog_python_source_dir, '_cecog.cxx')]
cecog_ext_libraries = set(['cecog'])
cecog_ext_include_dirs = cecog_include_dirs.copy()
cecog_ext_library_dirs = cecog_library_dirs.copy()
cecog_ext_extra_link_args = cecog_extra_link_args.copy()
cecog_ext_macros = set()
#cecog_ext_macros = [('BOOST_ALL_DYN_LINK', '1'),
#                      ('BOOST_PYTHON_SOURCE', '1'),
#                    ('BOOST_AUTO_LINK_NOMANGLE', '1'),
#                    ('_CRT_SECURE_NO_DEPRECATE', '1')
#                    ]
cecog_ext = Extension('cecog.ccore._cecog',
                      cecog_ext_sources,
                      libraries=list(cecog_ext_libraries),
                      include_dirs=list(cecog_ext_include_dirs),
                      library_dirs=list(cecog_ext_library_dirs),
                      extra_link_args=list(cecog_ext_extra_link_args),
                      define_macros=list(cecog_ext_macros)
                      )

class cecog_build_ext(build_ext):
    user_options = build_ext.user_options[:]
    user_options.extend([
        ('pyvigra-dir', None, 'pyVIGRA distribution root (trunk) directory'),
        ('vigra-dir', None, 'VIGRA distribution root directory'),
        ('vigra-define', None, 'macro definitions for VIGRA'),
        ('boost-dir', None, 'boost distribution root directory'),
        ('boost-define', None, 'macro definitions for boost.python'),
        ('tiff-include-dir', None, 'TIFF include dir'),
        ('tiff-library-dir', None, 'TIFF library dir'),
        ('tiff-lib', None, 'TIFF library name'),
        ('cecog-define', None, 'macro definitions for cecog'),
        ('cecog-copy-libs', None, 'path to copy extra libs to'),
        ])

    def initialize_options(self):
        # valid initialization function pylint: disable-msg=W0201
        build_ext.initialize_options(self)
        self.pyvigra_dir = None
        self.vigra_dir = None
        self.vigra_define = None
        self.boost_dir = None
        self.boost_define = None
        self.jpeg_include_dir = None
        self.jpeg_library_dir = None
        self.jpeg_lib = None
        self.png_include_dir = None
        self.png_library_dir = None
        self.png_lib = None
        self.tiff_include_dir = None
        self.tiff_library_dir = None
        self.tiff_lib = None
        self.fft_include_dir = None
        self.fft_library_dir = None
        self.fft_lib = None
        self.cecog_define = None
        self.cecog_copy_libs = None
        # pylint: enable-msg=W0201


if on_windows():
    from distutils.ccompiler import (compiler_class,
                                     new_compiler)
    from distutils.file_util import copy_file
    from distutils import msvccompiler

    class MSVCExpressCompiler(msvccompiler.MSVCCompiler):
        def initialize(self):
            msvccompiler.MSVCCompiler.initialize(self)
            self.compile_options = ['/nologo', '/O2', '/Ot', '/Ob2', '/arch:SSE2',
                                    '/MD', '/W1',
                                    '/EHsc' , '/DNDEBUG', '/bigobj',
                                    '/Gy', '/GF', '/FD', '/Zm400']
            self.compile_options_debug = ['/nologo', '/Od', '/MDd',
                                          '/W3', '/EHsc', '/Z7',
                                          '/D_DEBUG']

        def link(self,
                 target_desc,
                 objects,
                 output_filename,
                 output_dir=None,
                 libraries=None,
                 library_dirs=None,
                 runtime_library_dirs=None,
                 export_symbols=None,
                 debug=0,
                 extra_preargs=None,
                 extra_postargs=None,
                 build_temp=None,
                 target_lang=None):
            msvccompiler.MSVCCompiler.link(
                            self, target_desc, objects, output_filename,
                            output_dir=output_dir,
                            libraries=libraries,
                            library_dirs=library_dirs,
                            runtime_library_dirs=runtime_library_dirs,
                            export_symbols=export_symbols,
                            debug=debug,
                            extra_preargs=extra_preargs,
                            extra_postargs=extra_postargs,
                            build_temp=build_temp,
                            target_lang=target_lang)
            if not export_symbols is None:
                # Copy the export .lib and .exp files in case we need them
                # later.
                output_dirname = os.path.dirname(output_filename)
                (dll_name, dll_ext) = os.path.splitext(
                                          os.path.basename(output_filename))
                implib_file = self.library_filename(dll_name)
                input_dirname = os.path.dirname(objects[0])
                if os.path.isfile(os.path.join(input_dirname, implib_file)):
                    copy_file(os.path.join(input_dirname, implib_file),
                              os.path.join(output_dirname, implib_file))
                exp_file = "%s.exp" % os.path.splitext(implib_file)[0]
                if os.path.isfile(os.path.join(input_dirname, exp_file)):
                    copy_file(os.path.join(input_dirname, exp_file),
                              os.path.join(output_dirname, exp_file))


    # FIXME: this is hacky, but currently distutils expects custom compilers
    #        in the distutils directory, which we may have no write access to
    msvccompiler.MSVCExpressCompiler = MSVCExpressCompiler
    compiler_class['msvcexpress'] = \
        ('msvccompiler', 'MSVCExpressCompiler',
         'Microsoft Visual C++ Express Edition / Visual Studio 2005')

# Prepare setup options.
pkginfo = read_pkginfo_file(__file__)
options = dict(name=pkginfo.name,
               version=pkginfo.version,
               author=pkginfo.author,
               author_email=pkginfo.author_email,
               license=pkginfo.license,
               description=pkginfo.description,
               long_description=pkginfo.long_description,
               url=pkginfo.url,
               download_url=pkginfo.download_url,
               classifiers=pkginfo.classifiers,
               package_dir=pkginfo.package_dir,
               packages=pkginfo.packages,
               platforms=pkginfo.platforms,
               provides=pkginfo.provides)
options['ext_modules'] = [cecog_lib,
                          cecog_ext]
options['cmdclass'] = dict(build_ext=cecog_build_ext)

# Run setup.
setup(**options)

import shutil
dest = parser.get('build_ext', 'cecog_copy_libs')
if dest != '':
    target = 'pysrc/cecog/ccore'
    for name in os.listdir(target):
        if os.path.splitext(name)[1] == '.dylib':
            name_path = os.path.join(target, name)
            print "Copy %s -> %s" % (name_path, dest)
            shutil.copy(name_path, dest)

