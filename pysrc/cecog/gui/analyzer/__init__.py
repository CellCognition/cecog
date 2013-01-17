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

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = []

import types
import traceback
import logging
import logging.handlers
import sys
import os
import time
import copy
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from collections import OrderedDict
from pdk.datetimeutils import TimeInterval

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import sklearn.hmm as hmm

from multiprocessing import cpu_count

from cecog import CHANNEL_PREFIX
from cecog.gui.display import TraitDisplayMixin
from cecog.learning.learning import (CommonObjectLearner,
                                     CommonClassPredictor,
                                     ConfusionMatrix,
                                     )
from cecog.util.util import hexToRgb, write_table
from cecog.gui.util import (ImageRatioDisplay,
                            numpy_to_qimage,
                            question,
                            critical,
                            information,
                            status,
                            waitingProgressDialog,
                            )
from cecog.analyzer import CONTROL_1, CONTROL_2

from cecog.analyzer.channel import PrimaryChannel
from cecog.analyzer.channel import SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel

from cecog.analyzer.core import AnalyzerCore
from cecog.io.imagecontainer import PIXEL_TYPES
from cecog.config import R_SOURCE_PATH
from cecog import ccore
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION
from cecog.traits.analyzer.postprocessing import SECTION_NAME_POST_PROCESSING
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.traits.settings import convert_package_path
from cecog.analyzer.gallery import compose_galleries
from cecog.plugin.display import PluginBay
from cecog.gui.widgets.tabcontrol import TabControl
from cecog.analyzer.ibb import IBBAnalysis, SecurinAnalysis

from cecog.threads.picker import PickerThread
from cecog.threads.analyzer import AnalyzerThread
from cecog.threads.training import TrainingThread
from cecog.threads.hmm_scafold import HmmThread_Python_Scafold
from cecog.threads.hmm import HmmThread
from cecog.threads.post_processing import PostProcessingThread
from cecog.multiprocess.multianalyzer import MultiAnalyzerThread

def mk_stochastic(k):
    """function [T,Z] = mk_stochastic(T)
    MK_STOCHASTIC ensure the matrix is a stochastic matrix,
    i.e., the sum over the last dimension is 1."""
    raw_A = numpy.random.uniform( size = k * k ).reshape( ( k, k ) )
    return ( raw_A.T / raw_A.T.sum( 0 ) ).T

def dhmm_correction(n_clusters, labels):
    trans = mk_stochastic(n_clusters)
    eps = numpy.spacing(1)
    sprob = numpy.array([1-eps,eps,eps,eps,eps,eps])
    dhmm = hmm.MultinomialHMM(
        n_components=n_clusters,transmat = trans,startprob=sprob)
    eps = 1e-3;
    dhmm.emissionprob = numpy.array([[1-eps, eps, eps, eps, eps, eps],
                    [eps, 1-eps, eps, eps, eps, eps],
                    [eps, eps, 1-eps, eps, eps, eps],
                    [eps, eps, eps, 1-eps, eps, eps],
                    [eps, eps, eps, eps, 1-eps, eps],
                    [eps, eps, eps, eps, eps, 1-eps]]);
    dhmm.fit([labels], init_params ='')
    # vector format [1 x num_tracks *num_frames]
    labels_dhmm = dhmm.predict(labels)
    return labels_dhmm


class BaseFrame(TraitDisplayMixin):

    ICON = ":cecog_analyzer_icon"
    TABS = None
    CONTROL = CONTROL_1

    toggle_tabs = pyqtSignal(str)

    def __init__(self, settings, parent):
        super(BaseFrame, self).__init__(settings, parent)
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
        '''
          Abstract method. Invoked by the AnalyzerMainWindow when this frame
        is activated for display.
        '''
        pass

    def settings_loaded(self):
        '''
        change notification called after a settings file is loaded
        '''
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
    def __init__(self):
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
        layout.setContentsMargins(0,0,0,0)

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
                    ('ErrorCorrection', 'primary_graph'),
                    ('ErrorCorrection', 'secondary_graph'),
                    ('ErrorCorrection', 'mappingfile_path'),
                    ]
        for section, option in converts:
            value = settings.get(section, option)
            settings.set(section, option, convert_package_path(value))
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
        if not qApp._image_dialog is None:
            pix = qApp._graphics.pixmap()
            pix2 = QPixmap(pix.size())
            pix2.fill(Qt.black)
            qApp._graphics.setPixmap(pix2)
            qApp._image_dialog.raise_()

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

                    # remove HmmThread if process is not first in list and
                    # not valid error correction was activated
                    if (HmmThread in self._process_items and
                        self._process_items.index(HmmThread) > 0 and
                        not (self._settings.get('Processing', 'primary_errorcorrection') or
                             (self._settings.get('Processing', 'secondary_errorcorrection') and
                              self._settings.get('Processing', 'secondary_processchannel')))):
                        self._process_items.remove(HmmThread)

                else:
                    self._process_items = None
                    self._current_process_item = 0
            else:
                cls = self._process_items[self._current_process_item]


            if self.SECTION_NAME == 'Classification':
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

            elif cls is HmmThread:

                success, cmd = HmmThread.test_executable(self._settings.get('ErrorCorrection', 'filename_to_R'))
                if not success:
                    critical(self, 'Error running R',
                             "The R command line program '%s' could not be executed.\n\n"\
                             "Make sure that the R-project is installed.\n\n"\
                             "See README.txt for details." % cmd)
                    is_valid = False

            elif cls is MultiAnalyzerThread:
                ncpu = cpu_count()
                (ncpu, ok) = QInputDialog.getInt(None, "On your machine are %d processers available." % ncpu, \
                                             "Select the number of processors", \
                                              ncpu, 1, ncpu*2)
                if not ok:
                    self._process_items = None
                    is_valid = False

            if is_valid:
                self._current_process = name
                #qApp._image_dialog = None

                if not start_again:
                    qApp._log_window.clear()

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
                    self._set_display_renderer_info()
                    self._clear_image()

                elif cls is AnalyzerThread:
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)
                    self._analyzer = cls(self, self._current_settings, imagecontainer)
                    self._set_display_renderer_info()
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

                    self._set_display_renderer_info()

                elif cls is HmmThread:
                    self._current_settings = self._get_modified_settings(name, imagecontainer.has_timelapse)

                      # FIXME: classifier handling needs revision!!!
                    learner_dict = {}
                    for kind in ['primary', 'secondary']:
                        _resolve = lambda x,y: self._settings.get(x, '%s_%s' % (kind, y))
                        env_path = convert_package_path(_resolve('Classification', 'classification_envpath'))
                        if (os.path.exists(env_path)
                              and (kind == 'primary' or self._settings.get('Processing', 'secondary_processchannel'))
                             ):

                            learner = CommonClassPredictor( \
                                env_path,
                                _resolve('ObjectDetection', 'channelid'),
                                _resolve('Classification', 'classification_regionname'))
                            learner.importFromArff()
                            learner_dict[kind] = learner

                    ### Whee, I like it... "self.parent().main_window._imagecontainer" crazy, crazy, michael... :-)
                    self._analyzer = cls(self, self._current_settings,
                                         learner_dict,
                                         self.parent().main_window._imagecontainer)
                    self._analyzer.setTerminationEnabled(True)

                elif cls is PostProcessingThread:
                    learner_dict = {}
                    for kind in ['primary', 'secondary']:
                        _resolve = lambda x,y: self._settings.get(x, '%s_%s' % (kind, y))
                        env_path = convert_package_path(_resolve('Classification', 'classification_envpath'))
                        if (_resolve('Processing', 'classification') and
                            (kind == 'primary' or self._settings.get('Processing', 'secondary_processchannel'))):
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

                self._analyzer.start(QThread.LowestPriority)
                if self._current_process_item == 0:
                    status('Process started...')

        else:
            self._abort_processing()

    def _toggle_tabs(self, state):
        if not self.TABS is None:
            self._tab.enable_non_active(state)

    def _abort_processing(self):
        self.setCursor(Qt.BusyCursor)
        self._is_abort = True
        self.dlg = waitingProgressDialog('Please wait until the processing has been terminated...', self)
        self.dlg.setTarget(self._analyzer.abort, wait=True)
        self.dlg.exec_()
        self.setCursor(Qt.ArrowCursor)

    def _on_render_changed(self, name):
        #FIXME: proper sub-classing needed
        self._analyzer.renderer = name

    def _on_error(self, msg):
        self._has_error = True
        critical(self, 'An error occurred during processing.', detail=msg)

    def _on_process_finished(self):

        if (not self._process_items is None and
            self._current_process_item+1 < len(self._process_items) and
            not self._is_abort and
            not self._has_error):
            self._current_process_item += 1
            self._on_process_start(self._current_process, start_again=True)
        else:
            self._is_running = False
            #logger = logging.getLogger()
            #logger.removeHandler(self._handler)
            self._set_control_button_text(idx=0)
            self._toggle_control_buttons()
            self._toggle_tabs(True)
            # enable all section button of the main widget
            self.toggle_tabs.emit(self.get_name())
            if not self._is_abort and not self._has_error:
                if self.SECTION_NAME == 'ObjectDetection':
                    msg = 'Object detection successfully finished.'
                elif self.SECTION_NAME == 'Classification':
                    if self._current_process == self.PROCESS_PICKING:
                        msg = 'Samples successfully picked.\n\n'\
                              'Please train the classifier now based on the '\
                              'newly picked samples.'
                        result_frame = self._get_result_frame(self._tab_name)
                        result_frame.load_classifier(check=False)
                        nr_removed = len(result_frame._learner.filterData(apply=False))
                        if nr_removed > 0:
                            msg += '\n\n%d features contained NA values and will be removed from training.' % nr_removed
                    elif self._current_process == self.PROCESS_TRAINING:
                        msg = 'Classifier successfully trained.\n\n'\
                              'You can test the classifier performance here'\
                              'visually or apply the classifier in the '\
                              'processing workflow.'
                    elif self._current_process == self.PROCESS_TESTING:
                        msg = 'Classifier testing successfully finished.'
                elif self.SECTION_NAME == 'Tracking':
                    if self._current_process == self.PROCESS_TRACKING:
                        msg = 'Tracking successfully finished.'
                    elif self._current_process == self.PROCESS_SYNCING:
                        msg = 'Motif selection successfully finished.'
                elif self.SECTION_NAME == 'ErrorCorrection':
                    msg = 'HMM error correction successfully finished.'
                elif self.SECTION_NAME == 'Processing':
                    msg = 'Processing successfully finished.'
                elif self.SECTION_NAME == "PostProcessing":
                    msg = 'Postprocessing successfully finished'

                information(self, 'Process finished', msg)
                status(msg)
            else:
                if self._is_abort:
                    status('Process aborted by user.')
                elif self._has_error:
                    status('Process aborted by error.')

            self._current_process = None
            self._process_items = None

    def _on_esc_pressed(self):
        if self._is_running:
            self._abort_processing()

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
                        estimate = TimeInterval(avg * float(info['max']-info['progress']))
                        msg += '%s~ %.1fs / %s%s%s remaining' % (sep,
                                                               #interval.get_interval(),
                                                               avg,
                                                               info['item_name'],
                                                               sep,
                                                               estimate.format())
                    else:
                        self._intervals = []
                    status(msg)
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
                        estimate = TimeInterval(numpy.average(self._intervals) *
                                                float(total-current))
                        msg += '%s%.1fs / %s%s%s remaining' % (sep,
                                                               interval,
                                                               self._stage_infos[2]['item_name'],
                                                               sep,
                                                               estimate.format())
                    else:
                        self._intervals = []
                    status(msg)
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

    def _on_update_image(self, image_rgb, info, filename):
        if self._show_image.isChecked():
            # FIXME:
            if image_rgb.width % 4 != 0:
                image_rgb = ccore.subImage(
                    image_rgb, ccore.Diff2D(0,0), ccore.Diff2D(image_rgb.width - \
                               (image_rgb.width % 4), image_rgb.height))
            qimage = numpy_to_qimage(image_rgb.toArray(copy=False))

            if qApp._image_dialog is None:
                qApp._image_dialog = QFrame()
                ratio = qimage.height()/float(qimage.width())
                qApp._image_dialog.setGeometry(50, 50, 800, 800*ratio)

                shortcut = QShortcut(QKeySequence(Qt.Key_Escape), qApp._image_dialog)
                shortcut.activated.connect(self._on_esc_pressed)

                layout = QVBoxLayout(qApp._image_dialog)
                layout.setContentsMargins(0,0,0,0)

                qApp._graphics = ImageRatioDisplay(qApp._image_dialog, ratio)
                qApp._graphics.setScaledContents(True)
                qApp._graphics.resize(800, 800*ratio)
                qApp._graphics.setMinimumSize(QSize(100,100))
                policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                policy.setHeightForWidth(True)
                qApp._graphics.setSizePolicy(policy)
                layout.addWidget(qApp._graphics)

                dummy = QFrame(qApp._image_dialog)
                dymmy_layout = QHBoxLayout(dummy)
                dymmy_layout.setContentsMargins(5,5,5,5)

                qApp._image_combo = QComboBox(dummy)
                qApp._image_combo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                            QSizePolicy.Fixed))
                self._set_display_renderer_info()

                dymmy_layout.addStretch()
                dymmy_layout.addWidget(qApp._image_combo)
                dymmy_layout.addStretch()
                layout.addWidget(dummy)
                layout.addStretch()

                qApp._image_dialog.show()
                qApp._image_dialog.raise_()
            #else:
            #    qApp._graphics_pixmap.setPixmap(QPixmap.fromImage(qimage))
            qApp._graphics.setPixmap(QPixmap.fromImage(qimage))
            qApp._image_dialog.setWindowTitle(info)
            qApp._image_dialog.setToolTip(filename)

            if not qApp._image_dialog.isVisible():
                qApp._image_dialog.show()
                qApp._image_dialog.raise_()


    def _set_display_renderer_info(self):
        # WTF - to exclude properties for gallery images
        rendering = [x for x in self._current_settings.get('General', 'rendering')
                     if not x in CHANNEL_PREFIX]
        rendering += self._current_settings.get('General', 'rendering_class').keys()
        rendering.sort()

        idx = 0
        if not qApp._image_dialog is None:
            widget = qApp._image_combo
            current = widget.currentText()
            widget.clear()
            if len(rendering) > 1:
                widget.addItems(rendering)
                widget.show()
                widget.currentIndexChanged[str].connect(self._on_render_changed)
                if current in rendering:
                    widget.setCurrentIndex(widget.findText(current, Qt.MatchExactly))
                    idx = rendering.index(current)
            else:
                widget.hide()

        if len(rendering) > 0:
            self._analyzer.renderer = rendering[idx]
        else:
            self._analyzer.renderer = None

        self._analyzer.image_ready.connect(self._on_update_image)

class BaseProcessorFrame(BaseFrame, _ProcessorMixin):

    def __init__(self, settings, parent):
        BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

    def set_active(self, state):
        # set internl state and enable/disable control buttons
        super(BaseProcessorFrame, self).set_active(state)
        self.enable_control_buttons(state)
