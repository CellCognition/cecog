"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2009 Michael Held
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

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys
import os
import types
import pprint
import logging
import traceback
import copy
import time
import subprocess
import StringIO

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.ordereddict import OrderedDict
from pdk.fileutils import safe_mkdirs
from pdk.datetimeutils import TimeInterval

#import netCDF4


#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.extensions.ConfigParser import RawConfigParser
from cecog.io.reader import PIXEL_TYPES
from cecog.analyzer.core import AnalyzerCore
from cecog import ccore
from cecog.learning.learning import CommonObjectLearner, CommonClassPredictor
from cecog.util import hexToRgb, write_table

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
SECONDARY_COLORS = {'inside' : '#FFFF00',
                    'outside' : '#00FF00',
                    'expanded': '#00FFFF',
                    }

COMPRESSION_FORMATS = ['raw', 'bz2', 'gz']
TRACKING_METHODS = ['ClassificationCellTracker',]

CONTROL_1 = 'CONTROL_1'
CONTROL_2 = 'CONTROL_2'

R_LIBRARIES = ['hwriter', 'RColorBrewer', 'igraph']

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

def message(parent, title, text, info=None, detail=None, buttons=None,
            icon=None):
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    if not info is None:
        msg_box.setInformativeText(info)
    if not detail is None:
        msg_box.setDetailedText(detail)
    if not icon is None:
        msg_box.setIcon(icon)
    if not buttons is None:
        msg_box.setStandardButtons(buttons)
    return msg_box.exec_()

def information(parent, title, text, info=None, detail=None):
    return message(parent, title, text, info=info, detail=detail,
                   buttons=QMessageBox.Ok,
                   icon=QMessageBox.Information)

def question(parent, title, text, info=None, detail=None):
    return message(parent, title, text, info=info, detail=detail,
                   buttons=QMessageBox.Yes|QMessageBox.No,
                   icon=QMessageBox.Question)

def critical(parent, title, text, info=None, detail=None):
    return message(parent, title, text, info=info, detail=detail,
                   buttons=QMessageBox.Ok,
                   icon=QMessageBox.Critical)

def warning(parent, title, text, info=None, detail=None):
    return message(parent, title, text, info=info, detail=detail,
                   buttons=QMessageBox.Ok,
                   icon=QMessageBox.Warning)

def status(msg, timeout=0):
    qApp._statusbar.showMessage(msg, timeout)

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

        #menu_help = self.menuBar().addMenu('&Help')

        qApp._statusbar = QStatusBar(self)
        self.setStatusBar(qApp._statusbar)


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

        self._tab_lookup = OrderedDict()
        self._tabs = [GeneralFrame(self._settings, self._pages),
                      ObjectDetectionFrame(self._settings, self._pages),
                      ClassificationFrame(self._settings, self._pages),
                      TrackingFrame(self._settings, self._pages),
                      ErrorCorrectionFrame(self._settings, self._pages),
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

        qApp._log_handler = GuiLogHandler(self)
        qApp._log_window = LogWindow(qApp._log_handler)
        qApp._log_window.setGeometry(50,50,600,300)

        logger = logging.getLogger()
        qApp._log_handler.setLevel(logging.NOTSET)
        formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
        qApp._log_handler.setFormatter(formatter)
        #logger.addHandler(self._handler)
        logger.setLevel(logging.NOTSET)

        qApp._image_dialog = None
        qApp._graphics = None

        self.setGeometry(0, 0, 1100, 750)
        self.setMinimumSize(QSize(700,600))
        self.show()
        self.center()
        self.raise_()


    def closeEvent(self, event):
        print "close"
        QMainWindow.closeEvent(self, event)
        qApp.quit()

    def test_r_import(self):
        try:
            import rpy2.robjects as robjects
            import rpy2.rinterface as rinterface
            import rpy2.robjects.numpy2ri

            # some tests
            x = robjects.r['pi']
            v = robjects.FloatVector([1.1, 2.2, 3.3, 4.4, 5.5, 6.6])
            m = robjects.r['matrix'](v, nrow = 2)
            has_R_version = True
            version = '%s.%s' % (robjects.r['version'][5][0],
                                 robjects.r['version'][6][0])
        except:
            has_R_version = False
            msg = 'R installation not found.\n\n'\
                  'To use HMM error correction or plotting functions '\
                  'R >= Version 2.9 must be installed together with these.'\
                  'packages:\n'
            msg += ', '.join(R_LIBRARIES)
            msg += '\n\nSee http://www.r-project.org\n\n'
            msg += traceback.format_exc(1)
            QMessageBox.warning(self, 'R installation not found', msg)


        if has_R_version:
            missing_libs = []
            buffer = []
            rinterface.setWriteConsole(lambda x: buffer.append(x))
            for lib_name in R_LIBRARIES:
                try:
                    robjects.r['library'](lib_name)
                except:
                    missing_libs.append(lib_name)
            rinterface.setWriteConsole(None)
            if len(missing_libs) > 0:
                msg = 'Missing R package(s)\n\n'
                msg += ', '.join(missing_libs)
                msg += '\n\nSee http://www.r-project.org\n\n'
                msg += '\n'.join(buffer)

                QMessageBox.warning(self, 'Missing R libraries', msg)
                qApp.valid_R_version = False
            else:
                qApp.valid_R_version = True


    def _add_page(self, widget):
        button = QListWidgetItem(self._selection)
        button.setIcon(QIcon(widget.ICON))
        button.setText(widget.get_name())
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
        widget.toggle_tabs.connect(self._on_toggle_tabs)
        self._tab_lookup[widget.get_name()] = (button, widget)
        return widget.size()

    def _on_toggle_tabs(self, name):
        '''
        toggle ItemIsEnabled flag for all list items but name
        '''
        for name2 in self._tab_lookup:
            if name2 != name:
                item, widget = self._tab_lookup[name2]
                flags = item.flags()
                # check flag (and)
                if flags & Qt.ItemIsEnabled:
                    # remove flag (nand)
                    item.setFlags(flags & ~Qt.ItemIsEnabled)
                else:
                    # set flag (or)
                    item.setFlags(flags | Qt.ItemIsEnabled)

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
        status('Settings successfully loaded.')

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
        status('Settings successfully saved.')

    def _on_about(self):
        print "about"
        dialog = QDialog(self)
        #dialog.setBackgroundRole(QPalette.Dark)
        dialog.setStyleSheet('background: #000000; '
                             'background-image: url(:cecog_about)')
        dialog.setWindowTitle('About')
        dialog.setFixedSize(400,300)
        layout = QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        #image = QImage(':cecog_splash')
        #label1 = QLabel(dialog)
        #label1.setStyleSheet('background-image: url(:cecog_splash)')
        #label1.setPixmap(QPixmap.fromImage(image))
        #layout.addWidget(label1, 0, 0)
        label2 = QLabel(dialog)
        label2.setStyleSheet('background: transparent;')
        label2.setAlignment(Qt.AlignCenter)
        label2.setText('CellCognition AnalyzerOne\n'
                       'Copyright (c) 2006 - 2009 by Michael Held\n'
                       'Gerlich Lab, ETH Zurich, Switzerland')
        label3 = QLabel(dialog)
        label3.setStyleSheet('background: transparent;')
        label3.setTextFormat(Qt.AutoText)
        label3.setOpenExternalLinks(True)
        label3.setAlignment(Qt.AlignCenter)
        #palette = label2.palette()
        #palette.link = QBrush(QColor(200,200,200))
        #label3.setPalette(palette)
        label3.setText('<style>a { color: green; } a:visited { color: green; }</style>'
                       '<a href="http://www.cellcognition.org">www.cellcognition.org</a><br><br>')
        layout.addWidget(label2, 1, 0)
        layout.addWidget(label3, 2, 0)
        layout.setAlignment(Qt.AlignCenter|
                            Qt.AlignBottom)
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
        logger = logging.getLogger()
        logger.addHandler(qApp._log_handler)
        qApp._log_window.show()
        qApp._log_window.raise_()

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


class _ProcessingThread(QThread):

    stage_info = pyqtSignal(dict)
    analyzer_error = pyqtSignal(str, int)

    def __init__(self, parent, settings):
        QThread.__init__(self, parent)
        self._settings = settings
        self._abort = False
        self._mutex = QMutex()
        self._stage_info = {'text': '',
                            'progress': 0,
                            'max': 0,
                            }

    def __del__(self):
        #self._mutex.lock()
        self._abort = True
        self._mutex.unlock()
        self.stop()
        self.wait()

    def run(self):
        try:
            self._run()
        except:
            msg = traceback.format_exc()
            msg2 = traceback.format_exc(5)
            logger = logging.getLogger()
            logger.error(msg)
            self.analyzer_error.emit(msg2, 0)
            raise

    def set_abort(self):
        self._mutex.lock()
        self._abort = True
        self._mutex.unlock()

    def get_abort(self):
        abort = self._abort
        return abort

    def set_stage_info(self, info):
        self._mutex.lock()
        self.stage_info.emit(info)
        self._mutex.unlock()



class HmmThread(_ProcessingThread):

    def __init__(self, parent, settings, learner_dict):
        _ProcessingThread.__init__(self, parent, settings)
        self._learner_dict = learner_dict

        qApp._log_window.show()
        qApp._log_window.raise_()
        logger = logging.getLogger()
        logger.addHandler(qApp._log_handler)

    def __del__(self):
        logger = logging.getLogger()
        logger.removeHandler(qApp._log_handler)

    @classmethod
    def test_executable(cls, filename):
        filename = filename.strip()
        if filename != '':
            cmd = filename
        else:
            cmd = 'R32'
        #process = QProcess()
        #process.setWorkingDirectory(wd)
        #process.start(cmd, ['--version'])
        #process.waitForFinished()

        return ''

    def _run(self):
        filename = self._settings.get('ErrorCorrection', 'filename_to_R').strip()
        if filename != '':
            cmd = filename
        else:
            cmd = 'R32'

        #import tempfile
        #filename_out = os.path.join(tempfile.gettempdir(), 'cecog_error_correction.txt')
        wd = 'resources/rsrc/hmm'
        wd = os.path.abspath(wd)
        print wd

        f = file(os.path.join(wd, 'run_hmm.R'), 'r')
        lines = f.readlines()
        f.close()

        self._settings.set_section('ErrorCorrection')

        # R on windows works better with '/' then '\'
        self._join = lambda *x: '/'.join(x)
        path_analyzed = self._join(self._settings.get('General', 'pathout'), 'analyzed')
        path_out_hmm = self._join(self._settings.get('General', 'pathout'), 'hmm')
        safe_mkdirs(path_out_hmm)

        region_name_primary = self._settings.get('Classification', 'primary_classification_regionname')
        region_name_secondary = self._settings.get('Classification', 'secondary_classification_regionname')

        if self._settings.get2('position_labels'):
            mapping_file = self._settings.get2('mappingfile')
        else:
            mapping_file = self._generate_mapping(wd, path_out_hmm, path_analyzed)

        #print self._learner_dict, self._settings.get('Processing', 'primary_errorcorrection'), self._settings.get('Processing', 'primary_errorcorrection')

        for i in range(len(lines)):
            line2 = lines[i].strip()
            if line2 == '#WORKING_DIR':
                lines[i] = "WORKING_DIR = '%s'\n" % wd
            elif line2 == '#FILENAME_MAPPING':
                lines[i] = "FILENAME_MAPPING = '%s'\n" % mapping_file
            elif line2 == '#PATH_INPUT':
                path_out = path_analyzed
                lines[i] = "PATH_INPUT = '%s'\n" % path_out
            elif line2 == '#PATH_OUTPUT':
                lines[i] = "PATH_OUTPUT = '%s'\n" % path_out_hmm
            elif line2 == '#GROUP_BY_GENE':
                lines[i] = "GROUP_BY_GENE = %s\n" % str(self._settings.get2('groupby_genesymbol')).upper()
            elif line2 == '#GROUP_BY_OLIGOID':
                lines[i] = "GROUP_BY_OLIGOID = %s\n" % str(self._settings.get2('groupby_oligoid')).upper()
            elif line2 == '#TIMELAPSE':
                lines[i] = "TIMELAPSE = %s\n" % self._settings.get2('timelapse')
            elif line2 == '#MAX_TIME':
                lines[i] = "MAX_TIME = %s\n" % self._settings.get2('max_time')

            if 'primary' in self._learner_dict and self._settings.get('Processing', 'primary_errorcorrection'):

                if self._settings.get2('constrain_graph'):
                    primary_graph = self._settings.get2('primary_graph')
                else:
                    primary_graph = self._generate_graph('primary', wd, path_out_hmm, region_name_primary)

                if line2 == '#FILENAME_GRAPH_P':
                    lines[i] = "FILENAME_GRAPH_P = '%s'\n" % primary_graph
                elif line2 == '#CLASS_COLORS_P':
                    learner = self._learner_dict['primary']
                    colors = ",".join(["'%s'" % learner.dctHexColors[x] for x in learner.lstClassNames])
                    lines[i] = "CLASS_COLORS_P = c(%s)\n" % colors
                elif line2 == '#REGION_NAME_P':
                    lines[i] = "REGION_NAME_P = '%s'\n" % region_name_primary
                elif line2 == '#SORT_CLASSES_P':
                    primary_sort = self._settings.get2('primary_sort')
                    if primary_sort == '':
                        lines[i] = "SORT_CLASSES_P = NULL\n"
                    else:
                        lines[i] = "SORT_CLASSES_P = c(%s)\n" % primary_sort

            if 'secondary' in self._learner_dict and self._settings.get('Processing', 'secondary_errorcorrection'):
                if self._settings.get2('constrain_graph'):
                    secondary_graph = self._settings.get2('secondary_graph')
                else:
                    secondary_graph = self._generate_graph('secondary', wd, path_out_hmm, region_name_secondary)

                if line2 == '#FILENAME_GRAPH_S':
                    lines[i] = "FILENAME_GRAPH_S = '%s'\n" % secondary_graph
                elif line2 == '#CLASS_COLORS_S':
                    learner = self._learner_dict['secondary']
                    colors = ",".join(["'%s'" % learner.dctHexColors[x] for x in learner.lstClassNames])
                    lines[i] = "CLASS_COLORS_S = c(%s)\n" % colors
                elif line2 == '#REGION_NAME_S':
                    lines[i] = "REGION_NAME_S = '%s'\n" % region_name_secondary
                elif line2 == '#SORT_CLASSES_S':
                    secondary_sort = self._settings.get2('secondary_sort')
                    if secondary_sort == '':
                        lines[i] = "SORT_CLASSES_S = NULL\n"
                    else:
                        lines[i] = "SORT_CLASSES_S = c(%s)\n" % secondary_sort

        input_filename = os.path.join(path_out_hmm, 'cecog_hmm_input.R')
        input = file(input_filename, 'w')
        input.writelines(lines)
        input.close()

        info = {'min' : 0,
                'max' : 0,
                'stage': 0,
                'progress': 0}
        self.set_stage_info(info)

        self._process = QProcess()
        self._process.setStandardInputFile(input_filename)
        self._process.setWorkingDirectory(wd)
        self._process.start(cmd, ['--slave', '--no-save'])
        self.connect(self._process, SIGNAL('finished ( int )'),
                     self._on_finished)
        self.connect(self._process, SIGNAL('readyReadStandardOutput()'),
                     self._on_stdout)
        self.connect(self._process, SIGNAL('readyReadStandardError()'),
                     self._on_stderr)

        self._process.waitForFinished()


    def _generate_graph(self, channel, wd, hmm_path, region_name):
        f_in = file(os.path.join(wd, 'graph_template.txt'), 'rU')
        filename_out = self._join(hmm_path, 'graph_%s.txt' % region_name)
        f_out = file(filename_out, 'w')
        learner = self._learner_dict[channel]
        for line in f_in:
            line2 = line.strip()
            if line2 in ['#numberOfClasses', '#numberOfHiddenStates']:
                f_out.write('%d\n' % len(learner.lstClassNames))
            elif line2 == '#startNodes':
                f_out.write('%s\n' % '  '.join(map(str, learner.lstClassLabels)))
            elif line2 == '#transitionGraph':
                f_out.write('%s -> %s\n' %
                            (','.join(map(str, learner.lstClassLabels)),
                             ','.join(map(str, learner.lstClassLabels))))
            elif line2 == '#hiddenNodeToClassificationNode':
                for label in learner.lstClassLabels:
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
                         if os.path.isdir(os.path.join(path_analyzed, x)) and
                         x[0] != '_']
        else:
            positions = positions.split(',')
        for pos in positions:
            rows.append({'Position': pos, 'OligoID':'', 'GeneSymbol':'', 'Group':''})
        header_names = ['Position', 'OligoID', 'GeneSymbol', 'Group']
        write_table(filename_out, header_names, rows, sep='\t')
        return filename_out

    def _on_finished(self, code):
        print 'finished', code
        progress = 1 if code == 0 else None
        info = {'min' : 0,
                'max' : 1,
                'stage': 0,
                'progress': progress}
        self.set_stage_info(info)

    def _on_stdout(self):
        self._process.setReadChannel(QProcess.StandardOutput)
        msg = str(self._process.readLine()).rstrip()
        #print msg
        logger = logging.getLogger()
        logger.info(msg)

    def _on_stderr(self):
        self._process.setReadChannel(QProcess.StandardError)
        #print str(self._process.readLine()).rstrip()
        msg = ''.join(list(self._process.readAll()))
        self.analyzer_error.emit(msg, 0)

    def set_abort(self):
        _ProcessingThread.set_abort(self)
        if self._abort:
            self._process.kill()

class AnalzyerThread(_ProcessingThread):

    image_ready = pyqtSignal(ccore.ImageRGB, str, str)

    def __init__(self, parent, settings):
        _ProcessingThread.__init__(self, parent, settings)
        self._renderer = None

    def _run(self):
        analyzer = AnalyzerCore(self._settings)
        analyzer.processPositions(self)

    def set_renderer(self, name):
        self._mutex.lock()
        self._renderer = name
        self._mutex.unlock()

    def get_renderer(self):
        return self._renderer

    def set_image(self, image_rgb, info, filename=''):
        self._mutex.lock()
        self.image_ready.emit(image_rgb, info, filename)
        self._mutex.unlock()


class ClassifierResultFrame(QGroupBox):

    LABEL_FEATURES = '#Features: %d'
    LABEL_ACC = 'Accuracy: %.1f%%'
    LABEL_C = 'Log2(C) = %.1f'
    LABEL_G = 'Log2(g) = %.1f'

    def __init__(self, parent, channel, settings):
        QGroupBox.__init__(self, parent)

        self._channel = channel
        self._settings = settings

        layout = QGridLayout(self)

        self._button = QPushButton('Load', self)
        self.connect(self._button, SIGNAL('clicked()'), self._on_load)
        layout.addWidget(self._button, 1, 2)

        self._label_features = QLabel(self.LABEL_FEATURES % 0, self)
        layout.addWidget(self._label_features, 3, 2)
        self._label_acc = QLabel(self.LABEL_ACC % float('NAN'), self)
        layout.addWidget(self._label_acc, 4, 2)
        self._label_c = QLabel(self.LABEL_C % float('NAN'), self)
        layout.addWidget(self._label_c, 5, 2)
        self._label_g = QLabel(self.LABEL_G % float('NAN'), self)
        layout.addWidget(self._label_g, 6, 2)

        label = QLabel('Confusion matrix', self)
        layout.addWidget(label, 0, 1, Qt.AlignBottom)
        self._table_conf = QTableWidget(self)
        self._table_conf.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table_conf.setSelectionMode(QTableWidget.NoSelection)

        self._table_conf.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
                                              QSizePolicy.Expanding|QSizePolicy.Maximum))
        layout.addWidget(self._table_conf, 1, 1, 6, 1)

        label = QLabel('Class & annotation info', self)
        layout.addWidget(label, 0, 0, Qt.AlignBottom)
        self._table_info = QTableWidget(self)
        self._table_info.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table_info.setSelectionMode(QTableWidget.NoSelection)
        self._table_info.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                                   QSizePolicy.Expanding|QSizePolicy.Maximum))
        layout.addWidget(self._table_info, 1, 0, 6, 1)
        layout.addItem(QSpacerItem(1, 1,
                                   QSizePolicy.Fixed,
                                   QSizePolicy.MinimumExpanding), 2, 2)
#        layout.addItem(QSpacerItem(1, 1,
#                                   QSizePolicy.MinimumExpanding,
#                                   QSizePolicy.MinimumExpanding), 0, 3, 4, 1)


        self._has_data = False

    def clear(self):
        self._table_conf.clear()
        self._table_info.clear()
        self._has_data = False

    def _on_load(self):
        self.load_classifier(check=True)

    def load_classifier(self, check=True):

        _resolve = lambda x,y: self._settings.get(x, '%s_%s' % (self._channel, y))
        classifier_infos = {'strEnvPath' : _resolve('Classification', 'classification_envpath'),
                            #'strModelPrefix' : _resolve('Classification', 'classification_prefix'),
                            'strChannelId' : _resolve('ObjectDetection', 'channelid'),
                            'strRegionId' : _resolve('Classification', 'classification_regionname'),
                            }
        self._learner = CommonClassPredictor(dctCollectSamples=classifier_infos)

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

            widget = information(self, 'Classifier inspection results',
                                 'Classifier inspection results',
                                 info=msg)

        if result['has_arff']:
            self._learner.importFromArff()
            self._label_features.setText(self.LABEL_FEATURES %
                                         len(self._learner.lstFeatureNames))

        elif result['has_definition']:
            self._learner.loadDefinition()
            self._set_info_table()

        if result['has_conf']:
            c, g, accuracy, conf = self._learner.importConfusion()
            self._set_info(c, g, accuracy)
            self._init_conf_table(conf)
            self._update_conf_table(conf)

        self._set_info_table()

    def msg_pick_samples(self, parent):
        result = self._learner.check()
        title = 'Sample picking is not possible'
        info = 'You need to provide a class definition '\
               'file and annotation files.'
        detail = 'Missing components:\n'
        if not result['has_path_annotations']:
            detail += "- Annotation path '%s' not found.\n" % result['path_annotations']
        if not result['has_definition']:
            detail += "- Class definition file '%s' not found.\n" % result['definition']
        return information(parent, title, title, info, detail)

    def is_pick_samples(self):
        result = self._learner.check()
        return result['has_path_annotations'] and result['has_definition']

    def msg_train_classifier(self, parent):
        result = self._learner.check()
        title = 'Classifier training is not possible'
        info = 'You need to pick samples first.'
        detail = 'Missing components:\n'
        if not result['has_arff']:
            detail += "- Feature file '%s' not found.\n" % result['arff']
        return information(parent, title, title, info, detail)

    def is_train_classifier(self):
        result = self._learner.check()
        return result['has_arff']

    def msg_apply_classifier(self, parent):
        result = self._learner.check()
        title = 'Classifier model not found'
        info = 'You need to train a classifier first.'
        detail = 'Missing components:\n'
        if not result['has_model']:
            detail += "- SVM model file '%s' not found.\n" % result['model']
        if not result['has_range']:
            detail += "- SVM range file '%s' not found.\n" % result['range']
        return information(parent, title, title, info, detail)

    def is_apply_classifier(self):
        result = self._learner.check()
        return result['has_model'] and result['has_range']

    def _set_info_table(self):
        rows = len(self._learner.lstClassLabels)
        self._table_info.clear()
        self._table_info.setColumnCount(3)
        self._table_info.setRowCount(rows)
        self._table_info.setHorizontalHeaderLabels(['Name', 'Samples', 'Color'])
        self._table_info.setVerticalHeaderLabels([str(self._learner.nl2l[r])
                                                  for r in range(rows)])
        self._table_info.setColumnWidth(1, 20)
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
        self._table_info.resizeColumnsToContents()

    def _init_conf_table(self, conf):
        rows, cols = conf.shape
        self._table_conf.clear()
        self._table_conf.setColumnCount(cols)
        self._table_conf.setRowCount(rows)
        for c in range(cols):
            self._table_conf.setColumnWidth(c, 20)
            label = self._learner.nl2l[c]
            name = self._learner.dctClassNames[label]
            item = QTableWidgetItem(str(label))
            item.setToolTip('%d : %s' % (label, name))
            #item.setForeground(QBrush(QColor(*hexToRgb(names2cols[name]))))
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
        rows, cols = conf.shape
        conf_norm = conf.swapaxes(0,1) / numpy.array(numpy.sum(conf, 1), numpy.float)
        conf_norm = conf_norm.swapaxes(0,1)
        self._table_conf.clearContents()
        for r in range(rows):
            for c in range(cols):
                item = QTableWidgetItem()
                item.setToolTip('%d samples, %.2f%%' % (conf[r,c], conf_norm[r,c]*100.))
                col = int(255 * (1 - conf_norm[r,c]))
                item.setBackground(QBrush(QColor(col, col, col)))
                self._table_conf.setItem(r, c, item)

    def _set_info(self, c, g, accuracy):
        self._label_acc.setText(self.LABEL_ACC % (accuracy*100.))
        self._label_c.setText(self.LABEL_C % c)
        self._label_g.setText(self.LABEL_G % g)

    def on_conf_result(self, c, g, accuracy, conf):
        print "moo", c, g
        self._set_info(c, g, accuracy)

        if not self._has_data:
            self._has_data = True
            self._init_conf_table(conf)
            self._set_info_table()
        self._update_conf_table(conf)


class TrainingThread(_ProcessingThread):

    conf_result = pyqtSignal(float, float, float, numpy.ndarray)

    def __init__(self, parent, settings, learner):
        _ProcessingThread.__init__(self, parent, settings)
        self._learner = learner

    def _run(self):
        print "training"

        c_begin, c_end, c_step = -5,  15, 2
        c_info = c_begin, c_end, c_step

        g_begin, g_end, g_step = -15, 3, 2
        g_info = g_begin, g_end, g_step

        stage_info = {'stage': 0,
                      'text': '',
                      'min': 0,
                      'max': 1,
                      'progress': 0,
                      }
        self.set_stage_info(stage_info)

        i = 0
        best_accuracy = -1
        best_c = None
        best_g = None
        best_conf = None
        is_abort = False
        for n,c,g,validation,labels in self._learner.iterGridSearchSVM(c_info=c_info,
                                                                       g_info=g_info):
            stage_info.update({'min': 1,
                               'max': n,
                               'progress': i+1,
                               })
            self.set_stage_info(stage_info)
            i += 1
            #print i,n,len(labels)
            accuracy = numpy.sum(labels == validation) / float(len(labels))
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_c = c
                best_g = g
                #print 'BEST: ', best_accuracy, best_c, best_g

                k = len(self._learner.l2nl)
                conf = numpy.zeros((k, k))
                for l, v in zip(labels, validation):
                    l2 = self._learner.l2nl[l]
                    v2 = self._learner.l2nl[v]
                    conf[l2,v2] += 1
                best_conf = conf

                self.conf_result.emit(c, g, accuracy, conf)
            time.sleep(.3)

            if self.get_abort():
                is_abort = True
                break

        # overwrite only if grid-search was not aborted by the user
        if not is_abort:
            self.conf_result.emit(best_c, best_g, best_accuracy, best_conf)
            self._learner.train(2**best_c, 2**best_g)
            self._learner.exportConfusion(best_c, best_g, best_accuracy,
                                          best_conf)
            self._learner.exportRanges()


class LogWindow(QFrame):

    LEVELS = {'DEBUG' : logging.DEBUG,
              'INFO'  : logging.INFO,
              'WARN'  : logging.WARNING,
              'ERROR' : logging.ERROR}

    def __init__(self, handler):
        QFrame.__init__(self)
        self.setWindowTitle('Log window')

        self._handler = handler
        self._handler.message_received.connect(self._on_message_received)

        layout = QGridLayout(self)
        layout.setContentsMargins(5,5,5,5)
        self._log_widget = QPlainTextEdit(self)
        format = QTextCharFormat()
        format.setFontFixedPitch(True)
        format.setFontPointSize(11)
        self._log_widget.setCurrentCharFormat(format)
        layout.addWidget(self._log_widget, 0, 0, 1, 4)
        layout.setColumnStretch(0,2)
        layout.setColumnStretch(3,2)

        layout.addWidget(QLabel('Log level', self), 1, 0, Qt.AlignRight)
        combo = QComboBox(self)
        layout.addWidget(combo, 1, 1, Qt.AlignLeft)
        self.connect(combo, SIGNAL('currentIndexChanged(const QString &)'),
                     self._on_level_changed)
        for name in sorted(self.LEVELS, key=lambda x: self.LEVELS[x]):
            combo.addItem(name)

        self._msg_buffer = []


    def _on_message_received(self, msg):
        self._msg_buffer.append(str(msg))
        if self.isVisible():
            self._log_widget.appendPlainText('\n'.join(self._msg_buffer))
        self._msg_buffer = []

    def _on_level_changed(self, name):
        self._handler.setLevel(self.LEVELS[str(name)])

    def clear(self):
        self._msg_buffer = []
        self._log_widget.clear()


class GuiLogHandler(QObject, logging.Handler):

    message_received = pyqtSignal(str)

    def __init__(self, parent):
        self._mutex = QMutex()
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

    def __init__(self, value, label=None, tooltip=None, doc=None,
                 checkable=False):
        self.value = value
        self.label = label
        self.tooltip = tooltip
        self.doc = doc
        self.checkable = checkable

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
        if self.checkable:
            widget[0].setValue(value[0])
            widget[1].setChecked(value[1])
        else:
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
        #print value
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
        #print value, self.list_data
        widget.setCurrentIndex(self.index(value))


class MultiSelectionTrait(SelectionTrait):

    def set_value(self, widget, value):
        widget.clearSelection()
        for item in value:
            w_listitem = widget.findItems(str(item), Qt.MatchExactly)
            #if len(w_listitem) > 0:
            widget.setCurrentItem(w_listitem[0], QItemSelectionModel.Select)

    def convert(self, value):
        #print "MOO", value
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


class CecogSpinBox(QFrame):

    def __init__(self, parent, checkable=False):
        QFrame.__init__(self, parent)
        self.checkable = checkable
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        if self.checkable:
            self._checkbox = QCheckBox(self)
            layout.addWidget(self._checkbox)
        self.widget = QSpinBox(self)
        layout.addWidget(self.widget)

    def isChecked(self):
        if self.checkable:
            return self._checkbox.isChecked()
        else:
            return None

    def setChecked(self, checked):
        if self.checkable:
            self._checkbox.setChecked(checked)

    def __getattr__(self, name):
        return getattr(self.widget, name)


class InputWidgetMixin(object):

    SECTION = None
    NAME = None

    def __init__(self, settings):
        self._registry = {}
        self._settings = settings
        self._settings.register_section(self.SECTION)
        self._extra_columns = 0

    def get_name(self):
        return self.SECTION if self.NAME is None else self.NAME

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
            frame_layout.addWidget(w_group, frame._input_cnt, 1, 1, 1)
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
                     self._on_show_help)
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
#            w_input = CecogSpinBox(parent, trait.checkable)
#            w_input.setRange(trait.min_value, trait.max_value)
#            w_input.setSizePolicy(policy_fixed)
#            trait.set_value(w_input, value)
#            if not trait.step is None:
#                w_input.setSingleStep(trait.step)
#            self.connect(w_input.widget, SIGNAL('valueChanged(int)'), handler(name))

        elif isinstance(trait, FloatTrait):
            w_input = QDoubleSpinBox(parent)
            w_input.setRange(trait.min_value, trait.max_value)
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
            #print "moo1", value
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
            self._extra_columns = 1

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
                #if not w_doc is None:
                #    layout.addWidget(w_doc, parent._input_cnt, 1)

                layout.addWidget(w_input, parent._input_cnt, 1)
                if not w_button is None:
                    layout.addWidget(w_button, parent._input_cnt, 2)
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
            #print self.SECTION, name, name in self._registry
            if name in self._registry:
                w_input = self._registry[name]
                trait = self._settings.get_trait(self.SECTION, name)
                #print '    ', name, value
                trait.set_value(w_input, value)

#        else:
#            self._settings.add_section(self.SECTION)

    def _on_show_help(self, link):
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
        else:
            w_text.insertHtml("Sorry but the file '%s' was not found." %\
                               file_name)
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
                #print dialog.selectedFiles()[0]
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

    def register_process(self, name):
        pass

    def register_control_button(self, name, cls, labels):
        self._control_buttons[name] = {'labels' : labels,
                                       'widget' : None,
                                       'cls'    : cls,
                                       }

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

        for i, name in enumerate(self._control_buttons):
            w_button = QPushButton('', self._control)
            layout.addWidget(w_button)
            handler = lambda x: lambda : self._on_process_start(x)
            self.connect(w_button, SIGNAL('clicked()'), handler(name))
            self._control_buttons[name]['widget'] = w_button

        help_button = QToolButton(self._control)
        help_button.setIcon(QIcon(':question_mark'))
        handler = lambda x: lambda : self._on_show_help(x)
        self.connect(help_button, SIGNAL('clicked()'), handler('control-panel'))
        layout.addWidget(help_button)

        if not self.TABS is None:
            self.connect(self._tab, SIGNAL('currentChanged(int)'), self._on_tab_changed)
            self._on_tab_changed(0)
        else:
            for name in self._control_buttons:
                self._set_control_button_text(name=name)

    def _get_modified_settings(self, name):
        return copy.deepcopy(self._settings)

    def _on_tab_changed(self, idx):
        names = ['primary', 'secondary']
        self._tab_name = names[idx]
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


    def _toggle_control_buttons(self, name=None):
        if name is None:
            name = self._current_process
        for name2 in self._control_buttons:
            if name != name2:
                w_button = self._control_buttons[name2]['widget']
                w_button.setEnabled(not w_button.isEnabled())


    def _on_process_start(self, name, start_again=False):
        if not self._is_running or start_again:

            if self._process_items is None:
                cls = self._control_buttons[name]['cls']
                if type(cls) == types.ListType:
                    self._process_items = cls
                    self._current_process_item = 0
                    cls = cls[0]
                else:
                    self._process_items = None
            else:
                cls = self._process_items[self._current_process_item]

            is_valid = True
            self._is_abort = False
            self._has_error = False

            if isinstance(self, ClassificationFrame):
                result_frame = self._get_result_frame(self._tab_name)
                result_frame.load_classifier(check=False)
                learner = result_frame._learner

                if name == self.PROCESS_PICKING:
                    if not result_frame.is_pick_samples():
                        is_valid = False
                        result_frame.msg_pick_samples(self)
                    elif result_frame.is_train_classifier():
                        if question(self, '', 'Samples already picked',
                                    'Do you want to pick samples again and overwrite previous results?') != QMessageBox.Yes:
                            is_valid = False

                elif name == self.PROCESS_TRAINING:
                    if not result_frame.is_train_classifier():
                        is_valid = False
                        result_frame.msg_train_classifier(self)
                    elif result_frame.is_apply_classifier():
                        if question(self, '', 'Classifier already trained',
                                    'Do you want to train the classifier again?') != QMessageBox.Yes:
                            is_valid = False

                elif name == self.PROCESS_TESTING and not result_frame.is_apply_classifier():
                    is_valid = False
                    result_frame.msg_apply_classifier(self)


            elif cls is HmmThread:

                err = HmmThread.test_executable(self._settings.get('ErrorCorrection', 'filename_to_R'))
                if len(err) > 0:
                    QMessageBox.critical(self, '', err)

#                if self._settings.get('Classification', 'primary_classification'):
#                    result_frame = self._get_result_frame('primary')
#                    result_frame.load_classifier(check=False)
#                    learner = result_frame._learner
#                    if not result_frame.is_apply_classifier():
#                        is_valid = False
#                        QMessageBox.information(self, '', result_frame.msg_apply_classifier())
#
#                    if is_valid:
#                        filename = self._settings.get('ErrorCorrection', 'primary_graph')




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

                if cls is AnalzyerThread:

                    self._current_settings = self._get_modified_settings(name)
                    self._analyzer = cls(self, self._current_settings)

                    rendering = self._current_settings.get('General', 'rendering').keys()
                    rendering += self._current_settings.get('General', 'rendering_class').keys()
                    rendering.sort()
                    if hasattr(qApp, '_image_combo'):
                        qApp._image_combo.clear()
                        if len(rendering) > 1:
                            for name in rendering:
                                qApp._image_combo.addItem(str(name))
                            qApp._image_combo.show()
                        else:
                            qApp._image_combo.hide()

                    if len(rendering) > 0:
                        self._analyzer.set_renderer(rendering[0])
                    self._analyzer.image_ready.connect(self._on_update_image)

                    print qApp._image_dialog
                    if not qApp._image_dialog is None:
                        pix = qApp._graphics.pixmap()
                        pix.fill()
                        qApp._graphics.setPixmap(pix)
                        qApp._image_dialog.raise_()


                elif cls is TrainingThread:
                    self._current_settings = copy.deepcopy(self._settings)

                    self._analyzer = cls(self, self._current_settings,
                                         result_frame._learner)
                    self._analyzer.setTerminationEnabled(True)

                    self._analyzer.conf_result.connect(result_frame.on_conf_result,
                                                       Qt.QueuedConnection)

                elif cls is HmmThread:
                    self._current_settings = self._get_modified_settings(name)

                    # FIXME: classifier handling needs revision!!!
                    learner_dict = {}
                    for kind in ['primary', 'secondary']:
                        _resolve = lambda x,y: self._settings.get(x, '%s_%s' % (kind, y))
                        if _resolve('Processing', 'classification'):
                            classifier_infos = {'strEnvPath' : _resolve('Classification', 'classification_envpath'),
                                                'strChannelId' : _resolve('ObjectDetection', 'channelid'),
                                                'strRegionId' : _resolve('Classification', 'classification_regionname'),
                                                }
                            learner = CommonClassPredictor(dctCollectSamples=classifier_infos)
                            learner.importFromArff()
                            learner_dict[kind] = learner
                    self._analyzer = cls(self, self._current_settings,
                                         learner_dict)
                    self._analyzer.setTerminationEnabled(True)

                self.connect(self._analyzer, SIGNAL('finished()'),
                             self._on_process_finished)
                self._analyzer.stage_info.connect(self._on_update_stage_info,
                                                  Qt.QueuedConnection)
                self._analyzer.analyzer_error.connect(self._on_error,
                                                      Qt.QueuedConnection)

                self._analyzer.start(QThread.IdlePriority)
                status('Process started...')

        else:
            self.setCursor(Qt.BusyCursor)
            self._is_abort = True
            self._analyzer.set_abort()
            #self._analyzer.terminate()
            self._analyzer.wait()
            self.setCursor(Qt.ArrowCursor)


#            if (not self._image_dialog is None and
#                self._show_image.isChecked()):
#                qApp._graphics_pixmap.pixmap().fill(Qt.black)
#                self._image_dialog.show()
#                self._image_dialog.raise_()



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



    def _toggle_tabs(self, state):
        if not self.TABS is None:
            for i in range(self._tab.count()):
                if i != self._tab.currentIndex():
                    self._tab.setTabEnabled(i, state)

    def _on_render_changed(self, name):
        self._analyzer.set_renderer(str(name))

    def _on_error(self, msg, type=0):
        self._has_error = True
        msgbox = QMessageBox(self)
        msgbox.setText("An error occured during processing.")
        #msgBox.setInformativeText("Do you want to save your changes?");
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setDetailedText(str(msg))
        #msgbox.setWindowFlags(0)
        msgbox.setFixedSize(400,200)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec_()

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
                if isinstance(self, ObjectDetectionFrame):
                    msg = 'Object detection successfully finished.'
                elif isinstance(self, ClassificationFrame):
                    if self._current_process == self.PROCESS_PICKING:
                        msg = 'Samples successfully picked.'
                        result_frame = self._get_result_frame(self._tab_name)
                        result_frame.load_classifier(check=False)
                    elif self._current_process == self.PROCESS_TRAINING:
                        msg = 'Classifier successfully trained.'
                    elif self._current_process == self.PROCESS_TESTING:
                        msg = 'Testing successfully finished.'
                elif isinstance(self, TrackingFrame):
                    if self._current_process == self.PROCESS_TRACKING:
                        msg = 'Tracking successfully finished.'
                    elif self._current_process == self.PROCESS_SYNCING:
                        msg = 'Syncing successfully finished.'
                elif isinstance(self, ErrorCorrectionFrame):
                    msg = 'Error correction successfully finished.'
                elif isinstance(self, ProcessingFrame):
                    msg = 'Processing successfully finished.'

                information(self, 'Process finished', msg)
                status(msg)
            else:
                if self._is_abort:
                    status('Process aborted by user.')
                elif self._has_error:
                    status('Process aborted by error.')

            self._current_process = None

    def _on_esc_pressed(self):
        print 'ESC'
        if self._is_running:
            self.setCursor(Qt.BusyCursor)
            self._is_abort = True
            self._analyzer.set_abort()
            self._analyzer.wait()
            self.setCursor(Qt.ArrowCursor)

    def _on_update_stage_info(self, info):
        #print info
        if self.CONTROL == CONTROL_1:
            if info['stage'] == 0:
                self._progress0.setRange(info['min'], info['max'])
                if not info['progress'] is None:
                    self._progress0.setValue(info['progress'])
                    if info['max'] != 0:
                        self._progress_label0.setText('%3.1f%%' %\
                                                      (info['progress']*100.0/info['max']))
                else:
                    self._progress_label0.setText('')
            else:
                self._stage_infos[info['stage']] = info
                if len(self._stage_infos) > 1:
                    total = self._stage_infos[1]['max']*self._stage_infos[2]['max']
                    current = (self._stage_infos[1]['progress']-1)*self._stage_infos[2]['max']+self._stage_infos[2]['progress']
                    print current, total
                    self._progress0.setRange(0, total)
                    self._progress0.setValue(current)
                    #info = self._stage_infos[2]
                    self._progress_label0.setText('%.1f%%' % (current*100.0/total))
                    sep = '   |   '
                    msg = 'Image processing:   %s%s%s' % (self._stage_infos[1]['text'],
                                                          sep,
                                                          self._stage_infos[2]['text'])
                    if current > 1:
                        interval = info['interval']
                        self._intervals.append(interval.get_interval())
                        estimate = TimeInterval(numpy.average(self._intervals) * float(total-current))
                        msg += '%s%.1fs / T%s%s remaining' % (sep,
                                                              interval.get_interval(),
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
            print info, filename
            # FIXME:
            if image_rgb.width % 4 != 0:
                image_rgb = ccore.subImage(image_rgb, ccore.Diff2D(0,0), ccore.Diff2D(image_rgb.width - (image_rgb.width % 4), image_rgb.height))
            qimage = numpy_to_qimage(image_rgb.toArray(copy=False))
            #qimage = qimage.scaled(800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if qApp._image_dialog is None:
                qApp._image_dialog = QFrame()
                shortcut = QShortcut(QKeySequence(Qt.Key_Escape), qApp._image_dialog)
                qApp._image_dialog.connect(shortcut, SIGNAL('activated()'), self._on_esc_pressed)
                #self._image_dialog.setScaledContents(True)
                #self._image_dialog.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                layout = QVBoxLayout(qApp._image_dialog)
                layout.setContentsMargins(5,5,5,5)
#                qApp._graphics = QGraphicsScene()
#                qApp._graphics_pixmap = qApp._graphics.addPixmap(QPixmap.fromImage(qimage))
#                view = QGraphicsView(qApp._graphics, self._image_dialog)
#                view.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
                #size = qimage.size()
                ratio = qimage.height()/float(qimage.width())
                qApp._graphics = ImageDisplay(qApp._image_dialog, ratio)
                qApp._graphics.setScaledContents(True)
                qApp._graphics.resize(800, 800*ratio)
                qApp._graphics.setMinimumSize(QSize(100,100))
                policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                policy.setHeightForWidth(True)
                qApp._graphics.setSizePolicy(policy)
                layout.addWidget(qApp._graphics)
                #self._image_dialog.resize(qimage.size())
                #self._image_dialog.setMinimumSize(QSize(100,100))
                #size = self._image_dialog.size()
                #self._image_dialog.setMaximumSize(size)
                #self.connect(self._image_dialog, SIGNAL('hide()'),
                #             self._on_close_image_window)
                rendering = self._current_settings.get('General', 'rendering').keys()
                rendering += self._current_settings.get('General', 'rendering_class').keys()
                qApp._image_combo = QComboBox(qApp._image_dialog)
                qApp._image_combo.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                                            QSizePolicy.Fixed))
                layout.addWidget(qApp._image_combo)
                self.connect(qApp._image_combo, SIGNAL('currentIndexChanged(const QString &)'),
                             self._on_render_changed)
                for name in sorted(rendering):
                    qApp._image_combo.addItem(str(name))
                if len(rendering) > 1:
                    qApp._image_combo.show()
                else:
                    qApp._image_combo.hide()
                layout.addStretch()
                qApp._image_dialog.setGeometry(50, 50, 800, 800*ratio)
                #view.fitInView(qApp._graphics.sceneRect(), Qt.KeepAspectRatio)

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


class InputFrame(QFrame, InputWidgetMixin):

    ICON = ":cecog_analyzer_icon"
    TABS = None
    CONTROL = CONTROL_1

    toggle_tabs = pyqtSignal(str)

    def __init__(self, settings, parent):
        QFrame.__init__(self, parent)
        self._tab_lookup = {}
        self._tab_name = None

        self._control = QFrame(self)
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
                frame = self._tab_lookup[self._tab_name][1]
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
        frame.layout().addWidget(line, frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1


class ConfigSettings(RawConfigParser):

    def __init__(self):
        RawConfigParser.__init__(self, {}, OrderedDict)
        self._registry = OrderedDict()
        self._current_section = None
        self.naming_schemes = RawConfigParser({}, OrderedDict)
        filename = os.path.join('resources', 'naming_schemes.conf')
        if not os.path.isfile(filename):
            raise IOError("Naming scheme file '%s' not found." % filename)
        self.naming_schemes.read(filename)

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

        naming_schemes = settings.naming_schemes.sections()
        self.add_input("namingScheme",
                       SelectionTrait(naming_schemes[0], naming_schemes,
                                      label="Naming scheme"))

        self.add_line()

        self.add_group('constrain_positions',
                       BooleanTrait(False, label='Constrain positions'),
                       [('positions',
                        StringTrait('', 1000, label='Positions',
                                   mask='(\w+,)*\w+'))
                       ])

        self.add_input('redoFailedOnly',
                       BooleanTrait(True, label='Skip processed positions'))

        self.add_line()

        self.add_group('frameRange',
                       BooleanTrait(False, label='Constrain timepoints'),
                       [('frameRange_begin',
                         IntTrait(1, 1, 10000, label='Begin')),
                        ('frameRange_end',
                         IntTrait(1, 1, 1000, label='End'))
                        ], layout='flow')

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

        self.register_trait('rendering',
                            DictTrait({}, label='Rendering'))
#        self.register_trait('rendering_discwrite',
#                       BooleanTrait(True, label='Write images to disc'))
        self.register_trait('rendering_class',
                       DictTrait({}, label='Rendering class'))
#        self.register_trait('rendering_class_discwrite',
#                       BooleanTrait(True, label='Write images to disc'))


        self.register_trait('primary_featureExtraction_exportFeatureNames',
                            ListTrait([], label='Primary channel'))
        self.register_trait('secondary_featureExtraction_exportFeatureNames',
                            ListTrait([], label='Secondary channel'))


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

        help_button = QToolButton(self._control)
        help_button.setIcon(QIcon(':question_mark'))
        handler = lambda x: lambda : self._on_show_help(x)
        self.connect(help_button, SIGNAL('clicked()'), handler('control-panel'))
        layout.addWidget(help_button)


class ObjectDetectionFrame(InputFrame, ProcessorMixin):

    SECTION = 'ObjectDetection'
    NAME = 'Object Detection'
    TABS = ['PrimaryChannel', 'SecondaryChannel']

    def __init__(self, settings, parent):
        InputFrame.__init__(self, settings, parent)
        ProcessorMixin.__init__(self)

        self.register_control_button('detect',
                                     AnalzyerThread,
                                     ('Detect %s objects', 'Stop %s detection'))

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
        self.add_input('primary_medianRadius',
                       IntTrait(2, 0, 1000, label='Median radius'))

        self.add_group('Local adaptive threshold', None,
                       [('primary_latWindowSize',
                         IntTrait(20, 1, 1000, label='Window size'),
                         (1,0,1,1)),
                        ('primary_latLimit',
                         IntTrait(1, 0, 255, label='Min. contrast'),
                         (1,1,1,1)),
                        ])
        self.add_group('primary_lat2',
                       BooleanTrait(False, label='Local adaptive threshold 2'),
                       [('primary_latWindowSize2',
                         IntTrait(20, 1, 1000, label='Window size'),
                         (0,0,1,1)),
                        ('primary_latLimit2',
                         IntTrait(1, 0, 255, label='Min. contrast'),
                         (0,1,1,1)),
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
        self.register_trait('primary_emptyImageMax',
                         IntTrait(90, 0, 255, label='Empty frame threshold'))

        self.add_expanding_spacer()


        self.set_tab_name('SecondaryChannel')

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
                                             label='Regions'),
                         (0,0,3,1)),
                        ('secondary_regions_expansionsize',
                         IntTrait(0, 0, 4000, label='Expansion size'),
                         (0,1,1,1)),
                        ('secondary_regions_expansionseparationsize',
                         IntTrait(0, 0, 4000, label='Expansion spacer'),
                         (1,1,1,1)),
                        ('secondary_regions_shrinkingseparationsize',
                         IntTrait(0, 0, 4000, label='Shrinking size'),
                         (2,1,1,1)),
                        ])

        self.register_trait('secondary_zSliceOrProjection',
                       StringTrait('1', 10,
                                   label='Z-slice or projection'))

        self.add_expanding_spacer()

        self._init_control()

    def _get_modified_settings(self, name):
        settings = copy.deepcopy(self._settings)

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        sec_regions = settings.get2('secondary_regions')
        settings.set_section('Processing')
        settings.set2('secondary_processChannel', False)
        settings.set2('primary_classification', False)
        settings.set2('secondary_classification', False)
        settings.set2('tracking', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set2('primary_simplefeatures_texture', False)
        settings.set2('primary_simplefeatures_shape', False)
        settings.set2('secondary_simplefeatures_texture', False)
        settings.set2('secondary_simplefeatures_shape', False)
        settings.set_section('General')
        settings.set2('rendering_class', {})
        #settings.set2('rendering_discwrite', True)
        #settings.set2('rendering_class_discwrite', True)

        if self._tab.currentIndex() == 0:
            settings.set('General', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0), 'contours': {'primary': ('#FF0000', 1, False)}}}})
        else:
            settings.set('Processing', 'secondary_processChannel', True)
            settings.set('General', 'rendering', {'secondary_contours': {sec_id: {'raw': ('#FFFFFF', 1.0), 'contours': {sec_regions[0]: ('#FF0000', 1, False)}}}})

        return settings


class ClassificationFrame(InputFrame, ProcessorMixin):

    SECTION = 'Classification'
    TABS = ['PrimaryChannel', 'SecondaryChannel']
    PROCESS_PICKING = 'PROCESS_PICKING'
    PROCESS_TRAINING = 'PROCESS_TRAINING'
    PROCESS_TESTING = 'PROCESS_TESTING'

    def __init__(self, settings, parent):
        InputFrame.__init__(self, settings, parent)
        ProcessorMixin.__init__(self)
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

        self.set_tab_name('PrimaryChannel')

        self.add_input('primary_classification_envPath',
                       StringTrait('', 1000, label='Classifier folder',
                                   tooltip='abc...',
                                   widget_info=StringTrait.STRING_PATH))

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
        self.add_group('Feature extraction', None,
                       [
                        ('primary_simplefeatures_texture',
                         BooleanTrait(True, label='Texture features')),
                        ('primary_simplefeatures_shape',
                         BooleanTrait(True, label='Shape features')),
                        ], layout='flow')

#        self.add_input('primary_classification_regionName',
#                       SelectionTrait(REGION_NAMES_PRIMARY[0],
#                                      REGION_NAMES_PRIMARY,
#                                      label='Region name',
#                                      tooltip='abc...'))
#        self.add_input('primary_classification_labels',
#                         ListTrait([], label='Class labels',
#                                   tooltip='abc...'))

        self.register_trait('primary_classification_regionName',
                            SelectionTrait(REGION_NAMES_PRIMARY[0],
                                           REGION_NAMES_PRIMARY,
                                           label='Region name'))

        self.add_line()

        self._add_result_frame('primary')
        #self.add_expanding_spacer()


        self.set_tab_name('SecondaryChannel')

        self.add_input('secondary_classification_envPath',
                       StringTrait('', 1000, label='Classifier folder',
                                   tooltip='abc...',
                                   widget_info=StringTrait.STRING_PATH))

        self.add_line()

#                        ('secondary_classification_collectSamples',
#                         BooleanTrait(False, label='Collect samples',
#                                      tooltip='abc...')),
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

        self.add_input('secondary_classification_regionName',
                       SelectionTrait(REGION_NAMES_SECONDARY[0],
                                      REGION_NAMES_SECONDARY,
                                      label='Region name',
                                      tooltip='abc...'))
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
        self.register_trait('primary_classification_annotationFileExt',
                            StringTrait('.xml', 50, label='Annotation ext.'))
        self.register_trait('secondary_classification_annotationFileExt',
                            StringTrait('.xml', 50, label='Annotation ext.'))

        self.add_line()

        self._add_result_frame('secondary')
        #self.add_expanding_spacer()

        self._init_control()

    def _get_modified_settings(self, name):
        settings = copy.deepcopy(self._settings)
        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        #sec_regions = settings.get2('secondary_regions')
        settings.set_section('Processing')
        settings.set2('primary_classification', False)
        settings.set2('secondary_classification', False)
        settings.set2('tracking', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        if self._tab.currentIndex() == 0:
            settings.set_section('Classification')
            settings.set2('secondary_simplefeatures_texture', False)
            settings.set2('secondary_simplefeatures_shape', False)
            settings.set2('collectsamples_prefix', 'primary')
            settings.set('Processing', 'secondary_processChannel', False)

            if name == self.PROCESS_TESTING:
                settings.set('Processing', 'primary_classification', True)
                settings.set('General', 'rendering_class', {'primary_classification': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                 'contours': {'primary': ('class_label', 1, False)}}}})
            else:
                settings.set2('collectsamples', True)
                settings.set('General', 'positions', '')
                settings.set('General', 'framerange_begin', 0)
                settings.set('General', 'framerange_end', 0)

        else:
            settings.set_section('Classification')
            sec_region = settings.get2('secondary_classification_regionname')
            settings.set2('primary_simplefeatures_texture', False)
            settings.set2('primary_simplefeatures_shape', False)
            settings.set2('collectsamples_prefix', 'secondary')
            settings.set('ObjectDetection', 'secondary_regions', [sec_region])
            settings.set('Processing', 'secondary_processChannel', True)
            if name == self.PROCESS_TESTING:
                settings.set('Processing', 'secondary_classification', True)
                settings.set('General', 'rendering_class', {'secondary_classification': {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                  'contours': {sec_region: ('class_label', 1, False)}}}})
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

    def _get_result_frame(self, name):
        return self._result_frames[name]


class TrackingFrame(InputFrame, ProcessorMixin):

    SECTION = 'Tracking'
    PROCESS_TRACKING = 'PROCESS_TRACKING'
    PROCESS_SYNCING = 'PROCESS_SYNCING'

    def __init__(self, settings, parent):
        InputFrame.__init__(self, settings, parent)
        ProcessorMixin.__init__(self)

        self.register_control_button(self.PROCESS_TRACKING,
                                     AnalzyerThread,
                                     ('Test tracking', 'Stop tracking'))
        self.register_control_button(self.PROCESS_SYNCING,
                                     AnalzyerThread,
                                     ('Apply motif selection', 'Stop motif selection'))

        self.add_group('Tracking', None,
                       [('tracking_maxObjectDistance',
                        IntTrait(0, 0, 4000, label='Max object x-y distance'),
                        (0,0,1,1)),
                        ('tracking_maxTrackingGap',
                         IntTrait(0, 0, 4000, label='Max timepoint gap'),
                         (0,1,1,1)),
                        ('tracking_maxSplitObjects',
                         IntTrait(0, 0, 4000, label='Max split events'),
                         (1,0,1,1)),
                        ])


        self.add_line()

        self.add_group('tracking_synchronize_trajectories',
                       BooleanTrait(True, label='Motif selection'),
                       [
                        ('tracking_labelTransitions',
                        StringTrait('', 200, label='Class transition motif(s)',
                                    mask='(\(\d+,\d+\),)*\(\d+,\d+\)'),
                         (0,0,1,4)),
                        ('tracking_backwardRange',
                         IntTrait(0, -1, 4000, label='Timepoints [pre]'),
                         (1,0,1,1)),
                        ('tracking_forwardRange',
                         IntTrait(0, -1, 4000, label='Timepoints [post]'),
                         (1,1,1,1)),
                        ('tracking_backwardLabels',
                         StringTrait('', 200, label='Class filter [pre]',
                                     mask='(\d+,)*\d+'),
                         (2,0,1,1)),
                        ('tracking_forwardLabels',
                         StringTrait('', 200, label='Class filter [post]',
                                     mask='(\d+,)*\d+'),
                         (2,1,1,1)),
                        ('tracking_backwardCheck',
                         IntTrait(2, 0, 4000, label='Filter timepoints [pre]'),
                         (3,0,1,1)),
                        ('tracking_forwardCheck',
                         IntTrait(2, 0, 4000, label='Filter timepoints [post]'),
                         (3,1,1,1)),
                        ])

        self.register_trait('tracking_forwardRange_min',
                            BooleanTrait(False, label='Min.'))
        self.register_trait('tracking_backwardRange_min',
                            BooleanTrait(False, label='Min.'))


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

#        self.add_group('tracking_exportTrackFeatures',
#                       BooleanTrait(False, label='Export tracks'),
#                       [('tracking_compressionTrackFeatures',
#                         SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
#                                        label='Compression'))
#                       ], layout='flow')


        self.add_group('tracking_visualization',
                       BooleanTrait(False, label='Visualization'),
                       [('tracking_visualize_track_length',
                         IntTrait(5, -1, 10000,
                                  label='Max. timepoints')),
                        ('tracking_visualize_show_labels',
                         BooleanTrait(False, label='Show object IDs'))
                       ], layout='flow')

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
        self.register_trait('tracking_exportTrackFeatures',
                            BooleanTrait(True, label='Export tracks'))
        self.register_trait('tracking_compressionTrackFeatures',
                             SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
                                            label='Compression'))

        self._init_control()

    def _get_modified_settings(self, name):
        settings = copy.deepcopy(self._settings)

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        sec_regions = settings.get2('secondary_regions')
        settings.set('Processing', 'tracking', True)
        settings.set_section('Tracking')
#        settings.set2('tracking_visualization', True)
        settings.set2('tracking_synchronize_trajectories', False)
        show_ids = settings.get2('tracking_visualize_show_labels')
        settings.set_section('General')
        settings.set2('rendering_class', {})
        settings.set2('rendering', {})
        #settings.set2('rendering_discwrite', True)
        #settings.set2('rendering_class_discwrite', True)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
#        if settings.get2('primary_classification'):
#            settings.set2('secondary_simplefeatures_texture', False)
#            settings.set2('secondary_simplefeatures_shape', False)
#            settings.set('General', 'rendering_class', {'primary_tracking': {prim_id: {'raw': ('#FFFFFF', 1.0),
#                                                                                      'contours': {'primary': ('class_label', 1, False)}}}})
#        elif settings.get2('secondary_classification') and settings.get('ObjectDetection', 'secondary_processChannel'):
#            settings.set2('primary_simplefeatures_texture', False)
#            settings.set2('primary_simplefeatures_shape', False)
#            settings.set('General', 'rendering_class', {'primary_tracking2': {prim_id: {'raw': ('#FFFFFF', 1.0)},
#                                                                             sec_id:  {'contours': {sec_regions[0]: ('class_label', 1, False)}}}})
#        else:
        if name == self.PROCESS_TRACKING:
            settings.set2('primary_simplefeatures_texture', False)
            settings.set2('primary_simplefeatures_shape', False)
            settings.set2('secondary_simplefeatures_texture', False)
            settings.set2('secondary_simplefeatures_shape', False)
            settings.set('Processing', 'primary_classification', False)
            settings.set('Processing', 'secondary_classification', False)
            settings.set('Processing', 'secondary_processChannel', False)
            settings.set('General', 'rendering', {'primary_tracking': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                'contours': {'primary': ('#FF0000', 1, show_ids)}}}})
        else:
            settings.set('Tracking', 'tracking_synchronize_trajectories', True)
            settings.set('Processing', 'primary_classification', True)
            settings.set('General', 'rendering_class', {'primary_syncing': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                      'contours': [('primary', 'class_label', 1, False),
                                                                                                   ('primary', '#000000', 1, show_ids)]}}})

        return settings


class ErrorCorrectionFrame(InputFrame, ProcessorMixin):

    SECTION = 'ErrorCorrection'
    NAME = 'Error Correction'

    def __init__(self, settings, parent):
        InputFrame.__init__(self, settings, parent)
        ProcessorMixin.__init__(self)

        self.register_control_button('hmm',
                                     HmmThread,
                                     ('Correct errors', 'Stop correction'))

        self.add_input('filename_to_R',
                       StringTrait('', 1000, label='R-project executable',
                                   widget_info=StringTrait.STRING_FILE))

        self.add_line()

        self.add_group('constrain_graph',
                       BooleanTrait(True, label='Constrain graph'),
                       [('primary_graph',
                         StringTrait('', 1000, label='Primary file',
                                     widget_info=StringTrait.STRING_FILE)),
                        ('secondary_graph',
                         StringTrait('', 1000, label='Secondary file',
                                     widget_info=StringTrait.STRING_FILE)),
                        ])

        self.add_group('position_labels',
                       BooleanTrait(False, label='Position labels'),
                       [('mappingfile',
                         StringTrait('', 1000, label='File',
                                     widget_info=StringTrait.STRING_FILE)),
                        ])
        self.add_group('Group by', None,
                       [('groupby_oligoid',
                         BooleanTrait(False, label='Oligo ID',
                                      widget_info=BooleanTrait.RADIOBUTTON)),
                        ('groupby_genesymbol',
                         BooleanTrait(False, label='Gene symbol',
                                      widget_info=BooleanTrait.RADIOBUTTON)),
                        ('groupby_position',
                         BooleanTrait(True, label='Position',
                                      widget_info=BooleanTrait.RADIOBUTTON)),
                        ], layout='flow')

        self.add_line()

        self.add_group('Plot parameter', None,
                       [('timelapse',
                         FloatTrait(1, 0, 2000, digits=2,
                                    label='Time-lapse [min]')),
                        ('max_time',
                         FloatTrait(100, 1, 2000, digits=2,
                                    label='Max. time in plot [min]')),
                        ], layout='flow')

        self.register_trait('primary_sort',
                            StringTrait('NULL', 100))
        self.register_trait('secondary_sort',
                            StringTrait('NULL', 100))

        self.add_expanding_spacer()

        self._init_control(has_images=False)


class OutputFrame(InputFrame):

    SECTION = 'Output'

    def __init__(self, settings, parent):
        super(OutputFrame, self).__init__(settings, parent)

        self.add_group('Write results to disc', None,
                       [
                        ('rendering_labels_discwrite',
                         BooleanTrait(False, label='Label images'),
                         (0,0,1,1)),
                        ('rendering_contours_discwrite',
                         BooleanTrait(False, label='Contour images'),
                         (1,0,1,1)),
                        ('rendering_class_discwrite',
                         BooleanTrait(False, label='Classification images'),
                         (2,0,1,1)),
                        ])

#        self.add_input('rendering',
#                       DictTrait({}, label='Rendering',
#                                 tooltip='abc...'))
#        self.add_input('rendering_discwrite',
#                       BooleanTrait(True, label='Write images to disc',
#                                    tooltip='abc...'))
#        self.add_input('rendering_class',
#                       DictTrait({}, label='Rendering class',
#                                 tooltip='abc...'))
#        self.add_input('rendering_class_discwrite',
#                       BooleanTrait(True, label='Write images to disc',
#                                    tooltip='abc...'))
#
#
#        self.add_group('Filter feature values', None,
#                       [
#                        ('primary_featureExtraction_exportFeatureNames',
#                         ListTrait([], label='Primary channel',
#                                   tooltip='abc...')),
#                        ('secondary_featureExtraction_exportFeatureNames',
#                         ListTrait([], label='Secondary channel',
#                                   tooltip='abc...')),
#                        ], layout='flow')

        self.add_expanding_spacer()



class ProcessingFrame(InputFrame, ProcessorMixin):

    SECTION = 'Processing'

    def __init__(self, settings, parent):
        InputFrame.__init__(self, settings, parent)
        ProcessorMixin.__init__(self)

        self.register_control_button('process',
                                     [AnalzyerThread,
                                      HmmThread],
                                     ('Start processing', 'Stop processing'))


        self.add_group('Primary channel', None,
                       [('primary_classification',
                         BooleanTrait(False, label='Classification'),
                         (1,0,1,1)),
                        ('tracking',
                         BooleanTrait(False, label='Tracking'),
                         (3,0,1,1)),
                        ('primary_errorcorrection',
                         BooleanTrait(False, label='Error correction'),
                         (4,0,1,1))
                        ])

        self.add_group('secondary_processChannel',
                        BooleanTrait(False, label='Secondary channel'),
                       [('secondary_classification',
                         BooleanTrait(False, label='Classification'),
                         (2,0,1,1)),
                        ('secondary_errorcorrection',
                         BooleanTrait(False, label='Error correction'),
                         (4,0,1,1))
                        ])

        #self.add_line()

        self.add_expanding_spacer()

        self._init_control()

    def _get_modified_settings(self, name):
        settings = copy.deepcopy(self._settings)

        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        sec_regions = settings.get2('secondary_regions')
        settings.set_section('Classification')
        sec_region = settings.get2('secondary_classification_regionname')
        settings.set_section('Tracking')
        show_ids = settings.get2('tracking_visualize_show_labels')


        settings.get('General', 'rendering').update({'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                    'contours': {'primary': ('#FF0000', 1, False)}}}})

        if settings.get('Processing', 'primary_classification'):
            settings.get('General', 'rendering_class').update({'primary_classification': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                          'contours': [('primary', 'class_label', 1, False)]}}})
        if settings.get('Processing', 'secondary_processChannel'):
            settings.get('General', 'rendering').update({'secondary_contours': {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                         'contours': [(x, SECONDARY_COLORS[x] , 1, False)
                                                                                                      for x in sec_regions]
                                                                                                      }}})
            if settings.get('Processing', 'secondary_classification'):
                settings.get('General', 'rendering_class').update({'secondary_classification': {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                'contours': [(sec_region, 'class_label', 1, False)]}}})

        return settings


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
    import time
    import sys
    safe_mkdirs('log')
    sys.stdout = file('log/cecog_analyzerone_stdout.log', 'w')
    sys.stderr = file('log/cecog_analyzerone_stderr.log', 'w')

    app = QApplication(sys.argv)

    splash = QSplashScreen(QPixmap(':cecog_splash'))
    splash.show()
    splash.raise_()
    app.setWindowIcon(QIcon(':cecog_analyzer_icon'))
    time.sleep(.5)
    app.processEvents()
    main = AnalyzerMainWindow()
    main.raise_()
    #main.test_r_import()

    #filename = '/Users/miheld/src/mito_svn/trunk/mito/analyzer_mitocheck_settings.conf'
    #filename = '/Users/miheld/src/mito_svn/trunk/mito/_analyzer_test_settings.conf'
    filename = '/Users/miheld/data/CellCognition/demo_data/H2bTub20x_settings.conf'
    if os.path.isfile(filename):
        main.read_settings(filename)
    else:
        filename = r'Y:\data\CellCognition\demo_data\H2bTub20x_settings_WinXP.conf'
        if os.path.isfile(filename):
            main.read_settings(filename)
    splash.finish(main)

    sys.exit(app.exec_())
