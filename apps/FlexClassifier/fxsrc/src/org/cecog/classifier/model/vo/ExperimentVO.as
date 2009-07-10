package org.cecog.classifier.model.vo
{
    import mx.collections.ArrayCollection;

    [RemoteClass(alias="org.cecog.Experiment")]
    public class ExperimentVO
    {
        public var name:String;
        public var path:String;
        public var positions:Array;
        public var channels:Array;
        public var primary:String;

        public var dimX:int;
        public var dimY:int;
        public var dimT:int;
        public var dimC:int;
        public var dimZ:int;
        public var dimP:int;

        //public var url:String;
        //public var metaData:MetaDataVO;
    }
}