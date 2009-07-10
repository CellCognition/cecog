package org.cecog.classifier.model
{
    import mx.collections.ArrayCollection;

    import org.cecog.classifier.model.vo.ChannelVO;
    import org.cecog.classifier.model.vo.ExperimentVO;
    import org.cecog.classifier.model.vo.PositionVO;
    import org.puremvc.as3.interfaces.IProxy;
    import org.puremvc.as3.patterns.proxy.Proxy;

    public class ExperimentProxy extends Proxy implements IProxy
    {
        public static var NAME:String = "ExperimentProxy";

        public function ExperimentProxy(proxyName:String=null, data:Object=null)
        {
            super(NAME, new ArrayCollection());
            var dummy1:ExperimentVO = new ExperimentVO();
            var dummy2:PositionVO = new PositionVO();
            var dummy3:ChannelVO = new ChannelVO();
        }

        public function get experiments(): ArrayCollection
        {
            return data as ArrayCollection;
        }

    }
}