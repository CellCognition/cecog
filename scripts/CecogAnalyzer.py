#!/usr/bin/env python
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

import os
import sys
import numpy
import logging
import argparse

from os.path import join
from multiprocessing import freeze_support
from collections import OrderedDict

# use agg as long no Figure canvas will draw any qwidget
import matplotlib as mpl
mpl.use('Agg')

import sip
# set PyQt API version to 2.0
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QUrl', 2)

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.Qt import qApp
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QMessageBox

try:
    import cecog
except ImportError:
    sys.path.append(os.path.join(os.pardir, "pysrc"))
    import cecog

# from cecog import VERSION, APPNAME
from cecog.util.util import makedirs
from cecog.environment import CecogEnvironment

from cecog.analyzer import TRACKING_DURATION_UNITS_TIMELAPSE
from cecog.analyzer import TRACKING_DURATION_UNITS_DEFAULT

from cecog.io.imagecontainer import ImageContainer

from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.gui.config import GuiConfigSettings


from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION
from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
from cecog.traits.analyzer.postprocessing import SECTION_NAME_POST_PROCESSING
from cecog.traits.analyzer.classification import SECTION_NAME_CLASSIFICATION
from cecog.traits.analyzer.tracking import SECTION_NAME_TRACKING
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION
from cecog.traits.analyzer.eventselection import SECTION_NAME_EVENT_SELECTION
from cecog.traits.analyzer.output import SECTION_NAME_OUTPUT
from cecog.traits.analyzer.processing import SECTION_NAME_PROCESSING
from cecog.traits.analyzer.cluster import SECTION_NAME_CLUSTER

# Frames
from cecog.gui.analyzer.general import GeneralFrame
from cecog.gui.analyzer.objectdetection import ObjectDetectionFrame
from cecog.gui.analyzer.featureextraction import FeatureExtractionFrame
from cecog.gui.analyzer.postprocessing import PostProcessingFrame
from cecog.gui.analyzer.classification import ClassificationFrame
from cecog.gui.analyzer.tracking import TrackingFrame
from cecog.gui.analyzer.errorcorrection import ErrorCorrectionFrame
from cecog.gui.analyzer.eventselection import EventSelectionFrame
from cecog.gui.analyzer.output import OutputFrame
from cecog.gui.analyzer.processing import ProcessingFrame
from cecog.gui.analyzer.cluster import ClusterFrame

from cecog.gui.browser import Browser
from cecog.gui.log import GuiLogHandler, LogWindow


from cecog.gui.util import (status,
                            show_html,
                            critical,
                            question,
                            exception,
                            information,
                            warning,
                            waitingProgressDialog)

# compiled from qrc file
import cecog.cecog_rc

def enable_eclipse_debuging():
    try:
        import pydevd
        pydevd.connected = True
        pydevd.settrace(suspend=False)
        print 'Thread enabled interactive eclipse debuging...'
    except:
        pass

class CecogAboutDialog(QtGui.QDialog):

    def __init__(self, *args, **kw):
        super(CecogAboutDialog, self).__init__(*args, **kw)
        self.setBackgroundRole(QtGui.QPalette.Dark)
        self.setStyleSheet('background: #000000; '
                           'background-image: url(:cecog_about)')
        self.setWindowTitle('About CecogAnalyzer')
        self.setFixedSize(400, 300)
        layout = QtGui.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        label1 = QtGui.QLabel(self)
        label1.setStyleSheet('background: transparent;')
        label1.setAlignment(Qt.AlignCenter)
        label1.setText('CecogAnalyzer\nVersion %s\n\n'
                       'Copyright (c) 2006 - 2011\n' %cecog.VERSION)

        label2 = QtGui.QLabel(self)
        label2.setStyleSheet('background: transparent;')
        label2.setTextFormat(Qt.AutoText)
        label2.setOpenExternalLinks(True)
        label2.setAlignment(Qt.AlignCenter)

        label2.setText(('<style>a { color: green; } a:visited { color: green;'
                        ' }</style><a href="http://cellcognition.org">'
                        'cellcognition.org</a><br>'))
        layout.addWidget(label1, 1, 0)
        layout.addWidget(label2, 2, 0)
        layout.setAlignment(Qt.AlignCenter|Qt.AlignBottom)
        self.setLayout(layout)


class CecogAnalyzer(QtGui.QMainWindow):

    NAME_FILTERS = ['Settings files (*.conf)', 'All files (*.*)']
    modified = QtCore.pyqtSignal('bool')

    def __init__(self, appname, version, redirect, debug=False, *args, **kw):
        super(CecogAnalyzer, self).__init__(*args, **kw)
        self.setWindowTitle("%s-%s" %(appname, version) + '[*]')
        self.setCentralWidget(QtGui.QFrame(self))
        self.setObjectName(appname)

        self.version = version
        self.appname = appname
        self.debug = debug

        self.environ = CecogEnvironment(version, redirect=redirect, debug=debug)
        if debug:
            self.environ.pprint()

        self._is_initialized = False
        self._imagecontainer = None
        self._meta_data = None
        self._browser = None

        action_quit = self.create_action('&Quit', slot=self.close)
        action_pref = self.create_action('&Preferences',
                                         slot=self.open_preferences)

        action_open = self.create_action('&Open Settings...',
                                         shortcut=QtGui.QKeySequence.Open,
                                         slot=self._on_file_open)
        action_save = self.create_action('&Save Settings',
                                         shortcut=QtGui.QKeySequence.Save,
                                         slot=self._on_file_save)
        self.action_save = action_save
        action_save_as = self.create_action('&Save Settings As...',
                                            shortcut=QtGui.QKeySequence.SaveAs,
                                            slot=self._on_file_save_as)
        menu_file = self.menuBar().addMenu('&File')
        self.add_actions(menu_file, (action_pref,
                                     None, action_open,
                                     None, action_save, action_save_as,
                                     None, action_quit))

        action_open = self.create_action('&Open Browser...',
                                         shortcut=QtGui.QKeySequence('CTRL+B'),
                                         slot=self._on_browser_open)
        menu_browser = self.menuBar().addMenu('&Browser')
        self.add_actions(menu_browser, (action_open, ))

        action_log = self.create_action('&Show Log Window...',
                                        shortcut=QtGui.QKeySequence(Qt.CTRL+Qt.Key_L),
                                        slot=self._on_show_log_window)
        menu_window = self.menuBar().addMenu('&Window')
        self.add_actions(menu_window, (action_log,))

        action_help_startup = self.create_action('&Startup Help...',
                                                 shortcut=QtGui.QKeySequence.HelpContents,
                                                 slot=self._on_help_startup)
        action_about = self.create_action('&About', slot=self.on_about)

        menu_help = self.menuBar().addMenu('&Help')
        self.add_actions(menu_help, (action_help_startup, action_about))

        qApp._main_window = self
        qApp._statusbar = QtGui.QStatusBar(self)
        self.setStatusBar(qApp._statusbar)

        self._selection = QtGui.QListWidget(self.centralWidget())
        self._selection.setViewMode(QtGui.QListView.IconMode)
        self._selection.setIconSize(QtCore.QSize(35, 35))
        self._selection.setGridSize(QtCore.QSize(140, 60))
        self._selection.setMovement(QtGui.QListView.Static)
        self._selection.setMaximumWidth(self._selection.gridSize().width() + 5)
        self._selection.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._selection.setSizePolicy(
            QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                              QtGui.QSizePolicy.Expanding))

        self._pages = QtGui.QStackedWidget(self.centralWidget())
        self._pages.main_window = self

        self._settings_filename = None
        self._settings = GuiConfigSettings(self, SECTION_REGISTRY)

        self._tab_lookup = OrderedDict()
        self._tabs = [GeneralFrame(self._settings, self._pages, SECTION_NAME_GENERAL),
                      ObjectDetectionFrame(self._settings, self._pages, SECTION_NAME_OBJECTDETECTION),
                      FeatureExtractionFrame(self._settings, self._pages, SECTION_NAME_FEATURE_EXTRACTION),
                      ClassificationFrame(self._settings, self._pages, SECTION_NAME_CLASSIFICATION),
                      TrackingFrame(self._settings, self._pages, SECTION_NAME_TRACKING),
                      EventSelectionFrame(self._settings, self._pages, SECTION_NAME_EVENT_SELECTION),
                      ErrorCorrectionFrame(self._settings, self._pages, SECTION_NAME_ERRORCORRECTION),
                      PostProcessingFrame(self._settings, self._pages, SECTION_NAME_POST_PROCESSING),
                      OutputFrame(self._settings, self._pages, SECTION_NAME_OUTPUT),
                      ProcessingFrame(self._settings, self._pages, SECTION_NAME_PROCESSING)]

        if self.environ.analyzer_config.get('Analyzer', 'cluster_support'):
            self._tabs.append(ClusterFrame(self._settings, self._pages, SECTION_NAME_CLUSTER,
                                           self._imagecontainer))

        widths = []
        for tab in self._tabs:
            size = self._add_page(tab)
            widths.append(size.width())
        self.set_modules_active(state=False)
        self._pages.setMinimumWidth(max(widths) + 45)

        self._selection.currentItemChanged.connect(self._on_change_page)
        self._selection.setCurrentRow(0)

        w_logo = QtGui.QLabel(self.centralWidget())
        w_logo.setPixmap(QtGui.QPixmap(':cecog_logo_w145'))

        layout = QtGui.QGridLayout(self.centralWidget())
        layout.addWidget(self._selection, 0, 0)
        layout.addWidget(w_logo, 1, 0, Qt.AlignBottom | Qt.AlignHCenter)
        layout.addWidget(self._pages, 0, 1, 2, 1)
        layout.setContentsMargins(1, 1, 1, 1)

        handler = GuiLogHandler(self)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)

        self.log_window = LogWindow(self, handler)
        self.log_window.setGeometry(50, 50, 600, 300)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        qApp._image_dialog = None
        qApp._graphics = None

        self.setGeometry(0, 0, 1250, 750)
        self.setMinimumSize(QtCore.QSize(700, 600))
        self._is_initialized = True

    def show(self):
        super(CecogAnalyzer, self).show()
        self.center()

    def closeEvent(self, event):
        # Quit dialog only if not debuging flag is not set
        if self.debug:
            return
        ret = QMessageBox.question(self, "Quit %s" %self.appname,
                                   "Do you really want to quit?",
                                   QMessageBox.Yes|QMessageBox.No)
        if self._check_settings_saved() and ret == QMessageBox.No:
            event.ignore()
        else:
            # FIXME - some dialogs are attributs of qApp
            # --> QApplication does not exit automatically
            QtGui.QApplication.exit()

    def settings_changed(self, changed):
        if self._is_initialized:
            self.setWindowModified(changed)
            self.action_save.setEnabled(changed)
            self.modified.emit(changed)

    def _add_page(self, widget):
        button = QtGui.QListWidgetItem(self._selection)
        button.setIcon(QtGui.QIcon(widget.ICON))
        button.setText(widget.get_name())
        button.setTextAlignment(Qt.AlignHCenter)
        self._pages.addWidget(widget)

        widget.toggle_tabs.connect(self._on_toggle_tabs)
        self._tab_lookup[widget.get_name()] = (button, widget)
        return widget.size()

    def _on_toggle_tabs(self, name):
        """Toggle ItemIsEnabled flag for all list items but name."""
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

    def center(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2,
        (screen.height() - size.height()) / 2)

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(self, text, slot=None, shortcut=None, icon=None,
                      tooltip=None, checkable=None, signal='triggered()',
                      checked=False):
        action = QtGui.QAction(text, self)
        if icon is not None:
            action.setIcon(QtGui.QIcon(':/%s.png' % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tooltip is not None:
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
        if slot is not None:
            self.connect(action, QtCore.SIGNAL(signal), slot)
        if checkable is not None:
            action.setCheckable(True)
        action.setChecked(checked)
        return action

    def save_settings(self, save_as=False):
        filename = self._settings_filename
        if filename is None or save_as:
            filename = self._get_save_as_filename()
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
            title = self.windowTitle().split(' - ')[0]
            self.setWindowTitle('%s - %s[*]' % (title, filename))
            try:
                for widget in self._tabs:
                    widget.update_input()
            except:
                critical(self, "Problem loading settings file.",
                         info="Fix the problem in file '%s' and load the "\
                                "settings file again." % filename,
                         detail_tb=True)
            else:
                # convert settings
                if self.version > self._settings.get('General', 'version'):
                    print 'print new version'


                # set settings to not-changed (assume no changed since loaded from file)
                self.settings_changed(False)
                # notify tabs about new settings loaded
                for tab in self._tabs:
                    tab.settings_loaded()
                status('Settings successfully loaded.')

    def _write_settings(self, filename):
        try:
            f = file(filename, 'w')
            # create a new version (copy) of the current
            # settings which add the needed rendering information
            settings_dummy = ProcessingFrame.get_export_settings(self._settings)
            settings_dummy.write(f)
            f.close()
        except:
            critical(self,
                     "Error saving settings file",
                     info="Could not save settings file as '%s'." % filename,
                     detail_tb=True)
            status('Settings not successfully saved.')
        else:
            self._settings_filename = filename
            self.setWindowTitle('%s - %s[*]' % (self.appname, filename))
            self.settings_changed(False)
            status('Settings successfully saved.')

    def on_about(self):
        dialog = CecogAboutDialog(self)
        dialog.show()

    def open_preferences(self):
        print "pref"

    def _on_browser_open(self):
        if self._imagecontainer is None:
            warning(self, 'Data structure not loaded',
                    'The input data structure was not loaded.\n'
                    'Please click "Load image data" in General.')
        elif self._browser is None:
            try:
                browser = Browser(self._settings, self._imagecontainer)
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
        elif not os.path.isdir(path_in) and \
             not os.path.isdir(os.path.join(self.environ.package_dir, path_in)):
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
                        btn1 = QtGui.QPushButton('No', box)
                        box.addButton(btn1, QMessageBox.NoRole)
                        box.setDefaultButton(btn1)
                    elif len(found_plates) > 0:
                        btn1 = QtGui.QPushButton('Rescan missing', box)
                        box.addButton(btn1, QMessageBox.YesRole)
                        box.setDefaultButton(btn1)
                    else:
                        btn1 = None

                    btn2 = QtGui.QPushButton('Rescan all', box)
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
        self._imagecontainer = imagecontainer

        if scan_plates is None:
            scan_plates = dict((info[0], False) for info in plate_infos)

        def load(dlg):
            iter = imagecontainer.iter_import_from_settings(self._settings, scan_plates)
            for idx, info in enumerate(iter):
                dlg.targetSetValue.emit(idx + 1)

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

            self.set_image_crop_size()

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

            trait = self._settings.get_trait(SECTION_NAME_EVENT_SELECTION,
                                             'duration_unit')

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


            self.set_modules_active(state=True)
            if show_dlg:
                information(self, "Plate(s) successfully loaded",
                            "%d plates loaded successfully." % len(imagecontainer.plates))
        else:
            critical(self, "No valid image data found",
                     "The naming schema provided might not fit your image data"
                     "or the coordinate file is not correct.\n\nPlease modify "
                     "the values and scan the structure again.")

    def set_image_crop_size(self):
        x0, y0, x1, y1 = self._settings.get('General', 'crop_image_x0'), \
                         self._settings.get('General', 'crop_image_y0'), \
                         self._settings.get('General', 'crop_image_x1'), \
                         self._settings.get('General', 'crop_image_y1')

        x0_, y0_, x1_, y1_ = 0, \
                             0, \
                             self._imagecontainer.get_meta_data().dim_x, \
                             self._imagecontainer.get_meta_data().dim_y

        tr_x0 = self._settings.get_trait(SECTION_NAME_GENERAL, 'crop_image_x0')
        tr_y0 = self._settings.get_trait(SECTION_NAME_GENERAL, 'crop_image_y0')
        tr_x1 = self._settings.get_trait(SECTION_NAME_GENERAL, 'crop_image_x1')
        tr_y1 = self._settings.get_trait(SECTION_NAME_GENERAL, 'crop_image_y1')

        # Check if the crop values are valid
        if x0 > 0 and y0 > 0 and x1 <= x1_ and y1 <= y1_ and \
                x0 != x1 and y0 != y1:
            # Set to default values
            tr_x0.set_value(tr_x0.get_widget(), x0)
            tr_y0.set_value(tr_y0.get_widget(), y0)
            tr_x1.set_value(tr_x1.get_widget(), x1)
            tr_y0.set_value(tr_y1.get_widget(), y1)
        else:
            tr_x0.set_value(tr_x0.get_widget(), x0_)
            tr_y0.set_value(tr_y0.get_widget(), y0_)
            tr_x1.set_value(tr_x1.get_widget(), x1_)
            tr_y0.set_value(tr_y1.get_widget(), y1_)

        # Set GUI widget valid ranges
        tr_x0.set_min_value(x0_)
        tr_x0.set_max_value(x1_)
        tr_y0.set_min_value(y0_)
        tr_y0.set_max_value(y1_)
        tr_x1.set_min_value(x0_)
        tr_x1.set_max_value(x1_)
        tr_y1.set_min_value(y0_)
        tr_y1.set_max_value(y1_)

    def set_modules_active(self, state=True):
        for name, (button, widget) in self._tab_lookup.iteritems():
            widget.set_active(state)

    @QtCore.pyqtSlot()
    def _on_file_open(self):
        if self._check_settings_saved() != QMessageBox.Cancel:
            dir = ""
            if not self._settings_filename is None:
                settings_filename = self.environ.convert_package_path(
                    self._settings_filename)
                if os.path.isfile(settings_filename):
                    dir = settings_filename
            filename = QtGui.QFileDialog.getOpenFileName(self, 'Open config file',
                                                          dir, ';;'.join(self.NAME_FILTERS))
            if filename:
                self._read_settings(filename)
                if self._settings.was_old_file_format():
                    information(self, ('Selected config file had an old '
                                       'version <= 1.3.0. The current version is %s. '
                                       'The config file was  be updated...' %self.version))
                else:
                    information(self, "Config file version %s found"  \
                                %self._settings.get('General', 'version'))
                self._clear_browser()
                self.set_modules_active(state=False)

    @QtCore.pyqtSlot()
    def _on_file_save(self):
        self.save_settings(False)

    @QtCore.pyqtSlot()
    def _on_file_save_as(self):
        self.save_settings(True)

    def _clear_browser(self):
        # close and delete the current browser instance
        if not self._browser is None:
            self._browser.close()
            self._browser = None

    def _on_show_log_window(self):
        logger = logging.getLogger()
        logger.addHandler(self.log_window.handler)
        self.log_window.show()
        #self.log_window.raise_()

    def _get_save_as_filename(self):
        dir = ""
        if not self._settings_filename is None:
            settings_filename = self.environ.convert_package_path(
                self._settings_filename)
            if os.path.isfile(settings_filename):
                dir = settings_filename
        filename = QtGui.QFileDialog.getSaveFileName(
            self, 'Save config file as', dir, ';;'.join(self.NAME_FILTERS))
        return filename or None

    def _on_help_startup(self):
        show_html('_startup')


if __name__ == "__main__":

    enable_eclipse_debuging()

    parser = argparse.ArgumentParser(description='CellCognition Analyzer GUI')
    parser.add_argument('-l', '--load', action='store_true', default=False,
                            help='Load structure file if a config was provied.')
    parser.add_argument('-c''--configfile', dest='configfile',
                            default=os.path.join("battery_package",
                                                 "Settings", "demo_settings.conf"),
                            help='Load a config file. (default from battery package)')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                            help='Run applicaton in debug mode')
    args, _ = parser.parse_known_args()

    freeze_support()
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(':cecog_analyzer_icon'))
    app.setApplicationName(cecog.APPNAME)

    splash = QtGui.QSplashScreen(QtGui.QPixmap(':cecog_splash'))
    splash.show()

    is_app = hasattr(sys, 'frozen')
    if is_app:
        redirect = (sys.frozen == "windows_exe")
    else:
        redirect = False

    main = CecogAnalyzer(cecog.APPNAME, cecog.VERSION, redirect,  args.debug)
    main._read_settings(join(main.environ.user_config_dir, args.configfile))

    try:
        if (args.load and os.path.isfile(args.configfile)) or is_app:
            infos = list(ImageContainer.iter_check_plates(main._settings))
            main._load_image_container(infos, show_dlg=False)
    except Exception, e:
        msg = "Could not load images\n%s" %e.message
        QMessageBox.critical(None, "Error", msg)
    main.show()
    splash.finish(main)
    sys.exit(app.exec_())
