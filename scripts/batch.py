#!/usr/bin/env python
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
import sys
import logging

try:
    import cecog
except ImportError:
    sys.path.append(os.path.join(os.pardir, "pysrc"))
    import cecog

from cecog import VERSION
from cecog.traits.config import ConfigSettings
from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.traits.analyzer.output import SECTION_NAME_OUTPUT
from cecog.analyzer.core import AnalyzerCore
from cecog.io.imagecontainer import ImageContainer
from cecog.threads.link_hdf import link_hdf5_files

ENV_INDEX_SGE = 'SGE_TASK_ID'

if __name__ ==  "__main__":
    os.umask(0o000)
    from optparse import OptionParser, OptionGroup

    description = ("%prog - A headless (GUI-free) batch "
                   "analyzer for CellCognition.")

    parser = OptionParser(usage="usage: %prog [options]",
                          description=description,
                          version='CellCognition %s' % VERSION)
    parser.add_option("-s", "--settings",
                      help="", metavar="SETTINGS_FILE")

    group1 = OptionGroup(parser, "Overwrite options",
                         "These options overwrite definitions from SETTINGS_FILE.")
    group1.add_option("-i", "--input", metavar="INPUT_PATH",
                      help="Input path pointing to a directory that is one plate or a directory containing "
                      "multiple plates as sub-directories, see MULTIPLE_PLATES.")
    group1.add_option("-o", "--output", metavar="OUTPUT_PATH",
                      help="Output path where analysis results are written. Depending on MULTIPLE_PLATES either "
                      "one directory for one plate or the parent directory for multiple plates.")
    group1.add_option("--multiple_plates", action="store_true", dest="multiple_plates",
                      help="Multiple plates are expected in INPUT_PATH.")
    group1.add_option("--no_multiple_plates", action="store_false", dest="multiple_plates",
                      help="INPUT_PATH specifies exactly one plate.")
    group1.add_option("--position_list",
                      help="List of positions as comma-separated string. Note: The plate ID MUST be provided when "
                      "multiple plates are used, "
                      "e.g. 'position1,position2' OR 'plateid1___position1,plateid3___position5'")
    group1.add_option("--create_images", action="store_true", dest="create_images",
                      help="Turn image creation on.")
    group1.add_option("--create_no_images", action="store_false", dest="create_images",
                      help="Turn image creation off.")

    group2 = OptionGroup(parser, "Cluster options",
                         "These options are used in combination with a cluster.")
    group2.add_option("--cluster_index",
                      help="Index in a cluster job array referring to the position list. "
                           "Either an integer index or the name of an environment variable (only SGE supported).")
    group2.add_option("--batch_size",
                      help="Number of positions executed together as one job item in a bulk job. "
                           "Allowed only in combination with cluster index.", type="int")

    parser.add_option_group(group1)
    parser.add_option_group(group2)
    (options, args) = parser.parse_args()

    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("*************************************************" + '*'*len(VERSION))
    logger.info("*** CellCognition - Batch Analyzer - Version %s ***" % VERSION)
    logger.info("*************************************************" + '*'*len(VERSION))
    logger.info('argv: %s' % sys.argv)

    if options.settings is None:
        parser.error('Settings filename required.')

    filename_settings = os.path.abspath(options.settings)

    # read the settings data from file
    settings = ConfigSettings(SECTION_REGISTRY)
    settings.read(filename_settings)

    settings.set_section(SECTION_NAME_GENERAL)

    index = options.cluster_index
    batch_size = options.batch_size
    position_list = options.position_list
    create_images = options.create_images
    multiple_plates = options.multiple_plates
    path_input = options.input
    path_output = options.output

    if path_input is not None:
        settings.set2('pathin', path_input)
        logger.info('Overwrite input path by %s' % path_input)
    else:
        path_input = settings.get2('pathin')
    if path_output is not None:
        settings.set2('pathout', path_output)
        logger.info('Overwrite output path by %s' % path_output)
    else:
        path_output = settings.get2('pathout')


    if multiple_plates is None:
        multiple_plates = settings.get(SECTION_NAME_GENERAL, 'has_multiple_plates')
    else:
        logger.info('Overwrite has_multiple_plates by %s' % multiple_plates)


    imagecontainer = ImageContainer()
    imagecontainer.import_from_settings(settings)

    # FIXME: Could be more generally specified. SGE is setting the job item index via an environment variable
    if index is None:
        pass
    elif index.isdigit():
        index = int(index)
    else:
        if index == ENV_INDEX_SGE:
            logger.info("Using SGE job item index: environment variable '%s'" % index)

            if index not in os.environ:
                parser.error("SGE environment variable '%s' not defined.")
            index = int(os.environ[index])
            # decrement index (index is in range of 1..n for SGE)
            index -= 1
        else:
            parser.error("Only SGE supported at the moment (environment variable '%s')." % ENV_INDEX_SGE)


    # if no position list was specified via the program options get it from the settings file
    if  position_list is None:
        if settings.get(SECTION_NAME_GENERAL, 'constrain_positions'):
            position_list = settings.get(SECTION_NAME_GENERAL, 'positions') or None


    # construct a dummy string containing all plates and positions known to imagecontainer
    if position_list is None:
        positions = []
        for plate_id in imagecontainer.plates:
            imagecontainer.set_plate(plate_id)
            meta_data = imagecontainer.get_meta_data()
            positions += ['%s___%s' % (plate_id, pos) for pos in meta_data.positions]
    else:
        positions = position_list.split(',')


    if index is not None and (index < 0 or index >= len(positions)):
        parser.error("Cluster index %s does not match number of positions %d." % (index, len(positions)))

    # batch size was specified
    if batch_size is not None:
        if index is None:
            parser.error("Batch size requires a cluster index.")
        # select slice of positions according to index and batch size
        positions = positions[(index*batch_size) : ((index+1)*batch_size)]
    # index alone was specified
    elif index is not None:
        positions = [positions[index]]

    logger.info('Final list of position: %s' % positions)

    # redefine the image write to disc
    if create_images is not None:
        logger.info('Overwrite image creation from settings by %s' % create_images)
        for rendering in ['rendering_labels_discwrite',
                          'rendering_class_discwrite',
                          'rendering_contours_discwrite']:
            settings.set(SECTION_NAME_OUTPUT, rendering, create_images)

    # group positions by plate
    plates = {}
    for item in positions:
        compound = item.split('___')
        if len(compound) == 2:
            plate_id, pos = compound
        elif len(compound) == 1:
            if not multiple_plates:
                plate_id = os.path.split(path_input)[1]
                pos = compound[0]
            else:
                parser.error("Position must be of the form 'plateid___position'. Found '%s' instead." % item)
        else:
            parser.error("Position must be of the form 'position' or 'plateid___position'. Found '%s' instead." % item)

        if not plate_id in plates:
            plates[plate_id] = []
        plates[plate_id].append(pos)

    # start one analyzer per plate with the corresponding positions
    post_hdf5_link_list = []
    for plate_id in plates:
        # redefine the positions
        settings.set(SECTION_NAME_GENERAL, 'constrain_positions', True)
        settings.set(SECTION_NAME_GENERAL, 'positions', ','.join(plates[plate_id]))
        logger.info("Launching analyzer for plate '%s' with positions %s" % (plate_id, plates[plate_id]))
        # initialize and run the analyzer
        analyzer = AnalyzerCore(plate_id, settings, imagecontainer)
        hdf_links = analyzer.processPositions()
        post_hdf5_link_list.append(hdf_links)

    if settings.get('Output', 'hdf5_create_file') and settings.get('Output', 'hdf5_merge_positions'):
        if len(post_hdf5_link_list) > 0:
            post_hdf5_link_list = reduce(lambda x,y: x + y, post_hdf5_link_list)
            link_hdf5_files(sorted(post_hdf5_link_list))
    print 'BATCHPROCESSING DONE!'
