package org.cecog.classifier.controller
{
    import mx.collections.ArrayCollection;
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.model.FeatureDataProxy;
    import org.cecog.classifier.service.ClassifierDelegate;
    import org.cecog.classifier.service.ServiceLocator;
    import org.cecog.classifier.view.FeatureMediator;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class GetFeatureDataCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ClassifierDelegate = ServiceLocator.getInstance().classifierService;
            delegate.getFeatureData(this, notification.getBody() as Array);
        }

        public function result(data: Object): void
        {
            var featureData:Array = data.result as Array;
            var featureDataProxy:FeatureDataProxy = facade.retrieveProxy(FeatureDataProxy.NAME) as FeatureDataProxy;
            featureDataProxy.featureData.source = featureData;
            var featureMediator:FeatureMediator = facade.retrieveMediator(FeatureMediator.NAME) as FeatureMediator;
            featureMediator.updatePlot();
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}