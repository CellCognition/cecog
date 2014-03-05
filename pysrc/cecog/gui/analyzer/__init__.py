"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

from __future__ import division

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = []

import types
import os
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from collections import OrderedDict
from multiprocessing import cpu_count

from cecog import CHANNEL_PREFIX
from cecog.gui.display import TraitDisplayMixin
from cecog.learning.learning import CommonClassPredictor
from cecog.learning.learning import ConfusionMatrix

from cecog.units.time import seconds2datetime

from cecog.gui.util import question
from cecog.gui.util import critical
from cecog.gui.util import information


from cecog.analyzer import CONTROL_1, CONTROL_2
from cecog.analyzer.channel import PrimaryChannel
from cecog.analyzer.channel import SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel
from cecog.plugin.metamanager import MetaPluginManager

from cecog.environment import CecogEnvironment
from cecog.analyzer.core import AnalyzerCore
from cecog.io.imagecontainer import PIXEL_TYPES
from cecog import ccore
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION
from cecog.traits.analyzer.postprocessing import SECTION_NAME_POST_PROCESSING
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.plugin.display import PluginBay
from cecog.gui.widgets.tabcontrol import TabControl
from cecog.analyzer.ibb import IBBAnalysis, SecurinAnalysis

from cecog.threads import PickerThread
from cecog.threads import AnalyzerThread
from cecog.threads import TrainingThread
from cecog.threads import ErrorCorrectionThread
from cecog.threads import PostProcessingThread
from cecog.multiprocess.multianalyzer import MultiAnalyzerThread

from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION
from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
from cecog.traits.analyzer.classification import SECTION_NAME_CLASSIFICATION
from cecog.traits.analyzer.tracking import SECTION_NAME_TRACKING
from cecog.traits.analyzer.eventselection import SECTION_NAME_EVENT_SELECTION
from cecog.traits.analyzer.output import SECTION_NAME_OUTPUT
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.traits.analyzer.cluster import SECTION_NAME_CLUSTER
from cecog.gui.progressdialog import ProgressDialog


class BaseFrame(TraitDisplayMixin):

    ICON = ":cecog_analyzer_icon"
    TABS = None
    CONTROL = CONTROL_1

    toggle_tabs = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(self, settings, parent, name):
        super(BaseFrame, self).__init__(settings, parent)
        self.plugin_mgr = MetaPluginManager()
        self.name = name
        self._is_active = False
        self._intervals = list()

        self._tab_name = None
        self._control = QFrame(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tab = TabControl(self)

        tabs = [self._tab_name] if self.TABS is None else self.TABS
        for name in tabs:
            frame = QFrame(self._tab)
            frame._input_cnt = 0
            layout2 = QGridLayout(frame)
            layout2.setContentsMargins(20, 20, 20, 20)
            self._tab.add_tab(name, frame)

        self._tab.set_active_index(0)
        self._tab.current_changed.connect(self.on_tab_changed)

        layout.addWidget(self._tab)
        layout.addWidget(self._control)

    @pyqtSlot('int')
    def on_tab_changed(self, index):
        self.tab_changed(index)

    def set_tab_name(self, name):
        self._tab_name = name

    def set_active(self, state=True):
        self._is_active = state

    def _get_frame(self, name=None):
        if name is None:
            name = self._tab_name
        return self._tab.get_frame(name)

    def add_expanding_spacer(self):
        frame = self._get_frame(name=self._tab_name)
        dummy = QWidget(frame)
        dummy.setMinimumSize(0,0)
        dummy.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                        QSizePolicy.Expanding))
        frame.layout().addWidget(dummy, frame._input_cnt, 0)
        frame._input_cnt += 1

    def add_line(self):
        frame = self._get_frame(name=self._tab_name)
        line = QFrame(frame)
        line.setFrameShape(QFrame.HLine)
        frame.layout().addWidget(line, frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1

    def add_pixmap(self, pixmap, align=Qt.AlignLeft):
        frame = self._get_frame(name=self._tab_name)
        label = QLabel(frame)
        label.setPixmap(pixmap)
        frame.layout().addWidget(label, frame._input_cnt, 0, 1, 2, align)
        frame._input_cnt += 1

    def page_changed(self):
        """Abstract method. Invoked by the AnalyzerMainWindow when this frame
        is activated for display.
        """
        pass

    def settings_loaded(self):
        """change notification called after a settings file is loaded."""
        pass

    def tab_changed(self, index):
        pass

    def add_plugin_bay(self, plugin_manager, settings):
        frame = self._get_frame(self._tab_name)
        frame_layout = frame.layout()
        frame_layout.addWidget(PluginBay(self, plugin_manager, settings),
                               frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1


class _ProcessorMixin(object):
    def __init__(self, parent):
        self.idialog = parent.idialog

        self._is_running = False
        self._is_abort = False
        self._has_error = True
        self._current_process = None
        self._image_combo = None
        self._stage_infos = {}
        self._process_items = None

        self._control_buttons = OrderedDict()

        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.connect(shortcut, SIGNAL('activated()'), self._on_esc_pressed)

    def register_process(self, name):
        pass

    def register_control_button(self, name, cls, labels):
        self._control_buttons[name] = {'labels' : labels,
                                       'widget' : None,
                                       'cls'    : cls}

    def _init_control(self, has_images=True):
        layout = QHBoxLayout(self._control)
        layout.setContentsMargins(0, 0, 0, 0)

        self._progress_label0 = QLabel(self._control)
        self._progress_label0.setText('')
        layout.addWidget(self._progress_label0)

        self._progress0 = QProgressBar(self._control)
        self._progress0.setTextVisible(False)
        layout.addWidget(self._progress0)

        if has_images:
            self._show_image = QCheckBox('Show images', self._control)
            self._show_image.setChecked(True)
            layout.addWidget(self._show_image)

        for name in self._control_buttons:
            w_button = QPushButton('', self._control)
            layout.addWidget(w_button)
            handler = lambda x: lambda : self._on_process_start(x)
            self.connect(w_button, SIGNAL('clicked()'), handler(name))
            self._control_buttons[name]['widget'] = w_button

        help_button = QToolButton(self._control)
        help_button.setIcon(QIcon(':question_mark'))
        handler = lambda x: lambda : self._on_show_help(x)
        self.connect(help_button, SIGNAL('clicked()'), handler('controlpanel'))
        layout.addWidget(help_button)

        if not self.TABS is None:
            self._tab.current_changed.connect(self._on_tab_changed)
            self._on_tab_changed(0)
        else:
            for name in self._control_buttons:
                self._set_control_button_text(name=name)

    @classmethod
    def get_special_settings(cls, settings, has_timelapse=True):
        settings = settings.copy()

        # try to resolve the paths relative to the package dir
        # (only in case of an relative path given)
        converts = [('General', 'pathin'),
                    ('General', 'pathout'),
                    ('Classification', 'primary_classification_envpath'),
                    ('Classification', 'secondary_classification_envpath'),
                    ('Classification', 'tertiary_classification_envpath'),
                    ('ErrorCorrection', 'primary_graph'),
                    ('ErrorCorrection', 'secondary_graph'),
                    ('ErrorCorrection', 'mappingfile_path'),
                    ]
        for section, option in converts:
            value = settings.get(section, option)
            settings.set(section, option, CecogEnvironment.convert_package_path(value))
        return settings

    def _get_modified_settings(self, name, has_timelapse):
        return self.get_special_settings(self._settings, has_timelapse)

    def _on_tab_changed(self, idx):
        self._tab_name = CHANNEL_PREFIX[idx]
        for name in self._control_buttons:
            self._set_control_button_text(name=name)

    def _set_control_button_text(self, name=None, idx=0):
        if name is None:
            name = self._current_process
        w_button = self._control_buttons[name]['widget']
        try:
            text = self._control_buttons[name]['labels'][idx] % self._tab_name
        except:
            text = self._control_buttons[name]['labels'][idx]
        w_button.setText(text)

    def enable_control_buttons(self, state=True):
        for name in self._control_buttons:
            w_button = self._control_buttons[name]['widget']
            w_button.setEnabled(state)

    def _toggle_control_buttons(self, name=None):
        if name is None:
            name = self._current_process
        for name2 in self._control_buttons:
            if name != name2:
                w_button = self._control_buttons[name2]['widget']
                w_button.setEnabled(not w_button.isEnabled())

    def _clear_image(self):
        """Pop up and clear the image display"""
        self.idialog.clearImage()

    def _on_process_start(self, name, start_again=False):
        if not self._is_running or start_again:
            is_valid = True
            self._is_abort = False
            self._has_error = False

            if self._process_items is None:
                cls = self._control_buttons[name]['cls']
                if type(cls) == types.ListType:
                    self._process_items = cls
                    self._current_process_item = 0
                    cls = cls[self._current_process_item]
                else:
                    self._process_items = None
                    self._current_process_item = 0
            else:
                cls = self._process_items[self._current_process_item]


            if self.name == SECTION_NAME_CLASSIFICATION:
                result_frame = self._get_result_frame(self._tab_name)
                result_frame.load_classifier(check=False)
                learner = result_frame._learner

                if name == self.PROCESS_PICKING:
                    if not result_frame.is_pick_samples():
                        is_valid = False
                        result_frame.msg_pick_samples(self)
                    elif result_frame.is_train_classifier():
                        if not question(self, 'Samples already picked',
                                    'Do you want to pick samples again and '
                                    'overwrite previous '
                                    'results?'):
                            is_valid = False

                elif name == self.PROCESS_TRAINING:
                    if not result_frame.is_train_classifier():
                        is_valid = False
                        result_frame.msg_train_classifier(self)
                    elif result_frame.is_apply_classifier():
                        if not question(self, 'Classifier already trained',
                                    'Do you want to train the classifier '
                                    'again?'):
                            is_valid = False

                elif name == self.PROCESS_TESTING and not result_frame.is_apply_classifier():
                    is_valid = False
                    result_frame.msg_apply_classifier(self)

            if cls is MultiAnalyzerThread:
                ncpu = cpu_count()
                (ncpu, ok) = QInputDialog.getInt(None, "On your machine are %d processers available." % ncpu, \
                                             "Select the number of processors", \
                                              ncpu, 1, ncpu*2)
                if not ok:
                    self._process_items = None
                    is_valid = False

            if is_valid:
                self._current_process = name

                if not start_again:
                    self.parent().main_window.log_window.clear()

                    self._is_running = True
                    self._stage_infos = {}

                    self._toggle_tabs(False)
                    # disable all section button of the main widget
                    self.toggle_tabs.emit(self.get_name())

                    self._set_control_button_text(idx=1)
                    self._toggle_control_buttons()

                imagecontainer = self.parent().main_window._imagecontainer

                if cls is PickerThread:
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)
                    self._analyzer = cls(self, self._current_settings, imagecontainer)
                    self._clear_image()

                elif cls is AnalyzerThread:
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)
                    self._analyzer = cls(self, self._current_settings, imagecontainer)
                    self._clear_image()

                elif cls is TrainingThread:
                    self._current_settings = self._settings.copy()

                    self._analyzer = cls(self, self._current_settings, result_frame._learner)
                    self._analyzer.setTerminationEnabled(True)

                    self._analyzer.conf_result.connect(result_frame.on_conf_result,
                                                       Qt.QueuedConnection)
                    result_frame.reset()

                elif cls is MultiAnalyzerThread:
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)
                    self._analyzer = cls(self, self._current_settings, imagecontainer, ncpu)


                elif cls is ErrorCorrectionThread:
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)
                    self._analyzer = cls(self, self._current_settings,
                                         self.parent().main_window._imagecontainer)


                elif cls is PostProcessingThread:
                    learner_dict = {}
                    for kind in ['primary', 'secondary']:
                        _resolve = lambda x,y: self._settings.get(x, '%s_%s' % (kind, y))
                        env_path = CecogEnvironment.convert_package_path(_resolve('Classification', 'classification_envpath'))
                        if (_resolve('Processing', 'classification') and
                            (kind == 'primary' or self._settings('General', 'process_secondary'))):
                            learner = CommonClassPredictor( \
                                env_path,
                                _resolve('ObjectDetection', 'channelid'),
                                _resolve('Classification', 'classification_regionname'))

                            learner.importFromArff()
                            learner_dict[kind] = learner
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)
                    self._analyzer = cls(self, self._current_settings, learner_dict, imagecontainer)
                    self._analyzer.setTerminationEnabled(True)

                self._analyzer.finished.connect(self._on_process_finished)
                self._analyzer.stage_info.connect(self._on_update_stage_info, Qt.QueuedConnection)
                self._analyzer.analyzer_error.connect(self._on_error, Qt.QueuedConnection)
                self._analyzer.image_ready.connect(self._on_update_image)

                self._analyzer.start(QThread.LowestPriority)
                if self._current_process_item == 0:
                    self.status_message.emit('Process started...')

        else:
            self._abort_processing()

    def _toggle_tabs(self, state):
        if not self.TABS is None:
            self._tab.enable_non_active(state)

    def _abort_processing(self):
        self.setCursor(Qt.BusyCursor)
        self._is_abort = True
        self.dlg = ProgressDialog('terminating...', None, 0, 0, self)
        self.dlg.exec_(lambda: self._analyzer.abort(wait=True))
        self.setCursor(Qt.ArrowCursor)

    def _on_error(self, msg, short='An error occurred during processing!'):
        self._has_error = True
        critical(self, short, detail=msg)

    def _on_process_finished(self):
        self._analyzer.image_ready.disconnect(self._on_update_image)

        if (not self._process_items is None and
            self._current_process_item+1 < len(self._process_items) and
            not self._is_abort and
            not self._has_error):
            self._current_process_item += 1
            self._on_process_start(self._current_process, start_again=True)
        else:
            self._is_running = False
            self._set_control_button_text(idx=0)
            self._toggle_control_buttons()
            self._toggle_tabs(True)
            # enable all section button of the main widget
            self.toggle_tabs.emit(self.get_name())
            if not self._is_abort and not self._has_error:
                if self.name == SECTION_NAME_OBJECTDETECTION:
                    msg = 'Object detection successfully finished.'
                elif self.name == SECTION_NAME_CLASSIFICATION:
                    if self._current_process == self.PROCESS_PICKING:
                        msg = 'Samples successfully picked.\n\n'\
                              'Please train the classifier now based on the '\
                              'newly picked samples.'
                        result_frame = self._get_result_frame(self._tab_name)
                        result_frame.load_classifier(check=False)
#                        nr_removed = len(result_frame._learner.filter_nans(apply=False))
                        nr_removed = len(result_frame._learner.nan_features)
                        if nr_removed > 0:
                            msg += '\n\n%d features contained NA values and will be removed from training.' % nr_removed
                    elif self._current_process == self.PROCESS_TRAINING:
                        msg = 'Classifier successfully trained.\n\n'\
                              'You can test the classifier performance here'\
                              'visually or apply the classifier in the '\
                              'processing workflow.'
                    elif self._current_process == self.PROCESS_TESTING:
                        msg = 'Classifier testing successfully finished.'
                elif self.name == SECTION_NAME_TRACKING:
                    msg = 'Tracking successfully finished.'
                elif self.name == SECTION_NAME_EVENT_SELECTION:
                    msg = 'event selection successfully finished.'
                elif self.name == SECTION_NAME_ERRORCORRECTION:
                    msg = 'HMM error correction successfully finished.'
                elif self.name == SECTION_NAME_PROCESSING:
                    msg = 'Processing successfully finished.'
                elif self.name == SECTION_NAME_POST_PROCESSING:
                    msg = 'Postprocessing successfully finished'

                information(self, 'Process finished', msg)
                self.status_message.emit(msg)
            else:
                if self._is_abort:
                    self.status_message.emit('Process aborted by user.')
                elif self._has_error:
                    self.status_message.emit('Process aborted by error.')

            self._current_process = None
            self._process_items = None

    def _on_esc_pressed(self):
        if self._is_running:
            self._abort_processing()
            self._analyzer.image_ready.disconnect(self._on_update_image)

    def _on_update_stage_info(self, info):
        sep = '   |   '
        info = dict([(str(k), v) for k,v in info.iteritems()])
        #print info
        if self.CONTROL == CONTROL_1:
            if info['stage'] == 0:
                self._progress0.setRange(info['min'], info['max'])
                if not info['progress'] is None:
                    self._progress0.setValue(info['progress'])
                    if info['max'] != 0:
                        self._progress_label0.setText('%3.1f%%' %\
                                                      (info['progress']*100.0/info['max']))
                    msg = ''
                    if 'meta' in info:
                        msg += '%s' % info['meta']
                    if 'text' in info:
                        msg += '   %s' % info['text']
                    if info['progress'] > info['min'] and 'interval' in info:
                        interval = info['interval']
                        self._intervals.append(interval)
                        avg = numpy.average(self._intervals)
                        estimate = seconds2datetime(avg*float(info['max']-info['progress']))
                        msg += '%s~ %.1fs / %s%s%s remaining' % (sep,
                                                                 avg,
                                                                 info['item_name'],
                                                                 sep,
                                                                 estimate.strftime("%H:%M:%S"))
                    else:
                        self._intervals = []
                    self.status_message.emit(msg)
                else:
                    self._progress_label0.setText('')
            else:
                self._stage_infos[info['stage']] = info
                if len(self._stage_infos) > 1:
                    total = self._stage_infos[1]['max']*self._stage_infos[2]['max']
                    current = (self._stage_infos[1]['progress']-1)*self._stage_infos[2]['max']+self._stage_infos[2]['progress']
                    #print current, total
                    self._progress0.setRange(0, total)
                    self._progress0.setValue(current)
                    #info = self._stage_infos[2]
                    self._progress_label0.setText('%.1f%%' % (current*100.0/total))
                    sep = '   |   '
                    msg = '%s   %s%s%s' % (self._stage_infos[2]['meta'],
                                           self._stage_infos[1]['text'],
                                           sep,
                                           self._stage_infos[2]['text'])
                    if current > 1 and ('interval' in info.keys()):
                        interval = info['interval']
                        self._intervals.append(interval)
                        estimate = seconds2datetime(
                            numpy.average(self._intervals)*float(total-current))
                        msg += '%s%.1fs / %s%s%s remaining' % (sep,
                                                               interval,
                                                               self._stage_infos[2]['item_name'],
                                                               sep,
                                                               estimate.strftime("%H:%M:%S"))
                    else:
                        self._intervals = []
                    self.status_message.emit(msg)
        elif self.CONTROL == CONTROL_2:
            if info['stage'] == 1:
                if 'progress' in info:
                    self._analyzer_progress1.setRange(info['min'], info['max'])
                    self._analyzer_progress1.setValue(info['progress'])
                    self._analyzer_label1.setText('%s (%d / %d)' % (info['text'],
                                                                    info['progress'],
                                                                    info['max']))
                else:
                    self._analyzer_label1.setText(info['text'])
            else:
                if 'progress' in info:
                    self._analyzer_progress2.setRange(info['min'], info['max'])
                    self._analyzer_progress2.setValue(info['progress'])
                    self._analyzer_label2.setText('%s: %s (%d / %d)' % (info['text'],
                                                                        info['meta'],
                                                                        info['progress'],
                                                                        info['max']))
                else:
                    self._analyzer_label2.setText(info['text'])

    def _on_update_image(self, images, message):
        if self._show_image.isChecked():
            self.idialog.updateImages(images, message)
            if not self.idialog.isVisible():
                self.idialog.raise_()


class BaseProcessorFrame(BaseFrame, _ProcessorMixin):

    def __init__(self, settings, parent, name):
        BaseFrame.__init__(self, settings, parent, name)
        _ProcessorMixin.__init__(self, parent)

    def set_active(self, state):
        # set internl state and enable/disable control buttons
        super(BaseProcessorFrame, self).set_active(state)
        self.enable_control_buttons(state)
