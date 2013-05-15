/*******************************************************************************

                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL$

#ifndef CECOG_PYTHON_WRAP_SEGMENTATION_HXX_
#define CECOG_PYTHON_WRAP_SEGMENTATION_HXX_

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>

#include "cecog/seededregion.hxx"
#include "cecog/segmentation.hxx"
#include "cecog/thresholds.hxx"
#include "vigra/python_utility.hxx"

using namespace boost::python;

namespace cecog
{
  namespace python
  {
    template <class IMAGE>
    void pyHoleFilling(IMAGE & img_bin, bool eightneigborhood=false)
    {
       vigra::PyAllowThreads _pythread;
       cecog::holeFilling(img_bin, eightneigborhood);
    }

    template <class IMAGE1, class IMAGE2>
    PyObject * pyDiscMedian(IMAGE1 const &imgIn, int radius)
    {
      vigra::PyAllowThreads _pythread;
      std::auto_ptr< IMAGE2 > imgPtr(new IMAGE2(imgIn.size()));
      vigra::discMedian(srcImageRange(imgIn), destImage(*imgPtr), radius);
      return incref(object(imgPtr).ptr());
    }

    template <class IMAGE1, class IMAGE2>
    PyObject * pyThreshold(IMAGE1 const &imgIn,
                           typename IMAGE1::PixelType lower,
                           typename IMAGE1::PixelType higher,
                           typename IMAGE2::PixelType noresult,
                           typename IMAGE2::PixelType yesresult)
    {
      vigra::PyAllowThreads _pythread;
      std::auto_ptr< IMAGE2 > imgPtr(new IMAGE2(imgIn.size()));
      vigra::transformImage(srcImageRange(imgIn), destImage(*imgPtr),
                            vigra::Threshold<typename IMAGE1::PixelType,
                                             typename IMAGE2::PixelType>
                            (lower, higher, noresult, yesresult));
      return incref(object(imgPtr).ptr());
    }

    template <class IMAGE1, class IMAGE2>
    PyObject * pyToggleMapping(IMAGE1 const &imgIn, int size)
    {
	  vigra::PyAllowThreads _pythread;
      std::auto_ptr< IMAGE2 > imgPtr(new IMAGE2(imgIn.size()));
      using namespace cecog::morpho;
      structuringElement2D se(WITHCENTER8, size);
      ImFastToggleMapping(srcImageRange(imgIn), destImage(*imgPtr), se);
      return incref(object(imgPtr).ptr());
    }

    template <class IMAGE1, class IMAGE2>
    unsigned int pyLabelImage(IMAGE1 const & img1,
                              IMAGE2 & img2,
                              bool eightNbh, typename IMAGE1::PixelType background)
    {
      vigra::PyAllowThreads _pythread;
      return vigra::labelImageWithBackground(srcImageRange(img1),
                                             destImage(img2),
                                             eightNbh,
                                             background);
    }

    vigra::UInt8 pyOtsuThreshold(vigra::UInt8Image const &img)
    {
      vigra::PyAllowThreads _pythread;
      typedef FindHistogram<vigra::UInt8> histogram;
      histogram f(255);
      vigra::inspectImage(srcImageRange(img), f);
      return otsuThreshold(f.probabilities());
    }

    template <class Image1, class Image2>
    PyObject * pyWindowAverageThreshold(Image1 const &imgIn,
                                        unsigned size,
                                        typename Image1::value_type contrastLimit=vigra::NumericTraits<typename Image1::value_type>::zero(),
                                        typename Image1::value_type lower=vigra::NumericTraits<typename Image1::value_type>::min(),
                                        typename Image1::value_type higher=vigra::NumericTraits<typename Image1::value_type>::max())
    {
	  vigra::PyAllowThreads _pythread;
      std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
      cecog::windowAverageThreshold(imgIn, *imgPtr, size, contrastLimit, lower, higher);
      return incref(object(imgPtr).ptr());
    }

    template <class Image1, class Image2>
    PyObject * pyWindowStdThreshold(Image1 const &imgIn,
                                    unsigned size,
                                    float threshold,
                                    typename Image1::value_type contrastLimit=vigra::NumericTraits<typename Image1::value_type>::zero())
    {
	  vigra::PyAllowThreads _pythread;
      std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
      cecog::windowStdThreshold(imgIn, *imgPtr, size, threshold, contrastLimit);
      return incref(object(imgPtr).ptr());
    }

    template <class Image1, class Image2, class Image3, class RegionStatisticsArray>
    PyObject * pySeededRegionExpansion(Image1 const &imgIn,
                                       Image2 const &imgSeeds,
                                       const cecog::SRGType srgType,
                                       unsigned labelNumber,
                                       typename RegionStatisticsArray::value_type::cost_type costThreshold,
                                       int expansionRounds,
                                       int sepExpandRounds=0)
    {
	  vigra::PyAllowThreads _pythread;
      std::auto_ptr< Image3 > imgPtr(new Image3(imgIn.size()));
      RegionStatisticsArray stats(labelNumber);
      cecog::seededRegionExpansion(srcImageRange(imgIn),
                                  maskImage(imgSeeds),
                                  destImage(*imgPtr),
                                  srgType,
                                  stats,
                                  costThreshold,
                                  expansionRounds,
                                  sepExpandRounds);
      return incref(object(imgPtr).ptr());
    }

    template <class Image1, class Image2, class Image3, class RegionStatisticsArray>
    PyObject * pySeededRegionShrinking(Image1 const &imgIn,
                                       Image2 const &imgSeeds,
                                       unsigned labelNumber,
                                       int shrinkingRounds)
    {
	  vigra::PyAllowThreads _pythread;
      std::auto_ptr< Image3 > imgPtr(new Image3(imgIn.size()));
      RegionStatisticsArray stats(labelNumber);
      cecog::seededRegionShrinking(srcImageRange(imgIn),
                                  maskImage(imgSeeds),
                                  destImage(*imgPtr),
                                  stats,
                                  shrinkingRounds);
      return incref(object(imgPtr).ptr());
    }

    template <class Image1, class Image2>
    PyObject * pySegmentationPropagate(Image1 const &imgIn,
                                       vigra::BImage const &imgInBinary,
                                       Image2 const &imgLabelsIn,
                                       float lambda = 0.05,
                                       int deltaWidth = 1,
                                       SRGType srgType = CompleteGrow)
    {
		vigra::PyAllowThreads _pythread;
        std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
        cecog::segmentationPropagate(imgIn, imgInBinary,
                                     imgLabelsIn, *imgPtr,
                                     lambda, deltaWidth, srgType);
        return incref(object(imgPtr).ptr());
    }

    PyObject * pySegmentationCorrectionShape(vigra::BImage const & imgIn,
                                             vigra::BImage const & binIn,
                                             int rSize,
                                             int gaussSize, int maximaSize,
                                             int iMinMergeSize)
    {
	  vigra::PyAllowThreads _pythread;
      std::auto_ptr< vigra::BImage > imgPtr(new vigra::BImage(imgIn.size()));
      cecog::segmentationCorrection(imgIn, binIn, *imgPtr,
                                    rSize, gaussSize, maximaSize, iMinMergeSize,
                                    ShapeBasedSegmentation);
      return incref(object(imgPtr).ptr());
    }

    PyObject * pySegmentationCorrectionIntensity(vigra::BImage const & imgIn,
                                                 vigra::BImage const & binIn,
                                                 int rSize,
                                                 int gaussSize, int maximaSize,
                                                 int iMinMergeSize)
    {
	  vigra::PyAllowThreads _pythread;
      std::auto_ptr< vigra::BImage > imgPtr(new vigra::BImage(imgIn.size()));
      cecog::segmentationCorrection(imgIn, binIn, *imgPtr,
                                    rSize, gaussSize, maximaSize, iMinMergeSize,
                                    IntensityBasedSegmentation);
      return incref(object(imgPtr).ptr());
    }

  }
}

void wrap_segmentation()
{
  using namespace cecog::python;

  enum_<cecog::SRGType>("SrgType")
  .value("KeepContours",     cecog::KeepContours)
  .value("KeepContoursPlus", cecog::KeepContoursPlus)
  .value("CompleteGrow",     cecog::CompleteGrow)
  ;

  def("fill_holes", pyHoleFilling<vigra::BImage>,
      (arg("image"), arg("eightneighborhood")=false));
  def("label_image", pyLabelImage<vigra::BImage, vigra::Int16Image>);

  def("disc_median", pyDiscMedian<vigra::UInt8Image, vigra::UInt8Image>);
  def("disc_median", pyDiscMedian<vigra::UInt16Image, vigra::UInt16Image>);
  def("disc_median", pyDiscMedian<vigra::Int16Image, vigra::Int16Image>);

  def("toggle_mapping", pyToggleMapping<vigra::UInt8Image, vigra::UInt8Image>);
  def("toggle_mapping", pyToggleMapping<vigra::UInt16Image, vigra::UInt16Image>);
  def("toggle_mapping", pyToggleMapping<vigra::Int16Image, vigra::Int16Image>);

  def("threshold_image", pyThreshold< vigra::UInt8Image, vigra::UInt8Image >,
      (arg("image"), arg("lower"), arg("higher")=255, arg("noresult")=0, arg("yesresult")=255),
      "Static image threshold.");

  def("get_otsu_threshold", pyOtsuThreshold, (arg("image")),
      "Calculate the Otsu threshold value based on the histogram of a UInt8 image.");

  def("window_average_threshold", pyWindowAverageThreshold<vigra::BImage, vigra::BImage>,
      (arg("imgIn"), arg("size"), arg("contrastLimit")=0, arg("lower")=0, arg("higher")=255),
      "Window Average Threshold of window size.");

  def("window_std_threshold", pyWindowStdThreshold<vigra::BImage, vigra::BImage>,
      (arg("imgIn"), arg("size"), arg("threshold"), arg("contrastLimit")=0),
      "Window Stddev Threshold of window size and stddev threshold.");

  def("segmentation_correction_shape", pySegmentationCorrectionShape);
  def("segmentation_correction_intensity", pySegmentationCorrectionIntensity);

  def("seeded_region_expansion", pySeededRegionExpansion< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
                                                          vigra::ArrayOfRegionStatistics<cecog::SrgConstValueFunctor<double> > >,
      (arg("image"), arg("label_image"), arg("srg_type"), arg("label_number"),
       arg("cost_threshold"), arg("expansion_rounds"), arg("sep_expand_rounds")=0),
      "Expand an image of seeds (labels) several rounds without overlapping different seeds.");

//  def("seeded_region_expansion_mean", pySeededRegionExpansion< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
//                                                            vigra::ArrayOfRegionStatistics<cecog::SrgMeanValueFunctor<double> > >,
//      (arg("image"), arg("label_image"), arg("srg_type"), arg("label_number"),
//       arg("cost_threshold"), arg("expansion_rounds"), arg("sep_expand_rounds")=0),
//      "Expand an image of seeds (labels) several rounds without overlapping different seeds by a mean-based functor of the input image.");
//
//  def("seeded_region_expansion_nmean", pySeededRegionExpansion< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
//                                                          vigra::ArrayOfRegionStatistics<cecog::SrgNormMeanValueFunctor<double> > >,
//      (arg("image"), arg("label_image"), arg("srg_type"), arg("label_number"),
//       arg("cost_threshold"), arg("expansion_rounds"), arg("sep_expand_rounds")=0),
//      "Expand an image of seeds (labels) several rounds without overlapping different seeds by a normalized mean-based functor of the input image.");


  def("seeded_region_shrinking", pySeededRegionShrinking< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
                                                        vigra::ArrayOfRegionStatistics<cecog::SrgConstValueFunctor<double> > >,
      (arg("image"), arg("label_image"), arg("label_number"), arg("shrinking_rounds")),
      "Shrink an image of seeds (labels) several rounds without overlapping different seeds.");

//  def("seededRegionExpansionHalfSize", pySeededRegionShrinking< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
//                                                                vigra::ArrayOfRegionStatistics<cecog::ShrinkHalfSizeFunctor<double> > >,
//      (arg("imgIn"), arg("imLabels"), arg("labelNumber"), arg("shrinkingRounds")),
//      "Shrink an image of seeds (imgLabel) several rounds without overlapping different seeds.");


  def("segmentation_propagate", pySegmentationPropagate<vigra::UInt8Image, vigra::Int16Image>,
      (arg("image"), arg("binary"), arg("labels_in"), arg("lambda")=0.05, arg("delta_width")=1, arg("srg_type")=cecog::CompleteGrow),
      "Propagate segmentation from Jones et al. (2005). Lambda is the weight of the spatial pixel distance and delta_width the local area to compute the pixel difference.");


}
#endif /* CECOG_PYTHON_WRAP_SEGMENTATION_HXX_ */
