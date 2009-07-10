package org.cecog.classifier.controller
{
    import mx.collections.ArrayCollection;
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.service.ExperimentDelegate;
    import org.cecog.classifier.model.ImageObjectProxy;
    import org.cecog.classifier.service.ServiceLocator;
    import org.cecog.classifier.view.ExperimentMediator;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class DetectObjectsCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ExperimentDelegate = ServiceLocator.getInstance().experimentService;
            delegate.detectObjects(this);
        }

        public function result(data: Object): void
        {
            var imageObjects:Array = data.result as Array;
            var imageObjectProxy:ImageObjectProxy = facade.retrieveProxy(ImageObjectProxy.NAME) as ImageObjectProxy;
            imageObjectProxy.imageObjects.source = imageObjects;
            var experimentMediator:ExperimentMediator = facade.retrieveMediator(ExperimentMediator.NAME) as ExperimentMediator;
            experimentMediator.updateObjects();
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}