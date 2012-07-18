"""
                          The CellCognition Project
     Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
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
import os

#-------------------------------------------------------------------------------
# extension module imports:
#
import rpy2.robjects as robjects
import rpy2.rpy_classic as rpy
import rpy2.robjects.numpy2ri
rpy.set_default_mode(rpy.BASIC_CONVERSION)
r = rpy.r

#-------------------------------------------------------------------------------
# cecog imports:
#


#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class RPlotter(object):

    DCT_DEVICES = {'png' : (['png'], 'png',  None),
                   'pdf' : (['pdf'], 'pdf', 'cairo_pdf'),
                   'ps'  : (['ps'],  'postscript', 'cairo_ps'),
                   }

    def __init__(self, use_cairo=False):
        super(RPlotter, self).__init__()

        self.use_cairo = use_cairo
        #if self.bUseCairo:
        #    r.library("Cairo")

    def __getattr__(self, name):
        attr = getattr(robjects.r, name)
        return attr

    def rpy(self):
        return rpy

    def figure(self, filename=None, **dctOptions):
        strExt = os.path.splitext(filename)[1].lower()[1:]

        strDeviceName = None
        for strName, tlpDevice in self.DCT_DEVICES.iteritems():
            lstExt, strRAttr, strCairoAttr = tlpDevice
            if strExt in lstExt:
                strDeviceName = strName
                if self.use_cairo:
                    if strCairoAttr is None:
                        oDevice = getattr(robjects.r, strRAttr)
                        dctOptions['filename'] = filename
                        # MacOS default is 'quarz' which supports anti-aliasing
                        # and looks much nicer than cairo
                        #dctOptions['type'] = 'cairo'
                    else:
                        oDevice = getattr(robjects.r, strCairoAttr)
                        dctOptions['filename'] = filename
                else:
                    oDevice = getattr(robjects.r, strRAttr)
                    dctOptions['file'] = filename
                oDevice(**dctOptions)

        if strDeviceName is None:
            raise ValueError("R: Unknown file extension!")

    def close(self):
        robjects.r['dev.off']()


