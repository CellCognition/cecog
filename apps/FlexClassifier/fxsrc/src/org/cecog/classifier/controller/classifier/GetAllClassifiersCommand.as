package org.cecog.classifier.controller.classifier
{
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.model.ClassifierProxy;
    import org.cecog.classifier.service.ClassifierDelegate;
    import org.cecog.classifier.service.ServiceLocator;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class GetAllClassifiersCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ClassifierDelegate = ServiceLocator.getInstance().classifierService;
            delegate.getAll(this, notification.getBody() as Boolean);
        }

        public function result(data: Object): void
        {
            var classifierInfos:Array = data.result as Array;
            var classifierProxy:ClassifierProxy = facade.retrieveProxy(ClassifierProxy.NAME) as ClassifierProxy;
            //classifierInfos = classifierInfos.sort();
            classifierProxy.classifierInfos.source = classifierInfos;
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}