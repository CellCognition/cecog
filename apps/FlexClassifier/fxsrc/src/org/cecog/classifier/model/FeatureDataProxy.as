package org.cecog.classifier.model
{
    import mx.collections.ArrayCollection;

    import org.puremvc.as3.interfaces.IProxy;
    import org.puremvc.as3.patterns.proxy.Proxy;

    public class FeatureDataProxy extends Proxy implements IProxy
    {
        public static var NAME:String = "FeatureDataProxy";

        public function FeatureDataProxy(proxyName:String=null, data:Object=null)
        {
            super(NAME, new ArrayCollection());
        }

        public function get featureData(): ArrayCollection
        {
            return data as ArrayCollection;
        }

    }
}