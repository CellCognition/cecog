"""
params.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['ECParams']

from os.path import join

from cecog import CHANNEL_PREFIX
from cecog.errorcorrection import PlateMapping
from cecog.learning.learning import LearnerFiles
from cecog.learning.learning import ClassDefinition
from cecog.learning.learning import ClassDefinitionUnsup


# XXX belongs to the settings module/class
class ECParams(object):

    EVENTSELECTION_SUPERVISED = 0
    EVENTSELECTION_UNSUPERVISED = 1
    EVENTSELECTION = (EVENTSELECTION_SUPERVISED, EVENTSELECTION_UNSUPERVISED)

    __slots__ = ['regionnames', 'constrain_graph', 'constrain_files',
                 'classifier_dirs', 'position_labels', 'mapping_dir',
                 'sortby', 'skip_plates', 'timeunit', 'overwrite_timelapse',
                 'timelapse', 'sorting', 'sorting_sequence', 'tmax',
                 'ignore_tracking_branches', 'write_gallery', 'n_galleries',
                 'eventselection', 'nclusters', '_classdef']

    def __init__(self, settings, tstep, timeunit):

        self._classdef = None

        self.constrain_graph = settings('ErrorCorrection', 'constrain_graph')
        self.constrain_files = dict()
        self.classifier_dirs = dict()
        self.regionnames = dict()

        # settings that depend whether if the channel is checked for
        # error correction or not
        for channel in CHANNEL_PREFIX:
            if settings('ErrorCorrection', channel):
                self.regionnames[channel] = \
                    settings('Classification', '%s_classification_regionname'
                             %channel)
                self.constrain_files[channel] = \
                    settings('ErrorCorrection', '%s_graph' %channel)
                _setting = '%s_classification_envpath' %channel
                self.classifier_dirs[channel] = \
                    settings('Classification', _setting)

        self.position_labels = settings('ErrorCorrection', 'position_labels')
        self.mapping_dir = settings('ErrorCorrection', 'mappingfile_path')

        if settings('ErrorCorrection', 'groupby_oligoid'):
            self.sortby = PlateMapping.OLIGO
        elif settings('ErrorCorrection', 'groupby_genesymbol'):
            self.sortby = PlateMapping.GENE
        else:
            self.sortby = PlateMapping.POSITION

        # special case, sort by position if no mappings file is provided
        if not self.position_labels:
            self.sortby = PlateMapping.POSITION

        self.skip_plates = settings('ErrorCorrection', 'skip_processed_plates')

        # timelapse in minutes
        self.overwrite_timelapse = \
            settings('ErrorCorrection', 'overwrite_time_lapse')
        self.timeunit = timeunit
        if self.overwrite_timelapse:
            self.timelapse = settings('ErrorCorrection', 'timelapse')
        else:
            self.timelapse = tstep

        self.sorting = settings('ErrorCorrection', 'enable_sorting')
        self.sorting_sequence = \
            eval('('+settings('ErrorCorrection', 'sorting_sequence')+',)')
        self.tmax = settings('ErrorCorrection', 'max_time')
        self.ignore_tracking_branches = \
            settings('ErrorCorrection', 'ignore_tracking_branches')
        self.write_gallery = settings('ErrorCorrection', 'compose_galleries')
        self.n_galleries = \
            settings('ErrorCorrection', 'compose_galleries_sample')

        if settings('EventSelection', 'supervised_event_selection'):
            self.eventselection = self.EVENTSELECTION_SUPERVISED
        else:
            self.eventselection = self.EVENTSELECTION_UNSUPERVISED
        self.nclusters = settings('EventSelection', 'num_clusters')

    @property
    def class_definition(self):
        """Distinguish btw. supervised and unsupervised class/cluster-
        definitinion.
        """
        if self._classdef is None:
            classdef = dict()
            for channel, clfdir in self.classifier_dirs.iteritems():
                if self.eventselection == self.EVENTSELECTION_SUPERVISED:
                    classdef[channel] = ClassDefinition( \
                        join(clfdir, LearnerFiles.DEFINITION))
                else:
                    classdef[channel] = ClassDefinitionUnsup(self.nclusters)
                classdef[channel].load()
            self._classdef = classdef

        return self._classdef


    def __str__(self):
        return '\n'.join(["%s : %s" %(slot, getattr(self, slot))
                          for slot in self.__slots__])
