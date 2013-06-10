# -*- coding: utf-8 -*-
"""
hmm.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import os
from os.path import join, isfile, abspath, isdir
from PyQt4 import QtCore, QtGui

from cecog.util.util import write_table, makedirs
from cecog.environment import CecogEnvironment
from cecog.threads.corethread import CoreThread
from cecog.analyzer.gallery import compose_galleries
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION

class HmmThread(CoreThread):

    def __init__(self, parent, settings, learner_dict, imagecontainer):
        super(HmmThread, self).__init__(parent, settings)
        self._learner_dict = learner_dict
        self._imagecontainer = imagecontainer
        self._mapping_files = {}

        # R on windows works better with '/' then '\'
        self._convert = lambda x: x.replace('\\','/')
        self._join = lambda *x: self._convert('/'.join(x))

    @property
    def r_executable(self):
        cmd = self._settings("ErrorCorrection", "filename_to_r")
        if not isfile(cmd):
            raise RuntimeError(("R executable not found (%s)\n"
                                "See documentation for details.") %cmd)
        return cmd

    def _run(self):
        plates = self._imagecontainer.plates
        self._settings.set_section(SECTION_NAME_ERRORCORRECTION)

        # mapping files (mapping between plate well/position
        # and experimental condition) can be defined by a directory
        # which must contain all mapping files for all plates in
        # the form <plate_id>.txt or .tsv
        # if the option 'position_labels' is not enabled a
        # dummy mapping file is generated
        if self._settings('ErrorCorrection', 'position_labels'):
            path_mapping = self._convert(self._settings( \
                    'ErrorCorrection', 'mappingfile_path'))
            for plate_id in plates:
                mapping_file = join(path_mapping, '%s.tsv' % plate_id)
                if not isfile(mapping_file):
                    mapping_file = join(path_mapping, '%s.txt' % plate_id)
                    if not isfile(mapping_file):
                        raise IOError(("Mapping file '%s' for plate '%s' "
                                       "not found." % (mapping_file, plate_id)))
                self._mapping_files[plate_id] = abspath(mapping_file)

        info = {'min' : 0,
                'max' : len(plates),
                'stage': 0,
                'meta': 'Error correction...',
                'progress': 0}

        for idx, plate_id in enumerate(plates):
            if not self._abort:
                info['text'] = "Plate: '%s' (%d / %d)" \
                    % (plate_id, idx+1, len(plates))
                self.update_status(info)
                self._imagecontainer.set_plate(plate_id)
                self._run_plate(plate_id)
                info['progress'] = idx + 1
                self.update_status(info)
            else:
                break

    def _run_plate(self, plate_id):

        cmd = self.r_executable
        path_out = self._imagecontainer.get_path_out()

        wd = abspath(join(CecogEnvironment.R_SOURCE_DIR, 'hmm'))
        f = file(join(wd, 'run_hmm.R'), 'r')
        lines = f.readlines()
        f.close()

        path_analyzed = self._join(path_out, 'analyzed')
        path_out_hmm = self._join(path_out, 'hmm')

        # don't do anything if the 'hmm' folder already exists and
        # the skip-option is on
        if isdir(path_out_hmm) and self._settings('ErrorCorrection', 'skip_processed_plates'):
            return

        makedirs(path_out_hmm)
        region_name_primary = self._settings.get(
            'Classification', 'primary_classification_regionname')
        region_name_secondary = self._settings.get(
            'Classification', 'secondary_classification_regionname')

        path_out_hmm_region = self._convert(
            self._get_path_out(path_out_hmm,
                               '%s_%s' % ('primary', region_name_primary)))

        # take mapping file for plate or generate dummy mapping file
        # for the R script
        if plate_id in self._mapping_files:
            # convert path for R
            mapping_file = self._convert(self._mapping_files[plate_id])
        else:
            mapping_file = self._generate_mapping(
                wd, path_out_hmm, path_analyzed)

        if self._settings('ErrorCorrection', 'overwrite_time_lapse'):
            time_lapse = self._settings('ErrorCorrection', 'timelapse')
        else:
            meta_data = self._imagecontainer.get_meta_data()
            if meta_data.has_timestamp_info:
                time_lapse = meta_data.plate_timestamp_info[0] / 60.
            else:
                raise ValueError("Plate '%s' has not time-lapse info.\n"
                                 "Please define (overwrite) the value manually."
                                 % plate_id)

        if self._settings('ErrorCorrection', 'compose_galleries'):
            gallery_names = ['primary'] + \
                [x for x in ['secondary','tertiary']
                 if self._settings.get('Processing', '%s_processchannel' % x)]
        else:
            gallery_names = None

        for i in range(len(lines)):
            line2 = lines[i].strip()
            if line2 == '#WORKING_DIR':
                lines[i] = "WORKING_DIR = '%s'\n" % self._convert(wd)
            elif line2 == '#FILENAME_MAPPING':
                lines[i] = "FILENAME_MAPPING = '%s'\n" % mapping_file
            elif line2 == '#PATH_INPUT':
                lines[i] = "PATH_INPUT = '%s'\n" % path_analyzed
            elif line2 == '#GROUP_BY_GENE':
                lines[i] = "GROUP_BY_GENE = %s\n" \
                    % str(self._settings('ErrorCorrection', 'groupby_genesymbol')).upper()
            elif line2 == '#GROUP_BY_OLIGOID':
                lines[i] = "GROUP_BY_OLIGOID = %s\n" \
                    % str(self._settings('ErrorCorrection', 'groupby_oligoid')).upper()
            elif line2 == '#TIMELAPSE':
                lines[i] = "TIMELAPSE = %s\n" % time_lapse
            elif line2 == '#MAX_TIME':
                lines[i] = "MAX_TIME = %s\n" % self._settings('ErrorCorrection', 'max_time')
            elif line2 == '#SINGLE_BRANCH':
                lines[i] = "SINGLE_BRANCH = %s\n" \
                % str(self._settings('ErrorCorrection', 'ignore_tracking_branches')).upper()
            elif line2 == '#GALLERIES':
                if gallery_names is None:
                    lines[i] = "GALLERIES = NULL\n"
                else:
                    lines[i] = "GALLERIES = c(%s)\n" \
                        % ','.join(["'%s'" % x for x in gallery_names])

            if len(self._learner_dict) == 0 or \
                    'primary' not in self._learner_dict:
                raise RuntimeError(('Classifier not found. Please check '
                                    'your classifications settings...'))
            ##
            if 'primary' in self._learner_dict:
                if self._settings('ErrorCorrection', 'constrain_graph'):
                    primary_graph = self._convert(
                        self._settings('ErrorCorrection', 'primary_graph'))
                else:
                    primary_graph = self._generate_graph(
                        'primary', wd, path_out_hmm, region_name_primary)

                if line2 == '#FILENAME_GRAPH_P':
                    lines[i] = "FILENAME_GRAPH_P = '%s'\n" % primary_graph
                elif line2 == '#CLASS_COLORS_P':
                    learner = self._learner_dict['primary']
                    colors = ",".join(["'%s'" % learner.hexcolors[x] \
                                           for x in learner.class_names.values()])
                    lines[i] = "CLASS_COLORS_P = c(%s)\n" % colors
                elif line2 == '#REGION_NAME_P':
                    lines[i] = "REGION_NAME_P = '%s'\n" % region_name_primary
                elif line2 == '#SORT_CLASSES_P':
                    if self._settings('ErrorCorrection', 'enable_sorting'):
                        lines[i] = "SORT_CLASSES_P = c(%s)\n" \
                            % self._settings('ErrorCorrection', 'sorting_sequence')
                    else:
                        lines[i] = "SORT_CLASSES_P = NULL\n"
                elif line2 == "#PATH_OUT_P":
                    lines[i] = "PATH_OUT_P = '%s'\n" % path_out_hmm_region
            ##
            if 'secondary' in self._learner_dict:
                if self._settings('ErrorCorrection', 'constrain_graph'):
                    secondary_graph = self._convert(
                        self._settings('ErrorCorrection', 'secondary_graph'))
                else:
                    secondary_graph = self._generate_graph(
                        'secondary', wd, path_out_hmm, region_name_secondary)

                if line2 == '#FILENAME_GRAPH_S':
                    lines[i] = "FILENAME_GRAPH_S = '%s'\n" % secondary_graph
                elif line2 == '#CLASS_COLORS_S':
                    learner = self._learner_dict['secondary']
                    colors = ",".join(["'%s'" % learner.hexcolors[x] \
                                       for x in learner.class_names.values()])
                    lines[i] = "CLASS_COLORS_S = c(%s)\n" % colors
                elif line2 == '#REGION_NAME_S':
                    lines[i] = "REGION_NAME_S = '%s'\n" % region_name_secondary
                elif line2 == '#SORT_CLASSES_S':
                    secondary_sort = self._settings('ErrorCorrection', 'secondary_sort')
                    if secondary_sort == '':
                        lines[i] = "SORT_CLASSES_S = NULL\n"
                    else:
                        lines[i] = "SORT_CLASSES_S = c(%s)\n" % secondary_sort
                elif line2 == "#PATH_OUT_S":
                    lines[i] = "PATH_OUT_S = '%s'\n" % \
                        self._convert(self._get_path_out(
                            path_out_hmm, '%s_%s' \
                                % ('secondary', region_name_secondary)))

        input_filename = join(path_out_hmm, 'cecog_hmm_input.R')
        f = file(input_filename, 'w')
        f.writelines(lines)
        f.close()

        self._process = QtCore.QProcess()
        self._process.setWorkingDirectory(wd)
        self._process.start(cmd, ['BATCH', '--silent', '-f', input_filename])
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.waitForFinished(-1)

        if self._process.exitCode() != 0:
            self._process.setReadChannel(QtCore.QProcess.StandardError)
            msg = str(self._process.readLine()).rstrip()
            msg = ''.join(list(self._process.readAll()))
            self.analyzer_error.emit(msg)
            self.abort()

        elif self._settings('ErrorCorrection', 'compose_galleries') and not self._abort:
            sample = self._settings('ErrorCorrection', 'compose_galleries_sample')
            if sample == -1:
                sample = None
            for group_name in compose_galleries(
                path_out, path_out_hmm_region, sample=sample):
                self._logger.debug('gallery finished for group: %s' % group_name)
                if self._abort:
                    break

        if self._settings('ErrorCorrection', 'show_html') and not self._abort:
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl('file://'+join(path_out_hmm_region, 'index.html'),
                            QtCore.QUrl.TolerantMode))

    def _generate_graph(self, channel, wd, hmm_path, region_name):
        f_in = file(join(wd, 'graph_template.txt'), 'rU')
        filename_out = self._join(hmm_path, 'graph_%s.txt' % region_name)

        f_out = file(filename_out, 'w')
        learner = self._learner_dict[channel]
        for line in f_in:
            line2 = line.strip()
            if line2 in ['#numberOfClasses', '#numberOfHiddenStates']:
                f_out.write('%d\n' % len(learner.class_names))
            elif line2 == '#startNodes':
                f_out.write('%s\n' % '  '.join(map(str, learner.class_names.keys())))
            elif line2 == '#transitionGraph':
                f_out.write('%s -> %s\n' %
                            (','.join(map(str, learner.class_names.keys())),
                             ','.join(map(str, learner.class_names.keys()))))
            elif line2 == '#hiddenNodeToClassificationNode':
                for label in learner.class_names.keys():
                    f_out.write('%s\n' % '  '.join(map(str, [label]*2)))
            else:
                f_out.write(line)
        f_in.close()
        f_out.close()
        return filename_out

    def _generate_mapping(self, wd, hmm_path, path_analyzed):
        filename_out = self._join(hmm_path, 'layout.txt')
        rows = []
        positions = None
        if self._settings.get('General', 'constrain_positions'):
            positions = self._settings.get('General', 'positions')
        if positions is None or positions == '':
            positions = [x for x in os.listdir(path_analyzed)
                         if isdir(join(path_analyzed, x)) and
                         x[0] != '_']
        else:
            positions = positions.split(',')
        for pos in positions:
            rows.append({'Position': pos, 'OligoID':'',
                         'GeneSymbol':'', 'Group':''})
        header_names = ['Position', 'OligoID', 'GeneSymbol', 'Group']
        write_table(filename_out, rows, column_names=header_names, sep='\t')
        return filename_out

    def _on_stdout(self):
        self._process.setReadChannel(QtCore.QProcess.StandardOutput)
        msg = str(self._process.readLine()).rstrip()
        self._logger.info(msg)

    def _get_path_out(self, path, prefix):
        if self._settings('ErrorCorrection', 'groupby_oligoid'):
            suffix = 'byoligo'
        elif self._settings('ErrorCorrection', 'groupby_genesymbol'):
            suffix = 'bysymbol'
        else:
            suffix = 'bypos'
        path_out = join(path, '%s_%s' % (prefix, suffix))
        makedirs(path_out)
        return path_out

    def set_abort(self, wait=False):
        self._process.kill()
        super(HmmThread, self).set_abort(wait=wait)
