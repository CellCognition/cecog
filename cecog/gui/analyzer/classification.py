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

__all__ = ('ClassificationFrame', )


import os
from os.path import isdir, basename, splitext, join
import numpy as np
from collections import OrderedDict

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from cecog.colors import hex2rgb
from cecog.classifier import SupportVectorClassifier

from cecog import CHANNEL_PREFIX, CH_VIRTUAL, CH_PRIMARY, CH_OTHER
from cecog.traits.analyzer.classification import SECTION_NAME_CLASSIFICATION
from cecog.util.ctuple import CTuple
from cecog.gui.analyzer import BaseProcessorFrame

from cecog.threads.trainer import TrainerThread
from cecog.threads.analyzer import AnalyzerThread


from cecog.environment import CecogEnvironment


class ClassifierResultFrame(QGroupBox):

    LABEL_FEATURES = '#Features: %d (%d)'
    LABEL_ACC = 'Overall accuracy: %.1f%%'
    LABEL_C = 'Log2(C) = %.1f'
    LABEL_G = 'Log2(g) = %.1f'

    def __init__(self, parent, channel, settings):
        super(ClassifierResultFrame, self).__init__(parent)

        self._channel = channel
        self._settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setSizePolicy(\
            QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
                        QSizePolicy.Expanding|QSizePolicy.Maximum))
        splitter.setStretchFactor(0, 2)
        layout.addWidget(splitter)

        frame_info = QFrame()
        layout_info = QVBoxLayout(frame_info)
        label = QLabel('Class & annotation info', frame_info)
        layout_info.addWidget(label)
        self._table_info = QTableWidget(frame_info)
        self._table_info.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table_info.setSelectionMode(QTableWidget.NoSelection)
        self._table_info.setSizePolicy(\
            QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
                        QSizePolicy.Expanding|QSizePolicy.Maximum))
        layout_info.addWidget(self._table_info)
        splitter.addWidget(frame_info)


        frame_conf = QFrame()
        layout_conf = QVBoxLayout(frame_conf)
        label = QLabel('Confusion matrix', frame_conf)
        layout_conf.addWidget(label)
        self._table_conf = QTableWidget(frame_conf)
        self._table_conf.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table_conf.setSelectionMode(QTableWidget.NoSelection)
        self._table_conf.setSizePolicy(\
            QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
                        QSizePolicy.Expanding|QSizePolicy.Maximum))
        layout_conf.addWidget(self._table_conf)
        splitter.addWidget(frame_conf)

        desc = QFrame(self)
        layout_desc = QHBoxLayout(desc)
        self._label_acc = QLabel(self.LABEL_ACC % float('NAN'), desc)
        layout_desc.addWidget(self._label_acc, Qt.AlignLeft)
        self._label_features = QLabel(self.LABEL_FEATURES % (0,0), desc)
        layout_desc.addWidget(self._label_features, Qt.AlignLeft)
        self._label_c = QLabel(self.LABEL_C % float('NAN'), desc)
        layout_desc.addWidget(self._label_c, Qt.AlignLeft)
        self._label_g = QLabel(self.LABEL_G % float('NAN'), desc)
        layout_desc.addWidget(self._label_g, Qt.AlignLeft)
        self.browserBtn = QPushButton('Open Browser for Annotation', desc)
        layout_desc.addWidget(self.browserBtn)
        layout.addWidget(desc)

    def classifier_exists(self):
        return os.path.isfile(self.hdffile)

    @property
    def hdffile(self):
        path = self._settings.get("Classification",
                                  "%s_classification_envpath" %self._channel)
        return join(path, basename(path.rstrip(os.path.sep)+".hdf"))

    def clear(self):
        self._table_conf.clear()
        self._table_info.clear()

    def reset(self):
        self._table_conf.clearContents()

    def on_load(self):
        self.load_classifier()

    def load_classifier(self):

        try:
            clf = SupportVectorClassifier(self.hdffile)
        except IOError:
            return

        ftr_names = np.array(clf.feature_names)
        nftr = len(ftr_names)
        fmask = clf.feature_mask
        nmasked = np.invert(fmask).sum()
        removed_features = ftr_names[fmask]

        self._label_features.setText('#Features: %d (%d)' %(len(removed_features), nftr))
        self._label_features.setToolTip(
            "removed %d features containing NA values:\n%s" %
            (len(removed_features), "\n".join(removed_features)))

        # if classifier was trained
        try:
            conf = clf.confmat
            c, g = clf.hyper_params
        except IOError as e:
            conf = None
            self._init_conf_table(conf)
        else:
            self._set_info(c, g, conf)
            self._init_conf_table(conf, clf.classdef.names)
            self._update_conf_table(conf)
        self._set_info_table(conf, clf.classdef, clf.class_counts)

        clf.close()

    def _set_info_table(self, conf, classdef, counts):

        rows = len(classdef)

        self._table_info.clear()
        names_horizontal = [('Name', 'class name'),
                            ('Samples', 'class samples'),
                            ('Color', 'class color'),
                            ('%PR', 'class precision in %'),
                            ('%SE', 'class sensitivity in %')]

        names_vertical = [str(k) for k in classdef.labels.values()] + ['', '#']

        self._table_info.setColumnCount(len(names_horizontal))
        self._table_info.setRowCount(len(names_vertical))
        self._table_info.setVerticalHeaderLabels(names_vertical)
        self._table_info.setColumnWidth(1, 20)
        for c, (name, info) in enumerate(names_horizontal):
            item = QTableWidgetItem(name)
            item.setToolTip(info)
            self._table_info.setHorizontalHeaderItem(c, item)

        for r, label in enumerate(classdef.labels.values()):

            self._table_info.setRowHeight(r, 20)
            name = classdef.names[label]
            count = counts[label]
            self._table_info.setItem(r, 0, QTableWidgetItem(name))
            self._table_info.setItem(r, 1, QTableWidgetItem(str(count)))
            item = QTableWidgetItem(' ')
            item.setBackground(QBrush(\
                    QColor(*hex2rgb(classdef.colors[name]))))
            self._table_info.setItem(r, 2, item)

            if not conf is None and r < len(conf):
                item = QTableWidgetItem('%.1f' % (conf.ppv[r] * 100.))
                item.setToolTip('"%s" precision' %  name)
                self._table_info.setItem(r, 3, item)

                item = QTableWidgetItem('%.1f' % (conf.se[r] * 100.))
                item.setToolTip('"%s" sensitivity' %  name)
                self._table_info.setItem(r, 4, item)

        if not conf is None:
            self._table_info.setRowHeight(r+1, 20)
            r += 2
            self._table_info.setRowHeight(r, 20)
            name = "overal"
            samples = sum(counts.values())
            self._table_info.setItem(r, 0, QTableWidgetItem(name))
            self._table_info.setItem(r, 1, QTableWidgetItem(str(samples)))
            item = QTableWidgetItem(' ')
            item.setBackground(QBrush(QColor(*hex2rgb('#FFFFFF'))))
            self._table_info.setItem(r, 2, item)

            item = QTableWidgetItem('%.1f' % (conf.wav_ppv * 100.))
            item.setToolTip('%s per class precision' %  name)
            self._table_info.setItem(r, 3, item)

            item = QTableWidgetItem('%.1f' % (conf.wav_se * 100.))
            item.setToolTip('%s per class sensitivity' %  name)
            self._table_info.setItem(r, 4, item)

        self._table_info.resizeColumnsToContents()

    def _init_conf_table(self, conf, class_names):
        self._table_conf.clear()

        if not conf is None:
            conf_array = conf.conf
            rows, cols = conf_array.shape
            self._table_conf.setColumnCount(cols)
            self._table_conf.setRowCount(rows)

            for i, label in enumerate(class_names):
                h_item = QTableWidgetItem(str(label))
                v_item = QTableWidgetItem(str(label))

                tooltip = '%d : %s' %(label, class_names[label])
                v_item.setToolTip(tooltip)
                h_item.setToolTip(tooltip)

                self._table_conf.setHorizontalHeaderItem(i, h_item)
                self._table_conf.setVerticalHeaderItem(i, v_item)

                self._table_conf.setColumnWidth(i, 20)
                self._table_conf.setRowHeight(i, 20)

    def _update_conf_table(self, conf):
        conf_array = conf.conf
        rows, cols = conf_array.shape
        conf_norm = conf_array.swapaxes(0,1) / np.array(np.sum(conf_array, 1), np.float)
        conf_norm = conf_norm.swapaxes(0,1)
        self._table_conf.clearContents()
        for r in range(rows):
            for c in range(cols):
                item = QTableWidgetItem()
                item.setToolTip('%d samples' % conf_array[r,c])
                if not np.isnan(conf_norm[r,c]):
                    col = int(255 * (1 - conf_norm[r,c]))
                    item.setBackground(QBrush(QColor(col, col, col)))
                self._table_conf.setItem(r, c, item)

    def _set_info(self, c, g, conf):
        self._label_acc.setText(self.LABEL_ACC % (conf.ac_sample*100.))
        self._label_c.setText(self.LABEL_C % c)
        self._label_g.setText(self.LABEL_G % g)

    def on_conf_result(self, c, g, conf):
        self._set_info(c, g, conf)

        if not self._has_data:
            self._has_data = True
            self._init_conf_table(conf)
        self._set_info_table(conf)
        self._update_conf_table(conf)


class ClassificationFrame(BaseProcessorFrame):

    TABS = ['Primary Channel', 'Secondary Channel',
            'Tertiary Channel', 'Merged Channel']
    ICON = ":classification.png"

    Training = 0
    Testing = 1

    def __init__(self, settings, parent, name):
        super(ClassificationFrame, self).__init__(settings, parent, name)
        self._result_frames = OrderedDict()

        self.register_control_button(self.Training, TrainerThread,
                                     ('Train classifier', 'Stop training'))
        self.register_control_button(self.Testing, AnalyzerThread,
                                     ('Test classifier', 'Stop testing'))

        for tab_name, prefix in [('Primary Channel', 'primary'),
                                 ('Secondary Channel', 'secondary'),
                                 ('Tertiary Channel', 'tertiary'),
                                 ('Merged Channel', 'merged')]:

            self.set_tab_name(tab_name)
            self.add_input('%s_classification_envpath' % prefix)
            self.add_line()

            if prefix in CH_VIRTUAL:
                                      # checkboxes
                self.add_group(None, [('merge_primary', (0, 0, 1, 1)),
                                      ('merge_secondary', (0, 1, 1, 1)),
                                      ('merge_tertiary', (0, 2, 1, 1)),
                                      # comboboxes
                                      ('merged_primary_region', (1, 0, 1, 1)),
                                      ('merged_secondary_region', (1, 1, 1, 1)),
                                      ('merged_tertiary_region', (1, 2, 1, 1))],
                               link='merged_channel',
                               label='Merge Channels')
            else:
                self.add_input('%s_classification_regionname' % prefix)
            frame_results = self._add_result_frame(prefix)
            self.add_handler('%s_classification_envpath' % prefix,
                             frame_results.on_load)

        self._init_control()

    def connect_browser_btn(self, func):
        for name, frame in self._result_frames.iteritems():
            frame.browserBtn.clicked.connect(func)

    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings( \
            self, name, has_timelapse)

        settings.set('Processing', 'primary_classification', False)
        settings.set('Processing', 'secondary_classification', False)
        settings.set('Processing', 'tracking', False)
        settings.set('Classification', 'collectsamples', False)
        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})
        settings.set('Output', 'hdf5_create_file', False)


        current_tab = self._tab.current_index
        if current_tab == 0:
            prefix = 'primary'
            settings.set('Processing', 'primary_featureextraction', True)
            settings.set('Processing', 'secondary_featureextraction', False)
            settings.set('Processing', 'tertiary_featureextraction', False)
            settings.set('General', 'process_secondary', False)
            settings.set('General', 'process_tertiary', False)
            settings.set('General', 'process_merged', False)
            rdn = {"%s_%s" %(prefix, settings.get(
                "Classification",
                "%s_classification_regionname" %prefix)): {}}
        elif current_tab == 1:
            prefix = 'secondary'
            settings.set('Processing', 'primary_featureextraction', False)
            settings.set('Processing', 'secondary_featureextraction', True)
            settings.set('General', 'process_secondary', True)
            settings.set('Processing', 'tertiary_featureextraction', False)
            settings.set('General', 'process_tertiary', False)
            settings.set('General', 'process_merged', False)

            # to setup the rending of the image currently processed
            rdn = {"%s_%s" %(prefix, settings.get(
                "Classification",
                "%s_classification_regionname" %prefix)): {}}
        elif current_tab == 2:
            prefix = 'tertiary'
            seg_region = settings.get('Classification',
                                      'tertiary_classification_regionname')
            settings.set('Processing', 'primary_featureextraction', False)
            settings.set('Processing', 'secondary_featureextraction', False)
            settings.set('General', 'process_secondary', True)
            settings.set('Processing', 'tertiary_featureextraction', True)
            settings.set('General', 'process_tertiary', True)
            settings.set('General', 'process_merged', False)

            rdn = {"%s_%s" %(prefix, settings.get(
                "Classification",
                "%s_classification_regionname" %prefix)): {}}
        else:
            # checkboxes in merged channel tab
            pch = settings.get('Classification', 'merge_primary')
            sch = settings.get('Classification', 'merge_secondary')
            tch = settings.get('Classification', 'merge_tertiary')

            settings.set('Processing', 'primary_featureextraction', pch)
            settings.set('Processing', 'secondary_featureextraction', sch)
            settings.set('General', 'process_secondary', sch)
            settings.set('Processing', 'tertiary_featureextraction', tch)
            settings.set('General', 'process_tertiary', tch)
            settings.set('General', 'process_merged', True)
            prefix = 'merged'

            rdn = {}
            for pfx in (CH_PRIMARY+CH_OTHER):
                if settings.get("Classification", "merge_%s" %pfx):
                    rdn["%s_%s" %(pfx, settings.get(
                        "Classification","merged_%s_region" %pfx))] = {}

        settings.set('Classification', 'collectsamples_prefix', prefix)

        if name == self.Testing:
            rdn = dict()
            settings.set('Processing', '%s_classification' % prefix, True)
            settings.set('General', 'rendering_class',
                         self._class_rendering_params(prefix, settings))
        else:
            settings.set('Classification', 'collectsamples', True)
            settings.set('General', 'positions', '')
        settings.set('General', 'rendering', rdn)
        return settings

    def _class_rendering_params(self, prefix, settings):
        """Setup rendering prameters for images to show classified objects"""

        if prefix in CH_VIRTUAL:
            region = []
            for pfx in (CH_PRIMARY+CH_OTHER):
                if settings.get('Classification', 'merge_%s' %pfx):
                    region.append(settings.get("Classification",
                                               "merged_%s_region" %pfx))
            region = CTuple(region)
        else:
            region = settings.get('Classification',
                                  '%s_classification_regionname' %prefix)

        rpar = {prefix.title():
                    {'raw': ('#FFFFFF', 1.0),
                     'contours': [(region, 'class_label', 1, False),
                                  (region, '#000000', 1, False)]}}
        cl_rendering = {'%s_classification_%s' %(prefix, str(region)): rpar}
        return cl_rendering


    def _add_result_frame(self, name):
        frame = self._get_frame()
        result_frame = ClassifierResultFrame(frame, name, self._settings)
        self._result_frames[name] = result_frame
        frame.layout().addWidget(result_frame, frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1
        return result_frame

    def _get_result_frame(self, name):
        return self._result_frames[name]

    def _update_classifier(self):
        channel = CHANNEL_PREFIX[self._tab.current_index]
        result_frame = self._result_frames[channel]
        result_frame.load_classifier()

    def classifiers(self):
        classifiers = list()
        for k, v in self._result_frames.iteritems():
            if v.classifier_exists():
                classifiers.append(k.title())
        return classifiers

    def settings_loaded(self):
        for frame in self._result_frames.values():
            frame.load_classifier()
        self.update_region_boxes()

    def _merged_channel_and_region(self, prefix):
        for ch in (CH_PRIMARY+CH_OTHER):
            trait = self._settings.get_trait(SECTION_NAME_CLASSIFICATION,
                                             '%s_%s_region' %(prefix, ch))

            regions = self.plugin_mgr.region_info.names[ch]

            # ugly workaround for due to trait concept
            if regions:
                trait.set_list_data(regions)
            else:
                cbtrait = self._settings.get_trait(SECTION_NAME_CLASSIFICATION,
                                                   'merge_%s' %ch)
                cbtrait.set_value(False)
                trait.set_list_data([])

    def page_changed(self):
        super(ClassificationFrame, self).page_changed()
        self.update_region_boxes()

    def update_region_boxes(self):
        """Update the 'Region name' or 'Merge Channels' combo boxes resp."""

        for name in self.plugin_mgr.region_info.names.keys():
            if name in CH_VIRTUAL:
                self._merged_channel_and_region(name)
            else:
                trait = self._settings.get_trait(
                    SECTION_NAME_CLASSIFICATION, '%s_classification_regionname' %name)
                trait.set_list_data(self.plugin_mgr.region_info.names[name])

    def _on_process_finished(self):
        super(ClassificationFrame, self)._on_process_finished()
        self._update_classifier()
