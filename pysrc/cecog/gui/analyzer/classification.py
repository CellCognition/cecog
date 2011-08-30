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

__all__ = ['ClassificationFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.classification import SECTION_NAME_CLASSIFICATION
from cecog.gui.util import (information,
                            exception,
                            )
from cecog.gui.analyzer import (BaseProcessorFrame,
                                AnalzyerThread,
                                TrainingThread,
                                )
from cecog.analyzer import SECONDARY_REGIONS
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    )
from cecog.learning.learning import CommonClassPredictor
from cecog.util.util import (hexToRgb,
                             convert_package_path,
                             )

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class ClassifierResultFrame(QGroupBox):

    LABEL_FEATURES = '#Features: %d (%d)'
    LABEL_ACC = 'Overall accuracy: %.1f%%'
    LABEL_C = 'Log2(C) = %.1f'
    LABEL_G = 'Log2(g) = %.1f'

    def __init__(self, parent, channel, settings):
        QGroupBox.__init__(self, parent)

        self._channel = channel
        self._settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        #self._button = QPushButton('Load', self)
        #self.connect(self._button, SIGNAL('clicked()'), self._on_load)
        #layout.addWidget(self._button, 1, 2)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
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
        self._table_info.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
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
        self._table_conf.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
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
        btn = QPushButton('Show Browser', desc)
        btn.clicked.connect(qApp._main_window._on_browser_open)
        layout_desc.addWidget(btn)
        layout.addWidget(desc)

        self._has_data = False

    def clear(self):
        self._table_conf.clear()
        self._table_info.clear()
        self._has_data = False

    def reset(self):
        self._has_data = False
        self._table_conf.clearContents()

    def on_load(self):
        self.load_classifier(check=True)

    def load_classifier(self, check=True):

        _resolve = lambda x,y: self._settings.get(x, '%s_%s' % (self._channel, y))
        env_path = convert_package_path(_resolve('Classification',
                                                 'classification_envpath'))
        classifier_infos = {'strEnvPath' : env_path,
                            #'strModelPrefix' : _resolve('Classification', 'classification_prefix'),
                            'strChannelId' : _resolve('ObjectDetection', 'channelid'),
                            'strRegionId' : _resolve('Classification', 'classification_regionname'),
                            }
        try:
            self._learner = CommonClassPredictor(dctCollectSamples=classifier_infos)
        except:
            exception(self, 'Error on loading classifier.')
        else:
            result = self._learner.check()
            if check:
                b = lambda x: 'Yes' if x else 'No'
                msg =  'Classifier path: %s\n' % result['path_env']
                msg += 'Found class definition: %s\n' % b(result['has_definition'])
                msg += 'Found annotations: %s\n' % b(result['has_path_annotations'])
                msg += 'Can you pick new samples? %s\n\n' % b(self.is_pick_samples())
                msg += 'Found ARFF file: %s\n' % b(result['has_arff'])
                msg += 'Can you train a classifier? %s\n\n' % b(self.is_train_classifier())
                msg += 'Found SVM model: %s\n' % b(result['has_model'])
                msg += 'Found SVM range: %s\n' % b(result['has_range'])
                msg += 'Can you apply the classifier to images? %s\n\n' % b(self.is_apply_classifier())
                msg += 'Found samples: %s\n' % b(result['has_path_samples'])
                msg += 'Sample images are only used for visualization and annotation control at the moment.'

                txt = '%s classifier inspection results' % self._channel
                information(self, txt, info=msg)

            if result['has_arff']:
                self._learner.importFromArff()
                nr_features_prev = len(self._learner.lstFeatureNames)
                removed_features = self._learner.filterData(apply=False)
                nr_features = nr_features_prev - len(removed_features)
                self._label_features.setText(self.LABEL_FEATURES % (nr_features, nr_features_prev))
                self._label_features.setToolTip("removed %d features containing NA values:\n%s" %
                                                (len(removed_features), "\n".join(removed_features)))

            if result['has_definition']:
                self._learner.loadDefinition()

            if result['has_conf']:
                c, g, conf = self._learner.importConfusion()
                self._set_info(c, g, conf)
                self._init_conf_table(conf)
                self._update_conf_table(conf)
            else:
                conf = None
                self._init_conf_table(conf)
            self._set_info_table(conf)

    def msg_pick_samples(self, parent):
        result = self._learner.check()
        text = 'Sample picking is not possible'
        info = 'You need to provide a class definition '\
               'file and annotation files.'
        detail = 'Missing components:\n'
        if not result['has_path_annotations']:
            detail += "- Annotation path '%s' not found.\n" % result['path_annotations']
        if not result['has_definition']:
            detail += "- Class definition file '%s' not found.\n" % result['definition']
        return information(parent, text, info, detail)

    def is_pick_samples(self):
        result = self._learner.check()
        return result['has_path_annotations'] and result['has_definition']

    def msg_train_classifier(self, parent):
        result = self._learner.check()
        text = 'Classifier training is not possible'
        info = 'You need to pick samples first.'
        detail = 'Missing components:\n'
        if not result['has_arff']:
            detail += "- Feature file '%s' not found.\n" % result['arff']
        return information(parent, text, info, detail)

    def is_train_classifier(self):
        result = self._learner.check()
        return result['has_arff']

    def msg_apply_classifier(self, parent):
        result = self._learner.check()
        text = 'Classifier model not found'
        info = 'You need to train a classifier first.'
        detail = 'Missing components:\n'
        if not result['has_model']:
            detail += "- SVM model file '%s' not found.\n" % result['model']
        if not result['has_range']:
            detail += "- SVM range file '%s' not found.\n" % result['range']
        return information(parent, text, info, detail)

    def is_apply_classifier(self):
        result = self._learner.check()
        return result['has_model'] and result['has_range']

    def _set_info_table(self, conf):
        rows = len(self._learner.lstClassLabels)
        self._table_info.clear()
        names_horizontal = [('Name', 'class name'),
                            ('Samples', 'class samples'),
                            ('Color', 'class color'),
                            ('%PR', 'class precision in %'),
                            ('%SE', 'class sensitivity in %'),
#                            ('AC%', 'class accuracy in %'),
#                            ('SE%', 'class sensitivity in %'),
#                            ('SP%', 'class specificity in %'),
#                            ('PPV%', 'class positive predictive value in %'),
#                            ('NPV%', 'class negative predictive value in %'),
                            ]
        names_vertical = [str(self._learner.nl2l[r]) for r in range(rows)] + ['','#']
        self._table_info.setColumnCount(len(names_horizontal))
        self._table_info.setRowCount(len(names_vertical))
        self._table_info.setVerticalHeaderLabels(names_vertical)
        self._table_info.setColumnWidth(1, 20)
        for c, (name, info) in enumerate(names_horizontal):
            item = QTableWidgetItem(name)
            item.setToolTip(info)
            self._table_info.setHorizontalHeaderItem(c, item)
        r = 0
        for r in range(rows):
            self._table_info.setRowHeight(r, 20)
            label = self._learner.nl2l[r]
            name = self._learner.dctClassNames[label]
            samples = self._learner.names2samples[name]
            self._table_info.setItem(r, 0, QTableWidgetItem(name))
            self._table_info.setItem(r, 1, QTableWidgetItem(str(samples)))
            item = QTableWidgetItem(' ')
            item.setBackground(QBrush(QColor(*hexToRgb(self._learner.dctHexColors[name]))))
            self._table_info.setItem(r, 2, item)

            if not conf is None and r < len(conf):
                item = QTableWidgetItem('%.1f' % (conf.ppv[r] * 100.))
                item.setToolTip('"%s" precision' %  name)
                self._table_info.setItem(r, 3, item)

                item = QTableWidgetItem('%.1f' % (conf.se[r] * 100.))
                item.setToolTip('"%s" sensitivity' %  name)
                self._table_info.setItem(r, 4, item)

#                item = QTableWidgetItem('%.1f' % (conf.ac[r] * 100.))
#                item.setToolTip('"%s" accuracy' %  name)
#                self._table_info.setItem(r, 3, item)
#
#                item = QTableWidgetItem('%.1f' % (conf.se[r] * 100.))
#                item.setToolTip('"%s" sensitivity' %  name)
#                self._table_info.setItem(r, 4, item)
#
#                item = QTableWidgetItem('%.1f' % (conf.sp[r] * 100.))
#                item.setToolTip('"%s" specificity' %  name)
#                self._table_info.setItem(r, 5, item)
#
#                item = QTableWidgetItem('%.1f' % (conf.ppv[r] * 100.))
#                item.setToolTip('"%s" positive predictive value' %  name)
#                self._table_info.setItem(r, 6, item)
#
#                item = QTableWidgetItem('%.1f' % (conf.npv[r] * 100.))
#                item.setToolTip('"%s" negative predictive value' %  name)
#                self._table_info.setItem(r, 7, item)

        if not conf is None:
            self._table_info.setRowHeight(r+1, 20)
            r += 2
            self._table_info.setRowHeight(r, 20)
            name = "overal"
            samples = sum(self._learner.names2samples.values())
            self._table_info.setItem(r, 0, QTableWidgetItem(name))
            self._table_info.setItem(r, 1, QTableWidgetItem(str(samples)))
            item = QTableWidgetItem(' ')
            item.setBackground(QBrush(QColor(*hexToRgb('#FFFFFF'))))
            self._table_info.setItem(r, 2, item)

            item = QTableWidgetItem('%.1f' % (conf.wav_ppv * 100.))
            item.setToolTip('%s per class precision' %  name)
            self._table_info.setItem(r, 3, item)

            item = QTableWidgetItem('%.1f' % (conf.wav_se * 100.))
            item.setToolTip('%s per class sensitivity' %  name)
            self._table_info.setItem(r, 4, item)

#            item = QTableWidgetItem('%.1f' % (conf.av_ac * 100.))
#            item.setToolTip('%s per class accuracy' %  name)
#            self._table_info.setItem(r, 3, item)
#
#            item = QTableWidgetItem('%.1f' % (conf.av_se * 100.))
#            item.setToolTip('%s per class sensitivity' %  name)
#            self._table_info.setItem(r, 4, item)
#
#            item = QTableWidgetItem('%.1f' % (conf.av_sp * 100.))
#            item.setToolTip('%s per class specificity' %  name)
#            self._table_info.setItem(r, 5, item)
#
#            item = QTableWidgetItem('%.1f' % (conf.av_ppv * 100.))
#            item.setToolTip('%s per class positive predictive value' %  name)
#            self._table_info.setItem(r, 6, item)
#
#            item = QTableWidgetItem('%.1f' % (conf.av_npv * 100.))
#            item.setToolTip('%s per class negative predictive value' %  name)
#            self._table_info.setItem(r, 7, item)

        self._table_info.resizeColumnsToContents()

    def _init_conf_table(self, conf):
        self._table_conf.clear()
        if not conf is None:
            conf_array = conf.conf
            rows, cols = conf_array.shape
            self._table_conf.setColumnCount(cols)
            self._table_conf.setRowCount(rows)
            #names2cols = self._learner.dctHexColors
            for c in range(cols):
                self._table_conf.setColumnWidth(c, 20)
                label = self._learner.nl2l[c]
                name = self._learner.dctClassNames[label]
                item = QTableWidgetItem(str(label))
                item.setToolTip('%d : %s' % (label, name))
                #item.setBackground(QBrush(QColor(*hexToRgb(names2cols[name]))))
                self._table_conf.setHorizontalHeaderItem(c, item)
            for r in range(rows):
                self._table_conf.setRowHeight(r, 20)
                label = self._learner.nl2l[r]
                name = self._learner.dctClassNames[label]
                item = QTableWidgetItem(str(label))
                item.setToolTip('%d : %s' % (label, name))
                #item.setForeground(QBrush(QColor(*hexToRgb(names2cols[name]))))
                self._table_conf.setVerticalHeaderItem(r, item)

    def _update_conf_table(self, conf):
        conf_array = conf.conf
        rows, cols = conf_array.shape
        conf_norm = conf_array.swapaxes(0,1) / numpy.array(numpy.sum(conf_array, 1), numpy.float)
        conf_norm = conf_norm.swapaxes(0,1)
        self._table_conf.clearContents()
        for r in range(rows):
            for c in range(cols):
                item = QTableWidgetItem()
                item.setToolTip('%d samples' % conf_array[r,c])
                if not numpy.isnan(conf_norm[r,c]):
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

    SECTION_NAME = SECTION_NAME_CLASSIFICATION
    TABS = ['Primary Channel', 'Secondary Channel', 'Tertiary Channel']
    PROCESS_PICKING = 'PROCESS_PICKING'
    PROCESS_TRAINING = 'PROCESS_TRAINING'
    PROCESS_TESTING = 'PROCESS_TESTING'

    def __init__(self, settings, parent):
        super(ClassificationFrame, self).__init__(settings, parent)
        self._result_frames = {}

        self.register_control_button(self.PROCESS_PICKING,
                                     AnalzyerThread,
                                     ('Pick %s samples', 'Stop %s picking'))
        self.register_control_button(self.PROCESS_TRAINING,
                                     TrainingThread,
                                     ('Train classifier', 'Stop training'))
        self.register_control_button(self.PROCESS_TESTING,
                                     AnalzyerThread,
                                     ('Test classifier', 'Stop testing'))

        self.set_tab_name('Primary Channel')

        self.add_input('primary_classification_envpath')

        frame_results = self._add_result_frame('primary')
        self.add_handler('primary_classification_envpath',
                         frame_results.on_load)

        for tab_name, prefix in [('Secondary Channel', 'secondary'),
                                 ('Tertiary Channel', 'tertiary'),
                                 ]:
            self.set_tab_name(tab_name)

            self.add_input('%s_classification_envpath' % prefix)
            self.add_line()
            self.add_input('%s_classification_regionname' % prefix)

            frame_results = self._add_result_frame(prefix)
            self.add_handler('%s_classification_envpath' % prefix,
                             frame_results.on_load)

        self._init_control()

    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings(self, name, has_timelapse)

        settings.set_section('ObjectDetection')
        prim_id = PrimaryChannel.NAME
        sec_id = SecondaryChannel.NAME
        #sec_regions = settings.get2('secondary_regions')
        settings.set_section('Processing')
        settings.set2('primary_classification', False)
        settings.set2('secondary_classification', False)
        settings.set2('tracking', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})
        settings.set('Output', 'events_export_gallery_images', False)

        show_ids_class = settings.get('Output', 'rendering_class_showids')

        current_tab = self._tab.currentIndex()
        if current_tab == 0:
            settings.set('Processing', 'primary_featureextraction', True)
            settings.set('Processing', 'secondary_featureextraction', False)
            settings.set_section('Classification')
            settings.set2('collectsamples_prefix', 'primary')
            settings.set('Processing', 'secondary_processChannel', False)

            if name == self.PROCESS_TESTING:
                settings.set('Processing', 'primary_classification', True)
                settings.set('General', 'rendering_class', {'primary_classification': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                 'contours': [('primary', 'class_label', 1, False),
                                                                                                              ('primary', '#000000', 1, show_ids_class),
                                                                                                              ]}}})
            else:
                settings.set2('collectsamples', True)
                settings.set('General', 'positions', '')
                settings.set('General', 'framerange_begin', 0)
                settings.set('General', 'framerange_end', 0)

        else:
            settings.set('Processing', 'primary_featureextraction', False)
            settings.set('Processing', 'secondary_featureextraction', True)
            settings.set_section('Classification')
            sec_region = settings.get2('secondary_classification_regionname')
            settings.set2('collectsamples_prefix', 'secondary')
            for k,v in SECONDARY_REGIONS.iteritems():
                settings.set('ObjectDetection', k, v == sec_region)
            settings.set('Processing', 'secondary_processchannel', True)
            if name == self.PROCESS_TESTING:
                settings.set('Processing', 'secondary_classification', True)
                settings.set('General', 'rendering_class', {'secondary_classification_%s' % sec_region: {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                                  'contours': [(sec_region, 'class_label', 1, False),
                                                                                                                               (sec_region, '#000000', 1, show_ids_class),
                                                                                                                               ]}}})
            else:
                settings.set2('collectsamples', True)
                settings.set('General', 'positions', '')
                settings.set('General', 'framerange_begin', 0)
                settings.set('General', 'framerange_end', 0)

        return settings

    def _add_result_frame(self, name):
        frame = self._get_frame()
        result_frame = ClassifierResultFrame(frame, name, self._settings)
        #self._result_frame.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
        #                                             QSizePolicy.Expanding|QSizePolicy.Maximum))
        self._result_frames[name] = result_frame
        frame.layout().addWidget(result_frame, frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1
        return result_frame

    def _get_result_frame(self, name):
        return self._result_frames[name]

    def _update_classifier(self):
        if self._tab.currentIndex() == 0:
            channel = 'primary'
        else:
            channel = 'secondary'
        result_frame = self._result_frames[channel]
        result_frame.load_classifier(check=False)

    def page_changed(self):
        self._update_classifier()

    def tab_changed(self, index):
        self._update_classifier()
