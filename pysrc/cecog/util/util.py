"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

import os
import bz2
import gzip
import types

def makedirs(path):
    """Recursively make directory if path doesn't already exist.
    If permission is not set, an exception (os.error) is raised.
    """
    path = os.path.normpath(path)
    if not os.path.isdir(path):
        os.makedirs(path)

def get_file_handle(filename, mode, guess_compression=True, compress_level=6):
    ext = os.path.splitext(filename)[1].lower()
    if guess_compression:
        if ext == '.gz':
            fh = gzip.GzipFile(filename, mode=mode,
                               compresslevel=compress_level)
        elif ext == '.bz2':
            fh = bz2.BZ2File(filename, mode=mode,
                             compresslevel=compress_level)
        else:
            fh = file(filename, mode)
    else:
        fh = file(filename, mode)
    return fh

def read_table(filename, has_column_names=True, skip=0, sep='\t',
               guess_compression=True):
    '''
    Reads a list of dicts ordered by header_names to file.
    Unfortunately Python's csv is unable of writing headers.
    '''
    f = get_file_handle(filename, 'rbU', guess_compression=guess_compression)
    for i in range(skip):
        f.readline()
    if has_column_names:
        column_names = f.readline().split(sep)
        column_names = [x.strip() for x in column_names]
    else:
        column_names = None
    rows = []
    for line in f:
        items = line.split(sep)
        items = [x.strip() for x in items]
        if column_names is None:
            column_names = range(len(items))
        rows.append(dict(zip(column_names, items)))
    f.close()
    return column_names, rows

def write_table(filename, rows, column_names=None, sep='\t',
                guess_compression=True):
    '''
    Write a list of dicts ordered by header_names to file, or a list of lists
    if no column_names are specified.

    Unfortunately Python's csv is unable of writing headers
    (changed in Python 2.7)
    '''
    f = get_file_handle(filename, 'wb', guess_compression=guess_compression)
    if not column_names is None:
        f.write('%s\n' % sep.join(column_names))
        for row in rows:
            f.write('%s\n' % sep.join([str(row[n]) for n in column_names]))
    else:
        for row in rows:
            if type(row) == types.DictType:
                func = lambda x: x.values()
            else:
                func = lambda x: x
            f.write('%s\n' % sep.join(map(str, func(row))))
    f.close()

def unlist(a):
    b = []
    for x in a:
        b += x
    return b

def yesno(state):
    return 'yes' if state else 'no'

def print_memory_increase(func):
    try:
        import psutil
        pid = os.getpid()
        p = psutil.Process(pid)
        def wrapper(*arg, **kwargs):
            m1 = p.get_memory_info().rss/1024.0/1024.0
            res = func(*arg, **kwargs)
            m2 = p.get_memory_info().rss/1024.0/1024.0
            name = str(func.__class__) + '\t' + \
                func.func_name if hasattr(func, '__class__') else func.func_name
            print '%s\t%6.2f\t%6.2f\t%6.2f' % (name, (m2-m1), m1, m2)
            return res
        return wrapper
    except:
        return runc
