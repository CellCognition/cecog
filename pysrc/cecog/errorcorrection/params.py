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


from cecog import CHANNEL_PREFIX
from cecog.errorcorrection import PlateMapping


# XXX belongs to the settings module/class
class ECParams(object):

    # do I really need to define __slots__ here?
    __slots__ = ['regionnames',
                 'constrain_graph', 'constrain_files', 'classifier_dirs',
                 'position_labels', 'mapping_dir',
                 'sortby', 'skip_plates', 'timeunit', 'overwrite_timelapse', 'timelapse',
                 'sorting', 'sorting_sequence', 'tmax',
                 'tracking_branches', 'write_gallery', 'n_galleries']

    def __init__(self, settings, tstep, timeunit):

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
        self.overwrite_timelapse = settings('ErrorCorrection', 'overwrite_time_lapse')
        self.timeunit = timeunit
        if self.overwrite_timelapse:
            self.timelapse = settings('ErrorCorrection', 'timelapse')
        else:
            self.timelapse = tstep

        self.sorting = settings('ErrorCorrection', 'enable_sorting')
        self.sorting_sequence = \
            eval('('+settings('ErrorCorrection', 'sorting_sequence')+',)')
        self.tmax = settings('ErrorCorrection', 'max_time')
        self.tracking_branches = settings('ErrorCorrection', 'ignore_tracking_branches')
        self.write_gallery = settings('ErrorCorrection', 'compose_galleries')
        self.n_galleries = settings('ErrorCorrection', 'compose_galleries_sample')

    def __str__(self):
        return '\n'.join(["%s : %s" %(slot, getattr(self, slot))
                          for slot in self.__slots__])
