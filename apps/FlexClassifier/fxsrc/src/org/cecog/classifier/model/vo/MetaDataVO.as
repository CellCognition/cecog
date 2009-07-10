package org.cecog.classifier.model.vo
{
    import mx.collections.ArrayCollection;

    [RemoteClass(alias="org.cecog.MetaData")]
    public class MetaDataVO
    {
        public var positions:int;
        public var time:int;
        public var channels:int;
        public var zslices:int;
        public var width:int;
        public var height:int;
    }
}