package org.cecog.classifier.controller.experiment
{
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.model.ExperimentProxy;
    import org.cecog.classifier.model.vo.ExperimentVO;
    import org.cecog.classifier.service.ExperimentDelegate;
    import org.cecog.classifier.view.ExperimentMediator;
    import org.cecog.classifier.service.ServiceLocator;

    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class GetImageViewBySelectionCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ExperimentDelegate = ServiceLocator.getInstance().experimentService;
            delegate.getImageViewBySelection(this, notification.getBody());
        }

        public function result(data: Object): void
        {
            var url:String = data.result as String;
            var experimentMediator:ExperimentMediator = facade.retrieveMediator(ExperimentMediator.NAME) as ExperimentMediator;
            experimentMediator.updateImage(url);
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}