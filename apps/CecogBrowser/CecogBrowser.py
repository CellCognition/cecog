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

__all__ = []

#------------------------------------------------------------------------------
# standard library imports:
#
import sys

#------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import (STYLESHEET_CARBON,
                            )
from cecog.gui.widgets.mainwindow import BrowserMainWindow

#------------------------------------------------------------------------------
# constants:
#


#------------------------------------------------------------------------------
# classes:
#


#------------------------------------------------------------------------------
# main:
#

if __name__ == "__main__":
    # PyQt resource files
    import cecog_browser_resources

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET_CARBON)
    app.setWindowIcon(QIcon(':cecog_browser_icon'))
    main = BrowserMainWindow()
    main.raise_()
    sys.exit(app.exec_())
