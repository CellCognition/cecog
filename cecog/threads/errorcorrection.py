"""
errorcorrection.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["ErrorCorrectionThread"]


from PyQt5.QtCore import Qt

from cecog.threads.corethread import CoreThread
from cecog.errorcorrection import PlateRunner
from cecog.errorcorrection import ECParams
from cecog.units.time import TimeConverter


class ErrorCorrectionThread(CoreThread):

    def __init__(self, parent, settings, imagecontainer):
        super(ErrorCorrectionThread, self).__init__(parent, settings)
        self._imagecontainer = imagecontainer

    def _run(self):
        plates = self._imagecontainer.plates
        outdirs = []
        for plate in plates:
            self._imagecontainer.set_plate(plate)
            outdirs.append(self._imagecontainer.get_path_out())
        # CAUTION params_ec is plate specific !!
        platerunner = PlateRunner(plates, outdirs, self.params_ec)
        platerunner.progressUpdate.connect(self.update_status,
                                           Qt.QueuedConnection)
        self.aborted.connect(platerunner.abort, Qt.QueuedConnection)
        try:
            platerunner()
        finally:
            platerunner.progressUpdate.disconnect(self.update_status)
            self.aborted.disconnect(platerunner.abort)

    @property
    def params_ec(self):
        """Read error correction options from settings into a nice readable.
        class instance."""

        md = self._imagecontainer.get_meta_data()
        t_mean = md.plate_timestamp_info[0]
        tu = TimeConverter(t_mean, TimeConverter.SECONDS)
        increment = self._settings('General', 'frameincrement')
        t_step = tu.sec2min(t_mean)*increment
        return ECParams(self._settings, t_step, TimeConverter.MINUTES)
