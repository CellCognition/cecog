package org.cecog.classifier.view
{
    import flash.events.Event;

    import mx.events.ListEvent;

    import org.cecog.classifier.ClassifierFacade;
    import org.cecog.classifier.model.ClassProxy;
    import org.cecog.classifier.model.ClassifierProxy;
    import org.cecog.classifier.model.vo.ClassifierVO;
    import org.cecog.classifier.view.components.ClassesPanel;
    import org.cecog.classifier.view.components.ClassifiersPanel;
    import org.puremvc.as3.interfaces.IMediator;
    import org.puremvc.as3.patterns.mediator.Mediator;

    public class ClassifierMediator extends Mediator implements IMediator
    {
        private var __classifierProxy:ClassifierProxy;
        private var __classProxy:ClassProxy;
        private var __classesPanel:ClassesPanel;
        public static const NAME:String = 'ClassifierMediator';

        public function ClassifierMediator(viewComponentA:Object, viewComponentB:Object)
        {
            super(NAME, viewComponentA);

            panel.addEventListener(ClassifiersPanel.UPDATE_CLASSIFIERS, onUpdateClassifiers);
            panel.classifiersGrid.addEventListener(ListEvent.ITEM_CLICK, onGetClasses);

            __classifierProxy = facade.retrieveProxy(ClassifierProxy.NAME) as ClassifierProxy;
            __classProxy = facade.retrieveProxy(ClassProxy.NAME) as ClassProxy;

            // initialize view data:
            panel.classifierInfos = __classifierProxy.classifierInfos;
            panel.classInfos = __classProxy.classInfos;

            __classesPanel = viewComponentB as ClassesPanel;
        }

        // simple getter to prevent further casting
        private function get panel(): ClassifiersPanel
        {
            return viewComponent as ClassifiersPanel;
        }

        private function onUpdateClassifiers(ev:Event): void
        {
            trace('received event: onGetClassifiers');
            sendNotification(ClassifierFacade.GET_CLASSIFIERS_ALL, true);
        }

        private function onGetClasses(ev:ListEvent): void
        {
            trace('received event: onGetClasses');
            var classifierVO:ClassifierVO = ev.currentTarget.selectedItem as ClassifierVO;
            ClassifierFacade.getInstance().currentClassifierVO = classifierVO;
            var classificationMediator:ClassificationMediator = facade.retrieveMediator('ClassificationMediator') as ClassificationMediator;
            classificationMediator.setClassifierName(classifierVO.name);

            //panel.infoPanel.visible = true;
            panel.classifierInfoText.text = classifierVO.name;
            panel.classifierInfoGrid.visible = true;

            //__classesPanel.title = "Classes of '" + ev.label + "'";
            sendNotification(ClassifierFacade.GET_CLASSES_ALL, classifierVO.name);
            sendNotification(ClassifierFacade.GET_FEATURES_ALL, classifierVO.name);
        }
    }
}