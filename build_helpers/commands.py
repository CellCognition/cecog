"""
commands.py

Define new commands for the build process.
"""
from __future__ import absolute_import
from __future__ import print_function
import six

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['Build', 'BuildRcc', 'BuildHelp']

import os
from os.path import isfile, isdir, dirname
import subprocess
from  distutils.core import Command
from  distutils.command.build import build as _build


class Build(_build):
    """Custom build command for distutils to have the qrc files compiled before
    before the build process.
    """

    def run(self):
        self.run_command('build_rcc')
        self.run_command('build_help')
        _build.run(self)


class BuildHelp(Command):
    """Custom command to compile Qt Collection files"""

    description = "Compile qt5-collection files"
    user_options = [('qcollectiongeneator=', 'b', 'Path to qcollectiongeneator'),
                    ('infile=', 'i', 'Input file'),
                    ('outfile=', 'o', 'Output file')]

    def initialize_options(self):
        self.qcollectiongeneator = 'qcollectiongeneator'
        self.infile = None
        self.outfile = None

    def finalize_options(self):

        if not isfile(self.infile):
            raise RuntimeError('file %s not found' %self.infile)

        if not self.outfile.endswith('.qhc'):
            raise RuntimeError("Check extension of the output file")

    def run(self):
        print("Compiling colleciton file")
        print(self.outfile)

        if not isdir(dirname(self.outfile)):
            os.mkdir(dirname(self.outfile))

        try:
            subprocess.check_call([self.qcollectiongeneator, '-o', self.outfile,
                                   self.infile])
        except Exception as e:
            cmd = "%s -o %s %s" %(self.qcollectiongeneator,
                                  self.outfile, self.infile)
            print("running command '%s' failed" %cmd)
            raise


class BuildRcc(Command):
    """Custom command to compile Qt resource files"""

    description = "Compile qt-resource files"
    user_options = [('pyrccbin=', 'b', 'Path to pyrcc4 executable'),
                    ('qrc=', 'q', 'Input/output file dictionary'),]

    def initialize_options(self):
        self.pyrccbin = 'pyrcc5'
        self.qrc = None

    def finalize_options(self):
        for infile, outfile in six.iteritems(self.qrc):
            if not isfile(infile):
                raise RuntimeError('file %s not found' %infile)

            if not outfile.endswith('.py'):
                raise RuntimeError("Check extension of the output file")

    def run(self):
        for infile, outfile in six.iteritems(self.qrc):
            print("Compiling qrc %s" %infile)
            print(outfile)
            try:
                subprocess.check_call([self.pyrccbin, '-o', outfile, infile])
            except Exception as e:
                cmd = "%s -o %s %s" %(self.pyrccbin, outfile, infile)
                print("running command '%s' failed" %cmd)
                raise
