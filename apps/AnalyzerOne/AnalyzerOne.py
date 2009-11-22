"""
                          The CellCognition Project
                   Copyright (c) 2006 - 2009 Michael Held
                    Gerlich Lab, ETH Zurich, Switzerland

            CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__docformat__ = "epytext"
__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys
import os
import types
import pprint
import logging
import StringIO
import traceback
import copy

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
from pdk.ordereddict import OrderedDict
from cecog.extensions.ConfigParser import RawConfigParser
from cecog.reader import PIXEL_TYPES
from cecog.analyzer.core import AnalyzerCore
from cecog import ccore
import resource

#-------------------------------------------------------------------------------
# constants:
#
FEATURE_CATEGORIES = ['roisize',
                      'circularity',
                      'irregularity',
                      'irregularity2',
                      'axes',
                      'normbase',
                      'normbase2',
                      'levelset',
                      'convexhull',
                      'dynamics',
                      'granulometry',
                      'distance',
                      'moments',
                      ]
REGION_NAMES_PRIMARY = ['primary']
REGION_NAMES_SECONDARY = ['inside', 'outside', 'expanded']
COMPRESSION_FORMATS = ['raw', 'bz2', 'gz']
TRACKING_METHODS = ['ClassificationCellTracker',]

CONTROL_1 = 'CONTROL_1'
CONTROL_2 = 'CONTROL_2'


#-------------------------------------------------------------------------------
# functions:
#

def numpy_to_qimage(data, colors=None):
    w, h = data.shape[:2]
    #print data.shape, data.ndim
    if data.dtype == numpy.uint8:
        if data.ndim == 2:
            shape = (numpy.ceil(w / 4.) * 4, h)
            if shape != data.shape:
                image = numpy.zeros(shape, numpy.uint8, 'C')
                image[:w,:] = data
            else:
                image = data
            format = QImage.Format_Indexed8
            #colors = [QColor(i,i,i) for i in range(256)]
        elif data.ndim == 3:
            c = data.shape[2]
            shape = (int(numpy.ceil(w / 4.) * 4), h, c)
            if c == 3:
                if shape != data.shape:
                    image = numpy.zeros(shape, numpy.uint8)
                else:
                    image = data
                format = QImage.Format_RGB888
            elif data.shape[2] == 4:
                format = QImage.Format_RGB32

    qimage = QImage(image, w, h, format)
    qimage.ndarray = image
    if not colors is None:
        for idx, col in enumerate(colors):
            qimage.setColor(idx, col.rgb())
    return qimage


#-------------------------------------------------------------------------------
# classes:
#
class AnalyzerMainWindow(QMainWindow):

    TITLE = 'AnalyzerOne'

    def __init__(self):
        QMainWindow.__init__(self)

        self.setWindowTitle(self.TITLE)

        central_widget = QFrame(self)
        self.setCentralWidget(central_widget)


        action_about = self.create_action('&About', slot=self._on_about)
        action_quit = self.create_action('&Quit', slot=self._on_quit)
        action_pref = self.create_action('&Preferences',
                                         slot=self._on_preferences)

        #action_new = self.create_action('&New...', shortcut=QKeySequence.New,
        #                                  icon='filenew')
        action_open = self.create_action('&Open Settings...',
                                         shortcut=QKeySequence.Open,
                                         slot=self._on_file_open
                                         )
        action_save = self.create_action('&Save Settings',
                                         shortcut=QKeySequence.Save,
                                         slot=self._on_file_save
                                         )
        action_save_as = self.create_action('&Save Settings As...',
                                            shortcut=QKeySequence.SaveAs,
                                            slot=self._on_file_save_as
                                            )
        menu_file = self.menuBar().addMenu('&File')
        self.add_actions(menu_file, (action_about,  action_pref,
                                     None, action_open,
                                     None, action_save, action_save_as,
                                     None, action_quit))

        action_log = self.create_action('&Show Log Window...',
                                        shortcut=QKeySequence(Qt.CTRL + Qt.Key_L),
                                        slot=self._on_show_log_window
                                        )
        menu_window = self.menuBar().addMenu('&Window')
        self.add_actions(menu_window, (action_log,
                                       ))

        menu_help = self.menuBar().addMenu('&Help')


        self._selection = QListWidget(central_widget)
        self._selection.setViewMode(QListView.IconMode)
        #self._selection.setUniformItemSizes(True)
        self._selection.setIconSize(QSize(50, 50))
        self._selection.setGridSize(QSize(150,80))
        #self._selection.setWrapping(False)
        #self._selection.setMovement(QListView.Static)
        #self._selection.setFlow(QListView.TopToBottom)
        #self._selection.setSpacing(12)
        self._selection.setMaximumWidth(self._selection.gridSize().width()+5)
        self._selection.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._selection.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                                  QSizePolicy.Expanding))

        self._pages = QStackedWidget(central_widget)
        self._pages.main_window = self

        #pagesWidget->addWidget(new ConfigurationPage);
        #pagesWidget->addWidget(new UpdatePage);
        #pagesWidget->addWidget(new QueryPage);
        self._settings_filename = None
        self._settings = ConfigSettings() #ConfigParser.RawConfigParser()

        self._tabs = [GeneralFrame(self._settings, self._pages),
                      ObjectDetectionFrame(self._settings, self._pages),
                      ClassificationFrame(self._settings, self._pages),
                      TrackingFrame(self._settings, self._pages),
                      OutputFrame(self._settings, self._pages),
                      ProcessingFrame(self._settings, self._pages),
                      ]
        widths = []
        for tab in self._tabs:
            size = self._add_page(tab)
            widths.append(size.width())
        self._pages.setMinimumWidth(max(widths)+45)

        self.connect(self._selection,
                     SIGNAL('currentItemChanged(QListWidgetItem *, QListWidgetItem *)'),
                     self._on_change_page)

        self._selection.setCurrentRow(0)

        w_logo = QLabel(central_widget)
        w_logo.setPixmap(QPixmap(':cecog_logo_w145'))

        layout = QGridLayout(central_widget)
        layout.addWidget(self._selection, 0, 0)
        layout.addWidget(w_logo, 1, 0, Qt.AlignBottom|Qt.AlignHCenter)
        layout.addWidget(self._pages, 0, 1, 2, 1)

        self._handler = GuiLogHandler(self)
        self._log_window = LogWindow(self._handler)

        logger = logging.getLogger()
        self._handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
        self._handler.setFormatter(formatter)
        #logger.addHandler(self._handler)
        logger.setLevel(logging.DEBUG)

        self.setGeometry(0, 0, 1000, 700)
        self.setMinimumSize(QSize(700,600))
        self.show()
        self.center()
        self.raise_()

    def _add_page(self, widget):
        button = QListWidgetItem(self._selection)
        button.setIcon(QIcon(widget.ICON))
        button.setText(widget.SECTION)
        button.setTextAlignment(Qt.AlignHCenter)
        button.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

#        scroll_area = QScrollArea(self._pages)
#        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
#        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#        scroll_area.setWidgetResizable(True)
#        scroll_area.setWidget(widget)
#
#        self._pages.addWidget(scroll_area)
        self._pages.addWidget(widget)
        return widget.size()

    def _on_change_page(self, current, previous):
        if not current:
            current = previous
        self._pages.setCurrentIndex(self._selection.row(current));

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2,
        (screen.height()-size.height())/2)

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(self, text, slot=None, shortcut=None, icon=None,
                      tooltip=None, checkable=None, signal='triggered()',
                      checked=False):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(':/%s.png' % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tooltip is not None:
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable is not None:
            action.setCheckable(True)
        action.setChecked(checked)
        return action

    def read_settings(self, filename):
        self._settings.read(filename)
        self._settings_filename = filename
        self.setWindowTitle('%s - %s' % (self.TITLE, filename))
        for widget in self._tabs:
            widget.update_input()

    def write_settings(self, filename):
        try:
            f = file(filename, 'w')
            self._settings.write(f)
            f.close()
        except:
            QMessageBox().critical(self, "Save settings file",
                "Could not save settings file as '%s'." % filename)
#        else:
#            self._settings_filename = filename
#            QMessageBox().information(self, "Save settings file",
#                "Settings successfully saved as '%s'." % filename)

    def _on_about(self):
        print "about"
        dialog = QDialog(self)
        dialog.setBackgroundRole(QPalette.Dark)
        dialog.setStyleSheet('background: #000000')
        dialog.setWindowTitle('About CellCognition AnalyzerOne')
        layout = QGridLayout()
        layout.setContentsMargins(50,50,50,50)
        image = QImage(':cecog_logo_small_black')
        label1 = QLabel(dialog)
        label1.setPixmap(QPixmap.fromImage(image))
        layout.addWidget(label1, 0, 0)
        label2 = QLabel(dialog)
        label2.setAlignment(Qt.AlignCenter)
        label2.setText('CellCognition AnalyzerOne\n'
                       'Copyright (c) 2006 - 2009 by Michael Held\n'
                       'Gerlich Lab, ETH Zurich, Switzerland')
        label3 = QLabel(dialog)
        label3.setTextFormat(Qt.AutoText)
        label3.setOpenExternalLinks(True)
        label3.setAlignment(Qt.AlignCenter)
        #palette = label2.palette()
        #palette.link = QBrush(QColor(200,200,200))
        #label3.setPalette(palette)
        label3.setText('<style>a { color: green; } a:visited { color: green; }</style>'
                       '<a href="http://www.cellcognition.org">www.cellcognition.org</a>')
        layout.addWidget(label2, 1, 0)
        layout.addWidget(label3, 2, 0)
        layout.setAlignment(Qt.AlignCenter|
                            Qt.AlignVCenter)
        dialog.setLayout(layout)
        dialog.show()

    def _on_preferences(self):
        print "pref"

    def _on_quit(self):
        print "quit"
        QApplication.quit()

    def _on_file_open(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        if dialog.exec_():
            filename = str(dialog.selectedFiles()[0])
            print filename
            self.read_settings(filename)

    def _on_file_save(self):
        filename = self._settings_filename
        if filename is None:
            filename = self.__get_save_as_filename()
        if not filename is None:
            self.write_settings(filename)

    def _on_file_save_as(self):
        filename = self.__get_save_as_filename()
        if not filename is None:
            self.write_settings(filename)

    def _on_show_log_window(self):
        self._log_window.show()

    def __get_save_as_filename(self):
        #QFileDialog.getSaveFileName(self, )
        filename = None
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        if dialog.exec_():
            filename = str(dialog.selectedFiles()[0])
            self.setWindowTitle('%s - %s' % (self.TITLE, filename))
        return filename


class AnalzyerThread(QThread):

    stage_info = pyqtSignal(dict)
    image_ready = pyqtSignal(ccore.ImageRGB, str, str)
    analyzer_error = pyqtSignal(str)

    def __init__(self, parent, settings):
        QThread.__init__(self, parent)
        self._settings = settings
        self._abort = False
        self._renderer = None
        self._mutex = QMutex()
        self._stage_info = {'text': '',
                            'progress': 0,
                            'max': 0,
                            }

    def __del__(self):
        #self._mutex.lock()
        self._abort = True
        self.stop()
        self.wait()
        self._mutex.unlock()

    def run(self):
        try:
            analyzer = AnalyzerCore(self._settings)
            analyzer.processPositions(self)
        except:
            msg = traceback.format_exc()
            msg2 = traceback.format_exc(5)
            logger = logging.getLogger()
            logger.error(msg)
            self.analyzer_error.emit(msg2)
            raise

    def set_renderer(self, name):
        self._mutex.lock()
        self._renderer = name
        self._mutex.unlock()

    def get_renderer(self):
        return self._renderer

    def set_abort(self):
        self._mutex.lock()
        self._abort = True
        self._mutex.unlock()

    def get_abort(self):
        abort = self._abort
        return abort

    def set_image(self, image_rgb, info, filename=''):
        self._mutex.lock()
        self.image_ready.emit(image_rgb, info, filename)
        self._mutex.unlock()

    def set_stage_info(self, info):
        self._mutex.lock()
        self.stage_info.emit(info)
        self._mutex.unlock()


class LogWindow(QFrame):

    def __init__(self, handler):
        QFrame.__init__(self)
        self._mutex = QMutex()
        layout = QVBoxLayout(self)
        self._log_widget = QPlainTextEdit(self)
        format = QTextCharFormat()
        format.setFontFixedPitch(True)
        format.setFontPointSize(11)
        self._log_widget.setCurrentCharFormat(format)
        layout.addWidget(self._log_widget)
        self._msg_buffer = []

        self._handler = handler
        self._handler.message_received.connect(self._on_message_received)

    def _on_message_received(self, msg):
        self._msg_buffer.append(str(msg))
        if self.isVisible():
            self._log_widget.appendPlainText('\n'.join(self._msg_buffer))
            self._msg_buffer = []

    def clear(self):
        self._msg_buffer = []
        self._log_widget.clear()


class GuiLogHandler(QObject, logging.Handler):

    message_received = pyqtSignal(str)

    def __init__(self, parent):
        self._mutex = QMutex()
        #self._history = StringIO.StringIO()
        QObject.__init__(self, parent)
        logging.Handler.__init__(self)#, strm=self._history)

    def emit(self, record):
        try:
            msg = self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
        self.message_received.emit(msg)


class GuiTrait(object):

    DATATYPE = None

    def __init__(self, value, label=None, tooltip=None, doc=None):
        self.value = value
        self.label = label
        self.tooltip = tooltip
        self.doc = doc

    def convert(self, value):
        if not self.DATATYPE is None and not type(value) == self.DATATYPE:
            return self.DATATYPE(value)
        else:
            return value


class NumberTrait(GuiTrait):

    def __init__(self, value, min_value, max_value, step=None,
                 label=None, tooltip=None, doc=None):
        super(NumberTrait, self).__init__(value, label=label,
                                          tooltip=tooltip, doc=doc)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

    def set_value(self, widget, value):
        widget.setValue(value)


class IntTrait(NumberTrait):

    DATATYPE = int


class FloatTrait(NumberTrait):

    DATATYPE = float

    def __init__(self, value, min_value, max_value, step=None, digits=1,
                 label=None, tooltip=None, doc=None):
        super(FloatTrait, self).__init__(value, min_value, max_value, step=step,
                                         label=label, tooltip=tooltip,
                                         doc=doc)
        self.digits = digits


class StringTrait(GuiTrait):

    DATATYPE = str
    STRING_NORMAL = 0
    STRING_PATH = 1
    STRING_FILE = 2

    def __init__(self, value, max_length, mask=None,
                 label=None, tooltip=None, doc=None, widget_info=None):
        super(StringTrait, self).__init__(value, label=label,
                                          tooltip=tooltip, doc=doc)
        self.max_length = max_length
        self.mask = mask
        if widget_info is None:
            widget_info = self.STRING_NORMAL
        self.widget_info = widget_info

    def set_value(self, widget, value):
        widget.setText(value)


class BooleanTrait(GuiTrait):

    DATATYPE = bool
    CHECKBOX = 0
    RADIOBUTTON = 1

    def __init__(self, value, label=None, tooltip=None, doc=None,
                 widget_info=None):
        super(BooleanTrait, self).__init__(value, label=label,
                                           tooltip=tooltip, doc=doc)
        if widget_info is None:
            widget_info = self.CHECKBOX
        self.widget_info = widget_info

    def convert(self, value):
        if type(value) == self.DATATYPE:
            return value
        else:
            return False if str(value).lower() in ['0', 'false'] else True

    def set_value(self, widget, value):
        widget.setChecked(value)

class ListTrait(GuiTrait):

    DATATYPE = list

    def convert(self, value):
        print value
        if type(value) == self.DATATYPE:
            return value
        else:
            value = eval(value)
            #print value, type(value)
            if not type(value) in [types.ListType, types.DictType]:
                value = [value]
            return value

    def set_value(self, widget, value):
        widget.clear()
        for item in value:
            widget.append(str(item))


class SelectionTrait(ListTrait):

    def __init__(self, value, list_data,
                 label=None, tooltip=None, doc=None):
        super(SelectionTrait, self).__init__(value, label=label,
                                             tooltip=tooltip, doc=doc)
        self.list_data = list_data

    def index(self, value):
        return self.list_data.index(value)

    def convert(self, value):
        return value

    def set_value(self, widget, value):
        print value, self.list_data
        widget.setCurrentIndex(self.index(value))


class MultiSelectionTrait(SelectionTrait):

    def set_value(self, widget, value):
        widget.clearSelection()
        for item in value:
            w_listitem = widget.findItems(str(item), Qt.MatchExactly)
            #if len(w_listitem) > 0:
            widget.setCurrentItem(w_listitem[0], QItemSelectionModel.Select)

    def convert(self, value):
        print "MOO", value
        if type(value) == self.DATATYPE:
            return value
        else:
            value = eval(value)
            #print value, type(value)
            if not type(value) in [types.ListType, types.DictType]:
                value = [value]
            return value


class DictTrait(ListTrait):

    DATATYPE = dict

    def convert(self, value):
        if type(value) == self.DATATYPE:
            return value
        else:
            value = eval(value)
            if not type(value) == types.DictType:
                value = {}
            return value

    def set_value(self, widget, value):
        widget.setText(pprint.pformat(value, indent=2))


class InputWidgetMixin(object):

    SECTION = None
    WIDTH = 3

    def __init__(self, settings):
        self._registry = {}
        self._settings = settings
        self._settings.register_section(self.SECTION)

    def add_group(self, name, trait, items, layout="grid"):
        frame = self._get_frame(self._tab_name)
        frame_layout = frame.layout()

        if not trait is None:
            name = name.lower()
            w_input = self.add_input(name, trait)
        else:
            w_input = self._create_label(frame, name)
            frame_layout.addWidget(w_input, frame._input_cnt, 0, Qt.AlignRight|Qt.AlignTop)

        if len(items) > 0:
            w_group = QGroupBox(frame)
            w_group.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                              QSizePolicy.Fixed))
            if not trait is None:
                w_group.setEnabled(self.get_value(name))

            w_group._input_cnt = 0
            if layout == 'grid':
                QGridLayout(w_group)
            else:
                QBoxLayout(QBoxLayout.LeftToRight, w_group)
            for info in items:
                name2, trait2 = info[:2]
                grid = None
                alignment = None
                if len(info) >= 3:
                    grid = info[2]
                if len(info) >= 4:
                    alignment = info[3]
                self.add_input(name2, trait2, parent=w_group, grid=grid, alignment=alignment)
            frame_layout.addWidget(w_group, frame._input_cnt, 1, 1, self.WIDTH)
            if not trait is None:
                handler = lambda x : w_group.setEnabled(w_input.isChecked())
                self.connect(w_input, SIGNAL('toggled(bool)'), handler)
        frame._input_cnt += 1

    def get_value(self, name):
        return self._settings.get_value(self.SECTION, name)

    def set_value(self, name, value):
        self._settings.set(self.SECTION, name, value)

    def register_trait(self, name, trait):
        self._settings.register_trait(self.SECTION, name, trait)

    def _create_label(self, parent, label, link=None):
        if link is None:
            link = label
        w_label = QLabel(parent)
        w_label.setTextFormat(Qt.AutoText)
        #w_label.setOpenExternalLinks(True)
        w_label.setStyleSheet("*:hover { border:none; background: #e8ff66;}")
        w_label.setText('<style>a { color: black; text-decoration: none;}</style>'
                        '<a href="%s">%s</a>' % (link, label))
        self.connect(w_label, SIGNAL('linkActivated(const QString&)'),
                     self._on_label_clicked)
        w_label.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                          QSizePolicy.Fixed))
        w_label.setToolTip('Click on the label for help.')
        return w_label

    def add_input(self, name, trait, parent=None, grid=None, alignment=None):
        name = name.lower()

        # FIXME: this should be done from the modules
        self.register_trait(name, trait)

        if parent is None:
            parent = self._get_frame(self._tab_name)

        policy_fixed = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        policy_expanding = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        label = trait.label or name
        w_label = self._create_label(parent, label, link=name)
        w_button = None
        w_doc = None
        #w_label.setMinimumWidth(width)

        value = self.get_value(name)

        handler = lambda name: lambda value: self.set_value(name, value)

        if isinstance(trait, StringTrait):
            w_input = QLineEdit(parent)
            w_input.setMaxLength(trait.max_length)
            w_input.setSizePolicy(policy_expanding)
            if not trait.mask is None:
                regexp = QRegExp(trait.mask)
                regexp.setPatternSyntax(QRegExp.RegExp2)
                w_input.setValidator(QRegExpValidator(regexp, w_input))
            trait.set_value(w_input, value)
            self.connect(w_input, SIGNAL('textEdited(QString)'), handler(name))

            if trait.widget_info != StringTrait.STRING_NORMAL:
                w_button = QPushButton("Browse", parent)
                handler2 = lambda name, mode: lambda: \
                    self._on_browse_name(name, mode)
                self.connect(w_button, SIGNAL('clicked()'),
                             handler2(name, trait.widget_info))

        elif isinstance(trait, IntTrait):
            w_input = QSpinBox(parent)
            w_input.setRange(trait.min_value, trait.max_value)
            w_input.setSizePolicy(policy_fixed)
            trait.set_value(w_input, value)
            if not trait.step is None:
                w_input.setSingleStep(trait.step)
            self.connect(w_input, SIGNAL('valueChanged(int)'), handler(name))

        elif isinstance(trait, FloatTrait):
            w_input = QDoubleSpinBox(parent)
            w_input.setRange(trait.min_value, max_value)
            w_input.setSizePolicy(policy_fixed)
            trait.set_value(w_input, value)
            if not trait.step is None:
                w_input.setSingleStep(trait.step)
            if not trait.digits is None:
                w_input.setDecimals(trait.digits)
            self.connect(w_input, SIGNAL('valueChanged(double)'), handler(name))

        elif isinstance(trait, BooleanTrait):
            if trait.widget_info == BooleanTrait.CHECKBOX:
                w_input = QCheckBox(parent)
            elif trait.widget_info == BooleanTrait.RADIOBUTTON:
                w_input = QRadioButton(parent)
            trait.set_value(w_input, value)
            handler = lambda n: lambda v: self.set_value(n, trait.convert(v))
            w_input.setSizePolicy(policy_fixed)
            self.connect(w_input, SIGNAL('toggled(bool)'), handler(name))

        elif isinstance(trait, MultiSelectionTrait):
            w_input = QListWidget(parent)
            w_input.setMaximumHeight(100)
            w_input.setSelectionMode(QListWidget.ExtendedSelection)
            w_input.setSizePolicy(policy_fixed)
            print "moo1", value
            #value = trait.convert(value)
            #print "moo2", value
            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_selection_changed(n)
            self.connect(w_input, SIGNAL('itemSelectionChanged()'),
                         handler(name))

        elif isinstance(trait, SelectionTrait):
            w_input = QComboBox(parent)
            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_value(w_input, value)
            w_input.setSizePolicy(policy_fixed)
            handler = lambda n: lambda v: self._on_current_index(n, v)
            self.connect(w_input, SIGNAL('currentIndexChanged(int)'),
                         handler(name))

        elif isinstance(trait, DictTrait):
            w_input = QTextEdit(parent)
            w_input.setMaximumHeight(100)
            w_input.setSizePolicy(policy_expanding)
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_text_to_dict(n)
            self.connect(w_input, SIGNAL('textChanged()'), handler(name))

        elif isinstance(trait, ListTrait):
            w_input = QTextEdit(parent)
            w_input.setMaximumHeight(100)
            w_input.setSizePolicy(policy_expanding)
            #print value
            #value = trait.convert(value)
            #print value
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_text_to_list(n)
            self.connect(w_input, SIGNAL('textChanged()'), handler(name))

        else:
            raise TypeError("Cannot handle name '%s'." % name)

        self._registry[name] = w_input

        if not w_button is None:
            w_button.setSizePolicy(policy_fixed)

#        if not trait.doc is None:
#            w_doc = QPushButton(parent)
#            w_doc.setIcon(QIcon(':question_mark'))
#            #w_doc.setAutoRaise(True)
#            w_doc.setMaximumSize(14,14)
#            w_doc.setFlat(True)
#            handler2 = lambda: self._on_show_doc(name, trait)
#            self.connect(w_doc, SIGNAL('clicked()'), handler2)
#        else:
#            w_doc = QFrame(parent)
#        w_doc.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
#                                        QSizePolicy.Fixed))

        layout = parent.layout()
        if isinstance(layout, QGridLayout):

            if grid is None:
                layout.addWidget(w_label, parent._input_cnt, 0, Qt.AlignRight)
                if not w_doc is None:
                    layout.addWidget(w_doc, parent._input_cnt, 1)

                layout.addWidget(w_input, parent._input_cnt, 1, 1, self.WIDTH)
                if not w_button is None:
                    layout.addWidget(w_button, parent._input_cnt, 2+self.WIDTH)
            else:
                layout.addWidget(w_label, grid[0], grid[1]*3, Qt.AlignRight)
                if alignment is None:
                    layout.addWidget(w_input, grid[0], grid[1]*3+1, grid[2], grid[3])
                else:
                    layout.addWidget(w_input, grid[0], grid[1]*3+1, grid[2], grid[3], alignment)
                layout.addItem(QSpacerItem(1, 1,
                                           QSizePolicy.MinimumExpanding,
                                           QSizePolicy.Fixed), grid[0], grid[1]*3+2)
        else:
            layout.addWidget(w_label)
            layout.addWidget(w_input)
            layout.addStretch()
            if not w_button is None:
                layout.addWidget(w_button)

        parent._input_cnt += 1
        return w_input

    def update_input(self):
        #if self._settings.has_section(self.SECTION):
        for name, value in self._settings.items(self.SECTION):
            print self.SECTION, name, name in self._registry
            if name in self._registry:
                w_input = self._registry[name]
                trait = self._settings.get_trait(self.SECTION, name)
                print '    ', name, value
                trait.set_value(w_input, value)

#        else:
#            self._settings.add_section(self.SECTION)

    def _on_label_clicked(self, link):
        print self.SECTION, link

        if not hasattr(qApp, 'cecog_help_dialog'):
            dialog = QFrame()
            dialog.setWindowTitle('AnalyzerOne Help - %s' % self.SECTION)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            w_text = QTextEdit(dialog)
            layout.addWidget(w_text)
            dialog.setMinimumSize(QSize(800,600))
            qApp.cecog_help_dialog = dialog
            qApp.cecog_help_wtext = w_text
        else:
            dialog = qApp.cecog_help_dialog
            w_text = qApp.cecog_help_wtext

        w_text.clear()
        file_name = ':help/%s.html' % self.SECTION.lower()
        f = QFile(file_name)
        if f.open(QIODevice.ReadOnly | QIODevice.Text):
            s = QTextStream(f)
            html_text = s.readAll()
            f.close()
            w_text.insertHtml(html_text)
        dialog.show()
        dialog.raise_()

    def _on_set_radio_button(self, name, value):
        # FIXME: this is somehow hacky. we need to inform all the radio-buttons
        #        if the state of one is changed
        for option in self._settings.options(self.SECTION):
            trait = self._settings.get_trait(self.SECTION, option)
            if (isinstance(trait, BooleanTrait) and
                trait.widget_info == BooleanTrait.RADIOBUTTON):
                #print option, name, value
                self.set_value(option, option == name)

    def _on_browse_name(self, name, mode):
        # FIXME: signals are send during init were registry is not set yet
        if name in self._registry:
            path = str(self._registry[name].text())
            dialog = QFileDialog(self)
            if mode == StringTrait.STRING_FILE:
                dialog.setFileMode(QFileDialog.ExistingFile)
                dialog.setAcceptMode(QFileDialog.AcceptOpen)
            else:
                dialog.setFileMode(QFileDialog.DirectoryOnly)
                dialog.setAcceptMode(QFileDialog.AcceptOpen)
            if os.path.isdir(path):
                dialog.setDirectory(path)
            if dialog.exec_():
                print dialog.selectedFiles()[0]
                path = str(dialog.selectedFiles()[0])
                self._registry[name].setText(path)
                self.set_value(name, path)

    def _on_current_index(self, name, index):
        # FIXME: signals are send during init were registry is not set yet
        if name in self._registry:
            self.set_value(name, str(self._registry[name].currentText()))

    def _on_selection_changed(self, name):
        # FIXME: signals are send during init were registry is not set yet
        if name in self._registry:
            widgets = self._registry[name].selectedItems()
            self.set_value(name, [str(w.text()) for w in widgets])

    def _on_text_to_list(self, name):
        # FIXME: signals are send during init were registry is not set yet
        if name in self._registry:
            text = str(self._registry[name].toPlainText())
            self.set_value(name, [x.strip() for x in text.split('\n')])

    def _on_text_to_dict(self, name):
        # FIXME: signals are send during init were registry is not set yet
        if name in self._registry:
            text = str(self._registry[name].toPlainText())
            value = eval(text)
            assert type(value) == types.DictType
            self.set_value(name, value)

    def _on_show_doc(self, name, trait):
        widget = QMessageBox().information(self,
                                           "Help about '%s'" % trait.label,
                                           trait.doc)


class ProcessorMixin(object):


    def __init__(self):
        self._image_dialog = None
        self._is_running = False
        self._image_combo = None
        self._stage_infos = {}

        #frame = self._get_frame()
#        frame = self._control
#        layout = frame.layout()
#
#        self._analyzer_progress2 = QProgressBar(frame)
#        self._analyzer_label2 = QLabel(frame)
#        layout.addWidget(self._analyzer_progress2, 1, 0, 1, 3)
#        layout.addWidget(self._analyzer_label2, 2, 0, 1, 3)
#
#        self._analyzer_progress1 = QProgressBar(frame)
#        self._analyzer_label1 = QLabel(frame)
#        layout.addWidget(self._analyzer_progress1, 3, 0, 1, 3)
#        layout.addWidget(self._analyzer_label1, 4, 0, 1, 3)
#
#        self._show_image = QCheckBox('Show images', frame)
#        self._show_image.setTristate(False)
#        self._show_image.setCheckState(Qt.Checked)
#        layout.addWidget(self._show_image, 5, 0)
#
#        self._run_button = QPushButton('Start processing', frame)
#        self.connect(self._run_button, SIGNAL('clicked()'), self._on_run_analyer)
#        layout.addWidget(self._run_button, 5, 2)
#
#        self._is_running = False
#        self._image_combo = None


    def _init_control(self):
        layout = QGridLayout(self._control)

        self._progress_label0 = QLabel(self._control)
        self._progress_label0.setText('Status info')
        layout.addWidget(self._progress_label0, 0, 0)

        self._progress0 = QProgressBar(self._control)
        layout.addWidget(self._progress0, 0, 1)

        self._show_image = QCheckBox('Show images', self._control)
        self._show_image.setChecked(True)
        layout.addWidget(self._show_image, 0, 2)

        self._run_button = QPushButton('', self._control)
        layout.addWidget(self._run_button, 0, 3)
        self.connect(self._run_button, SIGNAL('clicked()'), self._on_run_analyer)

        self.connect(self._tab, SIGNAL('currentChanged(int)'), self._on_tab_changed)
        self._on_tab_changed(0)

    def _on_tab_changed(self, idx):
        names = ['primary', 'secondary']
        self._tab_name = names[idx]
        self._run_button.setText(self.RUN_BUTTON_TEXT1 % self._tab_name)

    def _on_run_analyer(self):

        #self._handler = GuiLogHandler(self)

        #self._analyzer_dialog = QDialog(self)
        #self._analyzer_dialog.setWindowTitle('Analyzer log window')
        #self._analyzer_dialog.setMinimumWidth(900)
        #layout = QGridLayout(self._analyzer_dialog)
        #layout.setContentsMargins(50,50,50,50)
        #log_window = LogWindow(self._analyzer_dialog, self._handler)
        #format = QTextCharFormat()
        #format.setFontFixedPitch(True)
        #log_window.setCurrentCharFormat(format)
        #log_window.setCurrentFont(QFont('Courier', 12))
        #layout.addWidget(log_window, 0, 0, 1, 2)

        if not self._is_running:

#            if (not self._image_dialog is None and
#                self._show_image.isChecked()):
#                self._graphics_pixmap.pixmap().fill(Qt.black)
#                self._image_dialog.show()
#                self._image_dialog.raise_()

            self._image_dialog = None
            self.parent().main_window._log_window.clear()

            self._current_settings = self._get_modified_settings()
            self._analyzer = AnalzyerThread(self, self._current_settings)

            self._is_running = True
            self._stage_infos = {}

            self._toggle_tabs(False)

        #layout.addWidget(QLabel('Rendering', self._analyzer_dialog), 1, 0)
        #layout.addWidget(combo, 1, 1)

        #btn = QPushButton('Stop analyzer', self._analyzer_dialog)
        #self._analyzer_dialog.connect(btn, SIGNAL('clicked()'), self._on_stop_analyzer)
        #layout.addWidget(btn, 6, 0, 1, 2)

#        self._analyzer_progress2 = QProgressBar(self._analyzer_dialog)
#        self._analyzer_label2 = QLabel(self._analyzer_dialog)
#        layout.addWidget(self._analyzer_progress2, 2, 0, 1, 2)
#        layout.addWidget(self._analyzer_label2, 3, 0, 1, 2)
#
#        self._analyzer_progress1 = QProgressBar(self._analyzer_dialog)
#        self._analyzer_label1 = QLabel(self._analyzer_dialog)
#        layout.addWidget(self._analyzer_progress1, 4, 0, 1, 2)
#        layout.addWidget(self._analyzer_label1, 5, 0, 1, 2)

            self._run_button.setText(self.RUN_BUTTON_TEXT2 % self._tab_name)

            self._analyzer.analyzer_error.connect(self._on_analyzer_error)

            self.connect(self._analyzer, SIGNAL('finished()'),
                         self._on_thread_finished)

            rendering = self._current_settings.get('Output', 'rendering').keys()
            rendering += self._current_settings.get('Output', 'rendering_class').keys()
            if len(rendering) > 0:
                self._analyzer.set_renderer(rendering[0])

            self._analyzer.stage_info.connect(self._on_update_stage_info)
            self._analyzer.image_ready.connect(self._on_update_image)

            #self._analyzer.setTerminationEnabled(True)
            self._analyzer.start(QThread.IdlePriority)

        else:
            self.setCursor(Qt.BusyCursor)
            self._analyzer.set_abort()
            self._analyzer.wait()
            self.setCursor(Qt.ArrowCursor)

    def _toggle_tabs(self, state):
        if not self.TABS is None:
            for i in range(self._tab.count()):
                if i != self._tab.currentIndex():
                    self._tab.setTabEnabled(i, state)

    def _on_render_changed(self, name):
        self._analyzer.set_renderer(str(name))

    def _on_analyzer_error(self, msg):
        QMessageBox.critical(self, 'Analyzer',
                             'An error occured during processing.\n' +
                             'Please check the log-window for details and report this message to us.\n\n' +
                             str(msg))


    def _on_thread_finished(self):
        self._is_running = False
        #logger = logging.getLogger()
        #logger.removeHandler(self._handler)
        self._run_button.setText(self.RUN_BUTTON_TEXT1 % self._tab_name)
        self._toggle_tabs(True)

    def _on_update_stage_info(self, info):
        if self.CONTROL == CONTROL_1:
            #print info
            self._stage_infos[info['stage']] = info
            if len(self._stage_infos) > 1:
                total = self._stage_infos[1]['max']*self._stage_infos[2]['max']
                current = (self._stage_infos[1]['progress']-1)*self._stage_infos[2]['max']+self._stage_infos[2]['progress']
                self._progress0.setRange(1, total)
                self._progress0.setValue(current)
                #info = self._stage_infos[2]
                self._progress_label0.setText('Processing %.1f%%' % (current*100.0/total))
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
                image_rgb = ccore.subImage(image_rgb, ccore.Diff2D(0,0), ccore.Diff2D(image_rgb.width - (image_rgb.width % 4), image_rgb.height))
            qimage = numpy_to_qimage(image_rgb.toArray(copy=False))
            qimage = qimage.scaled(800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if self._image_dialog is None:
                self._image_dialog = QFrame()
                #self._image_dialog.setScaledContents(True)
                #self._image_dialog.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                layout = QVBoxLayout(self._image_dialog)
                layout.setContentsMargins(5,5,5,5)
#                self._graphics = QGraphicsScene()
#                self._graphics_pixmap = self._graphics.addPixmap(QPixmap.fromImage(qimage))
#                view = QGraphicsView(self._graphics, self._image_dialog)
#                view.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
                size = self._image_dialog.size()
                self._graphics = ImageDisplay(self._image_dialog,
                                              size.height()/float(size.width()))
                self._graphics.setScaledContents(True)
                policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                policy.setHeightForWidth(True)
                self._graphics.setSizePolicy(policy)
                layout.addWidget(self._graphics)
                #self._image_dialog.resize(qimage.size())
                #self._image_dialog.setMinimumSize(QSize(100,100))
                #size = self._image_dialog.size()
                #self._image_dialog.setMaximumSize(size)
                #self.connect(self._image_dialog, SIGNAL('hide()'),
                #             self._on_close_image_window)
                rendering = self._current_settings.get('Output', 'rendering').keys()
                rendering += self._current_settings.get('Output', 'rendering_class').keys()
                if len(rendering) > 1:
                    self._image_combo = QComboBox(self._image_dialog)
                    layout.addWidget(self._image_combo, 5, 2)
                    self.connect(self._image_combo, SIGNAL('currentIndexChanged(const QString &)'),
                                 self._on_render_changed)
                    for name in sorted(rendering):
                        self._image_combo.addItem(str(name))
                layout.addStretch()
                self._image_dialog.setGeometry(50, 50, size.width(), size.height())
                #view.fitInView(self._graphics.sceneRect(), Qt.KeepAspectRatio)

                self._image_dialog.show()
            #else:
            #    self._graphics_pixmap.setPixmap(QPixmap.fromImage(qimage))
            self._graphics.setPixmap(QPixmap.fromImage(qimage))
            self._image_dialog.setWindowTitle(info)
            self._image_dialog.setToolTip(filename)
            if not self._image_dialog.isVisible():
                self._image_dialog.show()


class InputFrame(QFrame, InputWidgetMixin):

    ICON = ":cecog_analyzer_icon"
    TABS = None
    CONTROL = CONTROL_1

    def __init__(self, settings, parent):
        QFrame.__init__(self, parent)
        self._tab_lookup = {}
        self._tab_name = None

        self._control = QFrame(self)
        self._control.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                QSizePolicy.Minimum))
        layout = QVBoxLayout(self)

#        scroll_area = QScrollArea(self)
#        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
#        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#        scroll_area.setWidgetResizable(True)
#        scroll_area.setFrameShape(QFrame.NoFrame)

        if not self.TABS is None:
            self._tab = QTabWidget(self)
            #self._tab.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
            #                                    QSizePolicy.Expanding))
            for name in self.TABS:
                frame = QFrame(self._tab)
                frame._input_cnt = 0
                QGridLayout(frame)
                idx = self._tab.addTab(frame, name)
                self._tab_lookup[name] = (idx, frame)
            #scroll_area.setWidget(self._tab)
            layout.addWidget(self._tab)
        else:
            self._frame = QFrame(self)
            self._frame._input_cnt = 0
            QGridLayout(self._frame)
            #self._frame.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
            #                                    QSizePolicy.Expanding))
            #scroll_area.setWidget(self._frame)
            layout.addWidget(self._frame)

        #layout.addWidget(scroll_area)
        layout.addWidget(self._control)

        InputWidgetMixin.__init__(self, settings)

    def set_tab_name(self, name):
        self._tab_name = name

    def _get_frame(self, name=None):
        if name is None:
            if len(self._tab_lookup) > 0:
                frame = self._tab_lookup.values()[0][1]
            else:
                frame = self._frame
        else:
            frame = self._tab_lookup[name][1]
        return frame

    def add_expanding_spacer(self):
        frame = self._get_frame(name=self._tab_name)
        dummy = QWidget(frame)
        dummy.setMinimumSize(0,0)
        dummy.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                        QSizePolicy.Expanding))
        frame.layout().addWidget(dummy, frame._input_cnt, 0)
        frame._input_cnt += 1
#        self._layout.addItem(QSpacerItem(0, 0,
#                                         QSizePolicy.Fixed,
#                                         QSizePolicy.Expanding),
#                             self._input_cnt, 0, 1, self.WIDTH+2)


    def add_line(self):
        frame = self._get_frame(name=self._tab_name)
        line = QFrame(frame)
        line.setFrameShape(QFrame.HLine)
        frame.layout().addWidget(line, frame._input_cnt, 0, 1, self.WIDTH+1)
        frame._input_cnt += 1

class ConfigSettings(RawConfigParser):

    def __init__(self):
        RawConfigParser.__init__(self, {}, OrderedDict)
        self._registry = OrderedDict()
        self._current_section = None
        self.naming_schemes = RawConfigParser({}, OrderedDict)
        self.naming_schemes.read('/Users/miheld/src/cecog_svn/trunk/apps/AnalyzerOne/resources/naming_schemes.conf')

    def set_section(self, section):
        if self.has_section(section):
            self._current_section = section

    def register_section(self, section):
        self._registry[section] = OrderedDict()
        self.add_section(section)

    def register_trait(self, section, option, trait):
        option = option.lower()
        self._registry[section][option] = trait
        self.set(section, option, trait.value)

    def get_trait(self, section, option):
        return self._registry[section][option]

    def get_value(self, section, option):
        #trait = self._registry[section][option]
        return self.get(section, option)

    def get(self, section, option):
        option = option.lower()
        return RawConfigParser.get(self, section, option)

    def get2(self, option):
        return self.get(self._current_section, option)

    def set(self, section, option, value):
        option = option.lower()
        trait = self.get_trait(section, option)
        RawConfigParser.set(self, section, option, trait.convert(value))

    def set2(self, option, value):
        self.set(self._current_section, option, value)

    def read(self, filenames):
        RawConfigParser.read(self, filenames)
        for section, options in self._registry.iteritems():
            for option in options:
                value = self.get_value(section, option)
                #trait = self.get_trait(section, option)
                #print section, option, value,
                #print 'MOOOOOOOOOOOOOO', trait.convert(value), type(trait.convert(value))
                self.set(section, option, value)


class GeneralFrame(InputFrame):

    SECTION = 'General'

    def __init__(self, settings, parent):
        super(GeneralFrame, self).__init__(settings, parent)

        self.add_input('pathIn',
                       StringTrait('', 1000, label='Data folder',
                                   widget_info=StringTrait.STRING_PATH))
        self.add_input('pathOut',
                       StringTrait('', 1000, label='Output folder',
                                   widget_info=StringTrait.STRING_PATH))

        #self.add_input("namingSchemePath", "Path to naming schemes", "abc...", "string")
        naming_schemes = settings.naming_schemes.sections()
        self.add_input("namingScheme",
                       SelectionTrait(naming_schemes[0], naming_schemes,
                                      label="Naming scheme"))

        self.add_input('positions',
                       StringTrait('', 1000, label='Positions'))

        self.add_input('redoFailedOnly',
                       BooleanTrait(True, label='Skip processed positions'))

        self.add_input('frameRange',
                       StringTrait('', 1000, label='Timepoints'))
        self.add_input('frameIncrement',
                       IntTrait(1, 1, 100, label='Timepoint increment'))

#        self.add_input('imageOutCompression',
#                       StringTrait('98', 5, label='Image output compresion',
#                                   tooltip='abc...'))

        self.register_trait('preferimagecontainer', BooleanTrait(False))
        self.register_trait('binningFactor', IntTrait(1,1,10))
        self.register_trait('timelapseData', BooleanTrait(True))
        self.register_trait('qualityControl', BooleanTrait(False))
        self.register_trait('debugMode', BooleanTrait(False))
        self.register_trait('createImages', BooleanTrait(True))
        self.register_trait('imageOutCompression',
                            StringTrait('98', 5,
                                        label='Image output compresion'))

        self.add_expanding_spacer()

        layout = QHBoxLayout(self._control)
        btn1 = QPushButton('Load settings...', self._control)
        btn2 = QPushButton('Save settings', self._control)
        btn3 = QPushButton('Save settings as...', self._control)
        layout.addStretch()
        layout.addWidget(btn1)
        layout.addWidget(btn2)
        layout.addWidget(btn3)
        layout.addStretch()
        self.connect(btn1, SIGNAL('clicked()'), self.parent().main_window._on_file_open)
        self.connect(btn2, SIGNAL('clicked()'), self.parent().main_window._on_file_save)
        self.connect(btn3, SIGNAL('clicked()'), self.parent().main_window._on_file_save_as)



class ObjectDetectionFrame(InputFrame, ProcessorMixin):

    SECTION = 'ObjectDetection'
    TABS = ['PrimaryChannel', 'SecondaryChannel']
    RUN_BUTTON_TEXT1 = 'Detect %s objects'
    RUN_BUTTON_TEXT2 = 'Stop %s detection'

    def __init__(self, settings, parent):
        InputFrame.__init__(self, settings, parent)
        ProcessorMixin.__init__(self)

        self.set_tab_name('PrimaryChannel')

        self.add_input('primary_channelId',
                       StringTrait('rfp', 100, label='Primary channel ID'))
#        self.add_input('zSliceOrProjection',
#                       StringTrait('1', 10,
#                                   label='Z-slice or projection',
#                                   tooltip='abc...'))
        self.add_group('16 to 8 bit conversion', None,
                       [('primary_normalizeMin',
                        IntTrait(0, -2**16, 2**16, label='Min.')),
                        ('primary_normalizeMax',
                        IntTrait(255, -2**16, 2**16, label='Max.')),
                        ], layout='flow')
        self.add_line()
        self.add_group('Local adaptive threshold', None,
                       [('primary_medianRadius',
                         IntTrait(2, 0, 1000, label='Median radius'),
                         (0,0,1,1)),
                        ('primary_latWindowSize',
                         IntTrait(20, 1, 1000, label='Window size'),
                         (0,1,1,1)),
                        ('primary_latLimit',
                         IntTrait(1, 0, 255, label='Min. contrast'),
                         (1,0,1,1)),
                        ('primary_emptyImageMax',
                         IntTrait(90, 0, 255, label='Empty frame threshold'),
                         (1,1,1,1)),
                        ])


        self.add_group('primary_shapeWatershed',
                       BooleanTrait(False, label='Watershed by shape'),
                       [('primary_shapeWatershed_gaussSize',
                         IntTrait(1, 0, 10000, label='Gauss radius'),
                         (0,0,1,1)),
                        ('primary_shapeWatershed_maximaSize',
                         IntTrait(1, 0, 10000, label='Min. seed distance'),
                         (0,1,1,1)),
                        ('primary_shapeWatershed_minMergeSize',
                         IntTrait(1, 0, 10000, label='Object size threshold'),
                         (1,0,1,1)),
                        ])

#        self.add_group('intensityWatershed',
#                       BooleanTrait(False, label='Watershed by intensity',
#                                    tooltip='abc...'),
#                       [('intensityWatershed_gaussSize',
#                         IntTrait(1, 0, 10000, label='Gauss radius',
#                                  tooltip='abc...')),
#                        ('intensityWatershed_maximaSize',
#                         IntTrait(1, 0, 10000, label='Min. seed distance',
#                                  tooltip='abc...')),
#                        ('intensityWatershed_minMergeSize',
#                         IntTrait(1, 0, 10000, label='Object size threshold',
#                                  tooltip='abc...'))],
#                        layout='box')

        self.add_group('primary_postProcessing',
                       BooleanTrait(False, label='Object filter',
                                    tooltip='abc...'),
                        [('primary_postProcessing_roisize_min',
                          IntTrait(-1, -1, 10000, label='ROI Size min.'),
                          (0,0,1,1)),
                          ('primary_postProcessing_roisize_max',
                          IntTrait(-1, -1, 10000, label='ROI Size max.'),
                          (0,1,1,1)),
                          ('primary_postProcessing_intensity_min',
                          IntTrait(-1, -1, 10000, label='Avg. intensity min.'),
                          (1,0,1,1)),
                          ('primary_postProcessing_intensity_max',
                          IntTrait(-1, -1, 10000, label='Avg. intensity max.'),
                          (1,1,1,1)),
                        ])

#                       [('primary_postProcessing_featureCategories',
#                         MultiSelectionTrait([], FEATURE_CATEGORIES,
#                                             label='Feature categories',
#                                             tooltip='abc...')),
#                        ('primary_postProcessing_conditions',
#                         StringTrait('', 200, label='Conditions',
#                                     tooltip='abc...')),
#                        ])


        self.register_trait('primary_regions',
                            MultiSelectionTrait([REGION_NAMES_PRIMARY[0]],
                                                REGION_NAMES_PRIMARY))
        self.register_trait('primary_postProcessing_deleteObjects',
                             BooleanTrait(True, 'Delete rejected objects'))
        self.register_trait('primary_zSliceOrProjection',
                       StringTrait('1', 10,
                                   label='Z-slice or projection'))
        self.register_trait('primary_removeBorderObjects',
                            BooleanTrait(True, label='Remove border objects'))

        self.register_trait('primary_intensityWatershed',
                       BooleanTrait(False, label='Watershed by intensity'))
        self.register_trait('primary_intensityWatershed_gaussSize',
                         IntTrait(1, 0, 10000, label='Gauss radius'))
        self.register_trait('primary_intensityWatershed_maximaSize',
                         IntTrait(1, 0, 10000, label='Min. seed distance'))
        self.register_trait('primary_intensityWatershed_minMergeSize',
                         IntTrait(1, 0, 10000, label='Object size threshold'))

        self.add_expanding_spacer()


        self.set_tab_name('SecondaryChannel')

        self.add_input('secondary_processChannel',
                       BooleanTrait(False, label='Process channel'))
        self.add_input('secondary_channelId',
                       StringTrait('rfp', 100, label='Secondary channel ID'))
#        self.add_input('zSliceOrProjection',
#                       StringTrait('1', 10,
#                                   label='Z-slice or projection',
#                                   tooltip='abc...'))
        self.add_group('16 to 8 bit conversion', None,
                       [('secondary_normalizeMin',
                        IntTrait(0, -2**16, 2**16, label='Min.')),
                        ('secondary_normalizeMax',
                        IntTrait(255, -2**16, 2**16, label='Max.')),
                        ], layout='flow')
        self.add_group('Channel registration', None,
                       [('secondary_channelRegistration_x',
                         IntTrait(0, -99999, 99999,
                                  label='Shift X')),
                        ('secondary_channelRegistration_y',
                         IntTrait(0, -99999, 99999,
                                  label='Shift Y')),
                        ], layout='flow')

#        self.add_input('medianRadius',
#                       IntTrait(2, 0, 1000, label='Median radius',
#                                tooltip='abc...'))
        self.add_line()

        self.add_group('Region definition', None,
                       [('secondary_regions',
                         MultiSelectionTrait([], REGION_NAMES_SECONDARY,
                                             label='Regions'), (0,0,3,1)),
                        ('secondary_regions_expansionsize',
                         IntTrait(0, 0, 4000, label='Expansion'), (0,1,1,1)),
                        ('secondary_regions_expansionseparationsize',
                         IntTrait(0, 0, 4000, label='Exp. spacer'), (0,2,1,1)),
                        ('secondary_regions_shrinkingseparationsize',
                         IntTrait(0, 0, 4000, label='Shrinking'), (1,1,1,1)),
                        ])

        self.register_trait('secondary_zSliceOrProjection',
                       StringTrait('1', 10,
                                   label='Z-slice or projection'))

        self.add_expanding_spacer()

        self._init_control()

    def _get_modified_settings(self):
        settings = copy.deepcopy(self._settings)

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        sec_regions = settings.get2('secondary_regions')
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set2('primary_classification', False)
        settings.set2('secondary_classification', False)
        settings.set2('primary_simplefeatures_texture', False)
        settings.set2('primary_simplefeatures_shape', False)
        settings.set2('secondary_simplefeatures_texture', False)
        settings.set2('secondary_simplefeatures_shape', False)
        settings.set_section('Tracking')
        settings.set2('tracking', False)
        settings.set('Output', 'rendering_class', {})

        if self._tab.currentIndex() == 0:
            settings.set('ObjectDetection', 'secondary_processChannel', False)
            settings.set('Output', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0), 'contours': {'primary': ('#FF0000', 1, False)}}}})
        else:
            settings.set('ObjectDetection', 'secondary_processChannel', True)
            settings.set('Output', 'rendering', {'secondary_contours': {sec_id: {'raw': ('#FFFFFF', 1.0), 'contours': {sec_regions[0]: ('#FF0000', 1, False)}}}})

        return settings


class ClassificationFrame(InputFrame, ProcessorMixin):

    SECTION = 'Classification'
    TABS = ['PrimaryChannel', 'SecondaryChannel']
    RUN_BUTTON_TEXT1 = 'Pick %s samples'
    RUN_BUTTON_TEXT2 = 'Stop %s picking'
    RUN2_BUTTON_TEXT1 = 'Train %s classifier'
    RUN2_BUTTON_TEXT2 = 'Stop %s training'

    def __init__(self, settings, parent):
        InputFrame.__init__(self, settings, parent)
        ProcessorMixin.__init__(self)

        self.set_tab_name('PrimaryChannel')

        self.add_group('Feature extraction', None,
                       [
                        ('primary_simplefeatures_texture',
                         BooleanTrait(True, label='Texture features')),
                        ('primary_simplefeatures_shape',
                         BooleanTrait(True, label='Shape features')),
                        ], layout='flow')

#        self.add_group('primary_featureExtraction',
#                       BooleanTrait(False, label='Apply feature extraction',
#                                    tooltip='abc...'),
#                       [('primary_featureExtraction_categories',
#                         MultiSelectionTrait([], FEATURE_CATEGORIES,
#                                             label='Feature categories',
#                                             tooltip='abc...')),
#                        ('primary_featureExtraction_parameters',
#                         DictTrait({}, label='Feature parameters',
#                                   tooltip='abc...')),
#                        ])
        self.add_line()

        self.add_input('primary_classification',
                       BooleanTrait(False, label='Apply classification',
                                    tooltip='Predict object during analysis.'))
#        self.add_input('primary_classification_regionName',
#                       SelectionTrait(REGION_NAMES_PRIMARY[0],
#                                      REGION_NAMES_PRIMARY,
#                                      label='Region name',
#                                      tooltip='abc...'))
        self.add_input('primary_classification_envPath',
                       StringTrait('', 1000, label='Classifier path',
                                   tooltip='abc...',
                                   widget_info=StringTrait.STRING_PATH))
#        self.add_input('primary_classification_labels',
#                         ListTrait([], label='Class labels',
#                                   tooltip='abc...'))

        self.register_trait('primary_classification_regionName',
                            SelectionTrait(REGION_NAMES_PRIMARY[0],
                                           REGION_NAMES_PRIMARY,
                                           label='Region name'))

        self.add_expanding_spacer()

        self.set_tab_name('SecondaryChannel')

        self.add_group('Feature extraction', None,
                       [
                        ('secondary_simplefeatures_texture',
                         BooleanTrait(True, label='Texture features')),
                        ('secondary_simplefeatures_shape',
                         BooleanTrait(True, label='Shape features'))
#                        ('secondary_featureExtraction_categories',
#                         MultiSelectionTrait([], FEATURE_CATEGORIES,
#                                             label='Feature categories',
#                                             tooltip='abc...')),
#                        ('secondary_featureExtraction_parameters',
#                         DictTrait({}, label='Feature parameters',
#                                   tooltip='abc...')),
                        ], layout='flow')

        self.add_line()

#                        ('secondary_classification_collectSamples',
#                         BooleanTrait(False, label='Collect samples',
#                                      tooltip='abc...')),
        self.add_input('secondary_classification',
                       BooleanTrait(False, label='Apply classification',
                                    tooltip='abc...'))
        self.add_input('secondary_classification_regionName',
                       SelectionTrait(REGION_NAMES_SECONDARY[0],
                                      REGION_NAMES_SECONDARY,
                                      label='Region name',
                                      tooltip='abc...'))
        self.add_input('secondary_classification_envPath',
                       StringTrait('', 1000, label='Classifier path',
                                   tooltip='abc...',
                                   widget_info=StringTrait.STRING_PATH))
#                        ('secondary_classification_prefix',
#                         StringTrait('', 50, label='Name prefix',
#                                     tooltip='abc...')),
#                        ('secondary_classification_annotationFileExt',
#                         StringTrait('', 50, label='Annotation ext.',
#                                     tooltip='abc...')),
#        self.add_input('secondary_classification_labels',
#                         ListTrait([], label='Class labels',
#                                   tooltip='abc...'))

        self.register_trait('collectsamples', BooleanTrait(False))
        self.register_trait('collectsamples_prefix', StringTrait('',100))

        self.add_expanding_spacer()

        self._init_control()

    def _get_modified_settings(self):
        settings = copy.deepcopy(self._settings)

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        sec_regions = settings.get2('secondary_regions')
        settings.set_section('Classification')
        settings.set2('primary_classification', False)
        settings.set2('secondary_classification', False)
        settings.set2('collectsamples', True)
        settings.set2('secondary_classification', False)
        settings.set_section('Tracking')
        settings.set2('tracking', False)
        settings.set('Output', 'rendering_class', {})

        if self._tab.currentIndex() == 0:
            settings.set_section('Classification')
            settings.set2('primary_featureExtraction', True)
            settings.set2('secondary_featureExtraction', False)
            settings.set2('collectsamples_prefix', 'primary')
            settings.set('ObjectDetection', 'secondary_processChannel', False)
            settings.set('Output', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0), 'contours': {'primary': ('#FF0000', 1, False)}}}})
        else:
            settings.set_section('Classification')
            settings.set2('primary_featureExtraction', False)
            settings.set2('secondary_featureExtraction', True)
            settings.set2('collectsamples_prefix', 'secondary')
            settings.set('ObjectDetection', 'secondary_processChannel', True)
            settings.set('Output', 'rendering', {'secondary_contours': {sec_id: {'raw': ('#FFFFFF', 1.0), 'contours': {sec_regions[0]: ('#FF0000', 1, False)}}}})

        return settings


class TrackingFrame(InputFrame):

    SECTION = 'Tracking'

    def __init__(self, settings, parent):
        super(TrackingFrame, self).__init__(settings, parent)

        self.add_group('tracking',
                       BooleanTrait(False, label='Apply tracking',
                                    tooltip='abc...'),
                       [('tracking_maxObjectDistance',
                        IntTrait(0, 0, 4000, label='Max object x-y distance',
                                 tooltip='abc...')),
                        ('tracking_maxTrackingGap',
                         IntTrait(0, 0, 4000, label='Max timepoint gap',
                                  tooltip='abc...')),
                        ('tracking_maxSplitObjects',
                         IntTrait(0, 0, 4000, label='Max split events',
                                  tooltip='abc...')),
                        ], layout='flow')


        self.add_line()

        self.add_input('tracking_labelTransitions',
                        StringTrait('', 200, label='Class transition motif(s)',
                                    tooltip='abc...'))

        self.add_group('tracking_synchronize_trajectories',
                       BooleanTrait(True, label='Synchronize trajectories'),
                       [
                        ('tracking_backwardRange',
                         IntTrait(0, 0, 4000, label='Timepoints pre-transition',
                                  tooltip='abc...'), (0,0,1,1)),
                        ('tracking_forwardRange',
                         IntTrait(0, 0, 4000, label='Timepoints post-transition',
                                  tooltip='abc...'), (0,1,1,1)),
                        ('tracking_backwardLabels',
                         StringTrait('', 200, label='Class filter pre-transition',
                                     tooltip='abc...'), (1,0,1,1)),
                        ('tracking_forwardLabels',
                         StringTrait('', 200, label='Class filter post-transition',
                                     tooltip='abc...'), (1,1,1,1)),
#                        ('tracking_backwardCheck',
#                         IntTrait(0, 0, 4000, label='Backward check',
#                                  tooltip='abc...'), (1,0,1,1)),
#                        ('tracking_forwardCheck',
#                         IntTrait(0, 0, 4000, label='Forward check',
#                                  tooltip='abc...'), (1,1,1,1)),
                        ])

        self.register_trait('tracking_forwardRange_min',
                            BooleanTrait(False, label='Min.',
                                         tooltip='abc...'))
        self.register_trait('tracking_backwardRange_min',
                            BooleanTrait(False, label='Min.',
                                         tooltip='abc...'))


#        self.add_group('tracking_event_tracjectory',
#                       BooleanTrait(True, label='Events by trajectory',
#                                    widget_info=BooleanTrait.RADIOBUTTON),
#                       [('tracking_backwardCheck',
#                         IntTrait(0, 0, 4000, label='Backward check',
#                                  tooltip='abc...')),
#                        ('tracking_forwardCheck',
#                         IntTrait(0, 0, 4000, label='Forward check',
#                                  tooltip='abc...')),
#                        ], layout='flow')


        self.add_line()

        self.add_group('tracking_exportTrackFeatures',
                       BooleanTrait(False, label='Export tracks',
                                    tooltip='abc...'),
                       [('tracking_compressionTrackFeatures',
                         SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
                                        label='Compression',
                                        tooltip='abc...'))
                       ])
#        self.add_group('tracking_exportFlatFeatures',
#                       BooleanTrait(False, label='Export flat',
#                                    tooltip='abc...'),
#                       [('tracking_compressionFlatFeatures',
#                         SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
#                                        label='Compression',
#                                        tooltip='abc...'))
#                       ])

        self.add_expanding_spacer()

        self.register_trait('tracking_maxInDegree',
                       IntTrait(0, 0, 4000, label='Max in-degree',
                                tooltip='abc...'))
        self.register_trait('tracking_maxOutDegree',
                       IntTrait(0, 0, 4000, label='Max out-degree',
                                tooltip='abc...'))

class OutputFrame(InputFrame):

    SECTION = 'Output'

    def __init__(self, settings, parent):
        super(OutputFrame, self).__init__(settings, parent)

        self.add_input('rendering',
                       DictTrait({}, label='Rendering',
                                 tooltip='abc...'))
        self.add_input('rendering_discwrite',
                       BooleanTrait(True, label='Write images to disc',
                                    tooltip='abc...'))
        self.add_input('rendering_class',
                       DictTrait({}, label='Rendering class',
                                 tooltip='abc...'))
        self.add_input('rendering_class_discwrite',
                       BooleanTrait(True, label='Write images to disc',
                                    tooltip='abc...'))


        self.add_group('Filter feature values', None,
                       [
                        ('primary_featureExtraction_exportFeatureNames',
                         ListTrait([], label='Primary channel',
                                   tooltip='abc...')),
                        ('secondary_featureExtraction_exportFeatureNames',
                         ListTrait([], label='Secondary channel',
                                   tooltip='abc...')),
                        ], layout='flow')

        self.add_expanding_spacer()


class ProcessingFrame(InputFrame):

    SECTION = 'Processing'

    def __init__(self, settings, parent):
        super(ProcessingFrame, self).__init__(settings, parent)

        frame = self._get_frame()
        layout = frame.layout()

        #log_window.setMaximumBlockCount(10)
        #log_window.setCenterOnScroll(True)
        #layout.addWidget(self._log_window, 0, 0, 1, 3)



class ImageDisplay(QLabel):

    def __init__(self, parent, ratio):
        QLabel.__init__(self, parent,
                        Qt.CustomizeWindowHint|Qt.WindowCloseButtonHint|
                        Qt.WindowMinimizeButtonHint|Qt.SubWindow)
        self._ratio = ratio

    def heightForWidth(self, w):
        return int(w*self._ratio)


class CleanupFrame(InputFrame):

    SECTION = 'Cleanup'

    def __init__(self, settings, parent):
        super(CleanupFrame, self).__init__(settings, parent)


class FarmingFrame(InputFrame):

    SECTION = 'Farming'

    def __init__(self, settings, parent):
        super(FarmingFrame, self).__init__(settings, parent)

        self.add_input('usePyFarm',
                       BooleanTrait(False, label='Use PyFarm',
                                    tooltip='abc...'))
        self.add_input('emailRecipients',
                       ListTrait([], label='Email recipients',
                                 tooltip='abc...'))

        self.add_expanding_spacer()


#-------------------------------------------------------------------------------
# main:
#

if __name__ == "__main__":

    app = QApplication(sys.argv)
    #app.setStyleSheet(STYLESHEET_CARBON)
    app.setWindowIcon(QIcon(':cecog_analyzer_icon'))
    main = AnalyzerMainWindow()
    main.raise_()

    #filename = '/Users/miheld/src/mito_svn/trunk/mito/analyzer_mitocheck_settings.conf'
    #filename = '/Users/miheld/src/mito_svn/trunk/mito/_analyzer_test_settings.conf'
    filename = '/Users/miheld/data/CellCognition/demo_data/H2bTub20x_settings.conf'
    if os.path.isfile(filename):
        main.read_settings(filename)
    #main._on_run_analyer()

    sys.exit(app.exec_())
