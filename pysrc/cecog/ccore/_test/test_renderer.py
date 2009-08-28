"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
              See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import unittest
import numpy

#-------------------------------------------------------------------------------
# extension module imports:
#
from pyvigra import (read_image,
                     #write_image,
                     #UInt8Image2d,
                     #UInt8Image2dRgb,
                     )
#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.ccore import make_image_overlay

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# classes:
#
class TestCase(unittest.TestCase):

    def setUp(self):
        self.img_r = read_image('swisscow_R.png')
        self.img_g = read_image('swisscow_G.png')
        self.img_b = read_image('swisscow_B.png')

    def _check_alpha(self, alpha):
        col_r = (255,0,0)
        col_g = (0,255,0)
        col_b = (0,0,255)

        img_rgb = make_image_overlay([self.img_r, self.img_g, self.img_b],
                                     [col_r, col_g, col_b],
                                     [alpha] * 3)
        array_rgb = img_rgb.to_array()
        array_r = self.img_r.to_array()
        array_g = self.img_g.to_array()
        array_b = self.img_b.to_array()

        assert (array_rgb[:,:,0] ==
                numpy.require(array_r * alpha, numpy.uint8)).all()
        assert (array_rgb[:,:,1] ==
                numpy.require(array_g * alpha, numpy.uint8)).all()
        assert (array_rgb[:,:,2] ==
                numpy.require(array_b * alpha, numpy.uint8)).all()

    def test_alphas(self):
        self._check_alpha(1.0)
        self._check_alpha(0.8)
        self._check_alpha(0.4)
        self._check_alpha(0.0)

    def test_colors(self):
        col_r = (127,0,0)
        col_g = (0,63,0)
        col_b = (0,0,43)

        img_rgb = make_image_overlay([self.img_r, self.img_g, self.img_b],
                                     [col_r, col_g, col_b])

        array_rgb = img_rgb.to_array()
        array_r = self.img_r.to_array()
        array_g = self.img_g.to_array()
        array_b = self.img_b.to_array()

        assert (array_rgb[:,:,0] ==
                numpy.require(array_r * (127/255.), numpy.uint8)).all()
        assert (array_rgb[:,:,1] ==
                numpy.require(array_g * (63/255.), numpy.uint8)).all()
        assert (array_rgb[:,:,2] ==
                numpy.require(array_b * (43/255.), numpy.uint8)).all()

    def test_blending(self):
        col_r = (127,0,255)
        col_g = (0,63,0)
        col_b = (0,0,43)

        img_rgb = make_image_overlay([self.img_r, self.img_g, self.img_b],
                                     [col_r, col_g, col_b])

        array_rgb = img_rgb.to_array()
        array_r = self.img_r.to_array()
        array_g = self.img_g.to_array()
        #array_b = self.img_b.to_array()

        assert (array_rgb[:,:,0] ==
                numpy.require(array_r * (127/255.), numpy.uint8)).all()
        assert (array_rgb[:,:,1] ==
                numpy.require(array_g * (63/255.), numpy.uint8)).all()
        assert (array_rgb[:,:,2] ==
                numpy.require(array_r, numpy.uint8)).all()


#-------------------------------------------------------------------------------
# functions:
#
def create_suite():
    loader = unittest.TestLoader().loadTestsFromTestCase
    suite = unittest.TestSuite([loader(TestCase),
                                ])
    return suite

#-------------------------------------------------------------------------------
# main:
#
if __name__ == "__main__":
    unittest.TextTestRunner().run(create_suite())

