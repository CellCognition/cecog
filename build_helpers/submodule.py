"""
submodule.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['find_submodules']

from os import listdir
from os.path import isdir, isfile, join, basename

def find_submodules(path, modname=None):
    """Search a given directory for submodules. If modname is given,
    the modname replaces the basename o the directory.
    (dirname.submodules -> modname.submodule)
    """

    modules = []

    if modname is None:
        modname = basename(path)

    if isfile(join(path, "__init__.py")):
        modules.append(modname)

    for dir in listdir(path):
        if isdir(join(path, dir)):
            subdir = join(path, dir)
            modules.extend(find_submodules(subdir, "%s.%s" %(modname, dir)))

    return modules


if __name__ == "__main__":
    print find_submodules("../cecog", "cecog")
