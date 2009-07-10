"""
"""

__docformat__ = "epytext"

__author__ = "Michael Held"
__date__ = "$Date:2008-10-25 01:08:32 +0200 (Sat, 25 Oct 2008) $"
__revision__ = "$Rev:117 $"
__source__ = "$URL::                                                           $"


#------------------------------------------------------------------------------
# standard modules:
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
    'ClassifierService' : ClassifierService('/Volumes/Data1T/Classifiers'),
    #'AnalysisService'   : AnalysisService(),
    #'ExperimentService' : ExperimentService('/Volumes/RAID5-2/Flex'),
}

GatewayController = WSGIGateway(services)
