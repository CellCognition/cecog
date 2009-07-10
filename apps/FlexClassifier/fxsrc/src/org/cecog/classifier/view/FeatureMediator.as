package org.cecog.classifier.view
{
    import flash.events.Event;
    import flash.events.MouseEvent;

    import mx.charts.LinearAxis;
    import mx.charts.series.AreaSeries;
    import mx.charts.series.PlotSeries;
    import mx.controls.CheckBox;

    import org.cecog.classifier.ClassifierFacade;
    import org.cecog.classifier.model.ClassProxy;
    import org.cecog.classifier.model.FeatureDataProxy;
    import org.cecog.classifier.model.FeatureInfoProxy;
    import org.cecog.classifier.model.vo.ClassVO;
    import org.cecog.classifier.view.components.FeaturePanel;
    import org.puremvc.as3.interfaces.IMediator;
    import org.puremvc.as3.patterns.mediator.Mediator;

    public class FeatureMediator extends Mediator implements IMediator
    {
        private var __featureInfoProxy:FeatureInfoProxy;
        private var __featureDataProxy:FeatureDataProxy;
        private var __classProxy:ClassProxy;
        private var __xField:String;
        private var __yField:String;
        private var __numberOfFields:int;
        private var __hasNewData:Boolean = false;

        public static const NAME:String = 'FeatureMediator';

        public function FeatureMediator(viewComponent:Object)
        {
            super(NAME, viewComponent);

            panel.check1.addEventListener(MouseEvent.CLICK, onChangeCheck);
            panel.check2.addEventListener(MouseEvent.CLICK, onChangeCheck);

            panel.addEventListener(FeaturePanel.CHANGE_FEATURE_SELECTION, onGetFeatureData);
            panel.addEventListener(FeaturePanel.CHANGE_FEATURE_SELECTION, onGetFeatureData);

            __featureInfoProxy = facade.retrieveProxy(FeatureInfoProxy.NAME) as FeatureInfoProxy;
            __featureDataProxy = facade.retrieveProxy(FeatureDataProxy.NAME) as FeatureDataProxy;
            __classProxy = facade.retrieveProxy(ClassProxy.NAME) as ClassProxy;

            // initialize view data:
            panel.featureInfos = __featureInfoProxy.featureInfos;

        }

        // simple getter to prevent further casting
        private function get panel(): FeaturePanel
        {
            return viewComponent as FeaturePanel;
        }

        private function onChangeCheck(ev:Event): void
        {
            var target:CheckBox = ev.target as CheckBox;
            if (target == panel.check1)
            {
                if (!target.selected && !panel.feature2.enabled)
                {
                    ev.stopImmediatePropagation();
                    target.selected = true;
                }
                else
                    panel.feature1.enabled = target.selected;
            }
            else if (target == panel.check2)
            {
                if (!target.selected && !panel.feature1.enabled)
                {
                    ev.stopImmediatePropagation();
                    target.selected = true;
                }
                else
                    panel.feature2.enabled = target.selected;
            }
            setFeatureNames();
        }

        private function onGetFeatureData(ev:Event): void
        {
            setFeatureNames();
            panel.focusManager.showFocus();
        }

        private function setFeatureNames(): void
        {
            if (panel.feature1.enabled && panel.feature2.enabled)
            {
                __numberOfFields = 2;
                __xField = panel.feature1.selectedItem.name;
                __yField = panel.feature2.selectedItem.name;
                sendNotification(ClassifierFacade.GET_FEATURE_DATA, [__xField, __yField]);
            }
            else if (panel.feature1.enabled)
            {
                __numberOfFields = 1;
                __xField = panel.feature1.selectedItem.name;
                sendNotification(ClassifierFacade.GET_FEATURE_DATA, [__xField]);
            }
            else if (panel.feature2.enabled)
            {
                __numberOfFields = 1;
                __xField = panel.feature2.selectedItem.name;
                sendNotification(ClassifierFacade.GET_FEATURE_DATA, [__xField]);
            }
            else
                __numberOfFields = 0;
        }

        public function resetPlot():void
        {
            panel.plotChart.visible = false;
            panel.barChart.visible = false;
            panel.plotLegend.visible = false;
            __numberOfFields = 0;
            __xField = "";
            __yField = "";
        }

        public function reset():void
        {
            __hasNewData = true;
        }

        public function initFirst():void
        {
            if (__hasNewData)
            {
                __numberOfFields = 1;
                __xField = panel.feature1.selectedItem.name;
                panel.feature2.enabled = false;
                panel.check2.selected = false;
                sendNotification(ClassifierFacade.GET_FEATURE_DATA, [__xField]);
                __hasNewData = false;
            }
        }

        public function updatePlot(): void
        {
            if (__numberOfFields == 1)
            {
                panel.plotChart.visible = false;
                panel.barChart.visible = true;
                panel.plotLegend.dataProvider = panel.barChart;
                __updateHistogram();
            }
            else if (__numberOfFields == 2)
            {
                panel.plotChart.visible = true;
                panel.barChart.visible = false;
                panel.plotLegend.dataProvider = panel.plotChart;
                __updateScatter();
            }
            panel.plotLegend.visible = true;
        }

        private function __updateScatter(): void
        {
            panel.plotChart.series = [];
            var data:Array = [];

            for (var i:int=0; i < __classProxy.classInfos.length; i++)
            {
                var pS:PlotSeries = new PlotSeries();
                pS.alpha = 0.7;
                var oClass:ClassVO = __classProxy.classInfos.getItemAt(i) as ClassVO;
                pS.xField = __xField;
                pS.yField = __yField;
                pS.displayName = oClass.name;
                pS.setStyle("fill", oClass.color);
                pS.dataProvider = __featureDataProxy.featureData[i];
                panel.plotChart.series.push(pS);
            }
            var xAxis:LinearAxis = new LinearAxis();
            xAxis.autoAdjust = true;
            xAxis.baseAtZero = false;
            xAxis.title = __xField;
            panel.plotChart.horizontalAxis = xAxis;

            var yAxis:LinearAxis = new LinearAxis();
            yAxis.autoAdjust = true;
            yAxis.baseAtZero = false;
            yAxis.title = __yField;
            panel.plotChart.verticalAxis = yAxis;
        }

        private function __updateHistogram(): void
        {
            panel.barChart.series = [];
            var data:Array = [];

            for (var i:int=0; i < __classProxy.classInfos.length; i++)
            {
                var pS:AreaSeries = new AreaSeries();
                pS.alpha = 0.7;
                var oClass:ClassVO = __classProxy.classInfos.getItemAt(i) as ClassVO;
                pS.xField = 'x';
                pS.yField = 'y';
                pS.displayName = oClass.name;
                pS.setStyle("areaFill", oClass.color);
                pS.dataProvider = __featureDataProxy.featureData[i];
                panel.barChart.series.push(pS);
            }

            var xAxis:LinearAxis = new LinearAxis();
            xAxis.autoAdjust = true;
            xAxis.baseAtZero = false;
            xAxis.title = __xField;
            panel.barChart.horizontalAxis = xAxis;

            var yAxis:LinearAxis = new LinearAxis();
            yAxis.autoAdjust = true;
            yAxis.baseAtZero = true;
            yAxis.title = 'probability';
            panel.barChart.verticalAxis = yAxis;
        }

    }
}