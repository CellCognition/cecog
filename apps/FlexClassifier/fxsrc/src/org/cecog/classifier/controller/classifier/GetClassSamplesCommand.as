package org.cecog.classifier.controller.classifier
{
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.view.ClassMediator;
    import org.cecog.classifier.model.SampleInfoProxy;
    import org.cecog.classifier.model.vo.ClassVO;
    import org.cecog.classifier.service.ClassifierDelegate;
    import org.cecog.classifier.service.ServiceLocator;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class GetClassSamplesCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ClassifierDelegate = ServiceLocator.getInstance().classifierService;
            delegate.getSampleInfos(this, notification.getBody() as ClassVO);
        }

        public function result(data: Object): void
        {
            var sampleInfos:Array = data.result as Array;
            var sampleInfoProxy:SampleInfoProxy = facade.retrieveProxy(SampleInfoProxy.NAME) as SampleInfoProxy;
            sampleInfoProxy.sampleInfos.source = sampleInfos;

            var classMediator:ClassMediator = facade.retrieveMediator(ClassMediator.NAME) as ClassMediator;
            classMediator.updateSamples();
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}