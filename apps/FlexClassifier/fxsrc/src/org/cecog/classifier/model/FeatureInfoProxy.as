package org.cecog.classifier.model
{
    import mx.collections.ArrayCollection;

    import org.puremvc.as3.interfaces.IProxy;
    import org.puremvc.as3.patterns.proxy.Proxy;
    import org.cecog.classifier.model.vo.FeatureVO;

    public class FeatureInfoProxy extends Proxy implements IProxy
    {
        public static var NAME:String = "FeatureInfoProxy";

        public function FeatureInfoProxy(proxyName:String=null, data:Object=null)
        {
            super(NAME, new ArrayCollection());
            var dummy:FeatureVO = new FeatureVO();
        }

        public function get featureInfos(): ArrayCollection
        {
            return data as ArrayCollection;
        }

    }
}