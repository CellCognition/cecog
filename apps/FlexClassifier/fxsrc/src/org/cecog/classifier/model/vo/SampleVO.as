package org.cecog.classifier.model.vo
{
    import flash.display.Bitmap;

    import flexlib.controls.area;

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
        public var alpha:int = 1;
        public var color:uint;
        public var class_name:String;

        public var map:Array;
//
//        public function SampleVO(path:String, url:String, coords:String)
//        {
//            this.map = new Array();
//            if (this.coords != null)
//            {
//                var a:area = new area();
//                //a.alt = 'moo';
//                a.shape = 'POLY';
//                a.coords = this.coords;//'0,0,10,0,10,10,0,10';
//                this.map.push(a);
//            }
//       }
    }
}