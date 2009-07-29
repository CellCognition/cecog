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
                     )
#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.ccore import (apply_lut,
                         apply_blending,
                         lut_from_single_color,
                         )

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# classes:
#
class TestCase(unittest.TestCase):

    def setUp(self):
        self.img_r = read_image('lena_R.tif')
        self.img_g = read_image('lena_G.tif')
        self.img_b = read_image('lena_B.tif')

    def test_lut_from_single_color(self):
        color = (255,0,255)
        lut = lut_from_single_color(color)
        assert len(lut) == 256
        for idx, col in enumerate(lut):
            assert col[0] == color[0] * idx / 255.
            assert col[1] == color[1] * idx / 255.
            assert col[2] == color[2] * idx / 255.

    def test_apply_lut(self):
        col_r = (255,0,0)
        col_g = (0,255,0)
        col_b = (0,0,255)

        lut_r = lut_from_single_color(col_r)
        lut_g = lut_from_single_color(col_g)
        lut_b = lut_from_single_color(col_b)

        img_rgb_r = apply_lut(self.img_r, lut_r)
        img_rgb_g = apply_lut(self.img_g, lut_g)
        img_rgb_b = apply_lut(self.img_b, lut_b)

        array_r = self.img_r.to_array()
        array_g = self.img_g.to_array()
        array_b = self.img_b.to_array()

        array_rgb_r = img_rgb_r.to_array()
        array_rgb_g = img_rgb_g.to_array()
        array_rgb_b = img_rgb_b.to_array()

        assert (array_rgb_r[:,:,0] == array_r).all()
        assert (array_rgb_r[:,:,1] == 0).all()
        assert (array_rgb_r[:,:,2] == 0).all()

        assert (array_rgb_g[:,:,1] == array_g).all()
        assert (array_rgb_g[:,:,0] == 0).all()
        assert (array_rgb_g[:,:,2] == 0).all()

        assert (array_rgb_b[:,:,2] == array_b).all()
        assert (array_rgb_b[:,:,0] == 0).all()
        assert (array_rgb_b[:,:,1] == 0).all()


        for alpha in [1.0, 0.5, 0.22]:
            img_overlay = apply_blending([img_rgb_r, img_rgb_g, img_rgb_b],
                                          [alpha]*3)
            array_overlay = img_overlay.to_array()
            assert (array_overlay[:,:,0] ==
                    numpy.require(array_r * alpha, numpy.uint8)).all()
            assert (array_overlay[:,:,1] ==
                    numpy.require(array_g * alpha, numpy.uint8)).all()
            assert (array_overlay[:,:,2] ==
                    numpy.require(array_b * alpha, numpy.uint8)).all()

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

