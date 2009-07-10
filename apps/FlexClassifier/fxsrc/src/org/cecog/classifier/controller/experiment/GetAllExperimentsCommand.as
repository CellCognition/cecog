package org.cecog.classifier.controller.experiment
{
    import mx.controls.Alert;
    import mx.rpc.IResponder;
    import mx.rpc.events.FaultEvent;

    import org.cecog.classifier.model.ExperimentProxy;
    import org.cecog.classifier.service.ExperimentDelegate;
    import org.cecog.classifier.service.ServiceLocator;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class GetAllExperimentsCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ExperimentDelegate = ServiceLocator.getInstance().experimentService;
            delegate.getAll(this);
        }

        public function result(data: Object): void
        {
            var experiments:Array = data.result as Array;
            var experimentProxy:ExperimentProxy = facade.retrieveProxy(ExperimentProxy.NAME) as ExperimentProxy;
            experimentProxy.experiments.source = experiments;
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}