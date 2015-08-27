"""
main.py

CecogAnalyzer main window

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import os
import sys
import numpy
import logging
import traceback
from collections import OrderedDict

from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QFile, QTextStream

from cecog import version
from cecog.units.time import TimeConverter
from cecog.environment import CecogEnvironment
from cecog.io.imagecontainer import ImageContainer

from cecog.gui.config import GuiConfigSettings
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION
from cecog.traits.analyzer.featureextraction import SECTION_NAME_FEATURE_EXTRACTION
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
from cecog.gui.analyzer.classification import ClassificationFrame
from cecog.gui.analyzer.tracking import TrackingFrame
from cecog.gui.analyzer.errorcorrection import ErrorCorrectionFrame
from cecog.gui.analyzer.eventselection import EventSelectionFrame
from cecog.gui.analyzer.output import OutputFrame
from cecog.gui.analyzer.processing import ProcessingFrame
from cecog.gui.analyzer.cluster import ClusterFrame
from cecog.gui.imagedialog import ImageDialog
from cecog.gui.aboutdialog import CecogAboutDialog
from cecog.gui.preferences import PreferencesDialog
from cecog.gui.preferences import AppPreferences
from cecog.gui.browser import Browser
from cecog.logging import LogWindow

from cecog.gui.progressdialog import ProgressDialog
from cecog.gui.progressdialog import ProgressObject
from cecog.gui.helpbrowser import AtAssistant
from cecog.css import loadStyle

def fix_path(path):
    "Windows sucks!"
    if sys.platform.startswith("win"):
        return path.strip("/")
    else:
        return path

class FrameStack(QtWidgets.QStackedWidget):

    def __init__(self, parent):
        super(FrameStack, self).__init__(parent)
        self.main_window = parent
        self.idialog = ImageDialog()
        self.idialog.hide()

        manual = os.path.join(parent.environ.doc_dir, AtAssistant.Manual)
        self.assistant = AtAssistant(manual, None)
        self.assistant.hide()

        self.log_window = LogWindow(self)
        self._wmap = dict()

    def showLogWindow(self):
        self.log_window.show()
        self.log_window.raise_()

    def addWidget(self, widget):
        wi = super(FrameStack, self).addWidget(widget)
        self._wmap[type(widget)] = wi

    def widgetByType(self, type_):
        return self.widget(self._wmap[type_])

    def removeWidget(self, widget):
        del self._wmap[type(widget)]
        super(FrameStack, self).removeWidget(widget)

    def close(self):
        self.assistant.close()

class CecogAnalyzer(QtWidgets.QMainWindow):

    NAME_FILTERS = ['Settings files (*.conf)', 'All files (*.*)']
    modified = QtCore.pyqtSignal('bool')

    def __init__(self, appname, version, redirect, settings=None,
                 debug=False, *args, **kw):
        super(CecogAnalyzer, self).__init__(*args, **kw)
        self.setWindowTitle("%s-%s" %(appname, version) + '[*]')
        self.setAcceptDrops(True)
        self.setCentralWidget(QtWidgets.QFrame(self))
        self.setObjectName(appname)

        self.version = version
        self.appname = appname
        self.debug = debug

        self.environ = CecogEnvironment(version=version, redirect=redirect,
                                        debug=debug)

        if debug:
            self.environ.pprint()

        self._is_initialized = False
        self._imagecontainer = None
        self._meta_data = None
        self._browser = None

        action_quit = self.create_action('&Quit', slot=self.close)
        action_pref = self.create_action('&Preferences',
                                         slot=self.open_preferences)

        action_load = self.create_action('&Load Settings...',
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
                                     None, action_load,
                                     None, action_save, action_save_as,
                                     None, action_quit))

        action_log = self.create_action('&Log window',
                                        shortcut=QtGui.QKeySequence(Qt.CTRL+Qt.Key_L),
                                        slot=self._on_show_log_window)

        action_open = self.create_action('&Browser',
                                         shortcut=QtGui.QKeySequence('CTRL+B'),
                                         slot=self._on_browser_open)

        menu_view = self.menuBar().addMenu('&View')
        self.add_actions(menu_view, (action_log,))
        self.add_actions(menu_view, (action_open,))

        action_assistant = self.create_action('&Help',
                                              shortcut=QtGui.QKeySequence.HelpContents,
                                              slot=self.show_assistant)
        action_about = self.create_action('&About', slot=self.on_about)
        action_aboutQt = self.create_action('&About Qt', slot=self.about_qt)


        menu_help = self.menuBar().addMenu('&Help')
        self.add_actions(menu_help, (action_assistant, action_about,
                                     action_aboutQt))

        self.setStatusBar(QtWidgets.QStatusBar(self))

        self._selection = QtWidgets.QListWidget(self.centralWidget())
        self._selection.setViewMode(QtWidgets.QListView.IconMode)
        self._selection.setIconSize(QtCore.QSize(35, 35))
        self._selection.setGridSize(QtCore.QSize(140, 60))
        self._selection.setMovement(QtWidgets.QListView.Static)
        self._selection.setMaximumWidth(self._selection.gridSize().width() + 5)
        self._selection.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._selection.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                  QtWidgets.QSizePolicy.Expanding))

        self._pages = FrameStack(self)

        self._settings_filename = None
        self._settings = GuiConfigSettings(self)

        self._tab_lookup = OrderedDict()
        self._tabs = [GeneralFrame(self._settings, self._pages, SECTION_NAME_GENERAL),
                      ObjectDetectionFrame(self._settings, self._pages, SECTION_NAME_OBJECTDETECTION),
                      FeatureExtractionFrame(self._settings, self._pages, SECTION_NAME_FEATURE_EXTRACTION),
                      ClassificationFrame(self._settings, self._pages, SECTION_NAME_CLASSIFICATION),
                      TrackingFrame(self._settings, self._pages, SECTION_NAME_TRACKING),
                      EventSelectionFrame(self._settings, self._pages, SECTION_NAME_EVENT_SELECTION),
                      ErrorCorrectionFrame(self._settings, self._pages, SECTION_NAME_ERRORCORRECTION),
                      OutputFrame(self._settings, self._pages, SECTION_NAME_OUTPUT),
                      ProcessingFrame(self._settings, self._pages, SECTION_NAME_PROCESSING)]

        # connections for the section frames
        self._tabs[3].connect_browser_btn(self._on_browser_open)
        for frame in self._tabs:
            frame.status_message.connect(self.statusBar().showMessage)

        app = AppPreferences()
        if app.cluster_support:
            clusterframe = ClusterFrame(self._settings, self._pages, SECTION_NAME_CLUSTER)
            clusterframe.set_imagecontainer(self._imagecontainer)
            self._tabs.append(clusterframe)

        try:
            self.updateStyleSheet(loadStyle(app.stylesheet))
        except Exception as e:
            # proceed with no stylesheet
            traceback.print_exc()


        widths = []
        for tab in self._tabs:
            size = self._add_page(tab)
            widths.append(size.width())
        self.set_modules_active(state=False)
        self._pages.setMinimumWidth(max(widths) + 45)

        self._selection.currentItemChanged.connect(self._on_change_page)
        self._selection.setCurrentRow(0)

        w_logo = QtWidgets.QLabel(self.centralWidget())
        w_logo.setPixmap(QtGui.QPixmap(':cecog_logo_w145'))

        layout = QtWidgets.QGridLayout(self.centralWidget())
        layout.addWidget(self._selection, 0, 0)
        layout.addWidget(w_logo, 1, 0, Qt.AlignBottom | Qt.AlignHCenter)
        layout.addWidget(self._pages, 0, 1, 2, 1)
        layout.setContentsMargins(1, 1, 1, 1)

        self.setGeometry(0, 0, 1250, 800)
        self.setMinimumSize(QtCore.QSize(700, 600))
        self._is_initialized = True

        self._restore_geometry()
        self.show()

        # finally load (demo) - settings
        if settings is None:
            self.load_settings(self.environ.demo_settings)
        elif os.path.isfile(settings):
            self.load_settings(settings)
        else:
            QMessageBox.warning(
                self, "Warning", "File (%s) does not exist" %settings)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            if len(mimeData.urls()) == 1:
                self.load_settings(fix_path(mimeData.urls()[0].path()))
                # self._on_load_input()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        event.accept()

    def _save_geometry(self):
        settings = QtCore.QSettings(version.organisation, version.appname)
        settings.beginGroup('Gui')
        settings.setValue('state', self.saveState())
        settings.setValue('geometry', self.saveGeometry())

        try:
            settings.setValue(
                'clusterjobs', self._pages.widgetByType(
                    ClusterFrame).get_jobids())
        except KeyError:
            pass

        settings.endGroup()

    def _restore_geometry(self):
        settings = QtCore.QSettings(version.organisation, version.appname)
        settings.beginGroup('Gui')

        if settings.contains('geometry'):
            self.restoreGeometry(settings.value('geometry'))

        if settings.contains('state'):
            self.restoreState(settings.value('state'))

        if settings.contains('clusterjobs'):
            jobids = settings.value('clusterjobs')
            if AppPreferences().cluster_support and jobids:
                self._pages.widgetByType(ClusterFrame).restore_jobids(jobids)

        settings.endGroup()

    def closeEvent(self, event):
        self._pages.close()
        # Quit dialog only if not debuging flag is not set
        self._save_geometry()
        if self.debug:
            QtWidgets.QApplication.exit()
        ret = QMessageBox.question(self, "Quit %s" %self.appname,
                                   "Do you really want to quit?",
                                   QMessageBox.Yes|QMessageBox.No)

        if ret == QMessageBox.No:
            event.ignore()
        else:
            self._check_settings_saved(QMessageBox.Yes|QMessageBox.No)
            QtWidgets.QApplication.exit()

    def settings_changed(self, changed):
        if self._is_initialized:
            self.setWindowModified(changed)
            self.action_save.setEnabled(changed)
            self.modified.emit(changed)

    def _add_page(self, widget):
        button = QtWidgets.QListWidgetItem(self._selection)
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
                item, _ = self._tab_lookup[name2]
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
        self._pages.setCurrentIndex(index)
        widget = self._pages.widget(index)
        widget.page_changed()

    def _check_settings_saved(
            self, buttons=QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel):
        if self.isWindowModified():
            result = QMessageBox.question(
                self, "Settings have been modified",
                "Do you want to save the settings?",
                buttons)

            if result == QMessageBox.Yes:
                self.save_settings()
        else:
            result = QMessageBox.No
        return result

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(self, text, slot=None, shortcut=None, icon=None,
                      tooltip=None, checkable=None, signal='triggered',
                      checked=False):
        action = QtWidgets.QAction(text, self)
        if icon is not None:
            action.setIcon(QtGui.QIcon(':/%s.png' % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tooltip is not None:
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
        if slot is not None:
            getattr(action, signal).connect(slot)
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

    def load_settings(self, filename):
        try:
            self._settings.read(filename)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 ("Error loading settings file\n"
                                  "Could not load settings file '%s'.\n%s"
                                  %(filename, str(e))))
            self.statusBar().showMessage('Error loading settings files.')
        else:
            self._settings_filename = filename
            title = self.windowTitle().split(' - ')[0]
            self.setWindowTitle('%s - %s[*]' % (title, filename))
            try:
                # reset naming scheme to load config file completely
                nst = self._settings.get_trait("General",  "namingscheme")
                namingscheme_file = self._settings("General", "namingscheme")
                if not namingscheme_file in nst.list_data:
                    self._settings.set("General", "namingscheme", nst.default_value)
                    QMessageBox.warning(self, "Unkown naming scheme",
                                        ("%s-%s can not use the naming scheme '%s'."
                                         " Resetting to default '%s'"
                                         %(version.appname, version.version,
                                           namingscheme_file, nst.default_value)))

                for widget in self._tabs:
                    widget.update_input()
            except Exception as e:
                msg = "Could not load settings file (%s)\n.%s" \
                      %(filename, traceback.format_exc())
                QMessageBox.critical(self, "Error", msg)

            else:
                # set settings to not-changed (assume no changed since loaded from file)
                self.settings_changed(False)
                # notify tabs about new settings loaded
                for tab in self._tabs:
                    tab.settings_loaded()
                self.statusBar().showMessage('Settings successfully loaded.')

    def _write_settings(self, filename):
        try:
            f = file(filename, 'w')
            # create a new version (copy) of the current
            # settings which add the needed rendering information
            pframe = self._tab_lookup[SECTION_NAME_PROCESSING][1]
            settings_dummy = pframe.get_export_settings(self._settings)
            settings_dummy.write(f)
            f.close()
        except Exception as e:
            msg = "Could not save settings\n%s" %str(e)
            QMessageBox.critical(self, "Error", msg)
            self.statusBar().showMessage('Settings not successfully saved.')
        else:
            self._settings_filename = filename
            self.setWindowTitle('%s - %s[*]' % (self.appname, filename))
            self.settings_changed(False)
            self.statusBar().showMessage('Settings successfully saved.')

    def on_about(self):
        dialog = CecogAboutDialog(self)
        dialog.show()

    def about_qt(self):
        QMessageBox.aboutQt(self, "about Qt")

    def open_preferences(self):
        pref = PreferencesDialog(self)
        pref.exec_()

    def updateStyleSheet(self, stylesheet):
        self.setStyleSheet("")
        self.setStyleSheet(stylesheet)

        self._pages.assistant.setStyleSheet("")
        self._pages.assistant.setStyleSheet(stylesheet)

        if self._browser is not None:
            self._browser.setStyleSheet("")
            self._browser.setStyleSheet(stylesheet)

    def _on_browser_open(self):
        if self._imagecontainer is None:
            QMessageBox.warning(self, 'Data structure not loaded',
                                'The input directory structure file was not loaded.\n'
                                'Click "Scan input directory" in section "General" to proceed.')
        elif self._browser is None:
            try:
                browser = Browser(self._settings, self._imagecontainer, None)
                browser.show()
                browser.raise_()
                browser.setFocus()
                app = AppPreferences()
                browser.setStyleSheet(loadStyle(app.stylesheet))
                self._browser = browser
            except Exception as e:
                traceback.print_exc()
                QMessageBox.critical(self, "Error", str(e))
        else:
            self._browser.show()
            self._browser.raise_()

    def _on_load_input(self):
        txt = "Error scanning image structure"
        path_in = self._settings.get(SECTION_NAME_GENERAL, 'pathin')
        if path_in == '':
            QMessageBox.critical(self, "Error", "%s\nImage path must be defined." %txt)
        elif not os.path.isdir(path_in) and \
             not os.path.isdir(os.path.join(self.environ.package_dir, path_in)):
            QMessageBox.critical(self, "Error", "%s\nImage path '%s' not found."
                                 %(txt, path_in))
        else:
            try:
                infos = list(ImageContainer.iter_check_plates(self._settings))
            except Exception as e:
                QMessageBox.critical(self, "Error", "%s\n%s" %(txt, str(e)))
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
                        btn1 = QtWidgets.QPushButton('No', box)
                        box.addButton(btn1, QMessageBox.NoRole)
                        box.setDefaultButton(btn1)
                    elif len(found_plates) > 0:
                        btn1 = QtWidgets.QPushButton('Rescan missing', box)
                        box.addButton(btn1, QMessageBox.YesRole)
                        box.setDefaultButton(btn1)
                    else:
                        btn1 = None

                    btn2 = QtWidgets.QPushButton('Rescan all', box)
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
                    ret = QMessageBox.question(self, "No structure data found",
                                               ("Scanning the input directory can be time "
                                                "consuming.\n\nDo you want to proceed?"),
                                               QMessageBox.Yes|QMessageBox.No)
                    if ret == QMessageBox.No:
                        cancel = True
                    scan_plates = dict((info[0], True) for info in infos)

                if not cancel:
                    self._load_image_container(infos, scan_plates)

    def _load_image_container(self, plate_infos=None, scan_plates=None,
                              show_dialog=True):
        self._clear_browser()

        if plate_infos is None:
            plate_infos = list(ImageContainer.iter_check_plates(self._settings))

        imagecontainer = ImageContainer()
        self._imagecontainer = imagecontainer

        if scan_plates is None:
            scan_plates = dict((info[0], False) for info in plate_infos)

        def load(emitter, icontainer, settings, splates):
            iter_ = icontainer.iter_import_from_settings(settings, scan_plates=splates)
            for idx, info in enumerate(iter_):
                emitter.setValue.emit(idx)

            emitter.setLabelText.emit("checking dimensions...")
            emitter.setRange.emit(0, 0)
            QtCore.QCoreApplication.processEvents()

            if len(icontainer.plates) > 0:
                icontainer.set_plate(icontainer.plates[0])
                icontainer.check_dimensions()


        label = ('Please wait until the input structure is scanned\n'
                 'or the structure data loaded...')
        self._dlg = ProgressDialog(label, None, 0, len(scan_plates), self)
        emitter = ProgressObject()
        emitter.setRange.connect(self._dlg.setRange)
        emitter.setValue.connect(self._dlg.setValue)
        emitter.setLabelText.connect(self._dlg.setLabelText)

        try:
            func = lambda: load(emitter, imagecontainer,
                                self._settings, scan_plates)
            self._dlg.exec_(func, (emitter, ))
        except ImportError as e:
            # structure file from versions older than 1.3 contain pdk which is
            # removed
            if 'pdk' in str(e):
                QMessageBox.critical(self, "Error",
                                     ("Your structure file format is outdated.\n"
                                      "You have to rescan the plate(s)"))
            else:
                QMessageBox.critical(self, "Error", traceback.format_exc())
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


        try: # I hate lookup tables!
            self._tab_lookup['Cluster'][1].set_imagecontainer(imagecontainer)
        except KeyError:
            pass

        if len(imagecontainer.plates) > 0:
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

            # report problems about a mismatch between channel IDs found in the data
            # and specified by the user
            if len(problems) > 0:
                # a mismatch between settings and data will cause changed settings
                self.settings_changed(True)

            trait = self._settings.get_trait(SECTION_NAME_EVENT_SELECTION,
                                             'duration_unit')

            # allow time-base tracking durations only if time-stamp
            # information is present
            meta_data = imagecontainer.get_meta_data()
            if meta_data.has_timestamp_info:
                result = trait.set_list_data(TimeConverter.units)
            else:
                result = trait.set_list_data([TimeConverter.FRAMES])
            if result is None:
                QMessageBox.critical(self, "Could not set tracking duration units",
                                     ("The tracking duration units selected to match the "
                                      "load data. Please check your settings."))
                # a mismatch between settings and data will cause changed settings
                self.settings_changed(True)

            # activate change notification again
            self._settings.set_notify_change(True)


            self.set_modules_active(state=True)
            if show_dialog:
                QMessageBox.information(
                    self, "Information",
                    "%d plate(s) successfully loaded." % len(imagecontainer.plates))
        else:
            QMessageBox.critical(self, "Error",
                                 ("No images found\n"
                                  "Verifiy your nameing scheme and rescan the data."))

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

        dir_ = os.path.dirname(self._settings_filename)
        if self._check_settings_saved() != QMessageBox.Cancel:
            if self._settings_filename is not None:
                settings_filename = self.environ.demo_settings
                if os.path.isfile(settings_filename):
                    home = settings_filename
            filename = QtWidgets.QFileDialog.getOpenFileName( \
               self, 'Open config file', dir_, ';;'.join(self.NAME_FILTERS))[0]
            if not bool(filename):
                return

            try:
                self.load_settings(filename)
                if self._settings.was_old_file_format():
                    QMessageBox.information(
                        self, 'Information',
                        'Config file was updated to version %s' %self.version)
            except Exception as e:
                msg = "File could not be loaded\n%s" %str(e)
                QMessageBox.critical(self, "Error", msg)
            finally:
                self._clear_browser()
                self.set_modules_active(state=False)

    def _on_file_save(self):
        self.save_settings(False)

    def _on_file_save_as(self):
        self.save_settings(True)

    def _clear_browser(self):
        if not self._browser is None:
            self._browser.close()
            self._browser = None

    def _on_show_log_window(self):
        self._pages.showLogWindow()

    def _get_save_as_filename(self):
        dir = ""
        if self._settings_filename is not None:
            settings_filename = self.environ.demo_settings
            if os.path.isfile(settings_filename):
                dir = settings_filename
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save config file as', dir, ';;'.join(self.NAME_FILTERS))[0]
        return filename or None

    def show_assistant(self):
        self._pages.assistant.show()
        self._pages.assistant.openKeyword('index')
