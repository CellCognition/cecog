#!/usr/bin/env python
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

import os
import sys
import argparse
import traceback

from os.path import join
from multiprocessing import freeze_support

# use agg as long no Figure canvas will draw any qwidget
import matplotlib as mpl
mpl.use('Agg')

import sip
# set PyQt API version to 2.0
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QUrl', 2)

from PyQt4 import QtGui

try:
    # if some packages were not included in the bundle
    # especially sklearn
    try:
        import cecog
    except ImportError:
        sys.path.append(os.path.join(os.pardir, "pysrc"))
        import cecog

    from cecog.gui.main import CecogAnalyzer
    from cecog.io.imagecontainer import ImageContainer
    # compiled from qrc file
    import cecog.cecog_rc

except Exception as e:
    app = QtGui.QApplication(sys.argv)
    QtGui.QMessageBox.critical(None, "Error", traceback.format_exc())
    raise


def enable_eclipse_debuging():
    try:
        import pydevd
        pydevd.connected = True
        pydevd.settrace(suspend=False)
        print 'Thread enabled interactive eclipse debuging...'
    except:
        pass


if __name__ == "__main__":
    enable_eclipse_debuging()
    parser = argparse.ArgumentParser(description='CellCognition Analyzer GUI')
    parser.add_argument('-l', '--load', action='store_true', default=False,
                        help='Load structure file if a config was provied.')
    parser.add_argument('-c''--configfile', dest='configfile',
                        default=os.path.join("battery_package",
                                             "Settings", "demo_settings.conf"),
                        help='Load a config file. (default from battery package)')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='Run applicaton in debug mode')
    args, _ = parser.parse_known_args()

    freeze_support()


    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(':cecog_analyzer_icon'))
    app.setApplicationName(cecog.APPNAME)

    splash = QtGui.QSplashScreen(QtGui.QPixmap(':cecog_splash'))
    splash.show()

    is_bundled = hasattr(sys, 'frozen')
    if is_bundled:
        redirect = (sys.frozen == "windows_exe")
    else:
        redirect = False

    main = CecogAnalyzer(cecog.APPNAME, cecog.VERSION, redirect,  args.debug)
    main._read_settings(join(main.environ.user_config_dir, args.configfile))

    try:
        if (args.load and os.path.isfile(args.configfile)) or is_bundled:
            infos = list(ImageContainer.iter_check_plates(main._settings))
            main._load_image_container(infos, show_dlg=False)
    except Exception, e:
        msg = "Could not load images\n%s" %e.message
        QtGui.QMessageBox.critical(None, "Error", msg)

    main.show()
    splash.finish(main)
    sys.exit(app.exec_())
