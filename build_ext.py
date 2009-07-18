"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""
# many thanks for inspiration to F. Oliver Gathmann from the pyVIGRA project


from distutils.command.build_ext import build_ext as _du_build_ext
try:
    # Attempt to use Pyrex for building extensions, if available
    # pylint: disable-msg=F0401
    from Pyrex.Distutils.build_ext import build_ext as _build_ext
except ImportError:
    _build_ext = _du_build_ext

import os, sys
import subprocess
from distutils.file_util import copy_file
from setuptools.extension import Library
from distutils.ccompiler import new_compiler
from distutils.sysconfig import customize_compiler, get_config_var
get_config_var("LDSHARED")  # make sure _config_vars is initialized
from distutils.sysconfig import _config_vars
from distutils import log
from distutils.errors import *


have_rtld = False
use_stubs = False
libtype = 'shared'

if sys.platform == "darwin":
    use_stubs = False
elif os.name != 'nt':
    try:
        from dl import RTLD_NOW
        have_rtld = True
        use_stubs = True
    except ImportError:
        pass

def if_dl(s):
    if have_rtld:
        return s
    return ''



class build_ext(_build_ext):
    def run(self):
        """Build extensions in build directory, then copy if --inplace"""
        old_inplace, self.inplace = self.inplace, 0
        _build_ext.run(self)
        self.inplace = old_inplace
        if old_inplace:
            self.copy_extensions_to_source()

    def copy_extensions_to_source(self):
        build_py = self.get_finalized_command('build_py')
        for ext in self.extensions:
            fullname = self.get_ext_fullname(ext.name)
            filename = self.get_ext_filename(fullname)
            modpath = fullname.split('.')
            package = '.'.join(modpath[:-1])
            package_dir = build_py.get_package_dir(package)
            dest_filename = os.path.join(package_dir,os.path.basename(filename))
            src_filename = os.path.join(self.build_lib,filename)

            # Always copy, even if source is older than destination, to ensure
            # that the right extensions for the current Python/platform are
            # used.
            copy_file(
                src_filename, dest_filename, verbose=self.verbose,
                dry_run=self.dry_run
            )
            # library symlinks for the source dir
            if isinstance(ext, Library):
                self.provide_dependent_libraries(ext, package_dir)

            if ext._needs_stub:
                self.write_stub(package_dir or os.curdir, ext, True)


    if _build_ext is not _du_build_ext and not hasattr(_build_ext,'pyrex_sources'):
        # Workaround for problems using some Pyrex versions w/SWIG and/or 2.4
        def swig_sources(self, sources, *otherargs):
            # first do any Pyrex processing
            sources = _build_ext.swig_sources(self, sources) or sources
            # Then do any actual SWIG stuff on the remainder
            return _du_build_ext.swig_sources(self, sources, *otherargs)



    def get_ext_filename(self, fullname):
        filename = _build_ext.get_ext_filename(self,fullname)
        ext = self.ext_map[fullname]
        if isinstance(ext,Library):
            fn, ext = os.path.splitext(filename)
            return self.shlib_compiler.library_filename(fn,libtype)
        elif use_stubs and ext._links_to_dynamic:
            d,fn = os.path.split(filename)
            return os.path.join(d,fn)
        else:
            return filename

    def initialize_options(self):
        _build_ext.initialize_options(self)
        self.shlib_compiler = None
        self.shlibs = []
        self.ext_map = {}

    def finalize_options(self):
        _build_ext.finalize_options(self)
        self.extensions = self.extensions or []
        self.check_extensions_list(self.extensions)
        self.shlibs = [ext for ext in self.extensions
                        if isinstance(ext,Library)]
        if self.shlibs:
            self.setup_shlib_compiler()
        for ext in self.extensions:
            ext._full_name = self.get_ext_fullname(ext.name)
        for ext in self.extensions:
            fullname = ext._full_name
            self.ext_map[fullname] = ext
            ltd = ext._links_to_dynamic = \
                self.shlibs and self.links_to_dynamic(ext) or False
            ext._needs_stub = ltd and use_stubs and not isinstance(ext,Library)
            filename = ext._file_name = self.get_ext_filename(fullname)
            libdir = os.path.dirname(os.path.join(self.build_lib,filename))
            if ltd and libdir not in ext.library_dirs:
                ext.library_dirs.append(libdir)
            if ltd and use_stubs and os.curdir not in ext.runtime_library_dirs:
                ext.runtime_library_dirs.append(os.curdir)

    def setup_shlib_compiler(self):
        compiler = self.shlib_compiler = new_compiler(
            compiler=self.compiler, dry_run=self.dry_run, force=self.force
        )
        if sys.platform == "darwin":
            tmp = _config_vars.copy()
            try:
                # XXX Help!  I don't have any idea whether these are right...
                _config_vars['LDSHARED'] = \
                       "gcc -Wl,-x -dynamiclib -undefined dynamic_lookup "  \
                       "-headerpad_max_install_names"
                _config_vars['CCSHARED'] = " -dynamiclib"
                _config_vars['SO'] = ".dylib"
                customize_compiler(compiler)
            finally:
                _config_vars.clear()
                _config_vars.update(tmp)
        else:
            customize_compiler(compiler)

        if self.include_dirs is not None:
            compiler.set_include_dirs(self.include_dirs)
        if self.define is not None:
            # 'define' option is a list of (name,value) tuples
            for (name,value) in self.define:
                compiler.define_macro(name, value)
        if self.undef is not None:
            for macro in self.undef:
                compiler.undefine_macro(macro)
        if self.libraries is not None:
            compiler.set_libraries(self.libraries)
        if self.library_dirs is not None:
            compiler.set_library_dirs(self.library_dirs)
        if self.rpath is not None:
            compiler.set_runtime_library_dirs(self.rpath)
        if self.link_objects is not None:
            compiler.set_link_objects(self.link_objects)

        # hack so distutils' build_extension() builds a library instead
        compiler.link_shared_object = link_shared_object.__get__(compiler)


    def provide_dependent_libraries(self, ext, dest_dir=None):
        # hacky solution to provide ext libraries vis symlinks
        if dest_dir is None:
            dest_dir = os.path.join(self.build_lib,
                                    os.path.split(ext._file_name)[0])
        for lib_name in ext.libraries:
            for lib_dir in ext.library_dirs:
                filename = 'lib%s.dylib' % lib_name
                filepath = os.path.join(lib_dir, filename)
                dest = os.path.join(dest_dir, filename)
                if (os.path.isfile(filepath) and
                    not os.path.islink(dest) and
                    not os.path.isfile(dest)):
                    os.symlink(filepath, dest)

    def get_export_symbols(self, ext):
        if isinstance(ext,Library):
            return ext.export_symbols
        return _build_ext.get_export_symbols(self,ext)

    def build_extension(self, ext):
        _compiler = self.compiler
        try:
            if isinstance(ext,Library):
                self.compiler = self.shlib_compiler
            _build_ext.build_extension(self,ext)

            # library symlinks for the build directory
            if isinstance(ext,Library):
                self.provide_dependent_libraries(ext)
            if ext._needs_stub:
                self.write_stub(
                    self.get_finalized_command('build_py').build_lib, ext
                )
        finally:
            self.compiler = _compiler

    def links_to_dynamic(self, ext):
        """Return true if 'ext' links to a dynamic lib in the same package"""
        # XXX this should check to ensure the lib is actually being built
        # XXX as dynamic, and not just using a locally-found version or a
        # XXX static-compiled version
        libnames = dict.fromkeys([lib._full_name for lib in self.shlibs])
        pkg = '.'.join(ext._full_name.split('.')[:-1]+[''])
        for libname in ext.libraries:
            if pkg+libname in libnames: return True
        return False

    def get_outputs(self):
        outputs = _build_ext.get_outputs(self)
        optimize = self.get_finalized_command('build_py').optimize
        for ext in self.extensions:
            if ext._needs_stub:
                base = os.path.join(self.build_lib, *ext._full_name.split('.'))
                outputs.append(base+'.py')
                outputs.append(base+'.pyc')
                if optimize:
                    outputs.append(base+'.pyo')
        return outputs

    def write_stub(self, output_dir, ext, compile=False):
        log.info("writing stub loader for %s to %s",ext._full_name, output_dir)
        # when building with --inplace it can happen that the output dir
        # ends and the extension full name starts with the package path,
        # in which case we strip it from the extension name.
        ext_modname_parts = ext._full_name.split('.')
        output_path = output_dir.split(os.path.sep)
        for idx in range(len(ext_modname_parts)):
            if idx+1 < len(output_path):
                if output_path[idx+1] != ext_modname_parts[idx]:
                    break
        ext_modname_parts = ext_modname_parts[idx:-1] +\
                            ["load%s.py" % ext_modname_parts[-1]]
        stub_file = os.path.join(output_dir, *ext_modname_parts)
        if os.path.exists(stub_file) and not self.dry_run:
            os.unlink(stub_file)
        if not self.dry_run:
            f = open(stub_file,'w')
            lines = [
                     "import os",
                     "print __file__",
                     "old_dir = os.getcwd()",
                     "os.chdir(os.path.dirname(__file__))",
                     "from %s import *" % ext._full_name.split('.')[-1],
                     "os.chdir(old_dir)",
                     ]
            f.write('\n'.join(lines))
            f.close()
            # import, read exported symbols, and write them into __all__.
#            ext_dir, ext_name = os.path.split(os.path.dirname(stub_file))
#            ext_modname = "%s.%s" % (ext_name, ext_modname_parts[-1])
#            sys.path.insert(0, ext_dir)
#            mod = __import__(ext_modname)
#            f = open(stub_file,'w')
#            predefined_names = ['__builtins__', '__name__', '__doc__']
#            all_names = [name for name in dir(mod)
#                         if not name in predefined_names]
#            all_name_string = '[%s]' % ',\n'.join(['"%s"' % name
#                                                   for name in all_names])
#            all_line = '__all__ = %s' % all_name_string
#            lines.insert(0, all_line)
#            lines.append('from %s import (%s)' %
#                         (ext_modname, ',\n'.join(all_names)))
#            f.write('\n'.join(lines))
#            f.close()
#            del sys.path[0]
        if compile:
            from distutils.util import byte_compile
            byte_compile([stub_file], optimize=0,
                         force=True, dry_run=self.dry_run)
            optimize = self.get_finalized_command('install_lib').optimize
            if optimize > 0:
                byte_compile([stub_file], optimize=optimize,
                             force=True, dry_run=self.dry_run)


if sys.platform=='darwin' or os.name=='nt':
    # Build shared libraries
    #
    def link_shared_object(self, objects, output_libname, output_dir=None,
        libraries=None, library_dirs=None, runtime_library_dirs=None,
        export_symbols=None, debug=0, extra_preargs=None,
        extra_postargs=None, build_temp=None, target_lang=None):
        self.link(
            self.SHARED_LIBRARY, objects, output_libname,
            output_dir, libraries, library_dirs, runtime_library_dirs,
            export_symbols, debug, extra_preargs, extra_postargs,
            build_temp, target_lang
        )
        if sys.platform == 'darwin':
            # use install_name_tool to make install path relative.
            install_filename = os.path.split(output_libname)[1]
            if not output_dir is None:
                install_filename = os.path.join(output_dir, install_filename)
            cmd = "install_name_tool -id %(ifn)s %(oln)s" \
                  % dict(ifn=install_filename, oln=output_libname)
            log.info(cmd)
            errorcode = os.system(cmd)
            if errorcode:
                raise DistutilsExecError("command failed: %s" % cmd)

            import shutil
            dest = "/Users/miheld/lib"
            log.info("Copy %s -> %s" % (output_libname, dest))
            shutil.copy(output_libname, dest)


else:
    # Build static libraries everywhere else
    libtype = 'static'

    def link_shared_object(self, objects, output_libname, output_dir=None,
        libraries=None, library_dirs=None, runtime_library_dirs=None,
        export_symbols=None, debug=0, extra_preargs=None,
        extra_postargs=None, build_temp=None, target_lang=None
    ):
        # XXX we need to either disallow these attrs on Library instances,
        #     or warn/abort here if set, or something...
        #libraries=None, library_dirs=None, runtime_library_dirs=None,
        #export_symbols=None, extra_preargs=None, extra_postargs=None,
        #build_temp=None

        assert output_dir is None   # distutils build_ext doesn't pass this
        output_dir,filename = os.path.split(output_libname)
        basename, ext = os.path.splitext(filename)
        if self.library_filename("x").startswith('lib'):
            # strip 'lib' prefix; this is kludgy if some platform uses
            # a different prefix
            basename = basename[3:]

        self.create_static_lib(
            objects, basename, output_dir, debug, target_lang
        )
