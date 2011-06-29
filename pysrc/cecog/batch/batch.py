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
from cecog.traits.config import init_application_support_path, init_constants
from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.traits.analyzer.output import SECTION_NAME_OUTPUT
from cecog.analyzer.core import AnalyzerCore
from cecog.io.imagecontainer import ImageContainer

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
    parser.add_option("", "--batch_size",
                      help="The number of positions executed together as one "
                           "job item in a bulk job. This reduces the load on "
                           "the job scheduler heavily.", default=1, type="int")
    parser.add_option("-p", "--position_list", default=None,
                      help="List of positions (as an alternative to the index"
                           "of a cluster job.", dest="position_list")
    parser.add_option("-c", "--create_images", default=None,
                      help="flag for image creation. Overwrites the settings"
                           "from the settings file.", dest="create_images")

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

    #init_application_support_path()
    #init_constants()

    filename_settings = os.path.abspath(options.settings)

    # read the settings data from file
    settings = ConfigSettings(SECTION_REGISTRY)
    settings.read(filename_settings)

    settings.set_section(SECTION_NAME_GENERAL)
    if not options.input is None:
        settings.set2('pathin', options.input)
    if not options.output is None:
        settings.set2('pathout', options.output)

    imagecontainer = ImageContainer()
    imagecontainer.import_from_settings(settings)

    index = options.cluster_index
    batch_size = options.batch_size
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
            batch_pos = positions[(index*batch_size) : ((index+1)*batch_size)]
            if index >= 0 and index < len(positions):

                plates = {}
                for item in batch_pos:
                    plate_id, pos = item.split('___')
                    if not plate_id in plates:
                        plates[plate_id] = []
                    plates[plate_id].append(pos)

                for plate_id in plates:
                    settings.set(SECTION_NAME_GENERAL, 'positions',
                                 ','.join(plates[plate_id]))
                    print "Launching analyzer for plate '%s' with positions %s"%\
                          (plate_id, plates[plate_id])
                    analyzer = AnalyzerCore(plate_id, settings, imagecontainer)
                    analyzer.processPositions()
            else:
                parser.error('Cluster index between 1 and %d required!' %
                             len(positions))
        else:
            parser.error('Cluster index requires a position list specified in '
                         'the settings file!')

    elif not position_list is None:
        # find the plates from the position list
        plates = {}
        for item in position_list:
            plate_id, pos = item.split('___')
            if not plate_id in plates:
                plates[plate_id] = []
            plates[plate_id].append(pos)

        settings.set(SECTION_NAME_GENERAL, 'constrain_positions', True)
        if options.create_images.lower() == 'false':
            settings.set(SECTION_NAME_GENERAL, 'createimages', False)
            for rendering in ['rendering_labels_discwrite',
                              'rendering_class_discwrite',
                              'rendering_contours_discwrite']:
                settings.set(SECTION_NAME_OUTPUT, rendering, False)

        #createimages = True
        for plate_id in plates:
            settings.set(SECTION_NAME_GENERAL, 'positions',
                         ','.join(plates[plate_id]))
            print "Launching analyzer for plate '%s' with positions %s"%\
            (plate_id, plates[plate_id])

            analyzer = AnalyzerCore(plate_id, settings, imagecontainer)
            analyzer.processPositions()

    else:
        print 'either a cluster index or a list of position has to be given.'

    print 'BATCHPROCESSING DONE!'


