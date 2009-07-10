package org.cecog.classifier.view
{
    import mx.events.IndexChangedEvent;

    import org.cecog.classifier.view.components.ClassificationPanel;
    import org.puremvc.as3.interfaces.IMediator;
    import org.puremvc.as3.patterns.mediator.Mediator;

    public class ClassificationMediator extends Mediator implements IMediator
    {
        public static const NAME:String = 'ClassificationMediator';

        public function ClassificationMediator(viewComponent:Object)
        {
            super(NAME, viewComponent);
            panel.tabNavigator.addEventListener(IndexChangedEvent.CHANGE, onChildChange);
        }

        private function get panel(): ClassificationPanel
        {
            return viewComponent as ClassificationPanel;
        }

        public function setClassifierName(name:String): void
        {
            panel.currentClassifierName = name;
        }

        public function onChildChange(ev:IndexChangedEvent):void
        {
            var obj:Object = ev.relatedObject as Object;
            if (obj.id == "featurePanel")
            {
                var featureMediator:FeatureMediator = facade.retrieveMediator(FeatureMediator.NAME) as FeatureMediator;
                featureMediator.initFirst();
            }
            else if (obj.id == "classesPanel")
            {
                var classMediator:ClassMediator = facade.retrieveMediator(ClassMediator.NAME) as ClassMediator;
                classMediator.initFirst();
            }
        }

    }
}