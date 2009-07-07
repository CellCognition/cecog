"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__docformat__ = "epytext"
__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'


#------------------------------------------------------------------------------
# standard library imports:
#

import unittest
import os

#------------------------------------------------------------------------------
# extension module imports:
#
from pyvigra import (PIXEL_TYPECODES,
                     UInt16Image2d, 
                     Image2d)
#------------------------------------------------------------------------------
# cecog imports:
#
from cecog.core.imagecontainer import (DIMENSION_NAME_POSITION,
                                       DIMENSION_NAME_TIME,
                                       DIMENSION_NAME_CHANNEL,
                                       DIMENSION_NAME_ZSLICE,
                                       FileTokenImporter,
                                       ImageContainer)
from cecog.util.token import (Token,
                              TokenHandler)

#------------------------------------------------------------------------------
# constants:
#
DEMO_DATA_PATH = '/Users/miheld/data/CellCognition/demo_data' 

#------------------------------------------------------------------------------
# classes:
#

class TestCase(unittest.TestCase):

    EXPERIMENT_NAME = None
    POSITIONS = None
    TIMES = None
    CHANNELS = None
    ZSLICES = None
    WIDTH = 1392
    HEIGHT = 1040

    IMAGE_TYPE = None
    PIXEL_TYPE = None

    def setUp(self):
        self.image_container = None
    
    def test_iterator1(self):
        meta_data = self.image_container.meta_data
        
        # build flat list of dimension values
        flat_info = []
        for p in meta_data.positions:
            for t in meta_data.times:
                for c in meta_data.channels:
                    for z in meta_data.zslices:
                        flat_info.append((p, t, c, z))
        
        # loop over all images in scan-order
        for idx, meta_image in enumerate(self.image_container.iterator()):
            info = flat_info[idx]
            self.assertEqual(meta_image.position, info[0])
            self.assertEqual(meta_image.time, info[1])
            self.assertEqual(meta_image.channel, info[2])
            self.assertEqual(meta_image.zslice, info[3])

    def test_iteratior2(self):
        # some pylint error? image_container is callable
        # pylint: disable-msg=E1102  
        
        # a loop over the image_container with fixed position and interruption
        # on the channel-level: for every time an iterator is return for the
        # remaining meta-images in scan-order (channel & zslice)
        for idx1, (time, channel_iter) in \
            enumerate(self.image_container(position=self.POSITIONS[0],
                                           interrupt_channel=True)):
            self.assertEqual(self.TIMES[idx1], time)
            # loop over all channels and zslices (zslices are the innermost 
            # loop for that scan-order)
            for idx2, meta_image in enumerate(channel_iter):
               
                idx_c = idx2 / len(self.ZSLICES)
                idx_z = idx2 - idx_c * len(self.ZSLICES)
                self.assertEqual(self.CHANNELS[idx_c], meta_image.channel)
                self.assertEqual(self.ZSLICES[idx_z], meta_image.zslice)
                
                self.assertEqual(self.TIMES[idx1], meta_image.time)
                self.assertEqual(self.POSITIONS[0], meta_image.position)
                self.assertEqual(self.WIDTH, meta_image.width)
                self.assertEqual(self.HEIGHT, meta_image.height)
                
    def test_iteratior3(self):
        # some pylint error? image_container is callable
        # pylint: disable-msg=E1102  
        
        # a loop over the image_container with interruption on time, channel
        # and zslice-level: per position a new iterator over next dimension is
        # return (maximal unfolding of the dimension loop)
        
        for idx1, (position, time_iter) in \
            enumerate(self.image_container(interrupt_time=True,
                                           interrupt_channel=True,
                                           interrupt_zslice=True)):
            self.assertEqual(self.POSITIONS[idx1], position)
            
            for idx2, (time, channel_iter) in enumerate(time_iter):
                self.assertEqual(self.TIMES[idx2], time)
            
                for idx3, (channel, zslice_iter) in enumerate(channel_iter):
                    self.assertEqual(self.CHANNELS[idx3], channel)
                
                    for idx4, meta_image in enumerate(zslice_iter):
                        self.assertEqual(self.ZSLICES[idx4], meta_image.zslice)
                        
                        self.assertEqual(channel, meta_image.channel)
                        self.assertEqual(time, meta_image.time)
                        self.assertEqual(position, meta_image.position)
                
    def test_dimensions(self):
        meta_data = self.image_container.meta_data
        
        self.assertEqual(meta_data.dim_p, len(self.POSITIONS))
        self.assertEqual(meta_data.dim_t, len(self.TIMES))
        self.assertEqual(meta_data.dim_c, len(self.CHANNELS))
        self.assertEqual(meta_data.dim_z, len(self.ZSLICES))

        self.assertEqual(meta_data.positions, self.POSITIONS)
        self.assertEqual(meta_data.times, self.TIMES)
        self.assertEqual(meta_data.channels, self.CHANNELS)
        self.assertEqual(meta_data.zslices, self.ZSLICES)

    def test_lazy_load(self):
        # the protected variable '_img' holds and image only after the
        # public property 'image' was accessed (lazy read)
        for meta_image in self.image_container.iterator():
            # meta_image should have no image data yet!
            self.assertEqual(meta_image._img, None)

    def _test_images(self):
        # accesses all raw image data (time consuming!)
        for meta_image in self.image_container.iterator():
            self.assertTrue(isinstance(meta_image.image, self.IMAGE_TYPE))

class TokenTestCase(TestCase):
   
    TOKEN_P = Token('P', type_code='i', length='+', prefix='', 
                    name=DIMENSION_NAME_POSITION)
    TOKEN_T = Token('T', type_code='i', length='+', prefix='', 
                    name=DIMENSION_NAME_TIME)
    TOKEN_C = Token('C', type_code='c', length='+', prefix='', 
                    name=DIMENSION_NAME_CHANNEL)
    TOKEN_Z = Token('Z', type_code='i', length='+', prefix='', 
                    name=DIMENSION_NAME_ZSLICE)
        
    def setUp(self):
        simple_token = TokenHandler(separator='_')
        simple_token.register_token(self.TOKEN_P)
        simple_token.register_token(self.TOKEN_T)
        simple_token.register_token(self.TOKEN_C)
        simple_token.register_token(self.TOKEN_Z)
    
        importer = FileTokenImporter(os.path.join(DEMO_DATA_PATH,
                                                  self.EXPERIMENT_NAME),
                                     simple_token)
        
        self.image_container = ImageContainer(importer)

    def tearDown(self):
        pass

    
class Token1(TokenTestCase):
    
    EXPERIMENT_NAME = 'H2b_aTub_exp911'
    POSITIONS = (37,38)
    TIMES = (1,2,3,4,5,6,7,8,9,10)
    CHANNELS = ('gfp', 'rfp')
    ZSLICES = (1,)   
    IMAGE_TYPE = Image2d
    PIXEL_TYPE = PIXEL_TYPECODES.UINT8
    
class Token2(TokenTestCase):
    
    EXPERIMENT_NAME = 'H2b_GalT_exp835'
    POSITIONS = (55,56)
    TIMES = (1,2,3,4,5,6,7,8,9,10)
    CHANNELS = ('gfp', 'rfp')
    ZSLICES = (1,)
    IMAGE_TYPE = Image2d
    PIXEL_TYPE = PIXEL_TYPECODES.UINT8
    
class Token3(TokenTestCase):
    
    EXPERIMENT_NAME = 'H2b_Ibb_exp757'
    POSITIONS = (1,2)
    TIMES = (1,2,3,4,5,6,7,8,9,10)
    CHANNELS = ('gfp', 'rfp')
    ZSLICES = (1,)
    IMAGE_TYPE = Image2d
    PIXEL_TYPE = PIXEL_TYPECODES.UINT8

class Token4(TokenTestCase):
    
    EXPERIMENT_NAME = 'H2b_Pds1_exp547'
    POSITIONS = (1,2)
    TIMES = (1,2,3,4,5,6,7,8,9,10)
    CHANNELS = ('gfp', 'rfp')
    ZSLICES = (1,)
    IMAGE_TYPE = Image2d
    PIXEL_TYPE = PIXEL_TYPECODES.UINT8

class Token5(TokenTestCase):
    
    EXPERIMENT_NAME = 'H2b_PCNA_16bit'
    POSITIONS = (1,2)
    TIMES = (1,2,3,4,5,6,7,8,9,10)
    CHANNELS = ('gfp', 'rfp')
    ZSLICES = (1,)
    IMAGE_TYPE = UInt16Image2d
    PIXEL_TYPE = PIXEL_TYPECODES.UINT16

class Token6(TokenTestCase):
    
    EXPERIMENT_NAME = 'H2b_aTub_zeisslife'
    POSITIONS = (1,2)
    TIMES = (1,2,3,4,5,6,7,8,9,10)
    CHANNELS = ('1Rhod', '2EGFP')
    ZSLICES = (1,2,3,4,5)
    IMAGE_TYPE = UInt16Image2d
    PIXEL_TYPE = PIXEL_TYPECODES.UINT16
    
    WIDTH = 672
    HEIGHT = 512
    
    TOKEN_P = Token('s', type_code='i', length='+', prefix='', 
                    name=DIMENSION_NAME_POSITION)
    TOKEN_T = Token('t', type_code='i', length='+', prefix='', 
                    name=DIMENSION_NAME_TIME)
    TOKEN_C = Token('w', type_code='c', length='+', prefix='', 
                    name=DIMENSION_NAME_CHANNEL)


def create_suite():
    loader = unittest.TestLoader().loadTestsFromTestCase
    suite = unittest.TestSuite([loader(Token1),
                                loader(Token2),
                                loader(Token3),
                                loader(Token4),
                                loader(Token5),
                                loader(Token6),
                                ])
    return suite


if __name__ == "__main__":
    unittest.TextTestRunner().run(create_suite())

    