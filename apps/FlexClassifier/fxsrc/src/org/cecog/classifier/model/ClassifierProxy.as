package org.cecog.classifier.model
{
    import mx.collections.ArrayCollection;

    import org.puremvc.as3.interfaces.IProxy;
    import org.puremvc.as3.patterns.proxy.Proxy;
    import org.cecog.classifier.model.vo.ClassifierVO;

    public class ClassifierProxy extends Proxy implements IProxy
    {
        public static var NAME:String = "ClassifierProxy";

        public function ClassifierProxy(proxyName:String=null, data:Object=null)
        {
            super(NAME, new ArrayCollection());
        }

        public function get classifierInfos(): ArrayCollection
        {
            return data as ArrayCollection;
        }

    }
}