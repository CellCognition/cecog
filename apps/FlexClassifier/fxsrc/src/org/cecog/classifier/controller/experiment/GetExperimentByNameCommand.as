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

    public class GetExperimentByNameCommand extends SimpleCommand implements ICommand, IResponder
    {

        override public function execute(notification:INotification):void
        {
            var delegate:ExperimentDelegate = ServiceLocator.getInstance().experimentService;
            delegate.getExperimentByName(this, notification.getBody() as String);
        }

        public function result(data: Object): void
        {
            var experiment:ExperimentVO = data.result as ExperimentVO;
            var experimentProxy:ExperimentProxy = facade.retrieveProxy(ExperimentProxy.NAME) as ExperimentProxy;

            for (var i:int=0; i < experimentProxy.experiments.length; i++)
                if (experimentProxy.experiments[i].name == experiment.name)
                    experimentProxy.experiments[i] = experiment;
            var experimentMediator:ExperimentMediator = facade.retrieveMediator(ExperimentMediator.NAME) as ExperimentMediator;
            experimentMediator.updateExperiment();
        }

        public function fault(info: Object): void
        {
            Alert.show((info as FaultEvent).toString());
        }

    }
}