# -*- coding: utf-8 -*-
"""
post_processing.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import numpy as np
from os.path import join, isfile, abspath

from cecog.util.util import makedirs
from cecog.analyzer.ibb import IBBAnalysis, SecurinAnalysis
from cecog.threads.corethread import CoreThread
from cecog.traits.analyzer.postprocessing import SECTION_NAME_POST_PROCESSING


class PostProcessingThread(CoreThread):

    def __init__(self, parent, settings, learner_dict, imagecontainer):
        super(PostProcessingThread, self).__init__(parent, settings)
        self._learner_dict = learner_dict
        self._imagecontainer = imagecontainer
        self._mapping_files = {}

    def _run(self):
        self._logger.info('post processing...')

        plates = self._imagecontainer.plates
        self._settings.set_section(SECTION_NAME_POST_PROCESSING)

        path_mapping = self._settings.get2('mappingfile_path')
        for plate_id in plates:
            mapping_file = join(path_mapping, '%s.tsv' % plate_id)
            if not isfile(mapping_file):
                mapping_file = join(path_mapping, '%s.txt' % plate_id)
                if not isfile(mapping_file):
                    raise IOError("Mapping file '%s' for plate '%s' not found."
                                  % (mapping_file, plate_id))
            self._mapping_files[plate_id] = abspath(mapping_file)

        info = {'min' : 0,
                'max' : len(plates),
                'stage': 0,
                'meta': 'Post processing...',
                'progress': 0}

        for idx, plate_id in enumerate(plates):
            if not self._abort:
                info['text'] = "Plate: '%s' (%d / %d)" \
                    % (plate_id, idx+1, len(plates))
                self.update_status(info)
                self._imagecontainer.set_plate(plate_id)
                self._run_plate(plate_id)
                info['progress'] = idx+1
                self.update_status(info)
            else:
                break

    def _run_plate(self, plate_id):
        path_out = self._imagecontainer.get_path_out()

        path_analyzed = join(path_out, 'analyzed')
        makedirs(path_analyzed)

        mapping_file = self._mapping_files[plate_id]

        class_colors = {}
        for i, name in self._learner_dict['primary'].class_names.items():
            class_colors[i] = self._learner_dict['primary'].hexcolors[name]

        class_names = {}
        for i, name in self._learner_dict['primary'].class_names.items():
            class_names[i] = name

        self._settings.set_section(SECTION_NAME_POST_PROCESSING)

        if self._settings.get2('ibb_analysis'):
            ibb_options = {}
            ibb_options['ibb_ratio_signal_threshold'] =  \
                self._settings.get2('ibb_ratio_signal_threshold')
            ibb_options['ibb_range_signal_threshold'] = \
                self._settings.get2('ibb_range_signal_threshold')
            ibb_options['ibb_onset_factor_threshold'] = \
                self._settings.get2('ibb_onset_factor_threshold')
            ibb_options['nebd_onset_factor_threshold'] = \
                self._settings.get2('nebd_onset_factor_threshold')
            ibb_options['single_plot'] = self._settings.get2('single_plot')
            ibb_options['single_plot_max_plots'] = \
                self._settings.get2('single_plot_max_plots')
            ibb_options['single_plot_ylim_range'] = \
                self._settings.get2('single_plot_ylim_low'), \
                self._settings.get2('single_plot_ylim_high')

            tmp = (self._settings.get2('group_by_group'),
                   self._settings.get2('group_by_genesymbol'),
                   self._settings.get2('group_by_oligoid'),
                   self._settings.get2('group_by_position'))
            ibb_options['group_by'] = \
                int(np.log2(int(reduce(lambda x,y: str(x)+str(y),
                                       np.array(tmp).astype(np.uint8)),2))+0.5)

            tmp = (self._settings.get2('color_sort_by_group'),
                   self._settings.get2('color_sort_by_genesymbol'),
                   self._settings.get2('color_sort_by_oligoid'),
                   self._settings.get2('color_sort_by_position'))

            ibb_options['color_sort_by'] = \
                int(np.log2(int(reduce(lambda x,y: str(x)+str(y),
                                       np.array(tmp).astype(np.uint8)),2))+0.5)

            if not ibb_options['group_by'] < ibb_options['color_sort_by']:
                raise AttributeError(('Group by selection must be more general '
                                      ' than the color sorting! (%d !> %d)'
                                      % (ibb_options['group_by'],
                                         ibb_options['color_sort_by'])))

            ibb_options['color_sort_by'] = \
                IBBAnalysis.COLOR_SORT_BY[ibb_options['color_sort_by']]

            ibb_options['timeing_ylim_range'] = \
                self._settings.get2('plot_ylim1_low'), \
                self._settings.get2('plot_ylim1_high')

            path_out_ibb = join(path_out, 'ibb')
            makedirs(path_out_ibb)
            ibb_analyzer = IBBAnalysis(path_analyzed,
                                       path_out_ibb,
                                       plate_id,
                                       mapping_file,
                                       class_colors,
                                       class_names,
                                       **ibb_options)
            ibb_analyzer.run()

        if self._settings.get2('securin_analysis'):
            path_out_securin = join(path_out, 'sec')
            makedirs(path_out_securin)

            securin_options = {}
            securin_analyzer = SecurinAnalysis(path_analyzed,
                                       path_out_securin,
                                       plate_id,
                                       mapping_file,
                                       class_colors,
                                       class_names,
                                       **securin_options)
            securin_analyzer.run()
