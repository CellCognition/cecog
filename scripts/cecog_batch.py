"""
cecog_batch.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2016'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'



import os
import sys
import time
import random
import logging
import argparse
from collections import defaultdict

import cellh5

try:
    import cecog
except ImportError:
    sys.path.append(os.pardir)
    import cecog

from matplotlib import use
use("Agg")

from cecog.version import version
from cecog.traits.config import ConfigSettings
from cecog.threads import ErrorCorrectionThread
from cecog.analyzer.plate import PlateAnalyzer
from cecog.environment import CecogEnvironment
from cecog.io.imagecontainer import ImageContainer


ENV_INDEX_SGE = 'SGE_TASK_ID'
PLATESEP = "___"
POSSEP = ","



def getCellH5NumberOfSites(file_):
    """Determine the number of site within a file."""

    try:
        c5 = cellh5.CH5File(file_)
        nsites = 0
        for pos in c5.positions.values():
            nsites += len(pos)
    finally:
        c5.close()

    return nsites


if __name__ ==  "__main__":
    os.umask(0o000)

    parser = argparse.ArgumentParser(
        description="%prog - commandline interface for CellCognition.")
    parser.add_argument('-s', '--settings',
                        help='CecogAnalyzer settings files')
    parser.add_argument('--cluster-index',
                        help=("Index in a cluster job array referring to the "
                              "position list. Either an integer index or the "
                              "name of an environment variable "
                              "(only SGE supported)."))
    parser.add_argument("--batch-size",
                        help=("Number of positions executed together as one "
                              "job item in a bulk job. Allowed only in "
                              "combination with cluster index."),
                        type=int)
    args = parser.parse_args()

    index = args.cluster_index
    batch_size = args.batch_size

    if args.settings is None:
        parser.error('Settings filename required.')

    # FIXME: Could be more generally specified.
    # SGE is setting the job item index via an environment variable
    if index is None:
        pass
    elif index.isdigit():
        index = int(index)
    elif index == ENV_INDEX_SGE:
        if index not in os.environ:
            raise RuntimeError("SGE environment variable '%s' not defined.")
        # decrement index (index is in range of 1..n for SGE)
        index = int(os.environ[index]) - 1
    else:
        raise RuntimeError(
            "Only SGE supported at the moment (environment variable '%s')."
            %ENV_INDEX_SGE)

    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("*"*(len(version) + 53))
    logger.info("*** CellCognition - Batch Script - Version %s ***" %version)
    logger.info("*"*(len(version) + 53))
    logger.info("SGE job item index: environment variable '%s'" %str(index))
    logger.info('cmd: %s' %" ".join(sys.argv))

    environ = CecogEnvironment(version, redirect=False, debug=False)
    settingsfile = os.path.abspath(args.settings)

    # read the settings data from file
    settings = ConfigSettings()
    settings.read(settingsfile)

    imagecontainer = ImageContainer()
    imagecontainer.import_from_settings(settings)

    if settings('General', 'constrain_positions'):
        positions = settings('General', 'positions').split(POSSEP)
        if not settings('General', 'has_multiple_plates'):
            plate = os.path.split(settings("General", "pathin"))[1]
            positions = ['%s%s%s' % (plate, PLATESEP, p) for p in positions]
    else:
        positions = list()
        for plate in imagecontainer.plates:
            imagecontainer.set_plate(plate)
            meta_data = imagecontainer.get_meta_data()
            positions += \
              ['%s%s%s' % (plate, PLATESEP, pos) for pos in meta_data.positions]

    if index is not None and (index < 0 or index >= len(positions)):
        raise RuntimeError(
            "Cluster index %s does not match number of positions %d."
            %(index, len(positions)))

    # batch size was specified
    if batch_size is not None:
        if index is None:
            raise RuntimeError("Batch size requires a cluster index.")
        # select slice of positions according to index and batch size
        positions = positions[(index*batch_size) : ((index+1)*batch_size)]
    elif index is not None:
        positions = [positions[index]]

    # group positions by plate
    plates = defaultdict(list)
    for p in positions:
        plate, pos = p.split(PLATESEP)
        plates[plate].append(pos)

    # HDF file lock does not work on different cluster nodes (no shared memory)
    # only storage is shared
    time.sleep(random.random()*30)

    for plate, positions in plates.iteritems():

        # redefine output path in case of mulitplate analyis
        if settings('General', 'has_multiple_plates'):
            settings.set('General', 'pathout',
                         os.path.join(settings('General', 'pathout'), plate))

        # redefine the positions
        settings.set('General', 'constrain_positions', True)
        settings.set('General', 'positions', ','.join(positions))
        logger.info("Processing site %s - %s" % (plate, ", ".join(positions)))

        analyzer = PlateAnalyzer(plate, settings, imagecontainer, mode="a")
        analyzer()
        ch5file = analyzer.h5f

    # Run the error correction on the cluster
    if settings("Processing", "primary_errorcorrection") or \
       settings("Processing", "secondary_errorcorrection") or \
       settings("Processing", "tertiary_errorcorrection") or \
       settings("Processing", "merged_errorcorrection"):

        nsites = getCellH5NumberOfSites(ch5file)
        npos = len(os.listdir(os.path.dirname(ch5file))) - 1
        npos2 = len(imagecontainer.get_meta_data().positions)
        posflag = settings("General", "constrain_positions")

        # compare the number of processed positions with the number
        # of positions to be processed
        if (posflag and npos == nsites) or (npos2 == nsites):
            # only one process is supposed to run error correction
            thread = ErrorCorrectionThread(None, settings, imagecontainer)
            thread.start()
            thread.wait() # must return from run method

    print 'BATCHPROCESSING DONE!'
