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

from os.path import isfile

from cecog import CHANNEL_PREFIX

# XXX belongs to the settings module/class
class ECParams(object):

    # do I really need to define __slots__ here?
    __slots__ = ['regionnames',
                 'constrain_graph', 'constrain_files', 'classifier_dirs',
                 'position_labels', 'mapping_dir',
                 'sortby', 'skip_plates', 'overwrite_timelapse', 'timelapse',
                 'sorting', 'sorting_sequence', 'max_plot_time',
                 'tracking_branches', 'write_gallery', 'n_galleries']

    POS = 'pos'
    OLIGO = 'oligo'
    GENESYMBOL = 'genesymbol'

    def __init__(self, settings):

        self.constrain_graph = settings('ErrorCorrection', 'constrain_graph')
        self.constrain_files = dict()
        self.classifier_dirs = dict()
        self.regionnames = dict()

        # settings that depend wether if the channel is checked for
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
            self.sortby = self.OLIGO
        elif settings('ErrorCorrection', 'groupby_genesymbol'):
            self.sortby = self.GENESYMBOL
        else:
            self.sortby = self.POS
        self.skip_plates = settings('ErrorCorrection', 'skip_processed_plates')
        self.overwrite_timelapse = settings('ErrorCorrection', 'overwrite_time_lapse')
        self.timelapse = settings('ErrorCorrection', 'timelapse')
        self.sorting = settings('ErrorCorrection', 'enable_sorting')
        self.sorting_sequence= settings('ErrorCorrection', 'sorting_sequence')
        self.max_plot_time = settings('ErrorCorrection', 'max_time')
        self.tracking_branches = settings('ErrorCorrection', 'ignore_tracking_branches')
        self.write_gallery = settings('ErrorCorrection', 'compose_galleries')
        self.n_galleries = settings('ErrorCorrection', 'compose_galleries_sample')

    def pprint(self):
        for slot in self.__slots__:
            print slot, ': ', getattr(self, slot)
