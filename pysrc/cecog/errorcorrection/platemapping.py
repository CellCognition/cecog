"""
platemapping.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['PlateMapping']

import csv
from os.path import isfile
from collections import OrderedDict

class PlateMapping(OrderedDict):
    """Read/Write plate mappings files. Default for all positions is None.
    After reading, all values are set according to the file."""

    POSITION = 'Position'
    WELL = 'Well'
    SITE = 'Site'
    ROW = 'Row'
    COLUMN = 'Column'
    GENE = 'Gene Symbol'
    OLIGO = 'OligoID'
    GROUP = 'Group'

    _colnames = [POSITION, WELL, SITE, ROW, COLUMN, GENE, OLIGO, GROUP]

    def __init__(self, positions):
        super(PlateMapping, self).__init__()
        for pos in positions:
            self.setdefault(pos, None)

    def read(self, filename):
        if not isfile(filename):
            raise IOError("Plate mapping file not found\n(%s)" %filename)

        with open(filename, "r") as fp:
            reader = csv.DictReader(fp, delimiter='\t')
            for line in reader:
                pos = line['Position']
                del line['Position']
                self[pos] = line

    def save(self, filename, mode="w"):
        with open(filename, mode=mode) as fp:
            writer = csv.DictWriter(fp, fieldnames=self._colnames,
                                    delimiter='\t')
            writer.writeheader()
            for k, v in self.iteritems():
                line = v.copy()
                line.update({"Position": k})
                writer.writerow(line)

if __name__ == "__main__":

    path_in = '/Users/hoefler/demo_data/ibb/mappings/input.txt'
    path_out = '/Users/hoefler/demo_data/ibb/mappings/output.txt'

    positons = ["018", "028", "051", "067"]
    pm = PlateMapping(positons)
    pm.read(path_in)
    pm['018']['OligoID'] = "just made up"
    pm.save(path_out)
