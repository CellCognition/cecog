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
import glob
import shutil
import random
import logging
import argparse
from collections import defaultdict

from matplotlib import use
use("Agg")

try:
    import cecog
except ImportError:
    sys.path.append(os.pardir)
    import cecog

from cecog.version import version
from cecog.traits.config import ConfigSettings
from cecog.threads import ErrorCorrectionThread
from cecog.analyzer.plate import PlateAnalyzer
from cecog.environment import CecogEnvironment
from cecog.io.imagecontainer import ImageContainer
from cecog.io.hdf import Ch5File
from cecog.io.hdf import Plate, Well, Site


ENV_INDEX_SGE = 'SGE_TASK_ID'
PLATESEP = "___"
POSSEP = ","


def mergeHdfFiles(target, source_dir, remove_source=True, mode="a"):

    hdffiles = glob.glob(os.path.join(source_dir, '*.ch5'))
    target = Ch5File(target, mode=mode)

    for i, h5 in enumerate(sorted(hdffiles)):

        source = Ch5File(h5, 'r')

        if i == 0:
            target.copy(source['/layout'], '/layout')
            target.copy(source['/definition'], "/definition")

        first_item = lambda view: next(iter(view))
        plate = first_item(source[Plate].keys())
        well = first_item(source[Well.format(plate)].keys())
        position = first_item(source[Site.format(plate, well, "")].keys())

        # cluster uses hdf v2.1 --> need to create a group first before
        # I copy the data sets,

        path1 = str(Site.format(plate, well, position))
        path2 = Site %(plate, well, "")

        if not path2 in target._f:
            group = target._f.create_group(path2)

        group.copy(source[path1], position)
        source.close()

        if remove_source:
            os.remove(h5)
            os.remove(h5.replace(".ch5", ".tmp"))

    target.close()




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
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

    print "*"*(len(version) + 53)
    print "*** CellCognition - Batch Script - Version %s ***" %version
    print "*"*(len(version) + 53)
    print "SGE job item index: environment variable '%s'" %str(index)
    print 'cmd: %s' %" ".join(sys.argv)

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

    n_positions = len(positions)

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
        print "Processing site %s - %s" % (plate, ", ".join(positions))

        analyzer = PlateAnalyzer(plate, settings, imagecontainer, mode="a")
        analyzer()
        ch5file = analyzer.h5f

    n_sites = len(glob.glob(os.path.join(settings("General", "pathout"), "cellh5", "*.tmp")))
    n_total = len(imagecontainer.get_meta_data().positions)
    posflag = settings("General", "constrain_positions")

    # compare the number of processed positions with the number
    # of positions to be processed
    if (posflag and n_positions == n_sites) or (n_total == n_sites):

        try:
            mergeHdfFiles(analyzer.h5f, analyzer.ch5dir, remove_source=True)
            shutil.rmtree(analyzer.ch5dir)
        except OSError as e:
            logger.warning(str(e))
            logger.warning("Could not remove cellh5 directory")

        # Run the error correction on the cluster
        if settings("Processing", "primary_errorcorrection") or \
           settings("Processing", "secondary_errorcorrection") or \
           settings("Processing", "tertiary_errorcorrection") or \
           settings("Processing", "merged_errorcorrection"):

            # only one process is supposed to run error correction
            thread = ErrorCorrectionThread(None, settings, imagecontainer)
            thread.start()
            thread.wait()

    print 'BATCHPROCESSING DONE!'
