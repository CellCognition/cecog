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

__all__ = ['ClusterFrame']

import types
import socket
import urlparse
from os.path import isdir

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *
from PyQt5.QtWidgets import QMessageBox

from pyamf.remoting.client import RemotingService
from pyamf.remoting import RemotingError

from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.gui.analyzer import BaseFrame
from cecog.gui.analyzer.processing import ExportSettings
from cecog.gui.progressdialog import ProgressDialog
from cecog.gui.preferences import AppPreferences

from cecog import JOB_CONTROL_RESUME, JOB_CONTROL_SUSPEND, \
    JOB_CONTROL_TERMINATE

from cecog.version import version, appname


class ConnectionError(Exception):
    pass


class ClusterDisplay(QGroupBox):

    MIN_API_VERSION = 2

    def __init__(self, parent, clusterframe,  settings):
        super(ClusterDisplay, self).__init__(parent)
        self._settings = settings
        self._clusterframe = clusterframe
        self._imagecontainer = None
        self._jobid = None
        self._toggle_state = JOB_CONTROL_SUSPEND
        self._service = None
        self._host_url = None

        self.setTitle('ClusterControl')
        label1 = QLabel('Cluster URL:', self)

        fixed = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        expanding = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        label1.setSizePolicy(fixed)

        self._label_hosturl = QLabel('', self)
        self._label_hosturl.setSizePolicy(expanding)

        label3 = QLabel('Cluster status:', self)
        label3.setSizePolicy(fixed)

        self._label_status = QLabel('', self)
        self._label_status.setSizePolicy(expanding)

        label4 = QLabel('Path mappings:', self)
        label4.setSizePolicy(fixed)

        self._table_info = QTableWidget(self)
        self._table_info.setSelectionMode(QTableWidget.NoSelection)
        labels = ['Local', 'Remote']
        self._table_info.setColumnCount(len(labels))
        self._table_info.setHorizontalHeaderLabels(labels)
        self._table_info.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
                        QSizePolicy.MinimumExpanding))

        layout = QGridLayout(self)
        layout.addWidget(label1, 0, 0, Qt.AlignRight)
        layout.addWidget(self._label_hosturl, 0, 1, 1, 4)
        layout.addWidget(label3, 1, 0, Qt.AlignRight)
        layout.addWidget(self._label_status, 1, 1, 1, 4)
        layout.addWidget(label4, 2, 0, Qt.AlignRight)
        layout.addWidget(self._table_info, 3, 0, 1, 5)

        self._btn_submit = QPushButton('Submit job', self)
        self._btn_submit.setEnabled(False)
        self._btn_submit.clicked.connect(self._on_submit_job)
        layout.addWidget(self._btn_submit, 5, 0, 1, 5)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line, 6, 0, 1, 5)

        label5 = QLabel('Current job ID:', self)
        layout.addWidget(label5, 7, 0, Qt.AlignRight)
        self._txt_jobid = QLineEdit(self._jobid or '', self)

        regexp = QRegExp('\d+')
        regexp.setPatternSyntax(QRegExp.RegExp2)
        self._txt_jobid.textEdited.connect(self._on_jobid_entered)
        self._txt_jobid.returnPressed.connect(self._on_update_job_status)

        layout.addWidget(self._txt_jobid, 7, 1)
        self._btn_update = QPushButton('Update', self)
        self._btn_update.clicked.connect(self._on_update_job_status)
        layout.addWidget(self._btn_update, 7, 2)
        self._btn_toogle = QPushButton(self._toggle_state, self)
        self._btn_toogle.clicked.connect(self._on_toggle_job)
        self._btn_toogle.setCheckable(True)
        layout.addWidget(self._btn_toogle, 7, 3)
        self._btn_terminate = QPushButton('Terminate', self)
        self._btn_terminate.clicked.connect(self._on_terminate_job)
        layout.addWidget(self._btn_terminate, 7, 4)

        label = QLabel('Job status:', self)
        layout.addWidget(label, 8, 0, Qt.AlignRight)
        self._label_jobstatus = QLabel('', self)
        layout.addWidget(self._label_jobstatus, 8, 1, 1, 4)

        layout.addItem(QSpacerItem(1, 1,
                                   QSizePolicy.MinimumExpanding,
                                   QSizePolicy.Expanding|QSizePolicy.Maximum),
                       10, 0, 1, 5)

    @property
    def jobIds(self):
        jids = self._txt_jobid.text()
        if not jids:
            return None
        else:
            return jids

    @jobIds.setter
    def jobIds(self, jobids):
        self._txt_jobid.setText(jobids)
        self._jobid = str(jobids)

    @property
    def imagecontainer(self):
        if self._imagecontainer is None:
            raise RuntimeError("Image container is not loaded yet")
        return self._imagecontainer

    @imagecontainer.deleter
    def imagecontainer(self):
        del self._imagecontainer

    @imagecontainer.setter
    def imagecontainer(self, imagecontainer):
        self._imagecontainer = imagecontainer

    def _on_jobid_entered(self, txt):
        self._jobid = str(txt)

    @pyqtSlot()
    def _on_submit_job(self):

        self._submit_settings.set_section(SECTION_NAME_GENERAL)
        if not self._submit_settings.get2('constrain_positions'):
            positions = []

            for plate_id in self.imagecontainer.plates:
                self.imagecontainer.set_plate(plate_id)
                meta_data = self.imagecontainer.get_meta_data()
                positions += ['%s___%s' % (plate_id, p) for p in meta_data.positions]
            self._submit_settings.set2('positions', ','.join(positions))
            nr_items = len(positions)
        else:
            positions = self._submit_settings.get2('positions')
            nr_items = len(positions.split(','))

        settings_dummy = self._clusterframe.get_special_settings(self._settings)

        apc = AppPreferences()
        batch_size = apc.batch_size
        pathout = self._submit_settings.get2('pathout')



        try:
            self.dlg = ProgressDialog("Submitting Jobs...", None, 0, 0, self)
            settings_str = self._submit_settings.to_string()

            func = lambda: self._service.submit_job('cecog_batch', settings_str,
                                                    pathout, nr_items,
                                                    batch_size, version)
            self.dlg.exec_(func)
            jobid = self.dlg.getTargetResult()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", 'Job submission failed (%s)' %str(e))
        else:
            # FIXME: no idea how DRMAA 1.0 compatible this is
            if type(jobid) == types.ListType:
                self._jobid = ','.join(jobid)
                main_jobid = jobid[0].split('.')[0]
            else:
                self._jobid = str(jobid)
                main_jobid = jobid
            self._txt_jobid.setText(self._jobid)
            self._update_job_status()
            QMessageBox.information(
                self, "Information", ("Job(s) successfully submitted\n"
                                      "Job ID: %s, #jobs: %d" % (main_jobid, nr_items)))

    @pyqtSlot()
    def _on_terminate_job(self):
        if self.jobIds is None:
            return

        try:
            self.dlg = ProgressDialog("Terminating Jobs...", None, 0, 0, self)
            func = lambda: self._service.control_job(self._jobid, JOB_CONTROL_TERMINATE)
            self.dlg.exec_(func)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", "Job termination failed (%s)" %str(e))
        else:
            self._btn_toogle.setChecked(False)
            self._toggle_state = JOB_CONTROL_SUSPEND
            self._btn_toogle.setText(self._toggle_state)
            self._update_job_status()

    @pyqtSlot()
    def _on_toggle_job(self):
        if self.jobIds is None:
            return
        try:
            self.dlg = ProgressDialog("Suspending Jobs...", None, 0, 0, self)
            func = lambda: self._service.control_job(self._jobid, self._toggle_state)
            self.dlg.exec_(func)
        except Exception as e:
            self._toggle_state = JOB_CONTROL_SUSPEND
            self._btn_toogle.setChecked(False)
            QMessageBox.critical(
                self, "Error", "Could not toggle job status (%s)" %str(e))
        else:
            if self._toggle_state == JOB_CONTROL_SUSPEND:
                self._toggle_state = JOB_CONTROL_RESUME
            else:
                self._toggle_state = JOB_CONTROL_SUSPEND
            self._update_job_status()
        self._btn_toogle.setText(self._toggle_state)

    @pyqtSlot()
    def _on_update_job_status(self):
        txt = self._update_job_status()
        if txt is not None:
            QMessageBox.information(self, "Cluster update", "Message: '%s'" % txt)

    def _update_job_status(self):
        if self.jobIds is None:
            return

        try:
            self.dlg = ProgressDialog("Updating Job Status...", None, 0, 0, self)

            func = lambda: self._service.get_job_status(self._jobid)
            self.dlg.exec_(func)
            txt = self.dlg.getTargetResult()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", 'Could not retrieve job status (%s)' %str(e))
        else:
            self._label_jobstatus.setText(txt)
            return txt

    def _check_host_url(self):
        url = urlparse.urlparse(self._host_url)
        try:
            test_sock = socket.create_connection((url.hostname, url.port), timeout=1)
            test_sock.shutdown(2)
            test_sock.close()
        except:
            msg = "Connection failed (%s)" %self._host_url
            raise ConnectionError(msg)


    def _check_api_version(self):
        try:
            api_version = self._service.api_version()
        except RemotingError:
            # this call is not supported by older version of the
            # cluster service
            api_version = 1

        if api_version < self.MIN_API_VERSION:
            msg = ("Api version of the cluster services is %d "
                   "but version %d is required.") \
                   %(self.MIN_API_VERSION, api_version)
            raise RuntimeError(msg)

    def _turn_off_cluster_support(self):
        pref = AppPreferences()
        pref.cluster_support = False
        pref.saveSettings()

    def _connect(self):

        success = False
        try:
            self._check_host_url()
            client = RemotingService(self._host_url)
            self.dlg = ProgressDialog("Connecting to Cluster...", None, 0, 0, self)
            func = lambda: client.getService('clustercontrol')
            self.dlg.exec_(func)
            self._service = self.dlg.getTargetResult()
            self._check_api_version()
        except ConnectionError as e:
            msg = ("%s\nDo you want to turn off the cluster support?") %str(e)
            ret = QMessageBox.question(
                self, "Error", msg)
            if ret == QMessageBox.Yes:
                self._turn_off_cluster_support()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        else:
            try:
                self.dlg.exec_(self._service.get_cecog_versions)
                cluster_versions = self.dlg.getTargetResult()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            else:
                if not version in set(cluster_versions):
                    QMessageBox.warning(
                        self, "Warning",
                        ("Cluster does not support %s %s"
                         "Available versions: %s"
                         %(appname, version, ', '.join(cluster_versions))))
                else:
                    success = True
        return success

    def _get_mappable_paths(self):
        """Get the paths/filenames which have to be mapped to run on a remote
        cluster. Whether an option is considered or not might depend on other
        values/switches, e.g. if classification is not needed there is no need
        to map the paths.
        """
        # FIXME: should be done in a better way.
        results = []
        targets = [(('General', 'pathin'), []),
                   (('General', 'pathout'),[]),
                   (('Classification', 'primary_classification_envpath'),
                    [('Processing', 'primary_classification')]),
                   (('Classification', 'secondary_classification_envpath'),
                    [('General', 'process_secondary'),
                     ('Processing', 'secondary_classification')]),
                   (('Classification', 'tertiary_classification_envpath'),
                    [('General', 'process_tertiary'),
                     ('Processing', 'tertiary_classification')]),
                   (('Classification', 'merged_classification_envpath'),
                    [('General', 'process_merged'),
                     ('Processing', 'merged_classification')]),
                   ]
        targets.extend(
            [(('ObjectDetection', '%s_flat_field_correction_image_dir' % prefix),
              [('ObjectDetection', '%s_flat_field_correction' % prefix)])
             for prefix in ['primary', 'secondary', 'tertiary']])

        for info, const in targets:
            passed = reduce(lambda x,y: x and y,
                            map(lambda z: self._settings.get(*z), const),
                            True)
            if passed:
                results.append(info)

        return results

    def check_directories(self):
        """Check local and remote directories defined in the path mapping table
        for existence and setup the table view accordingly.
        """

        ndirs = self._table_info.rowCount()
        remote_dirs = [self._table_info.item(i, 1).text() for i in xrange(ndirs)]
        remote_state = self._service.check_directory(remote_dirs)
        local_dirs = [self._table_info.item(i, 0).text() for i in xrange(ndirs)]
        local_state = [isdir(d) for d in local_dirs]
        states = [local_state, remote_state]

        for i in xrange(ndirs):
            for j in xrange(2):
                item = self._table_info.item(i, j)
                item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
                if states[j][i]:
                    item.setBackground(QBrush(QColor("green")))
                else:
                    if not item.text():
                        item.setText("Not available")
                    item.setBackground(QBrush(QColor("red")))

    def update_display(self, is_active):
        apc = AppPreferences()
        self._host_url = apc.url
        if self._connect():
            can_submit = True

            try:
                self._submit_settings = self._clusterframe.get_special_settings( \
                    self._settings, self.imagecontainer.has_timelapse)
            except:
                self._submit_settings = self._clusterframe.get_special_settings(self._settings)

            self._label_hosturl.setText(self._host_url)
            self._label_status.setText(self._service.get_service_info())

            mappable_paths = self._get_mappable_paths()
            self._table_info.clearContents()
            self._table_info.setRowCount(len(mappable_paths))

            for i, info in enumerate(mappable_paths):
                value = self._settings.get(*info)
                mapped = apc.map2platform(value)
                self._submit_settings.set(info[0], info[1], mapped)
                if mapped is None:
                    can_submit = False
                self._table_info.setItem(i, 0, QTableWidgetItem(value))
                self._table_info.setItem(i, 1, QTableWidgetItem(mapped))

            self.check_directories()
            self._table_info.resizeColumnsToContents()
            self._table_info.resizeRowsToContents()
            self._btn_submit.setEnabled(can_submit and is_active)
        else:
            self._btn_submit.setEnabled(False)

class ClusterFrame(BaseFrame, ExportSettings):

    ICON = ":network-server.png"

    def __init__(self, settings, parent, name):
        super(ClusterFrame, self).__init__(settings, parent, name)

        frame = self._get_frame()
        self._cluster_display = ClusterDisplay(frame, self, self._settings)
        frame.layout().addWidget(self._cluster_display, frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1

        # update display first time when tab is enable
        self._display_update = False


    def page_changed(self):
        self._cluster_display.update_display(self._is_active)
        self._display_update = True

    def settings_loaded(self):
        if self._display_update:
            self._cluster_display.update_display(self._is_active)

    def set_imagecontainer(self, imagecontainer):
        self._cluster_display.imagecontainer = imagecontainer

    def get_jobids(self):
        return self._cluster_display.jobIds

    def restore_jobids(self, jobids):
        self._cluster_display.jobIds = jobids
