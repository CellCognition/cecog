# -*- coding: utf-8 -*-
"""
hmm_scafold

XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
THIS MODULE IS PROBABLY DEPRECIATED
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from os.path import join, isfile, abspath

from cecog.threads.corethread import CoreThread
from cecog.traits.analyzer.errorcorrection import SECTION_NAME_ERRORCORRECTION

class HmmThread_Python_Scafold(CoreThread):
    def __init__(self, parent, settings, learner_dict, imagecontainer):
        super(CoreThread, self).__init__(parent, settings)

        self._settings.set_section(SECTION_NAME_ERRORCORRECTION)
        self._learner_dict = learner_dict
        self._imagecontainer = imagecontainer
        self.plates = self._imagecontainer.plates
        self._mapping_files = {}

        # Read Events from event txt files
        self.events = self._readEvents()

    def _readEvents(self):
        "Reads all events written by the CellCognition tracking."
        pass

    #XXX is this function called
    def _setMappingFile(self):
        if self._settings.get2('position_labels'):
            path_mapping = self._convert(self._settings.get2('mappingfile_path'))
            for plate_id in self.plates:
                mapping_file = join(path_mapping, '%s.tsv' % plate_id)
                if not isfile(mapping_file):
                    mapping_file = join(path_mapping, '%s.txt' % plate_id)
                    if not isfile(mapping_file):
                        raise IOError(("Mapping file '%s' for plate "
                                       "'%s' not found."
                                       % (mapping_file, plate_id)))
                self._mapping_files[plate_id] = abspath(mapping_file)

    def _run(self):
        # Initialize GUI Progress bar
        info = {'min' : 0,
                'max' : len(self.plates),
                'stage': 0,
                'meta': 'Error correction...',
                'progress': 0}

        # Process each plate and update Progressbar (if not aborted by user)
        for idx, plate_id in enumerate(self.plates):
            if not self._abort:
                info['text'] = "Plate: '%s' (%d / %d)" \
                    % (plate_id, idx+1, len(self.plates))
                self.update_status(info)
                self._imagecontainer.set_plate(plate_id)
                self._run_plate(plate_id)
                info['progress'] = idx+1
                self.update_status(info)
            else:
                break

    def _run_plate(self, plate_id):
        print "processing", plate_id

    def set_abort(self, wait=False):
        pass

    @classmethod
    def test_executable(cls, filename):
        "mock interface method"
        return True, ""

    @classmethod
    def get_cmd(cls, filename):
        "mock interface method"
        return ""

    def _produce_txt_output(self):
        pass
