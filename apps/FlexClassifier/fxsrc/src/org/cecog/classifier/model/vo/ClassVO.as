package org.cecog.classifier.model.vo
{
    import mx.collections.ArrayCollection;

    [RemoteClass(alias="org.cecog.Class")]
    public class ClassVO
    {
        public var name:String;
        public var label:int;
        public var samples:int;
        //public var samples:ArrayCollection;
        public var color:uint;
        public var oClassifier:ClassifierVO;
        public var features:Array;

//        public function ClassVO(name:String, label:int, samples:int, color:uint)
//        {
//            this.name = name;
//            this.label = label;
//            this.samples = samples;
//            this.color = color;
//        }
    }
}