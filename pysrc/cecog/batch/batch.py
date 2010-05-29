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
       logging

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
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
    from cecog.traits.config import ConfigSettings

    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-i", "--input", dest="input", default=None,
                      help="", metavar="PATH")
    parser.add_option("-o", "--output", dest="output", default=None,
                      help="", metavar="PATH")
    parser.add_option("-s", "--settings", dest="settings",
                      help="", metavar="FILE")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")

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

    analyzer = AnalyzerCore(settings)
    analyzer.processPositions()



