package org.cecog.classifier.controller
{
    import org.cecog.classifier.model.*;
    import org.cecog.classifier.view.*;
    import org.cecog.classifier.view.components.ClassificationPanel;
    import org.puremvc.as3.interfaces.ICommand;
    import org.puremvc.as3.interfaces.INotification;
    import org.puremvc.as3.patterns.command.SimpleCommand;

    public class InitClassificationCommand extends SimpleCommand implements ICommand
    {
        override public function execute(notification:INotification):void
        {
            facade.registerProxy(new ClassifierProxy());
            facade.registerProxy(new ClassProxy());
            facade.registerProxy(new FeatureInfoProxy());
            facade.registerProxy(new FeatureDataProxy());
            facade.registerProxy(new SampleInfoProxy());

            var panel:ClassificationPanel = notification.getBody() as ClassificationPanel;
            facade.registerMediator(new ClassifierMediator(panel.classifierPanel, panel.classesPanel));
            facade.registerMediator(new ClassMediator(panel.classesPanel));
            facade.registerMediator(new FeatureMediator(panel.featurePanel));

        }

    }
}