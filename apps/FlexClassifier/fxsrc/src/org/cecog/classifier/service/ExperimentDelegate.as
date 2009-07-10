package org.cecog.classifier.service
{
    import mx.rpc.IResponder;
    import mx.rpc.remoting.mxml.RemoteObject;

    //import org.cecog.classifier.ClassifierFacade;
    //import org.cecog.classifier.model.vo.ClassVO;

    public class ExperimentDelegate
    {
        private var __service:RemoteObject;

        public function ExperimentDelegate()
        {
            __service = new RemoteObject("ExperimentService");
            __service.endpoint = "http://bcgerlich08:5000/gateway";
            __service.showBusyCursor = true;
            __service.concurrency = "last";
        }

        public function getAll(responder:IResponder): void
        {
            var call:Object = __service.getAll();
            call.addResponder(responder);
        }

        public function getExperimentByName(responder:IResponder, name:String): void
        {
            var call:Object = __service.getExperimentByName(name);
            call.addResponder(responder);
        }

        public function getImageViewBySelection(responder:IResponder, selection:Object): void
        {
            var call:Object = __service.getImageViewBySelection(selection);
            call.addResponder(responder);
        }

        public function detectObjects(responder:IResponder): void
        {
            var call:Object = __service.detectObjects();
            call.addResponder(responder);
        }
    }
}