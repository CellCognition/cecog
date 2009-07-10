package org.cecog.classifier.model
{
    import mx.collections.ArrayCollection;

    import org.cecog.classifier.model.vo.SampleVO;
    import org.puremvc.as3.interfaces.IProxy;
    import org.puremvc.as3.patterns.proxy.Proxy;

    public class SampleInfoProxy extends Proxy implements IProxy
    {
        public static var NAME:String = "SampleInfoProxy";

        public function SampleInfoProxy(proxyName:String=null, data:Object=null)
        {
            super(NAME, new ArrayCollection());
            var dummy:SampleVO = new SampleVO();
        }

        public function get sampleInfos(): ArrayCollection
        {
            return data as ArrayCollection;
        }

    }
}