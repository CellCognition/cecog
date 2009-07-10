package org.cecog.classifier.model
{
    import mx.collections.ArrayCollection;

    import org.puremvc.as3.interfaces.IProxy;
    import org.puremvc.as3.patterns.proxy.Proxy;
    import org.cecog.classifier.model.vo.ClassVO;

    public class ClassProxy extends Proxy implements IProxy
    {
        public static var NAME:String = "ClassProxy";

        public function ClassProxy(proxyName:String=null, data:Object=null)
        {
            super(NAME, new ArrayCollection());
            // dummy class instance
            //var dummy:ClassVO = new ClassVO('',0,0,0);
        }

        public function get classInfos(): ArrayCollection
        {
            return data as ArrayCollection;
        }

    }
}