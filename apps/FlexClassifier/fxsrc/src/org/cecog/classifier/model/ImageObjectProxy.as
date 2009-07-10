package org.cecog.classifier.model
{
    import mx.collections.ArrayCollection;

    import org.puremvc.as3.interfaces.IProxy;
    import org.puremvc.as3.patterns.proxy.Proxy;
    import org.cecog.classifier.model.vo.ImageObjectVO;

    public class ImageObjectProxy extends Proxy implements IProxy
    {
        public static var NAME:String = "ImageObjectProxy";

        public function ImageObjectProxy(proxyName:String=null, data:Object=null)
        {
            super(NAME, new ArrayCollection());
            // dummy class instance
            var dummy:ImageObjectVO = new ImageObjectVO();
        }

        public function get imageObjects(): ArrayCollection
        {
            return data as ArrayCollection;
        }

    }
}