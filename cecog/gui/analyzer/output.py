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

__all__ = ['OutputFrame']

from cecog.gui.analyzer import BaseFrame

class OutputFrame(BaseFrame):

    ICON = ":output.png"

    def __init__(self, settings, parent, name):
        super(OutputFrame, self).__init__(settings, parent, name)

        self.add_group(None,
                       [('hdf5_include_raw_images', (0,0,1,1)),
                        ('hdf5_include_label_images', (1,0,1,1)),
                        ('hdf5_include_crack', (3,0,1,1)),
                        ('hdf5_include_features', (4,0,1,1)),
                        ('hdf5_include_classification', (5,0,1,1)),
                        ('hdf5_include_tracking', (6,0,1,1)),
                        ('hdf5_include_events', (7,0,1,1)),
                        (None, (8,0,1,3)),
                        ('hdf5_compression', (9,0,1,1)),
                        ('hdf5_merge_positions', (10,0,1,1)),
                        ], label="CellH5 options")
        self.add_group('hdf5_reuse', [])
        self.add_group('minimal_effort', [])
        self.add_expanding_spacer()
