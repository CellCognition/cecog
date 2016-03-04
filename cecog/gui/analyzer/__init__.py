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


import types
import numpy

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from collections import OrderedDict
from multiprocessing import cpu_count

from cecog import CHANNEL_PREFIX
from cecog.gui.display import TraitDisplayMixin
from cecog.units.time import seconds2datetime

from cecog.plugin.metamanager import MetaPluginManager
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION
from cecog.plugin.display import PluginBay
from cecog.gui.widgets.tabcontrol import TabControl

from cecog.threads import TrainerThread
from cecog.threads import AnalyzerThread
from cecog.threads import ErrorCorrectionThread
from cecog.multiprocess.multianalyzer import MultiAnalyzerThread

from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION
from cecog.traits.analyzer.classification import SECTION_NAME_CLASSIFICATION
from cecog.traits.analyzer.tracking import SECTION_NAME_TRACKING
from cecog.traits.analyzer.eventselection import SECTION_NAME_EVENT_SELECTION
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.gui.progressdialog import ProgressDialog
from cecog.gui.processcontrol import ProcessControl



class BaseFrame(TraitDisplayMixin):

    ICON = ":cecog_analyzer_icon"
    TABS = None

    toggle_tabs = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(self, settings, parent, name):
        super(BaseFrame, self).__init__(settings, parent, name)
        self.plugin_mgr = MetaPluginManager()
        self.name = name
        self._is_active = False
        self._intervals = list()

        self._tab_name = None
        self.process_control = ProcessControl(self)
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
        self._tab.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self._tab)
        layout.addWidget(self.process_control)

    @property
    def log_window(self):
        return self.parent().log_window

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
        frame_layout.addWidget(
            PluginBay(self, plugin_manager, settings, self.parent().assistant),
            frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1



class BaseProcessorFrame(BaseFrame):

    def __init__(self, settings, parent, name):
        super(BaseProcessorFrame, self).__init__(settings, parent, name)

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
        shortcut.activated.connect(self._on_esc_pressed)


    def set_active(self, state):
        # set intern state and enable/disable control buttons
        super(BaseProcessorFrame, self).set_active(state)
        self.process_control.setButtonsEnabled(state)

    def _on_update_image(self, images, message):
        if self.process_control.showImages():
            self.idialog.updateImages(images, message)
            if not self.idialog.isVisible():
                self.idialog.raise_()

    def register_process(self, name):
        pass

    def register_control_button(self, name, cls, labels):

        self._control_buttons[name] = {'labels': labels,
                                       'cls' : cls}

    def _init_control(self, has_images=True):

        if not has_images:
            self.process_control.hideImageCheckBox()

        for name in self._control_buttons:
            slot = lambda x: lambda : self._on_process_start(x)
            self.process_control.addControlButton(name, slot(name))

        if not self.TABS is None:
            self._tab.currentChanged.connect(self._on_tab_changed)
            self._on_tab_changed(0)
        else:
            for name in self._control_buttons:
                self._set_control_button_text(name=name)


    def _set_control_button_text(self, name=None, idx=0):

        if name is None:
            name = self._current_process
        try:
            text = self._control_buttons[name]['labels'][idx] % self._tab_name
        except:
            text = self._control_buttons[name]['labels'][idx]

        self.process_control.buttonByName(name).setText(text)


    def _toggle_control_buttons(self, name=None):
        if name is None:
            name = self._current_process

        for name2 in self._control_buttons:
            if name != name2:
                btn = self.process_control.buttonByName(name)
                btn.setEnabled(not btn.isEnabled())

    @classmethod
    def get_special_settings(cls, settings, has_timelapse=True):
        settings = settings.copy()
        return settings

    def _get_modified_settings(self, name, has_timelapse):
        return self.get_special_settings(self._settings, has_timelapse)

    def _on_tab_changed(self, idx):
        self._tab_name = CHANNEL_PREFIX[idx]
        for name in self._control_buttons:
            self._set_control_button_text(name=name)

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
                result_frame.load_classifier()

                if name == self.Training:
                    is_valid = True
                    if result_frame.classifier_exists():
                        ret = QMessageBox.question(self,'Trained Classifier found',
                                                   'Do you want to owerwrite the already '
                                                   'trained classifier?')
                        if ret == QMessageBox.No:
                            is_valid = False

                elif name == self.Testing and not result_frame.classifier_exists():
                    is_valid = False
                    QMessageBox.critical(self, "Error", "Please train the classifier first")

            if cls is MultiAnalyzerThread:

                if self._settings("General", "constrain_positions"):
                    count = self._settings("General", "positions").count(",") +1
                    ncpu = min(cpu_count(), count)
                else:
                    ncpu = cpu_count()

                (ncpu, ok) = QInputDialog.getInt(self,
                    "On your machine are %d processers available." % ncpu, \
                                                 "Selct the number of processors", ncpu, 1, ncpu*2)
                if not ok:
                    self._process_items = None
                    is_valid = False

            if is_valid:
                self._current_process = name

                if not start_again:
                    self.parent().log_window.clear()

                    self._is_running = True
                    self._stage_infos = {}

                    self._toggle_tabs(False)
                    # disable all section button of the main widget
                    self.toggle_tabs.emit(self.get_name())

                    self._set_control_button_text(idx=1)
                    self.process_control.toggleButtons(self._current_process)

                imagecontainer = self.parent().main_window._imagecontainer

                if cls is TrainerThread:
                    self._current_settings = self._get_modified_settings(
                        name, imagecontainer.has_timelapse)
                    self._analyzer = cls(
                        self, self._current_settings, imagecontainer)
                    self._clear_image()

                elif cls is AnalyzerThread:
                    self._current_settings = self._get_modified_settings(
                        name, imagecontainer.has_timelapse)
                    self._analyzer = cls(
                        self, self._current_settings, imagecontainer)
                    self._clear_image()

                elif cls is MultiAnalyzerThread:
                    self._current_settings = self._get_modified_settings(
                        name, imagecontainer.has_timelapse)
                    self._analyzer = cls(
                        self, self._current_settings, imagecontainer, ncpu)


                elif cls is ErrorCorrectionThread:
                    self._current_settings = self._get_modified_settings(
                        name, imagecontainer.has_timelapse)
                    self._analyzer = cls(
                        self, self._current_settings,
                        self.parent().main_window._imagecontainer)

                self._analyzer.finished.connect(self._on_process_finished)
                self._analyzer.stage_info.connect(
                    self._on_update_stage_info, Qt.QueuedConnection)
                self._analyzer.analyzer_error.connect(
                    self._on_error, Qt.QueuedConnection)
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

    def _on_error(self, msg, short='Error'):
        self._has_error = True
        QMessageBox.critical(self, short, msg)

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
            self.process_control.toggleButtons(self._current_process)
            self._toggle_tabs(True)
            # enable all section button of the main widget
            self.toggle_tabs.emit(self.get_name())
            if not self._is_abort and not self._has_error:
                if self.name == SECTION_NAME_OBJECTDETECTION:
                    msg = 'Object detection successfully finished.'
                elif self.name == SECTION_NAME_CLASSIFICATION:
                    if self._current_process == self.Training:
                        msg = 'Classifier training successfully finished.'
                        result_frame = self._get_result_frame(self._tab_name)
                        result_frame.load_classifier()
                        # nr_removed = len(result_frame._learner.nan_features)
                        # if nr_removed > 0:
                        #     msg += '\n\n%d features contained NA values and will be removed from training.' % nr_removed
                    elif self._current_process == self.Testing:
                        msg = 'Classifier testing successfully finished.'
                elif self.name == SECTION_NAME_TRACKING:
                    msg = 'Tracking successfully finished.'
                elif self.name == SECTION_NAME_EVENT_SELECTION:
                    msg = 'Event selection successfully finished.'
                elif self.name == SECTION_NAME_ERRORCORRECTION:
                    msg = 'Error correction successfully finished.'
                elif self.name == SECTION_NAME_PROCESSING:
                    msg = 'Processing successfully finished.'
                self.status_message.emit(msg)
                QMessageBox.information(self, "Finished", msg)
            else:
                if self._is_abort:
                    self.status_message.emit('Process aborted by user.')
                elif self._has_error:
                    self.status_message.emit('Process aborted by error.')

            self._current_process = None
            self._process_items = None

    def _on_esc_pressed(self):
        print "escape"
        if self._is_running:
            self._abort_processing()
            self._analyzer.image_ready.disconnect(self._on_update_image)


    def _on_update_stage_info(self, info):
        sep = ' | '
        info = dict([(str(k), v) for k, v in info.iteritems()])

        self.process_control.setRange(info['min'], info['max'])

        if info['progress'] is None:
            self.process_control.increment()
        else:
            self.process_control.setProgress(info['progress'])

        msg = ''
        if 'meta' in info:
            msg += '%s' % info['meta']
        if 'text' in info:
            msg += '   %s' % info['text']

        if info['interval'] is not None:
            prg = self.process_control.progress()
            self._intervals.append(info["interval"])
            avg = numpy.average(self._intervals)
            estimate = seconds2datetime(avg*float(info['max']-prg))
            msg += '%s~ %.1fs %s%s remaining' \
                   % (sep, avg, sep,
                      estimate.strftime("%H:%M:%S"))
        else:
            self._intervals = []
        self.status_message.emit(msg)
