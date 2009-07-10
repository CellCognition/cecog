package org.cecog.classifier.service
{
    public class ServiceLocator
    {
        public var classifierService:ClassifierDelegate;
        public var experimentService:ExperimentDelegate;

        private static var __instance : ServiceLocator;

        public function ServiceLocator()
        {
            if (__instance != null)
                throw new Error("Singleton already instantiated");
            classifierService = new ClassifierDelegate();
            experimentService = new ExperimentDelegate();
        }

        public static function getInstance(): ServiceLocator
        {
            if (__instance == null)
                __instance = new ServiceLocator();
            return __instance
        }

    }
}