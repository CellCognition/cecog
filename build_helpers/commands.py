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
    """Custom build command for distutils to have the qrc files compiled before
    before the build process.
    """

    def run(self):
        self.run_command('pyrcc')
        _build.run(self)


class PyRcc(Command):
    """Custom command to compile Qt4-qrc files"""

    description = "Compile qt4-qrc files"
    user_options = [('pyrccbin=', 'b', 'Path to pyrcc4 executable'),
                    ('infile=', 'i', 'Input file'),
                    ('outfile=', 'o', 'Output file')]

    def initialize_options(self):
        self.pyrccbin = 'pyrcc4'
        self.infile = None
        self.outfile = None

    def finalize_options(self):
        if not isfile(self.infile):
            raise RuntimeError('file %s not found' %self.infile)

        if not self.outfile.endswith('.py'):
            raise RuntimeError("Check extension of the output file")

    def run(self):
        cmd = '%s -o %s %s' %(self.pyrccbin, self.outfile, self.infile)
        print "Compiling qrc file"
        os.system(cmd)
        print self.outfile
