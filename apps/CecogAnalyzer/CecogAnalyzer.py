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

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys, \
       os, \
       logging, \
       time, \
       gc
import cPickle as pickle

#-------------------------------------------------------------------------------
# extension module imports:
#
import sip
# set PyQt API version to 2.0
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QUrl', 2)

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.ordereddict import OrderedDict

import numpy
#import vigra
#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog import VERSION
from cecog.analyzer import (R_LIBRARIES,
                            TRACKING_DURATION_UNITS_TIMELAPSE,
                            TRACKING_DURATION_UNITS_DEFAULT,
                            )
from cecog.io.imagecontainer import ImageContainer
from cecog.traits.config import (ANALYZER_CONFIG,
                                 APPLICATION_SUPPORT_PATH,
                                 )
from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.gui.config import GuiConfigSettings
from cecog.gui.analyzer.general import (GeneralFrame,
                                        SECTION_NAME_GENERAL,
                                        )
from cecog.gui.analyzer.objectdetection import (ObjectDetectionFrame,
                                                SECTION_NAME_OBJECTDETECTION,
                                                )
from cecog.gui.analyzer.featureextraction import FeatureExtractionFrame
from cecog.gui.analyzer.classification import ClassificationFrame
from cecog.gui.analyzer.tracking import (TrackingFrame,
                                         SECTION_NAME_TRACKING,
                                         )
from cecog.gui.analyzer.errorcorrection import ErrorCorrectionFrame
from cecog.gui.analyzer.output import OutputFrame
from cecog.gui.analyzer.processing import ProcessingFrame
from cecog.gui.analyzer.cluster import ClusterFrame
from cecog.gui.browser import Browser
from cecog.gui.log import (GuiLogHandler,
                           LogWindow,
                           )
from cecog.util.util import (convert_package_path,
                             set_package_path,
                             get_package_path,
                             )
from cecog.gui.util import (status,
                            show_html,
                            critical,
                            question,
                            exception,
                            information,
                            warning,
                            waitingProgressDialog,
                            )

import resource

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class AnalyzerMainWindow(QMainWindow):

    TITLE = 'CecogAnalyzer'

    NAME_FILTERS = ['Settings files (*.conf)',
                    'All files (*.*)']

    modified = pyqtSignal('bool')

    def __init__(self):
        QMainWindow.__init__(self)
        qApp._main_window = self

        self._is_initialized = False
        self._debug = False
        self._imagecontainer = None
        self._meta_data = None
        self._browser = None

        self.setWindowTitle(self.TITLE+'[*]')

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
        self.action_save = action_save
        action_save_as = self.create_action('&Save Settings As...',
                                            shortcut=QKeySequence.SaveAs,
                                            slot=self._on_file_save_as
                                            )
        menu_file = self.menuBar().addMenu('&File')
        self.add_actions(menu_file, (action_about,  action_pref,
                                     None, action_open,
                                     None, action_save, action_save_as,
                                     None, action_quit))

        action_open = self.create_action('&Open Browser...',
                                         shortcut=QKeySequence('CTRL+B'),
                                         slot=self._on_browser_open
                                         )
        menu_browser = self.menuBar().addMenu('&Browser')
        self.add_actions(menu_browser, (action_open,
                                     #None, action_save, action_save_as,
                                     #None, action_quit
                                     ))

        action_log = self.create_action('&Show Log Window...',
                                        shortcut=QKeySequence(Qt.CTRL + Qt.Key_L),
                                        slot=self._on_show_log_window
                                        )
        menu_window = self.menuBar().addMenu('&Window')
        self.add_actions(menu_window, (action_log,
                                       ))

        action_help_startup = self.create_action('&Startup Help...',
                                                 shortcut=QKeySequence.HelpContents,
                                                 slot=self._on_help_startup
                                                )
        menu_help = self.menuBar().addMenu('&Help')
        self.add_actions(menu_help, (action_help_startup,))

        qApp._statusbar = QStatusBar(self)
        self.setStatusBar(qApp._statusbar)


        self._selection = QListWidget(central_widget)
        self._selection.setViewMode(QListView.IconMode)
        #self._selection.setUniformItemSizes(True)
        self._selection.setIconSize(QSize(35, 35))
        self._selection.setGridSize(QSize(140,60))
        #self._selection.setWrapping(False)
        self._selection.setMovement(QListView.Static)
        #self._selection.setFlow(QListView.TopToBottom)
        #self._selection.setSpacing(12)
        self._selection.setMaximumWidth(self._selection.gridSize().width()+5)
        self._selection.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._selection.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                                  QSizePolicy.Expanding))

        self._pages = QStackedWidget(central_widget)
        self._pages.main_window = self

        self._settings_filename = None
        self._settings = GuiConfigSettings(self, SECTION_REGISTRY)

        self._tab_lookup = OrderedDict()
        self._tabs = [GeneralFrame(self._settings, self._pages),
                      ObjectDetectionFrame(self._settings, self._pages),
                      FeatureExtractionFrame(self._settings, self._pages),
                      ClassificationFrame(self._settings, self._pages),
                      TrackingFrame(self._settings, self._pages),
                      ErrorCorrectionFrame(self._settings, self._pages),
                      OutputFrame(self._settings, self._pages),
                      ProcessingFrame(self._settings, self._pages),
                      ]
        if ANALYZER_CONFIG.get('Analyzer', 'cluster_support'):
            self._tabs.append(ClusterFrame(self._settings, self._pages))

        widths = []
        for tab in self._tabs:
            size = self._add_page(tab)
            widths.append(size.width())
        self.set_modules_active(state=False)
        self._pages.setMinimumWidth(max(widths)+45)

        self._selection.currentItemChanged.connect(self._on_change_page)

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
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
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
        self._is_initialized = True

    def closeEvent(self, event):
        '''
        The app should quit when the main window is closed.
        '''
        if not self._exit_app():
            event.ignore()

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
            critical(self, 'R installation not found', info=msg, detail_tb=True)


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

                critical(self, 'Missing R libraries', info=msg, detail_tb=True)
                qApp.valid_R_version = False
            else:
                qApp.valid_R_version = True

    def settings_changed(self, changed):
        if self._is_initialized:
            self.setWindowModified(changed)
            self.action_save.setEnabled(changed)
            self.modified.emit(changed)

    def _add_page(self, widget):
        button = QListWidgetItem(self._selection)
        button.setIcon(QIcon(widget.ICON))
        button.setText(widget.get_name())
        button.setTextAlignment(Qt.AlignHCenter)
        #button.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        #self.connect(button, )
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
        index = self._selection.row(current)
        self._pages.setCurrentIndex(index);
        widget = self._pages.widget(index)
        widget.page_changed()

    def _check_settings_saved(self):
        if self.isWindowModified():
            result = question(self, 'Settings have been modified.',
                              info='Do you want to save settings?',
                              modal=True, show_cancel=True,
                              default=QMessageBox.Yes,
                              escape=QMessageBox.Cancel)
            if result == QMessageBox.Yes:
                self.save_settings()
        else:
            result = QMessageBox.No
        return result

    def _exit_app(self):
        do_exit = False
        if not self._debug:
            if question(self, 'Do you really want to exit?', modal=True):
                if self._check_settings_saved() != QMessageBox.Cancel:
                    do_exit = True
                    qApp.exit()
        else:
            do_exit = True
            qApp.exit()
        return do_exit


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

    def save_settings(self, save_as=False):
        filename = self._settings_filename
        if filename is None or save_as:
            filename = self.__get_save_as_filename()
        if not filename is None:
            self._write_settings(filename)

    def _read_settings(self, filename):
        try:
            self._settings.read(filename)
        except:
            critical(self,
                     "Error loading settings file",
                     info="Could not load settings file '%s'." % filename,
                     detail_tb=True)
            status('Settings not successfully loaded.')
        else:
            self._settings_filename = filename
            self.setWindowTitle('%s - %s[*]' % (self.TITLE, filename))
            try:
                for widget in self._tabs:
                    widget.update_input()
            except:
                critical(self, "Problem loading settings file.",
                         info = "Fix the problem in file '%s' and load the "\
                                "settings file again." % filename,
                         detail_tb = True)
            self.settings_changed(False)
            status('Settings successfully loaded.')

    def _write_settings(self, filename):
        try:
            f = file(filename, 'w')
            self._settings.write(f)
            f.close()
        except:
            critical(self,
                     "Error saving settings file",
                     info="Could not save settings file as '%s'." % filename,
                     detail_tb=True)
            status('Settings not successfully saved.')
        else:
            self._settings_filename = filename
            self.setWindowTitle('%s - %s[*]' % (self.TITLE, filename))
            self.settings_changed(False)
            status('Settings successfully saved.')

    def _on_about(self):
        print "about"
        dialog = QDialog(self)
        #dialog.setBackgroundRole(QPalette.Dark)
        dialog.setStyleSheet('background: #000000; '
                             'background-image: url(:cecog_about)')
        dialog.setWindowTitle('About CecogAnalyzer')
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
        label2.setText('CecogAnalyzer\nVersion %s\n\n'
                       'Copyright (c) 2006 - 2011\n' % VERSION)
        label3 = QLabel(dialog)
        label3.setStyleSheet('background: transparent;')
        label3.setTextFormat(Qt.AutoText)
        label3.setOpenExternalLinks(True)
        label3.setAlignment(Qt.AlignCenter)
        #palette = label2.palette()
        #palette.link = QBrush(QColor(200,200,200))
        #label3.setPalette(palette)
        label3.setText('<style>a { color: green; } a:visited { color: green; }</style>'
                       '<a href="http://cellcognition.org">cellcognition.org</a><br>')
        layout.addWidget(label2, 1, 0)
        layout.addWidget(label3, 2, 0)
        layout.setAlignment(Qt.AlignCenter|
                            Qt.AlignBottom)
        dialog.setLayout(layout)
        dialog.show()

    def _on_preferences(self):
        print "pref"

    def _on_quit(self):
        self._exit_app()

    def _on_browser_open(self):
        if self._imagecontainer is None:
            warning(self, 'Data structure not loaded',
                    'The input data structure was not loaded.\n'
                    'Please click "Load image data" in General.')
        elif self._browser is None:
            try:
                browser = Browser(self._settings,
                                  self._imagecontainer)
                browser.show()
                browser.raise_()
                browser.setFocus()
                self._browser = browser
            except:
                exception(self, 'Problem opening the browser')
        else:
            self._browser.show()
            self._browser.raise_()

    def _on_load_input(self):
        txt = "Error scanning image structure"
        path_in = self._settings.get(SECTION_NAME_GENERAL, 'pathin')
        if path_in == '':
            critical(self, txt, "Image path must be defined.")
        elif not os.path.isdir(path_in):
            critical(self, txt, "Image path '%s' not found." % path_in)
        else:
            try:
                infos = list(ImageContainer.iter_check_plates(self._settings))
            except:
                exception(self, txt)
            else:
                found_any = numpy.any([not info[3] is None for info in infos])
                cancel = False
                if found_any:
                    found_plates = [info[0] for info in infos
                                    if not info[3] is None]
                    missing_plates = [info[0] for info in infos
                                      if info[3] is None]
                    has_missing = len(missing_plates) > 0
                    txt = '%s plates were already scanned.\nDo you want ' \
                          'to rescan the file structure(s)? ' \
                          'This can take several minutes.' % \
                          ('Some' if has_missing else 'All')
                    title = 'Rescan input structure?'

                    box = QMessageBox(QMessageBox.Question, title, title,
                                      QMessageBox.Cancel, self, Qt.Sheet)
                    box.setWindowModality(Qt.WindowModal)
                    box.setInformativeText(txt)
                    box.setDetailedText('Plates with scanned structure: \n%s\n'
                                        '\nPlates without scanned structure: '
                                        '\n%s' %
                                        ('\n'.join(found_plates),
                                         '\n'.join(missing_plates)))
                    if not has_missing:
                        btn1 = QPushButton('No', box)
                        box.addButton(btn1, QMessageBox.NoRole)
                        box.setDefaultButton(btn1)
                    elif len(found_plates) > 0:
                        btn1 = QPushButton('Rescan missing', box)
                        box.addButton(btn1, QMessageBox.YesRole)
                        box.setDefaultButton(btn1)
                    else:
                        btn1 = None

                    btn2 = QPushButton('Rescan all', box)
                    box.addButton(btn2, QMessageBox.YesRole)

                    if box.exec_() == QMessageBox.Cancel:
                        cancel = True
                    else:
                        btn = box.clickedButton()
                        if btn == btn1:
                            if has_missing:
                                scan_plates = dict([(info[0], info[0] in missing_plates) for info in infos])
                            else:
                                scan_plates = dict((info[0], False) for info in infos)
                        else:
                            scan_plates = dict((info[0], True) for info in infos)
                else:
                    has_multiple = self._settings.get(SECTION_NAME_GENERAL,
                                                      "has_multiple_plates")
                    if not question(self, "No structure data found",
                                    "Are you sure to scan %s?\n\nThis can take "
                                    "several minutes depending on the number of"
                                    " images." %
                                    ("%d plates" % len(infos) if has_multiple
                                     else "one plate")):
                        cancel = True
                    scan_plates = dict((info[0], True) for info in infos)
                if not cancel:
                    self._load_image_container(infos, scan_plates)

    def _load_image_container(self, plate_infos, scan_plates=None, show_dlg=True):

        self._clear_browser()
        imagecontainer = ImageContainer()

        if scan_plates is None:
            scan_plates = dict((info[0], False) for info in plate_infos)

        def load(dlg):
            iter = imagecontainer.iter_import_from_settings(self._settings, scan_plates)
            for idx, info in enumerate(iter):
                dlg.targetSetValue.emit(idx+1)

            if len(imagecontainer.plates) > 0:
                plate = imagecontainer.plates[0]
                imagecontainer.set_plate(plate)

        self.dlg = waitingProgressDialog('Please wait until the input structure is scanned\n'
                                    'or the structure data loaded...', self, load, (0, len(scan_plates)))
        self.dlg.exec_(passDialog=True)

        if len(imagecontainer.plates) > 0:
            imagecontainer.check_dimensions()
            channels = imagecontainer.channels

            # do not report value changes to the main window
            self._settings.set_notify_change(False)

            problems = []
            for prefix in ['primary', 'secondary', 'tertiary']:
                trait = self._settings.get_trait(SECTION_NAME_OBJECTDETECTION,
                                                 '%s_channelid' % prefix)
                if trait.set_list_data(channels) is None:
                    problems.append(prefix)
                self._tabs[1].get_widget('%s_channelid' % prefix).update()

            # report problems about a mismatch between channel IDs found in the data and specified by the user
            if len(problems) > 0:
                critical(self, "Selected channel IDs not valid",
                         "The selected channel IDs for %s are not valid.\nValid IDs are %s." %
                         (", ".join(["'%s Channel'" % s.capitalize() for s in problems]),
                          ", ".join(["'%s'" % s for s in channels])))
                # a mismatch between settings and data will cause changed settings
                self.settings_changed(True)

            trait = self._settings.get_trait(SECTION_NAME_TRACKING,
                                             'tracking_duration_unit')

            # allow time-base tracking durations only if time-stamp
            # information is present
            meta_data = imagecontainer.get_meta_data()
            if meta_data.has_timestamp_info:
                result = trait.set_list_data(TRACKING_DURATION_UNITS_TIMELAPSE)
            else:
                result = trait.set_list_data(TRACKING_DURATION_UNITS_DEFAULT)
            if result is None:
                critical(self, "Could not set tracking duration units",
                         "The tracking duration units selected to match the load data. Please check your settings.")
                # a mismatch between settings and data will cause changed settings
                self.settings_changed(True)

            # activate change notification again
            self._settings.set_notify_change(True)

            self._imagecontainer = imagecontainer
            self.set_modules_active(state=True)
            if show_dlg:
                information(self, "Plate(s) successfully loaded",
                            "%d plates loaded successfully." % len(imagecontainer.plates))
        else:
            critical(self, "No valid image data found",
                     "The naming schema provided might not fit your image data"
                     "or the coordinate file is not correct.\n\nPlease modify "
                     "the values and scan the structure again.")

    def set_modules_active(self, state=True):
        for name, (button, widget) in self._tab_lookup.iteritems():
            widget.set_active(state)

    @pyqtSlot()
    def _on_file_open(self):
        if self._check_settings_saved() != QMessageBox.Cancel:
            dir = ''
            if not self._settings_filename is None:
                settings_filename = convert_package_path(self._settings_filename)
                if os.path.isfile(settings_filename):
                    dir = settings_filename
            filename = QFileDialog.getOpenFileName(self, 'Open config file', dir, ';;'.join(self.NAME_FILTERS))
            if filename:
                self._read_settings(filename)
                self._clear_browser()
                self.set_modules_active(state=False)


    @pyqtSlot()
    def _on_file_save(self):
        self.save_settings(False)

    @pyqtSlot()
    def _on_file_save_as(self):
        self.save_settings(True)

    def _clear_browser(self):
        # close and delete the current browser instance
        if not self._browser is None:
            self._browser.close()
            del self._browser
            # FIXME: necessary step to prevent crash after loading of new image container
            gc.collect()
            self._browser = None

    def _on_show_log_window(self):
        logger = logging.getLogger()
        logger.addHandler(qApp._log_handler)
        qApp._log_window.show()
        qApp._log_window.raise_()

    def __get_save_as_filename(self):
        dir = ''
        if not self._settings_filename is None:
            settings_filename = convert_package_path(self._settings_filename)
            if os.path.isfile(settings_filename):
                dir = settings_filename
        filename = QFileDialog.getSaveFileName(self, 'Save config file as', dir, ';;'.join(self.NAME_FILTERS))
        return filename or None

    def _on_help_startup(self):
        show_html('_startup')


def handle_exception(exc_type, exc_value, exc_traceback):
  import traceback
  filename, line, dummy, dummy = \
    traceback.extract_tb(exc_traceback).pop()
  filename = os.path.basename(filename)
  error = "%s: %s" % (str(exc_type).split(".")[-1], exc_value)

  QMessageBox.critical(None, "ERROR",
    "There has been an error: "
    + "<b>%s</b> " % error
    + "on line %d, file %s" % (line, filename))


#-------------------------------------------------------------------------------
# main:
#
if __name__ == "__main__":
    import time
    from pdk.fileutils import safe_mkdirs
    from cecog.util.util import get_appdata_path

    import argparse
    parser = argparse.ArgumentParser(description='CellCognition Analyzer GUI')
    parser.add_argument('--load', action='store_true', default=False,
                        help='Load data from settings file.')
    parser.add_argument('settings', nargs='?',
                        help='Settings file.')
    args = parser.parse_args()

#    log_path = 'log'
#    safe_mkdirs(log_path)
#    sys.stdout = \
#        file(os.path.join(log_path, 'cecog_analyzer_stdout.log'), 'w')
#    sys.stderr = \
#        file(os.path.join(log_path, 'cecog_analyzer_stderr.log'), 'w')

    app = QApplication(sys.argv)
    #sys.excepthook=handle_exception

    working_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    program_name = os.path.split(sys.argv[0])[1]
    package_path = None

    is_app = False

    if sys.platform == 'darwin':
        idx = working_path.find('/CecogAnalyzer.app/Contents/Resources')
        if idx > -1:
            package_path = working_path[:idx]
            is_app = True
    else:
        package_path = get_appdata_path()
        is_app = True

    if not package_path is None:
        set_package_path(package_path)
        log_path = os.path.join(get_appdata_path(), 'log')
        safe_mkdirs(log_path)
#        sys.stdout = \
#            file(os.path.join(log_path, 'cecog_analyzer_stdout.log'), 'w')
#        sys.stderr = \
#            file(os.path.join(log_path, 'cecog_analyzer_stderr.log'), 'w')

    splash = QSplashScreen(QPixmap(':cecog_splash'))
    splash.show()
    splash.raise_()
    app.setWindowIcon(QIcon(':cecog_analyzer_icon'))
    time.sleep(.2)
    app.processEvents()
    main = AnalyzerMainWindow()
    main.raise_()


    if not args.settings is None:
        filename = args.settings
    else:
        filename = os.path.join(get_package_path(), 'Data/Cecog_settings/demo_settings.conf')

    if os.path.isfile(filename):
        main._read_settings(filename)

        if args.load:
            infos = list(ImageContainer.iter_check_plates(main._settings))
            main._load_image_container(infos, show_dlg=False)

    if not is_app:
        main._debug = True

    splash.finish(main)
    sys.exit(app.exec_())
