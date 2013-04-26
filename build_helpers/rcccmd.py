"""
commands.py

Define new commands for the build process.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['Build', 'PyRcc']

import os
from os.path import isfile
from  distutils.core import Command
from  distutils.command.build import build as _build


class Build(_build):

    # compile qrc file before build starts
    def run(self):
        self.run_command('pyrcc')
        _build.run(self)


class PyRcc(Command):

    description = "Compile qt4-qrc files"
    user_options = [('pyrcc_exe=', 'b', 'Path to pyrcc4 executable'),
                    ('infile=', 'i', 'Input file'),
                    ('outfile=', 'o', 'Output file')]

    def initialize_options(self):
        self.pyrcc_exe = 'pyrcc4'
        self.infile = None
        self.outfile = None

    def finalize_options(self):
        if not isfile(self.infile):
            raise RuntimeError('file %s not found' %self.infile)

        if not self.outfile.endswith('.py'):
            raise RuntimeError("Check extension of the output file")

    def run(self):
        cmd = '%s -o %s %s' %(self.pyrcc_exe, self.outfile, self.infile)
        print "Compiling qrc file"
        os.system(cmd)
