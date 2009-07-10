package org.cecog.classifier
{
    import org.cecog.classifier.controller.*;
    import org.cecog.classifier.controller.analysis.*;
    import org.cecog.classifier.controller.classifier.*;
    import org.cecog.classifier.controller.experiment.*;
    import org.cecog.classifier.model.vo.ClassifierVO;
    import org.puremvc.as3.interfaces.IFacade;
    import org.puremvc.as3.patterns.facade.Facade;

    public class ClassifierFacade extends Facade implements IFacade
    {
        public static const APP_INIT:String = "APP_INIT";
        public static const CLASSIFICATION_INIT:String = "CLASSIFICATION_INIT";

        public static const GET_CLASSIFIERS_ALL:String = "GET_CLASSIFIERS_ALL";
        public static const UPDATE_CLASSIFIERS:String = "UPDATE_CLASSIFIERS";
        public static const GET_CLASSES_ALL:String = "GET_CLASSES_ALL";
        public static const GET_FEATURES_ALL:String = "GET_FEATURES_ALL";
        public static const GET_CLASS_SAMPLES:String = "GET_CLASS_SAMPLES";
        public static const GET_FEATURE_DATA:String = "GET_FEATURE_DATA";

        public static const GET_EXPERIMENTS_ALL:String = "GET_EXPERIMENTS_ALL";
        public static const GET_EXPERIMENT_BY_NAME:String = "GET_EXPERIMENT_BY_NAME";
        public static const GET_IMAGEVIEW_BY_SELECTION:String = "GET_IMAGEVIEW_BY_SELECTION";
        public static const DETECT_OBJECTS:String = "DETECT_OBJECTS";

        public static const START_ANALYSIS:String = "START_ANALYSIS";
        public static const LOOKUP_SERVER_PATH:String = "LOOKUP_SERVER_PATH";


        [Bindable]
        public var currentClassifierVO:ClassifierVO = null;

        // make a singleton
        public static function getInstance(): ClassifierFacade
        {
            if (instance == null)
                instance = new ClassifierFacade();
            return instance as ClassifierFacade;
        }

        // define the start-up
        override protected function initializeController(): void
        {
            super.initializeController();

            registerCommand(APP_INIT, InitAppCommand);
            registerCommand(CLASSIFICATION_INIT, InitClassificationCommand);

            registerCommand(GET_CLASSIFIERS_ALL, GetAllClassifiersCommand);
            registerCommand(GET_CLASSES_ALL, GetAllClassesCommand);
            registerCommand(GET_FEATURES_ALL, GetAllFeatureInfosCommand);
            registerCommand(GET_CLASS_SAMPLES, GetClassSamplesCommand);
            registerCommand(GET_FEATURE_DATA, GetFeatureDataCommand);

            registerCommand(GET_EXPERIMENTS_ALL, GetAllExperimentsCommand);
            registerCommand(GET_EXPERIMENT_BY_NAME, GetExperimentByNameCommand);
            registerCommand(GET_IMAGEVIEW_BY_SELECTION, GetImageViewBySelectionCommand);
            registerCommand(DETECT_OBJECTS, DetectObjectsCommand);

            //registerCommand(START_ANALYSIS, StartAnalysisCommand);
            //registerCommand(LOOKUP_SERVER_PATH, LookupServerPathCommand);
        }

    }
}