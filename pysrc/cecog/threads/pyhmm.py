"""
pyhmm.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


from cecog.threads.corethread import CoreThread
from cecog.errorcorrection import PlateRunner
from cecog.errorcorrection import ECParams

class PyHmmThread(CoreThread):

    def __init__(self, parent, settings, imagecontainer):
        super(PyHmmThread, self).__init__(parent, settings)
        self._imagecontainer = imagecontainer

    def _run(self):
        plates = self._imagecontainer.plates
        outdirs = []
        for plate in plates:
            self._imagecontainer.set_plate(plate)
            outdirs.append(self._imagecontainer.get_path_out())
        platerunner = PlateRunner(plates, outdirs, self.params_ec)
        platerunner.progressUpdate.connect(self.update_status)
        self.aborted.connect(platerunner.abort)
        try:
            platerunner()
        finally:
            platerunner.progressUpdate.disconnect(self.update_status)
            self.aborted.disconnect(platerunner.abort)

    @property
    def params_ec(self):
        """Read error correction options from settings into a nice readable.
        class instance."""

        return  ECParams(self._settings)
