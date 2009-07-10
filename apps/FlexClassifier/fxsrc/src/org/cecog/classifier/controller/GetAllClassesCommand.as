package org.cecog.classifier.controller
{
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.model.ClassProxy;
    import org.cecog.classifier.model.ClassifierProxy;
    import org.cecog.classifier.service.ClassifierDelegate;
    import org.cecog.classifier.service.ServiceLocator;
    import org.cecog.classifier.view.FeatureMediator;
    import org.cecog.classifier.view.ClassMediator;
    import org.cecog.classifier.model.SampleInfoProxy;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class GetAllClassesCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ClassifierDelegate = ServiceLocator.getInstance().classifierService;
            delegate.getClassInfos(this, notification.getBody() as String);
        }

        public function result(data: Object): void
        {
            var classInfos:Array = data.result as Array;
            var classProxy:ClassProxy = facade.retrieveProxy(ClassProxy.NAME) as ClassProxy;
            classProxy.classInfos.source = classInfos;
            var sampleInfoProxy:SampleInfoProxy = facade.retrieveProxy(SampleInfoProxy.NAME) as SampleInfoProxy;
            sampleInfoProxy.sampleInfos.removeAll();
            var classMediator:ClassMediator = facade.retrieveMediator(ClassMediator.NAME) as ClassMediator;
            classMediator.reset();

            //var featureMediator:FeatureMediator = facade.retrieveMediator(FeatureMediator.NAME) as FeatureMediator;
            //featureMediator.resetPlot();
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}