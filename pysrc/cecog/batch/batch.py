"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys, \
       os, \
       logging, \
       types

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog import VERSION
from cecog.traits.config import ConfigSettings
from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.analyzer.core import AnalyzerCore

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

if __name__ ==  "__main__":

    from optparse import OptionParser

    description =\
'''
%prog - A batch analyzer for CellCognition. Note that the input and output
folder of the settings file can be overwritten by the options below.
'''

    parser = OptionParser(usage="usage: %prog [options]",
                          description=description,
                          version=VERSION)
    parser.add_option("-i", "--input", default=None,
                      help="", metavar="PATH")
    parser.add_option("-o", "--output", default=None,
                      help="", metavar="PATH")
    parser.add_option("-s", "--settings",
                      help="", metavar="FILE")
    parser.add_option("", "--cluster_index",
                      help="The index in a cluster job array referring to the "
                           "position or any other bulk-definition. (Starting "
                           "at 1 for reasons of compatibility, e.g. with SGE).")

    (options, args) = parser.parse_args()

    if options.settings is None:
        parser.error('Settings filename required.')

    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.info("**************************************")
    logger.info("*** CellCognition - Batch Analyzer ***")
    logger.info("**************************************")

    filename_settings = os.path.abspath(options.settings)

    # read the settings data from file
    settings = ConfigSettings(SECTION_REGISTRY)
    settings.read(filename_settings)

    settings.set_section(SECTION_NAME_GENERAL)
    if not options.input is None:
        settings.set2('pathin', options.input)
    if not options.output is None:
        settings.set2('pathout', options.output)

    index = options.cluster_index
    print "moo123", index, sys.argv
    if not index is None:
        # FIXME: hack for the somewhat stupid DRMAA 1.0
        if type(index) == types.StringType and index in os.environ:
            index = int(os.environ[index])
        else:
            parser.error("Cluster index must be an integer or a defined environment variable, e.g. 'SGE_TASK_ID'")
        index -= 1
        settings.set(SECTION_NAME_GENERAL, 'constrain_positions', True)
        positions = settings.get(SECTION_NAME_GENERAL, 'positions')
        if not positions is None:
            positions = positions.split(',')
            if index >= 0 and index < len(positions):
                settings.set(SECTION_NAME_GENERAL, 'positions',
                             positions[index])
            else:
                parser.error('Cluster index between 1 and %d required!' %
                             len(positions))
        else:
            parser.error('Cluster index requires a position list specified in '
                         'the settings file!')

    analyzer = AnalyzerCore(settings)
    analyzer.processPositions()



