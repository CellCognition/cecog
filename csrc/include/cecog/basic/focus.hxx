#ifndef FOCUS_HXX_
#define FOCUS_HXX_

//#include "mito/settings/debug_environment.hxx"

#include <iostream>
#include "vigra/imageiterator.hxx"
#include "vigra/stdimage.hxx"
#include "vigra/stdimagefunctions.hxx"
#include "vigra/impex.hxx"
#include "vigra/imageinfo.hxx"
#include "vigra/inspectimage.hxx"
#include "cecog/inspectors.hxx"
#include "cecog/basic/functors.hxx"

//#include "vigra/flatmorphology.hxx"

//#include "vigra/tuple.hxx"

//#include "project_definitions.hxx"
//#include "mito/basic/functors.hxx"

namespace cecog {

//  ///////////////////////
//  // Global Focus Measure
//  template<class Iterator1, class Accessor1>
//  inline
//  double focusQuantification(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca, int method)
//  {
//
//    typedef typename Iterator1::value_type PIXELTYPE;
//    double resval = 0.0;
//
//    vigra::FindAverageAndVariance<PIXELTYPE> averageAndVariance;   // init functor
//
//    switch(method) {
//    case 1:
//      // variance of the image
//      vigra::inspectImage(srcUpperLeft, srcLowerRight, srca, averageAndVariance);
//      resval = averageAndVariance.variance();
//      break;
//    case 2:
//       vigra::FImage src(w,h), dest(w,h);
//
//       // define horizontal Sobel filter
//       vigra::Kernel2D<float> sobel;
//
//       sobel.initExplicitly(Diff2D(-1,-1), Diff2D(1,1)) =  // upper left and lower right
//           0.125, 0.0, -0.125,
//           0.25,  0.0, -0.25,
//           0.125, 0.0, -0.125;
//       sobel.setBorderTreatment(vigra::BORDER_TREATMENT_REFLECT);
//
//       vigra::convolveImage(srcImageRange(src), destImage(dest), kernel2d(sobel));
//
//      break;
//    default:
//      //VerboseOutput("Focus quantification method not implemented.");
//      cout << "Focus quantification method not implemented." << "\n";
//      break;
//    }
//    return(resval);
//  } // end focusQuantification

  ////////////////////////
  // using factories
  template<class IMAGE>
  inline
  double focusQuantification(IMAGE const &src, int method)
  {
    typedef typename IMAGE::PixelType PIXELTYPE;
    double resval = 0.0;

    // initializations
    vigra::Kernel2D<float> filter;
    vigra::FImage temp(src.width(), src.height());
    FindSquaredSum<float> sqrtsum;
    FindAbsSum<float> abssum;
    vigra::FindAverageAndVariance<PIXELTYPE> stats;

    switch(method){
    case 1: // variance of the original image
      vigra::inspectImage(srcImageRange(src), stats);
      resval = stats.variance();
      break;

    case 2: // gradient absolute values
      // sobel in x-direction
      filter.initExplicitly(vigra::Diff2D(-1,-1), vigra::Diff2D(1,1)) =  // upper left and lower right
            0.125, 0.0, -0.125,
            0.25,  0.0, -0.25,
            0.125, 0.0, -0.125;
      filter.setBorderTreatment(vigra::BORDER_TREATMENT_REFLECT);
      vigra::convolveImage(srcImageRange(src), destImage(temp), kernel2d(filter));
      vigra::inspectImage(srcImageRange(temp), abssum);
      resval = abssum();
      abssum.reset();

      // sobel in x-direction
      filter.initExplicitly(vigra::Diff2D(-1,-1), vigra::Diff2D(1,1)) =  // upper left and lower right
            0.125, 0.25, 0.125,
            0.0,  0.0, 0.0,
            -0.125, -0.25, -0.125;
      vigra::convolveImage(srcImageRange(src), destImage(temp), kernel2d(filter));
      vigra::inspectImage(srcImageRange(temp), abssum);
      resval += abssum();
      break;

    case 3: // gradient energy (sum of squares)
      // sobel in x-direction
      filter.initExplicitly(vigra::Diff2D(-1,-1), vigra::Diff2D(1,1)) =  // upper left and lower right
            0.125, 0.0, -0.125,
            0.25,  0.0, -0.25,
            0.125, 0.0, -0.125;
      filter.setBorderTreatment(vigra::BORDER_TREATMENT_REFLECT);
      vigra::convolveImage(srcImageRange(src), destImage(temp), kernel2d(filter));
      vigra::inspectImage(srcImageRange(temp), sqrtsum);
      resval = sqrtsum();
      sqrtsum.reset();

      // sobel in x-direction
      filter.initExplicitly(vigra::Diff2D(-1,-1), vigra::Diff2D(1,1)) =  // upper left and lower right
             0.125,  0.25, 	0.125,
             0.0,  	 0.0, 	0.0,
            -0.125, -0.25, -0.125;
      vigra::convolveImage(srcImageRange(src), destImage(temp), kernel2d(filter));
      vigra::inspectImage(srcImageRange(temp), sqrtsum);
      resval += sqrtsum();
      break;

    case 4: // Laplace operator
      filter.initExplicitly(vigra::Diff2D(-1,-1), vigra::Diff2D(1,1)) =  // upper left and lower right
                   0.0625,  0.0625, 0.0625,
                   0.0625,  -0.5, 	0.0625,
                   0.0625,  0.0625, 0.0625;
      filter.setBorderTreatment(vigra::BORDER_TREATMENT_REFLECT);
      vigra::convolveImage(srcImageRange(src), destImage(temp), kernel2d(filter));
      vigra::inspectImage(srcImageRange(temp), sqrtsum);
      resval = sqrtsum();

      break;

    default:
      cout << "focus quantification method " << method << " not implemented." << "\n";
      break;

    }
    return(resval);
  } // end of focusQuantification

} // end namespace mito

#endif
