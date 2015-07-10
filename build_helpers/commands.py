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

__all__ = ['Build', 'BuildRcc', 'BuildHelp', 'BuildCSSRcc']

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
        print "Compiling colleciton file"
        print self.outfile

        if not isdir(dirname(self.outfile)):
            os.mkdir(dirname(self.outfile))

        try:
            subprocess.check_call([self.qcollectiongeneator, '-o', self.outfile,
                                   self.infile])
        except Exception, e:
            cmd = "%s -o %s %s" %(self.qcollectiongeneator,
                                  self.outfile, self.infile)
            print "running command '%s' failed" %cmd
            raise


class BuildRcc(Command):
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
        print "Compiling qrc file"
        print self.outfile
        try:
            subprocess.check_call([self.pyrccbin, '-o', self.outfile,
                                   self.infile])
        except Exception, e:
            cmd = "%s -o %s %s" %(self.pyrccbin, self.outfile, self.infile)
            print "running command '%s' failed" %cmd
            raise
        
        
class BuildCSSRcc(Command):
    """Custom command to compile Qt4-qrc files"""

    description = "Compile css source and pngs from qrc files"
    user_options = [('pyrccbin=', 'b', 'Path to pyrcc4 executable'),]

    def initialize_options(self):
        self.pyrccbin = 'pyrcc5'
        self.css_src_folder = 'resources/css/src'

    def finalize_options(self):
        pass

    def run(self):
        print "Compiling style sheets qrc files in %s" % self.css_src_folder
        print "***"*20
        try:
            for f in os.listdir(self.css_src_folder):
                if (os.path.isdir(os.path.join(self.css_src_folder,f)) and 
                    os.path.exists(os.path.join(os.path.join(self.css_src_folder, f), "style.qrc"))):
                    cmd = [self.pyrccbin, os.path.join(self.css_src_folder, "%s/style.qrc" % f), 
                                           "-o", os.path.join(self.css_src_folder, "..","%s.py" % f)]
                    print "running", " ".join(cmd)
                    subprocess.check_call(cmd)
            
        except Exception, e:
            print "running command '%s' failed" %cmd
            raise
