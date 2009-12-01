"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
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

#------------------------------------------------------------------------------
# standard library imports:
#

#------------------------------------------------------------------------------
# extension modules:
#

#------------------------------------------------------------------------------
# classifier modules:
#
from classifier.lib.helpers import WSGIGateway
from classifier.services.classifierservice import ClassifierService
#from classifier.services.experimentservice import ExperimentService
#from classifier.services.analysisservice import AnalysisService

#------------------------------------------------------------------------------
#

services = {
    'ClassifierService' : ClassifierService('/Users/miheld/data/Classifiers'),
    #'AnalysisService'   : AnalysisService(),
    #'ExperimentService' : ExperimentService('/Volumes/RAID5-2/Flex'),
}

GatewayController = WSGIGateway(services)
