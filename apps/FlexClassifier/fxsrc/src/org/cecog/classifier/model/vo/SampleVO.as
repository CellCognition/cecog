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

        public var map:Array;

        public function SampleVO()
        {
            this.map = new Array();
            if (this.coords != null)
            {
                var a:area = new area();
                //a.alt = 'moo';
                a.shape = 'POLY';
                a.coords = this.coords;
                this.map.push(a);
            }
       }
    }
}