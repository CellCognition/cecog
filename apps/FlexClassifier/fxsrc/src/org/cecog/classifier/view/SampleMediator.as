package org.cecog.classifier.view
{
    import mx.events.ItemClickEvent;

    import org.cecog.classifier.ClassifierFacade;
    import org.cecog.classifier.model.ClassProxy;
    import org.cecog.classifier.view.components.ClassesPanel;
    import org.puremvc.as3.interfaces.IMediator;
    import org.puremvc.as3.patterns.mediator.Mediator;
    import org.cecog.classifier.model.vo.ClassVO;

    public class SampleMediator extends Mediator implements IMediator
    {
        private var __classProxy:ClassProxy;
        public static const NAME:String = 'SampleMediator';

        public function SampleMediator(viewComponent:Object)
        {
            super(NAME, viewComponent);

            //classesPanel.addEventListener(ClassesPanel.GET_CLASS_SAMPLES, onGetClassSamples);

            __classProxy = facade.retrieveProxy(ClassProxy.NAME) as ClassProxy;

            // initialize view data:
            classesPanel.classInfos = __classProxy.classInfos;
        }

        // simple getter to prevent further casting
        private function get classesPanel(): ClassesPanel
        {
            return viewComponent as ClassesPanel;
        }

        private function onGetClassSamples(ev:ItemClickEvent): void
        {
            trace('received event: onGetClass');
            sendNotification(ClassifierFacade.GET_CLASS_SAMPLES, ev.item);
        }
        
        public function update():void
        {
            
        }

    }
}