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

            var app:Classifier = notification.getBody() as Classifier;
            //facade.registerMediator(new ClassifierMediator(app.classifierPanel, app.classesPanel));
            //facade.registerMediator(new ClassMediator(app.classesPanel));
            //facade.registerMediator(new FeatureMediator(app.featurePanel));

            //facade.registerMediator(new SampleMediator(app.featurePanel));

            facade.registerMediator(new ExperimentMediator(app.experimentPanel));
            facade.registerMediator(new ClassificationMediator(app.classificationPanel));
        }

    }
}