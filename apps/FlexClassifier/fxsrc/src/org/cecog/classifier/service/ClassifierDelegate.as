package org.cecog.classifier.service
{
    import mx.rpc.IResponder;
    import mx.rpc.remoting.mxml.RemoteObject;

    import org.cecog.classifier.ClassifierFacade;
    import org.cecog.classifier.model.vo.ClassVO;

    public class ClassifierDelegate
    {
        private var __service:RemoteObject;

        public function ClassifierDelegate()
        {
            __service = new RemoteObject("ClassifierService");
            __service.endpoint = "http://bcute:5000/gateway";
            //__service.endpoint = "http://cellcognition.org:5000/gateway";
            __service.showBusyCursor = true;
            __service.concurrency = "last";
        }

        public function getAll(responder:IResponder, update:Boolean=false): void
        {
            var call:Object = __service.getAll(update);
            call.addResponder(responder);
        }

        public function getClassInfos(responder:IResponder, name:String): void
        {
            var call:Object = __service.getClassInfos(name);
            call.addResponder(responder);
        }

        public function getFeatureInfos(responder:IResponder, name:String): void
        {
            var call:Object = __service.getFeatureInfos(name);
            call.addResponder(responder);
        }

        public function getSampleInfos(responder:IResponder, oClass:ClassVO): void
        {
            var classifierName:String = ClassifierFacade.getInstance().currentClassifierVO.name;
            var call:Object = __service.getSampleInfos(classifierName, oClass.name);
            call.addResponder(responder);
        }

        public function getFeatureData(responder:IResponder, featureNames:Array): void
        {
            var classifierName:String = ClassifierFacade.getInstance().currentClassifierVO.name;
            var call:Object = __service.getFeatureData(classifierName, featureNames);
            call.addResponder(responder);
        }
    }
}