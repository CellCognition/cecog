"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2012 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                             See LICENSE.txt for details.
                  See AUTHORS.txt for author contributions.


pkginfo.py - distutils metadata (since python 2.7 does not support distutils2)
"""

__author__ = 'rudolf.hoefler@gmail.com'

__all__ = ['metadata']

from cecog import VERSION_NUM, VERSION

metadata = { 'name': 'CecogAnalyzer',
             'version': VERSION,
             'author': 'Michael Held',
             'author_email': 'held(at)cellcognition.org',
             'maintainer': 'Christoph Sommer, Rudolf Hoefler',
             'maintainer_email' : ( 'christop.sommer@imba.oeaw.ac.at, '
                                  'rudolf.hoefler@imba.oeaw.ac.at' ),
             'license': 'LGPL',
             'description': ('CecogAnalyzer is a cross-platform standalone graphical '
                             'user interface for the time-resolved analysis of '
                             'single cells.'),
             'long_description': ('The CecogAnalyzer is a stand-alone application built'
                                  ' on top of the CellCognition framework. A graphical'
                                  ' user interface provides a comfortable setup and'
                                  ' parameterization of the analysis workflow.'
                                  '\n\nFeatures are:\n\n'
                                  '   *) Object detection\n'
                                  '   *) Feature extraction\n'
                                  '   *) Classification\n'
                                  '   *) Tracking of individual cells over time '
                                  '      Detection of class-transition motifs '
                                  '      (e.g. cells entering mitosis).\n'
                                  '   *) Correction of classification errors on \n'
                                  '      the detected event tracks.\n'
                                  '   *) The workflow can either be executed either on '
                                  '      the local computer or as a batch process on '
                                  '      any luster environment.'),
             'url': 'http://www.cellcognition.org',
             'download_url': 'http://www.cellcognition.org./download',
             'platforms': ['Win32', 'Linux', 'Mac OS-X'],
             'provides': ['cecog'] }
