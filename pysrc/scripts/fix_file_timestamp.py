'''
Fix the mtime file information of a input path of images by a given timelapse value
based on the mtime of the first (oldest) file of any sub-directory starting with 'P'.

Used in rare cases when the file mtime info is broken, e.g. time sync problems on the microscope

'''

#-------------------------------------------------------------------------------
# standard library imports:
#
import os, sys, shutil

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.fileutils import safe_mkdirs

#-------------------------------------------------------------------------------
# cecog imports:
#

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#

#-------------------------------------------------------------------------------
# main:
#

path_in = sys.argv[1]
path_out = sys.argv[2]
timelapse = float(sys.argv[3])

for pos in os.listdir(path_in):

    path_in_pos = os.path.join(path_in, pos)
    path_out_pos = os.path.join(path_out, pos)

    if pos[0] != 'P':
        shutil.copytree(path_in_pos, path_out_pos)
        continue

    safe_mkdirs(path_out_pos)
    start = None

    for idx, filename in enumerate(os.listdir(path_in_pos)):
        path_in_pos_filename = os.path.join(path_in_pos, filename)
        path_out_pos_filename = os.path.join(path_out_pos, filename)
        shutil.copy2(path_in_pos_filename, path_out_pos)

        if start is None:
            stat = os.stat(path_out_pos_filename)
            start = stat.st_mtime

        stat = os.stat(path_out_pos_filename)
        atime = stat.st_atime

        mtime = start + idx * timelapse

        os.utime(path_out_pos_filename, (atime, mtime))




