package org.cecog.classifier.controller
{
    import org.cecog.classifier.model.*;
    import org.cecog.classifier.view.*;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class InitAppCommand extends SimpleCommand implements ICommand
    {
        override public function execute(notification:INotification):void
        {
            facade.registerProxy(new ExperimentProxy());
            facade.registerProxy(new ImageObjectProxy());

            var app:FlexClassifier = notification.getBody() as FlexClassifier;

            //facade.registerMediator(new ExperimentMediator(app.experimentPanel));
            facade.registerMediator(new ClassificationMediator(app.classificationPanel));
            //facade.registerMediator(new AnalysisMediator(app.analysisPanel));
        }

    }
}