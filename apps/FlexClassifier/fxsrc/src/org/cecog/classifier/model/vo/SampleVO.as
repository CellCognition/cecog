package org.cecog.classifier.model.vo
{
    import flash.display.Bitmap;

    import mx.collections.ArrayCollection;
    import mx.controls.Image;

    [RemoteClass(alias="org.cecog.Sample")]
    public class SampleVO
    {
        public var path:String;
        public var url:String;
        public var features:ArrayCollection;
        public var coords:String;
        public var bmp:Bitmap;
        public var img:Image;
    }
}