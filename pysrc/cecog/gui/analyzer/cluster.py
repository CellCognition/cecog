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

__all__ = ['ClusterFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#
import types, \
       copy, \
       traceback

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pyamf.remoting.client import RemotingService

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.cluster import SECTION_NAME_CLUSTER
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL
from cecog.traits.config import (ANALYZER_CONFIG,
                                 PATH_MAPPER,
                                 map_path_to_os,
                                 is_path_mappable,
                                 )
from cecog.gui.analyzer import (BaseFrame,
                                AnalzyerThread,
                                HmmThread,
                                )
from cecog.gui.analyzer.processing import ProcessingFrame
from cecog.analyzer import (SECONDARY_REGIONS,
                            SECONDARY_COLORS,
                            )
from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.util.util import OS_LINUX
from cecog.gui.util import (exception,
                            information,
                            warning,
                            waitingProgressDialog,
                            )
from cecog import (JOB_CONTROL_RESUME,
                   JOB_CONTROL_SUSPEND,
                   JOB_CONTROL_TERMINATE,
                   VERSION
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
class ClusterDisplay(QGroupBox):

    def __init__(self, parent, settings):
        QGroupBox.__init__(self, parent)
        self._settings = settings
        self._jobid = None
        self._toggle_state = JOB_CONTROL_SUSPEND
        self._service = None

        self._host_url = ANALYZER_CONFIG.get('Cluster', 'host_url')

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
        #self._table_info.setEditTriggers(QTableWidget.)
        self._table_info.setSelectionMode(QTableWidget.NoSelection)
        labels = ['status', 'your machine', 'on the cluster']
        self._table_info.setColumnCount(len(labels))
        self._table_info.setHorizontalHeaderLabels(labels)
        self._table_info.setSizePolicy(QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
                                                   QSizePolicy.MinimumExpanding))


        layout = QGridLayout(self)
        layout.addWidget(label1, 0, 0, Qt.AlignRight)
        layout.addWidget(self._label_hosturl, 0, 1, 1, 4)
        layout.addWidget(label3, 1, 0, Qt.AlignRight)
        layout.addWidget(self._label_status, 1, 1, 1, 4)
        layout.addWidget(label4, 2, 0, Qt.AlignRight)
        layout.addWidget(self._table_info, 3, 0, 1, 5)

        label = QLabel('Mail addresses:', self)
        layout.addWidget(label, 4, 0, Qt.AlignRight)
        mails = ANALYZER_CONFIG.get('Cluster', 'mail_adresses')
        self._txt_mail = QLineEdit(mails, self)
        layout.addWidget(self._txt_mail, 4, 1, 1, 4)

        self._btn_submit = QPushButton('Submit job', self)
        self._btn_submit.setEnabled(False)
        self._btn_submit.clicked.connect(self._on_submit_job)
        layout.addWidget(self._btn_submit, 5, 0, 1, 5)

        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line, 6, 0, 1, 5)
#        layout.addItem(QSpacerItem(1, 1,
#                                   QSizePolicy.MinimumExpanding,
#                                   QSizePolicy.Expanding|QSizePolicy.Maximum),
#                       6, 0, 1, 5)

        label5 = QLabel('Current job ID:', self)
        layout.addWidget(label5, 7, 0, Qt.AlignRight)
        self._txt_jobid = QLineEdit(self._jobid or '', self)

        regexp = QRegExp('\d+')
        regexp.setPatternSyntax(QRegExp.RegExp2)
        #self._txt_jobid.setValidator(QRegExpValidator(regexp, self._txt_jobid))
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

    def _on_jobid_entered(self, txt):
        print txt
        self._jobid = str(txt)

    @pyqtSlot()
    def _on_submit_job(self):
        self._submit_settings.set_section(SECTION_NAME_GENERAL)
        if not self._submit_settings.get2('constrain_positions'):
            # FIXME:
            imagecontainer = qApp._main_window._imagecontainer
            positions = []
            for plate_id in imagecontainer.plates:
                imagecontainer.set_plate(plate_id)
                meta_data = imagecontainer.get_meta_data()
                positions += ['%s___%s' % (plate_id, p) for p in meta_data.positions]
            self._submit_settings.set2('positions', ','.join(positions))
            nr_items = len(positions)
        else:
            positions = self._submit_settings.get2('positions')
            nr_items = len(positions.split(','))

        # FIXME: we need to get the current value for 'position_granularity'
        settings_dummy = ProcessingFrame.get_special_settings(self._settings)
        position_granularity = settings_dummy.get(SECTION_NAME_CLUSTER, 'position_granularity')

        path_out = self._submit_settings.get2('pathout')
        emails = str(self._txt_mail.text()).split(',')
        try:
            dlg = waitingProgressDialog('Please wait until the job has been submitted...', self)
            dlg.setTarget(self._service.submit_job,
                          'cecog_batch', self._submit_settings.to_string(), path_out, emails, nr_items,
                          position_granularity, VERSION)
            dlg.exec_()
            jobid = dlg.getTargetResult()
        except:
            exception(self, 'Error on job submission')
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
            information(self, 'Job submitted successfully',
                        "Job successfully submitted to the cluster.\nJob ID: %s, items: %d" % (main_jobid, nr_items))

    @pyqtSlot()
    def _on_terminate_job(self):
        try:
            dlg = waitingProgressDialog("Please wait until the job has been terminated...", self)
            dlg.setTarget(self._service.control_job, self._jobid, JOB_CONTROL_TERMINATE)
            dlg.exec_()
        except:
            exception(self, 'Error on job termination')
        else:
            self._btn_toogle.setChecked(False)
            self._toggle_state = JOB_CONTROL_SUSPEND
            self._btn_toogle.setText(self._toggle_state)
            self._update_job_status()

    @pyqtSlot()
    def _on_toggle_job(self):
        try:
            dlg = waitingProgressDialog("Please wait until the job has been suspended/resumed...", self)
            dlg.setTarget(self._service.control_job, self._jobid, self._toggle_state)
            dlg.exec_()
        except:
            self._toggle_state = JOB_CONTROL_SUSPEND
            self._btn_toogle.setChecked(False)
            exception(self, 'Error on toggle job status')
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
        information(self, 'Cluster update', "Message: '%s'" % txt)

    def _update_job_status(self):
        try:
            dlg = waitingProgressDialog('Please wait for the cluster update...', self)
            dlg.setTarget(self._service.get_job_status, self._jobid)
            dlg.exec_()
            txt = dlg.getTargetResult()
        except:
            exception(self, 'Error on retrieve job status')
        else:
            self._label_jobstatus.setText(txt)
        return txt

    def _connect(self):
        success = False
        try:
            client = RemotingService(self._host_url)
            dlg = waitingProgressDialog('Please wait for the cluster...', self)
            dlg.setTarget(client.getService, 'clustercontrol')
            dlg.exec_()
            self._service = dlg.getTargetResult()
        except:
            exception(self, 'Error on connecting to cluster control service')
        else:
            cluster_versions = self._service.get_cecog_versions()
            if not VERSION in set(cluster_versions):
                warning(self, 'Cecog version %s not supported by the cluster' %
                        VERSION, 'Valid versions are: %s' %
                        ', '.join(cluster_versions))
            else:
                success = True
        return success

    def _get_mappable_paths(self):
        '''
        Get the paths/filenames which have to be mapped to run on a remote
        cluster. Whether an option is considered or not might depend on other
        values/switches, e.g. if classification is not needed there is no need
        to map the paths.
        '''
        #FIXME: should be done in a better way.
        results = []
        targets = [(('General', 'pathin'), []),
                   (('General', 'pathout'),[]),
                   (('General', 'structure_file_extra_path_name'),
                    [('General', 'structure_file_extra_path')]),
                   (('Classification', 'primary_classification_envpath'),
                    [('Processing', 'primary_classification')]),
                   (('Classification', 'secondary_classification_envpath'),
                    [('Processing', 'secondary_processchannel'),
                     ('Processing', 'secondary_classification')]),
                   ]
        for info, const in targets:
            passed = reduce(lambda x,y: x and y,
                            map(lambda z: self._settings.get(*z), const),
                            True)
            if passed:
                results.append(info)
        return results

    def update_display(self, is_active):
        if self._connect():
            self._can_submit = True

            imagecontainer = qApp._main_window._imagecontainer
            if imagecontainer is None:
                self._submit_settings = ProcessingFrame.get_special_settings(self._settings)
            else:
                self._submit_settings = ProcessingFrame.get_special_settings(self._settings,
                                                                             imagecontainer.has_timelapse)

            self._label_hosturl.setText(self._host_url)
            self._label_status.setText(self._service.get_service_info())

            mappable_paths = self._get_mappable_paths()
            self._table_info.clearContents()
            self._table_info.setRowCount(len(mappable_paths))
            for idx, info in enumerate(mappable_paths):
                value = self._settings.get(*info)
                mapped = map_path_to_os(value, target_os=OS_LINUX, force=False)
                self._submit_settings.set(info[0], info[1], mapped)
                status = not mapped is None
                item = QTableWidgetItem()
                item.setBackground(QBrush(QColor('green' if status else 'red')))
                txt_mapped = str(mapped) if status else \
                            'Warning: path can not be mapped on the cluster'
                self._table_info.setItem(idx, 0, item)
                self._table_info.setItem(idx, 1, QTableWidgetItem(value))
                self._table_info.setItem(idx, 2, QTableWidgetItem(txt_mapped))
                self._can_submit &= status
            self._table_info.resizeColumnsToContents()
            self._table_info.resizeRowsToContents()
            self._btn_submit.setEnabled(self._can_submit and is_active)
            self._btn_terminate.setEnabled(is_active)
            self._btn_toogle.setEnabled(is_active)
            self._btn_update.setEnabled(is_active)
        else:
            self._btn_submit.setEnabled(False)
            self._btn_terminate.setEnabled(False)
            self._btn_toogle.setEnabled(False)
            self._btn_update.setEnabled(False)


class ClusterFrame(BaseFrame):

    SECTION_NAME = SECTION_NAME_CLUSTER

    def __init__(self, settings, parent):
        super(ClusterFrame, self).__init__(settings, parent)

        self._cluster_display = self._add_frame()
        self.add_group(None,
                       [('position_granularity', (0,0,1,1)),
                        ], label='Cluster Settings')

    def _add_frame(self):
        frame = self._get_frame()
        cluster_display = ClusterDisplay(frame, self._settings)
        frame.layout().addWidget(cluster_display,
                                 frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1
        return cluster_display

    def page_changed(self):
        self._cluster_display.update_display(self._is_active)
