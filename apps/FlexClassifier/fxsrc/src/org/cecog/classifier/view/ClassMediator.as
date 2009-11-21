package org.cecog.classifier.view
{
    import flash.events.Event;
    import flash.events.MouseEvent;
    import flexlib.controls.area;

    import mx.controls.SWFLoader;
    import mx.events.ItemClickEvent;
    import mx.events.SliderEvent;

    import org.cecog.classifier.ClassifierFacade;
    import org.cecog.classifier.model.ClassProxy;
    import org.cecog.classifier.model.SampleInfoProxy;
    import org.cecog.classifier.model.vo.ClassVO;
    import org.cecog.classifier.model.vo.SampleVO;
    import org.cecog.classifier.view.components.ClassesPanel;
    import org.puremvc.as3.interfaces.IMediator;
    import org.puremvc.as3.patterns.mediator.Mediator;

    public class ClassMediator extends Mediator implements IMediator
    {
        private var __classProxy:ClassProxy;
        private var __sampleInfoProxy:SampleInfoProxy;
        private var __hasNewData:Boolean = false;
        public static const NAME:String = 'ClassMediator';
        private var maxWidth:int = 0;
        private var maxHeight:int = 0;


        public function ClassMediator(viewComponent:Object)
        {
            super(NAME, viewComponent);

            panel.addEventListener(ClassesPanel.GET_CLASS_SAMPLES, onGetClassSamples);
            panel.scaleSlider.addEventListener(SliderEvent.CHANGE, onScaleSlide);
            panel.scaleButton.addEventListener(MouseEvent.CLICK, onScaleReset);

            __classProxy = facade.retrieveProxy(ClassProxy.NAME) as ClassProxy;
            __sampleInfoProxy = facade.retrieveProxy(SampleInfoProxy.NAME) as SampleInfoProxy;

            // initialize view data:
            panel.classInfos = __classProxy.classInfos;
            //classesPanel.sampleInfos = __sampleInfoProxy.sampleInfos;
        }

        // simple getter to prevent further casting
        private function get panel(): ClassesPanel
        {
            return viewComponent as ClassesPanel;
        }

        private function onGetClassSamples(ev:ItemClickEvent): void
        {
            trace('received event: onGetClass');
            sendNotification(ClassifierFacade.GET_CLASS_SAMPLES, ev.item);
        }

        public function reset():void
        {
            __hasNewData = true;
        }

        public function initFirst():void
        {
            if (__hasNewData)
            {
                __hasNewData = false;
                var classVO:ClassVO = __classProxy.classInfos[0];
                panel.classesGrid.selectedItem = classVO;
                sendNotification(ClassifierFacade.GET_CLASS_SAMPLES, classVO);
            }
        }

        public function updateSamples(): void
        {
            maxWidth = 0;
            maxHeight = 0;
            //var images:Array = [];
            //classesPanel.sampleImages = new ArrayCollection();
            for each (var sample:SampleVO in __sampleInfoProxy.sampleInfos)
            {
//                var img:SWFLoader = new SWFLoader();
//                img.addEventListener(Event.COMPLETE, onComplete);
//                img.load(sample.url);
//                //for each (var sample:SampleVO in sampleInfos)
//                //{
                    if (sample.coords != null)
                    {
                        sample.map = new Array();
                        var a:area = new area();
                        a.shape = 'POLY';
                        a.coords = sample.coords;
                        sample.map.push(a);
                    }
                //}
                //sampleInfoProxy.sampleInfos.source = sampleInfos;

                //var data:BitmapData = Bitmap(img.content
                //sample.bmp = Bitmap(img.content);

//                sample.bmp.addEventListener(Event.COMPLETE, onComplete);
//                sample.bmp.
                //sample.bmp.load(sample.url);
                //images.push(img.source);
                //sample.img = img;
            }
            //classesPanel.sampleImages = new ArrayCollection(images);
            panel.sampleInfos = __sampleInfoProxy.sampleInfos;
        }

        private function onComplete(ev:Event): void
        {
            //ev.target as
            maxWidth = Math.max(maxWidth, ev.target.contentWidth);
            maxHeight = Math.max(maxHeight, ev.target.contentHeight);
            panel.sampleGrid.columnWidth = maxWidth;
            panel.sampleGrid.rowHeight = maxHeight;
        }

        private function onScaleSlide(ev:SliderEvent):void
        {
            panel.sampleGrid.scaleX = ev.value;
            panel.sampleGrid.scaleY = ev.value;
            panel.scaleText.text = (ev.value*100).toFixed(1)+"%";
        }

        private function onScaleReset(ev:MouseEvent):void
        {
            panel.scaleSlider.value = 1.0;
            panel.sampleGrid.scaleX = 1.0;
            panel.sampleGrid.scaleY = 1.0;
            panel.scaleText.text = "100%";
        }

    }
}