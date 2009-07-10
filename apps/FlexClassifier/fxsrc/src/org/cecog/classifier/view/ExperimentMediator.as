package org.cecog.classifier.view
{
    import flash.events.Event;

    import flexlib.controls.area;

    import mx.events.ItemClickEvent;

    import org.cecog.classifier.ClassifierFacade;
    import org.cecog.classifier.model.ClassProxy;
    import org.cecog.classifier.model.ExperimentProxy;
    import org.cecog.classifier.model.ImageObjectProxy;
    import org.cecog.classifier.model.vo.ChannelVO;
    import org.cecog.classifier.model.vo.ExperimentVO;
    import org.cecog.classifier.model.vo.ImageObjectVO;
    import org.cecog.classifier.view.components.ExperimentPanel;
    import org.puremvc.as3.interfaces.IMediator;
    import org.puremvc.as3.patterns.mediator.Mediator;

    public class ExperimentMediator extends Mediator implements IMediator
    {
        private var __experimentProxy:ExperimentProxy;
        private var __imageObjectProxy:ImageObjectProxy;
        private var __classProxy:ClassProxy;

        private var __experimentIndex:int;
        private var __imageViewWidth:int;
        private var __imageViewHeight:int;
        private var __hasExperimentImage:Boolean = false;

        public static const NAME:String = 'ExperimentMediator';

        public function ExperimentMediator(viewComponent:Object)
        {
            super(NAME, viewComponent);

            experimentPanel.addEventListener(ExperimentPanel.GET_EXPERIMENT_BY_NAME, __onGetExperimentByName);
            experimentPanel.addEventListener(ExperimentPanel.SLIDER_CHANGED, __onSliderChanged);
            experimentPanel.addEventListener(ExperimentPanel.IMAGEVIEW_SCALE_CHANGED, __onImageViewScaleChanged);
            experimentPanel.addEventListener(ExperimentPanel.DETECT_OBJECTS, __onDetectObjects);

            experimentPanel.imageView.addEventListener(Event.COMPLETE, __onImageComplete);

            __experimentProxy = facade.retrieveProxy(ExperimentProxy.NAME) as ExperimentProxy;
            __imageObjectProxy = facade.retrieveProxy(ImageObjectProxy.NAME) as ImageObjectProxy;
            __classProxy = facade.retrieveProxy(ClassProxy.NAME) as ClassProxy;

            // initialize view data:
            experimentPanel.experiments = __experimentProxy.experiments;
            experimentPanel.classInfos = __classProxy.classInfos;
        }

        // simple getter to prevent further casting
        private function get experimentPanel(): ExperimentPanel
        {
            return viewComponent as ExperimentPanel;
        }

        private function __onGetExperimentByName(ev:ItemClickEvent): void
        {
            __experimentIndex = ev.index;
            var experiment:ExperimentVO = ev.item as ExperimentVO;
            sendNotification(ClassifierFacade.GET_EXPERIMENT_BY_NAME, experiment.name);
        }

        private function __onSliderChanged(ev:Event):void
        {
            getImageView();
        }

        private function __onImageViewScaleChanged(ev:Event):void
        {
//            var widthNew:int = experimentPanel.imageView.contentWidth * experimentPanel.sliderScale.value;
//            var heightNew:int = experimentPanel.imageView.contentHeight * experimentPanel.sliderScale.value;
//
//            if (widthNew >= experimentPanel.viewCanvas.width &&
//                heightNew >= experimentPanel.viewCanvas.height)
//            {
                var widthOld:int = experimentPanel.imageView.measuredWidth;
                var heightOld:int = experimentPanel.imageView.measuredHeight;

                var scale:Number = experimentPanel.sliderScale.value / 100.0;

                experimentPanel.imageView.scaleX = scale;
                experimentPanel.imageView.scaleY = scale;
                __imageViewWidth = experimentPanel.imageView.contentWidth*scale;
                __imageViewHeight = experimentPanel.imageView.contentHeight*scale;

                var correctX:int = (__imageViewWidth-widthOld) / 2.0;
                    //(2.0 * ((experimentPanel.imageView.x-experimentPanel.viewCanvas.x) / ((experimentPanel.imageView.x+experimentPanel.imageView.width)-(experimentPanel.viewCanvas.x+experimentPanel.viewCanvas.width))));
                experimentPanel.imageView.x -= correctX;
//                if (experimentPanel.imageView.x-correctX > experimentPanel.viewCanvas.x)
//                    experimentPanel.imageView.x = experimentPanel.viewCanvas.x;
//                else if (experimentPanel.imageView.x + __imageViewWidth - correctX < experimentPanel.viewCanvas.x + experimentPanel.viewCanvas.width)
//                    experimentPanel.imageView.x = experimentPanel.viewCanvas.x + experimentPanel.viewCanvas.width - __imageViewWidth;
//                else experimentPanel.imageView.x -= correctX;
                var correctY:int = (__imageViewHeight-heightOld) / 2.0;
                experimentPanel.imageView.y -= correctY;
//                if (experimentPanel.imageView.y-correctY > experimentPanel.viewCanvas.y)
//                    experimentPanel.imageView.y = experimentPanel.viewCanvas.y;
//                else if (experimentPanel.imageView.y + __imageViewHeight - correctY < experimentPanel.viewCanvas.y + experimentPanel.viewCanvas.height)
//                    experimentPanel.imageView.y = experimentPanel.viewCanvas.y + experimentPanel.viewCanvas.height - __imageViewHeight;
//                else experimentPanel.imageView.y -= correctY;
//            } else
//            {
//                experimentPanel.sliderScale.value = experimentPanel.imageView.scaleX;
//                ev.stopImmediatePropagation();
//            }
        }

        private function __onImageComplete(ev:Event):void
        {
            if (!__hasExperimentImage)
            {
                __imageViewWidth = experimentPanel.imageView.contentWidth;
                __imageViewHeight = experimentPanel.imageView.contentHeight;
                experimentPanel.imageView.x = 0;
                experimentPanel.imageView.y = 0;
                experimentPanel.imageView.scaleX = 1.0;
                experimentPanel.imageView.scaleY = 1.0;
                experimentPanel.sliderScale.value = 100;
                __hasExperimentImage = true;
            }
        }

        private function __onDetectObjects(ev:Event):void
        {
            detectObjects();
        }

        public function getImageView():void
        {
           var experiment:ExperimentVO = __experimentProxy.experiments[__experimentIndex];
           var selection:Object = { //P:experimentPanel.sliderP.value,
                                    P:experimentPanel.positionsGrid.selectedItem.name,
                                    T:experimentPanel.sliderT.value,
                                    Z:experimentPanel.sliderZ.value,
                                    C:experimentPanel.channelsGrid.selectedItem as ChannelVO
                                  };
           sendNotification(ClassifierFacade.GET_IMAGEVIEW_BY_SELECTION, selection);
        }

        public function detectObjects():void
        {
            experimentPanel.imageView.map = null;
            if (experimentPanel.detectObjects.selected)
                sendNotification(ClassifierFacade.DETECT_OBJECTS);
        }

        public function updateExperiment():void
        {
            var experiment:ExperimentVO = __experimentProxy.experiments[__experimentIndex];
            experimentPanel.positionsGrid.dataProvider = experiment.positions;
            experimentPanel.positionsGrid.selectedIndex = 0;

            experimentPanel.channelsGrid.dataProvider = experiment.channels;
            var selection:int = 0;
            for (var i:int=0; i < experiment.channels.length; i++)
                if (experiment.channels[i].name == experiment.primary)
                {
                    selection = i;
                    break;
                }
            experimentPanel.channelsGrid.selectedIndex = selection;

            updateMetaData();
            getImageView();
        }

        public function updateMetaData():void
        {
            var experiment:ExperimentVO = __experimentProxy.experiments[__experimentIndex];
            experimentPanel.labelID.text = String(experiment.name);
            experimentPanel.labelP.text = String(experiment.dimP);
            experimentPanel.labelT.text = String(experiment.dimT);
            experimentPanel.labelC.text = String(experiment.dimC);
            experimentPanel.labelZ.text = String(experiment.dimZ);
            experimentPanel.labelX.text = String(experiment.dimX);
            experimentPanel.labelY.text = String(experiment.dimY);

            experimentPanel.sliderZ.minimum = 1;
            experimentPanel.sliderZ.maximum = experiment.dimZ;
            experimentPanel.sliderZ.labels = ["1"]
            experimentPanel.sliderZ.value = 1;

            experimentPanel.sliderT.minimum = 1;
            experimentPanel.sliderT.maximum = experiment.dimT;
            experimentPanel.sliderT.value = 1;

//            experimentPanel.sliderP.minimum = 1;
//            experimentPanel.sliderP.maximum = experiment.dimP;
//            experimentPanel.sliderP.value = 1;

            __hasExperimentImage = false;
        }

        public function updateImage(url:String):void
        {
            //experimentPanel.imageView.se
            experimentPanel.imageView.load(url);
            detectObjects();
        }

        public function updateObjects():void
        {
            var map:Array = [];
            for each (var imgObj:ImageObjectVO in __imageObjectProxy.imageObjects)
            {
                var item:area = new area();
                item.shape = 'POLY';
                item.coords = imgObj.coords;
                item.alt = imgObj.id.toString();
                map.push(item);
            }
            experimentPanel.imageView.map = map;
        }

    }
}