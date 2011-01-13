"""
File handling utilities.

FIXME: the various  C{on_*} calls are ugly; consider factoring this out into
       platform-specific subpackages.

FOG 08.2001
"""

__docformat__ = "epytext"

__author__ = "F Oliver Gathmann"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['collect_files',
           'collect_files_by_suffix',
           'collect_files_by_regex',
           'common_prefix',
           'common_postfix',
           'compare_file_sizes',
           'compare_file_stats',
           'copy_files',
           'create_link',
           'delete_files',
           'delete_log_files',
           'file_name_root',
           'file_name_ext',
           'file_is_locked',
           'get_mod_time_string',
           'is_executable',
           'is_readable',
           'is_writable',
           'lock_file',
           'overwrite_prompt',
           'safe_mkdirs',
           'strip_prefix',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import glob
import os
import re
import shutil
import stat
import sys
import time
from subprocess import (Popen,
                        PIPE)

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.errors import IllegalArgumentError
from pdk.platform import (on_posix,
                          on_windows)

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# functions:
#

def file_name_root(file_path):
    """
    Returns the root name of the given file path.

    The root of a file name or full path is obtained by stripping the
    directory and the extension from it.

    @param file_path: path to return the root name
    @type file_path: string
    @return: name root (string)
    """
    return os.path.splitext(os.path.basename(file_path))[0]


def file_name_ext(file_path):
    """
    Returns the extension of the given file path.

    @param file_path: path to return the extension for
    @type file_path: string
    @return: extension (string)
    """
    return os.path.splitext(os.path.basename(file_path))[1]


def get_mod_time_string(file_name, format="%Y-%b-%d %H:%M"):
    """
    Returns the modification time of a file as a formatted string.

    @param file_name: name of the file to obtain the modification time for
    @type file_name: string
    @param format: date/time format
    @type format: string
    @return: formatted date-time string (string)
    """
    mod_time = time.localtime(os.path.getmtime(file_name))
    return time.strftime(format, mod_time)


def common_prefix(*paths):
    """
    Finds the common prefix for the given paths.

    @param paths: paths to check for a common prefix
    @type paths: variable-length tuple of strings
    @return: common prefix path of all the given paths (string) or the
      empty string, if there is no common prefix
    @note: this function, unlike its counterpart in os.path, does a
      C{os.path.normpath} on each path prior to the comparison so that
      C{/home/user/../../vitaldata} and C{/home/user} do I{not} have a common
      prefix!
    @note: relative and absolute paths are distinguished - C{/home/user}
      does not have a common prefix with C{home/user}
    @raise IllegalArgumentError: if less than two paths were passed
    """
    def compare(str1, str2):
        if str1 == str2:
            result = str2
        else:
            result = None
        return result
    if len(paths) < 2:
        raise IllegalArgumentError('need at least two paths to compare')
    std_paths = [os.path.normpath(os.path.normcase(path)).split(os.sep)
                 for path in paths]
    if std_paths:
        min_length = min([len(path) for path in std_paths])
        if min_length == 0:
            cmn_prf = ''
        else:
            all_equal = True
            count = 0
            for count in range(min_length):
                if reduce(compare,
                          [path[count] for path in std_paths]) is None:
                    all_equal = False
                    break
            if count == min_length-1 and all_equal:
                count += 1
            cmn_prf = os.sep.join(paths[0].split(os.sep)[:count])
    else:
        cmn_prf = ''
    return cmn_prf


def common_postfix(*paths):
    """
    Finds the common postfix for the given paths.

    Calls L{common_prefix} on the reversed input paths.

    @param paths: paths to check for a common postfix
    @type paths: variable-length tuple of strings
    @return: common postfix path of all the given paths (string) or the
      empty string, if there is no common postfix
    """
    split_paths = \
     [os.path.normpath(os.path.normcase(path)).rstrip(os.sep).split(os.sep)
      for path in paths]
    prefix = common_prefix(*[os.sep.join(reversed(path_tokens)) # pylint: disable-msg=W0142
                             for path_tokens in split_paths])
    return os.sep.join(reversed(prefix.split(os.sep)))


def compare_file_stats(first_file_name, second_file_name,
                       file_stat=stat.ST_SIZE):
    """
    Compares the two specified files with respect to the specified file
    stats.

    @param first_file_name: first file to compare
    @type first_file_name: string
    @param second_file_name: second file to compare
    @type second_file_name: string
    @param file_stat: file stat to compare by; defaults to file size
    @type file_stat: one of the L{stat}.C{ST*} constants
    """
    return os.stat(first_file_name)[file_stat] == \
                                        os.stat(second_file_name)[file_stat]


def compare_file_sizes(first_file_name, second_file_name):
    """
    Compares the sizes of the two specified files.

    @param first_file_name: first file to compare
    @type first_file_name: string
    @param second_file_name: second file to compare
    @type second_file_name: string
    @return: C{True}, if both files have equal length, or C{False}
    """
    return compare_file_stats(first_file_name, second_file_name)


def strip_prefix(prefix_path, path):
    """
    Strips the given prefix from the given file path.

    If the given prefix path is I{not} a prefix of the given path, the
    path is returned unchanged.

    @param prefix_path: prefix to strip off
    @type prefix_path: string
    @param path: path to strip the prefix from
    @type path: string
    @return: stripped path (string)
    """
    std_prefix_path = os.path.normpath(os.path.normcase(prefix_path))
    std_path = os.path.normpath(os.path.normcase(path))
    if common_prefix(std_prefix_path, std_path) == std_prefix_path:
        len_prefix = std_prefix_path.count(os.sep) + 1
        stripped_path = os.sep.join(std_path.split(os.sep)[len_prefix:])
    else:
        stripped_path = path
    return stripped_path


def collect_files(start_dir, extensions,
                 absolute=False, follow=False, recursive=True, exclude=None,
                 ignore_case=False, force_python=True):
    """
    Collects all files that have any of the given extensions from a
    directory tree.

    @param start_dir: directory where to start collecting
    @type start_dir: string
    @param extensions: file extensions to collect. If this
    @type extensions: list of strings
    @param absolute: if set, absolute file names are returned
    @type absolute: Boolean
    @param follow: if set, symbolic links are resolved
    @type follow: Boolean
    @param recursive: if set, the search descends into subdirectories
    @type recursive: Boolean
    @param exclude: a regular expression specifying directories to skip
    @type exclude: string
    @return: list of collected file names (strings)
    """
    # compose the list of extension globs to match:
    if on_windows() or force_python:
        # process the directory exclusion regex:
        patterns = [ext[0] == '.' and '%s' % ext or '.%s' % ext
                    for ext in extensions]
        if ignore_case:
            # pylint: disable-msg=W0141
            patterns = map(lambda x: x.lower(), patterns)
        if not exclude is None:
            try:
                if ignore_case:
                    exclude_pat = re.compile(exclude. re.IGNORECASE)
                else:
                    exclude_pat = re.compile(exclude)
            except:
                raise IllegalArgumentError('regular expression for '
                                           'directories to exclude did not '
                                           'compile (%s)' % exclude)
        else:
            exclude_pat = None

        # local directory tree visitor function:
        def _visit_dir(params, cur_dir, cur_names):
            out_names, pats, strt_dir, excl_pat = params
            if not excl_pat is None and excl_pat.search(cur_dir):
                return
            for cur_name in cur_names:
                ext = os.path.splitext(cur_name)[1]
                if ignore_case:
                    ext = ext.lower()
                if ext in pats or '.*' in pats:
                    if strt_dir is None:
                        path = os.path.join(cur_dir, cur_name)
                    else:
                        path = os.path.join(strt_dir, cur_dir, cur_name)
                    out_names.append(os.path.normpath(path))
        file_names = []
        if not absolute:
            cur_dir = os.getcwd()
            if cur_dir != start_dir:
                os.chdir(os.path.join(start_dir, os.pardir))
            os.path.walk(os.path.basename(start_dir), _visit_dir,
                         (file_names, patterns, None, exclude_pat))
            if cur_dir != start_dir:
                os.chdir(cur_dir)
        else:
            os.path.walk(start_dir, _visit_dir,
                         (file_names, patterns,
                          os.getcwd(), exclude_pat))
    else:
        if ignore_case:
            name = '-iname'
            regex = '-iregex'
        else:
            name = '-name'
            regex = '-regex'

        patterns = [ext[0]=='.' and '*%s'%ext or '*.%s'%ext
                       for ext in extensions]
        find_options = []
        if follow:
            find_options.append('-follow')
        if recursive:
            if not exclude is None:
                find_options.extend([regex, exclude, '-prune', '-o'])
        else:
            find_options.extend(['-maxdepth', '1'])
        find_names = []
        for pattern in patterns:
            find_names.extend([name, pattern, '-o'])
        if len(patterns) > 0:
            del find_names[-1] # remove the last '-o'
        cmds = ['find', start_dir] + find_options + find_names
        child = Popen(cmds, stdout=PIPE, stderr=PIPE)
        file_names = [name.strip()
                      for name in child.stdout.readlines()]
        if child.wait() != 0:
            raise OSError(child.stderr.read())
    return file_names


def collect_files_by_suffix(start_dir, suffix):
    """
    Collects files with the given suffix in the tree starting from the given
    directory.

    This is a simple version of L{collect_files}.

    @param start_dir: directory where to start collecting
    @type start_dir: string
    @param suffix: file name suffix
    @type suffix: string
    """
    return collect_files(start_dir, [suffix],
                        absolute=False, follow=False,
                        recursive=True, exclude=None)


def collect_files_by_regex(start_dir, regex, extensions=None, absolute=False):
    """
    Collects files matching the given suffix in the tree starting from the given
    directory.

    This is a simple version of L{collect_files}.

    @param start_dir: directory where to start collecting
    @type start_dir: string
    @param regex: regular expression following the L{re} syntax
    @type regex: string
    @param extensions: list of file name extensions
    @type extensions: list
    @return: list of tuples containing found file_name and matching L{re}.object
    """
    if extensions is None:
        extensions = []
    file_names = collect_files(start_dir, extensions,
                              absolute=absolute, follow=False,
                              recursive=True, exclude=None)
    regex = re.compile(regex)
    results = []
    for name in file_names:
        match = regex.match(name)
        if not match is None:
            results.append((name, match))
    return results


def copy_files(file_names, target_dir, prompt=True):
    """
    Copies the specified files to the given target directory.

    @param file_names: names of the files to copy
    @type file_names: list of strings
    @param target_dir: target directory
    @type target_dir: Boolean
    @param prompt: if set, a console dialog is popped up in a file is about
      to be overwritten
    @type prompt: Boolean
    @note: in case the operation is aborted (by responding with "q" or "Q"
      to the confirmation dialog), I{no} file is copied at all
    """
    if prompt:
        for file_name in file_names:
            target_file_name = os.path.join(target_dir, file_name)
            if os.path.isfile(target_file_name):
                src_mod_time = get_mod_time_string(file_name)
                target_mod_time = get_mod_time_string(target_file_name)
                choice = raw_input('Replace file %s, modified on %s,\n'
                                   'with file %s, modified on %s\n'
                                   '[Y/N/A/Q] ?' %
                                   (target_file_name, target_mod_time,
                                    file_name, src_mod_time))
                if choice in 'Nn':
                    continue
                elif choice in 'Qq':
                    return # abort without copying anything
                elif choice in 'Aa':
                    break
    for file_name in file_names:
        target_file_name = os.path.join(target_dir, file_name)
        shutil.copy(file_name, target_dir)


def create_link(pointee, pointer):
    """
    Creates a link pointing to the given pointee with the given pointer name.

    On Posix systems, this will create a symbolic link, on Windows a C{.lnk}
    shortcut.

    Example: ::
    >>> # create a_link.lnk in C:\ pointing to moo.txt in My Documents:
    >>> create_link("C:\My Documents\moo.txt", "C:\a_link.txt")

    @param pointee: name of the file being pointed to
    @type pointee: string
    @param pointer: name of the new link
    @type pointer: string
    """
    if on_windows():
        # Windows only pylint: disable-msg=F0401
        from win32com.shell import shell
        import pythoncom
        shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink,
                                               None,
                                               pythoncom.CLSCTX_INPROC_SERVER,
                                               shell.IID_IShellLink)
        # Windows only pylint: enable-msg=F0401
        shortcut.SetPath(pointee)
        # make sure the link file has the .lnk extension:
        dirname, link_name = os.path.split(pointer)
        link_file_name = '%s.lnk' % os.path.splitext(link_name)[0]
        cur_dir = os.getcwd()
        if dirname:
            # changing the current working directory to be in the link dir:
            os.chdir(dirname)
        query_interface = shortcut.QueryInterface(pythoncom.IID_IPersistFile) # pylint: disable-msg=E1101
        query_interface.Save(link_file_name, 0)
        # changing back to the old directory:
        os.chdir(cur_dir)
    else:
        os.symlink(pointee, pointer) # POSIX only pylint: disable-msg=E1101


def is_readable(path):
    """
    Checks whether the given path is readable.

    @param path: path to check
    @type path: string
    @return: check result (Boolean)
    """
    return os.access(path, os.R_OK)


def is_writable(path):
    """
    checks whether the given path is writable.

    @param path: path to check
    @type path: string
    @return: check result (Boolean)
    """
    return os.access(path, os.W_OK)


def is_executable(path):
    """
    Checks whether the given path is executable.

    @param path: path to check
    @type path: string
    @return: check result (Boolean)
    """
    return os.access(path, os.X_OK)


def overwrite_prompt(file_name,
                    message='File "%s" already exists. Overwrite [Y/N]?'):
    """
    Prompts a console-type file overwrite dialog.

    @param file_name: name of the file about to be overwritten
    @type file_name: string
    @param message: message to show
    @type message: string
    @return: C{True}, if the file should be overwritten, or C{False}
    """
    do_overwrite = True
    if os.path.isfile(file_name):
        while True:
            sys.stdin.flush()
            choice = raw_input(message % file_name)
            if choice in 'YNyn':
                break
        if choice in 'Nn':
            do_overwrite = False
    return do_overwrite


def safe_mkdirs(path, prompt=False):
    """
    Safe version of the builtin L{os.mkdirs}.

    Checks if the path to create is writable; if yes, checks if it already
    exists; if yes, prompts if the existing path should be overwritten.

    @param path: path to create
    @type path: string
    @return: C{True} if the path was created, or C{False}
    """
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        # split path until existing directory is reached
        test_path = path
        while not os.path.isdir(test_path):
            test_path, pathB = os.path.split(test_path)
            # reached root
            if len(pathB) == 0:
                break
        # test existing directory for write permissions
        if not is_writable(test_path):
            is_ok = False
        else:
            if prompt:
                is_ok = overwrite_prompt('The requested path already exists. '
                                        'Overwrite [Y/N]?')
            else:
                is_ok = True
            if is_ok:
                # this function is not atomic, so another process could create
                # the folder in between.
                # if an IOError occurs but the folder exists, everything is
                # still ok, otherwise there are other errors which are raised
                try:
                    os.makedirs(path)
                except OSError as err:
                    if not os.path.isdir(path):
                        raise err
    else:
        is_ok = True
    return is_ok


def delete_files(directory, extension='*'):
    """
    Deletes the files matching the specified extension from the specified
    directory.

    @param directory: directory to remove files from
    @type directory: string
    @param extension: extension of the files to delete
    @type extension: string
    """
    for file_name in glob.glob(os.path.join(directory, "*.%s" % extension)):
        os.unlink(file_name)


def delete_log_files(directory, extension='log'):
    """
    Removes log files in the given directory. Calls L{delete_files}; see there
    for parameter details.
    """
    delete_files(directory, extension)


def lock_file(file_descriptor):
    """
    Cross-platform utility function for obtaining an exclusive lock on the
    given open file.

    Based on http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65203.

    @param file_descriptor: open file descriptor
    @type file_descriptor: file
    @raise IOError: if the file cannot be locked
    """
    if on_posix():
        import fcntl
        fcntl.lockf(file_descriptor, fcntl.LOCK_EX|fcntl.LOCK_NB)
    else:
        import pywintypes, win32con, win32file # pylint: disable-msg=F0401
        file_handle = win32file._get_osfhandle(file_descriptor.fileno()) # pylint: disable-msg=W0212
        flags = \
          win32con.LOCKFILE_EXCLUSIVE_LOCK|win32con.LOCKFILE_FAIL_IMMEDIATELY
        try:
            win32file.LockFileEx(file_handle, flags, 0, -0x10000,
                                 pywintypes.OVERLAPPED()) # pylint: disable-msg=E1101
        except win32file.error, oError:
            if oError.args[0] == 33: # somebody else (partly) locked the file
                raise IOError(*oError.args) # pylint: disable-msg=W0142
            else:
                raise # unexpected error code


def unlock_file(file_descriptor):
    """
    Cross-platform utility function for releasing the lock on the given
    open file.

    Based on http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65203.

    @param file_descriptor: open file descriptor
    @type file_descriptor: file
    """
    if on_posix():
        import fcntl
        fcntl.lockf(file_descriptor, fcntl.LOCK_UN)
    else:
        import pywintypes, win32file # pylint: disable-msg=F0401
        file_handle = win32file._get_osfhandle(file_descriptor.fileno()) # pylint: disable-msg=W0212
        win32file.UnlockFileEx(file_handle, 0, -0x10000,
                               pywintypes.OVERLAPPED()) # pylint: disable-msg=E1101


def file_is_locked(file_descriptor):
    """
    Cross-platform utility function to check if the given file is locked.

    @param file_descriptor: open file descriptor
    @type file_descriptor: file
    @return: check result (Boolean)
    """
    try:
        lock_file(file_descriptor)
        is_locked = False
    except IOError:
        is_locked = True
    else:
        unlock_file(file_descriptor)
    return is_locked
