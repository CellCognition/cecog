package org.cecog.classifier.controller
{
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.model.FeatureInfoProxy;
    import org.cecog.classifier.service.ClassifierDelegate;
    import org.cecog.classifier.service.ServiceLocator;
    import org.cecog.classifier.view.FeatureMediator;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class GetAllFeatureInfosCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ClassifierDelegate = ServiceLocator.getInstance().classifierService;
            delegate.getFeatureInfos(this, notification.getBody() as String);
        }

        public function result(data: Object): void
        {
            var featureInfos:Array = data.result as Array;
            var featureProxy:FeatureInfoProxy = facade.retrieveProxy(FeatureInfoProxy.NAME) as FeatureInfoProxy;
            featureProxy.featureInfos.source = featureInfos;
            var featureMediator:FeatureMediator = facade.retrieveMediator(FeatureMediator.NAME) as FeatureMediator;
            featureMediator.reset();
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}