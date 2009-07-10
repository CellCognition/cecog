from classifier.tests import *

class TestGatewayController(TestController):

    def test_index(self):
        response = self.app.get(url_for(controller='gateway'))
        # Test response...
