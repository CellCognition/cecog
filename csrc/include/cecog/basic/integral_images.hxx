/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                             www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Thomas Walter
// $Date$
// $Rev$
// $URL$


#ifndef INTEGRAL_IMAGES_HXX_
#define INTEGRAL_IMAGES_HXX_

#include "vigra/tuple.hxx"

#include "project_definitions.hxx"
#include "cecog/basic/functors.hxx"

namespace cecog {

  //////////////////
  // Integral Image
  template<class Iterator1, class Accessor1, class Iterator2, class Accessor2>
  inline
  void IntegralImage(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
             Iterator2 destUpperLeft, Accessor2 desta)
  {
    // size of the image
    vigra::Diff2D size = srcLowerRight - srcUpperLeft;

    // The upperleft pixel is copied.
    desta.set(srca(srcUpperLeft), destUpperLeft);

    vigra::Diff2D ll(-1, 0);
    vigra::Diff2D ul(-1,-1);
    vigra::Diff2D ur( 0,-1);

    // first row
    Iterator1 scurrent = srcUpperLeft + vigra::Diff2D(1,0);
    Iterator2 dcurrent = destUpperLeft + vigra::Diff2D(1,0);
    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x)
    {
      desta.set(
        desta(dcurrent, ll) + srca(scurrent),
        dcurrent);
    }

    // first column
    scurrent = srcUpperLeft + vigra::Diff2D(0,1);
    dcurrent = destUpperLeft + vigra::Diff2D(0,1);
    for(; scurrent.y < srcLowerRight.y; ++scurrent.y, ++dcurrent.y)
    {
      desta.set(
        desta(dcurrent, ur) + srca(scurrent),
        dcurrent);
    }

    destUpperLeft += vigra::Diff2D(1,1);
    srcUpperLeft += vigra::Diff2D(1,1);

    for(; srcUpperLeft.y < srcLowerRight.y; ++srcUpperLeft.y, ++destUpperLeft.y)
    {
      Iterator1 srcul = srcUpperLeft;
      Iterator2 destul = destUpperLeft;

      for(; srcul.x < srcLowerRight.x; ++srcul.x, ++destul.x)
      {
        desta.set(
          srca(srcul)
          + desta(destul, ur)
          + desta(destul, ll)
          - desta(destul, ul),
          destul);
      } // end for x
    } // end for y
  } // end of IntegralImage


  ////////////////////////
  // using factories:
  template<class Iterator1, class Accessor1, class Iterator2, class Accessor2>
  inline
  void IntegralImage(vigra::triple<Iterator1, Iterator1, Accessor1> src,
             vigra::pair<Iterator2, Accessor2> dest)
  {

      IntegralImage(src.first, src.second, src.third,
                     dest.first, dest.second);

  } // end of IntegralImage


  //////////////////////////////////////////////////////////////
  // ImLocalAverageOperator
  //////////////////////////////////////////////////////////////
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class Functor>
  inline
  void ImLocalAverageOperator(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                  Iterator2 destUpperLeft, Accessor2 desta,
                  vigra::Diff2D ws,
                  Functor f)
  {
    // ws: the window has the width 2 * ws.x + 1 and the height 2 * ws.y + 1

    typedef typename Iterator1::value_type INTYPE;

    // This function calculates the local average of an input image.
    // the code has been optimized which made it less readable :-(

    // winCenterDistance defines the size of the window.
    // it defines the distance between the center and the upper/right border.
    vigra::Diff2D size = srcLowerRight - srcUpperLeft;

    double maximalIntegralValue = std::pow((double)2, (double)(sizeof(INTYPE) * 8)) * (double)size.x * (double)size.y;
    if(maximalIntegralValue >= std::pow((double)2,32))
    {
      std::cout << sizeof(INTYPE) << "Byte -> "
         << "maximal  possible value of integral image = " << maximalIntegralValue << std::endl;
      std::cout << "warning: integral image overflow possible -- "
         << "allowed image maximum: "
         << (int)(std::pow((double)2,32) / (double)(size.x * size.y))
         << std::endl;
    }

    vigra::IImage integralImage(size);
    IntegralImage(vigra::srcIterRange(srcUpperLeft, srcLowerRight, srca),
            vigra::destImage(integralImage));

    vigra::IImage::Iterator integralUpperLeft = integralImage.upperLeft(),
                integralLowerRight = integralImage.lowerRight();
    vigra::IImage::Accessor integrala = integralImage.accessor();
    typedef typename vigra::IImage::Iterator IIterator;
    typedef typename vigra::IImage::value_type integral_type;

    // The offsets (specific for integral images)
    // The offsets are all outside the sliding window.
    vigra::Diff2D offsetLR(ws.x, ws.y); // the pixel in the lower right
    vigra::Diff2D offsetUR(ws.x, -ws.y - 1); // the pixel in the upper right
    vigra::Diff2D offsetLL(-ws.x - 1, ws.y); // the pixel in the lower left
    vigra::Diff2D offsetUL(-ws.x - 1, -ws.y - 1); // the pixel in the upper left

    // currentWin is the window size for the first pixel (has still to be incremented).
    vigra::Diff2D currentWin(ws.x,ws.y);

    Iterator1 srcFirstValidPoint(srcUpperLeft + vigra::Diff2D(ws.x + 1, ws.y + 1) );
    Iterator1 srcLastValidPoint(srcLowerRight - vigra::Diff2D(ws.x + 1, ws.y + 1) );

    for(;srcUpperLeft.y < srcFirstValidPoint.y; ++srcUpperLeft.y, ++destUpperLeft.y, ++integralUpperLeft.y)
    {
      Iterator1 scurrent(srcUpperLeft);
      Iterator2 dcurrent(destUpperLeft);
      IIterator icurrent(integralUpperLeft);

      currentWin.x = ws.x; // initilization of the window size (begin of the row).
      ++currentWin.y;  // the window size in y direction is incremented.

      // y-loop until the window is completely inside the image.
      for(; scurrent.x < srcFirstValidPoint.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        ++currentWin.x;
        float localMean = (float)integrala(icurrent,offsetLR)
                     / (float)(currentWin.x*currentWin.y);

        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
      float win_size = (float)(currentWin.x * currentWin.y);
      for(; scurrent.x <= srcLastValidPoint.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        float localMean = (float)(  integrala(icurrent, offsetLR)
                        - integrala(icurrent, offsetLL) )
                        / win_size;
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
      integral_type fixedValLR = integrala(integralUpperLeft, vigra::Diff2D(size.x - 1, ws.y));
      for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        --currentWin.x;
        float localMean=  (float)(  fixedValLR
                       - integrala(icurrent, offsetLL) )
                       /(float)(currentWin.x * currentWin.y);
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
    }

    // y-loop on the part where the window fits (in y-direction).
    for(;srcUpperLeft.y <= srcLastValidPoint.y; ++srcUpperLeft.y, ++destUpperLeft.y, ++integralUpperLeft.y)
    {
      Iterator1 scurrent = srcUpperLeft;
      Iterator2 dcurrent = destUpperLeft;
      IIterator icurrent = integralUpperLeft;

      currentWin.x = ws.x;
      for(; scurrent.x < srcFirstValidPoint.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        ++currentWin.x;
        float localMean = (float)(   integrala(icurrent, offsetLR)
                           - integrala(icurrent, offsetUR))
                           / (float)(currentWin.x*currentWin.y);
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
      float win_size = (float)currentWin.x * currentWin.y;
      for(; scurrent.x <= srcLastValidPoint.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        float localMean =  (float)(  integrala(icurrent, offsetLR)
                          - integrala(icurrent, offsetLL)
                        - integrala(icurrent, offsetUR)
                        + integrala(icurrent, offsetUL) )
                        / win_size;
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }

      integral_type fixedValLR = integrala(integralUpperLeft, vigra::Diff2D(size.x - 1, ws.y));
      integral_type fixedValUR = integrala(integralUpperLeft, vigra::Diff2D(size.x - 1, -1 - ws.y));
      for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        --currentWin.x;
        float localMean = (float)(  fixedValLR
                         - integrala(icurrent, offsetLL)
                       - fixedValUR
                       + integrala(icurrent, offsetUL) )
                       / (float)(currentWin.x * currentWin.y);
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
    } // end of middle y-loop.


    for(;srcUpperLeft.y < srcLowerRight.y; ++srcUpperLeft.y, ++destUpperLeft.y, ++integralUpperLeft.y)
    {
      Iterator1 scurrent(srcUpperLeft);
      Iterator2 dcurrent(destUpperLeft);
      IIterator icurrent(integralUpperLeft);

      currentWin.x = ws.x;

      offsetLR.y = integralLowerRight.y - integralUpperLeft.y - 1;
      offsetLL.y = integralLowerRight.y - integralUpperLeft.y - 1;

      --currentWin.y;

      for(; scurrent.x < srcFirstValidPoint.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
         ++currentWin.x;
         float localMean = (float)(  integrala(icurrent, offsetLR)
                        - integrala(icurrent, offsetUR) )
                        / (float)(currentWin.x*currentWin.y);
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
      float win_size = (float)(currentWin.x * currentWin.y);
      for(; scurrent.x <= srcLastValidPoint.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        float localMean = (float)(  integrala(icurrent, offsetLR)
                      - integrala(icurrent, offsetLL)
                      - integrala(icurrent, offsetUR)
                      + integrala(icurrent, offsetUL) )
                      / win_size;
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
      vigra::Diff2D tempSize = integralLowerRight - integralUpperLeft;
      integral_type fixedValLR = integrala(integralUpperLeft, vigra::Diff2D(size.x - 1, tempSize.y - 1));
      integral_type fixedValUR = integrala(integralUpperLeft, vigra::Diff2D(size.x - 1, -1 - ws.y));

      for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x, ++icurrent.x)
      {
        --currentWin.x;
        float localMean = (float)( fixedValLR
                          - integrala(icurrent, offsetLL)
                          - fixedValUR
                          + integrala(icurrent, offsetUL))
                          / (float)(currentWin.x * currentWin.y);
        desta.set(f(srca(scurrent), localMean), dcurrent);
      }
    } // end of lower y-loop.
  } // end of ImLocalThreshold

  template<class Image1, class Image2>
  inline
  void ImLocalThreshold(Image1 const & in, Image2 & out, vigra::Diff2D ws,
              typename Image1::value_type thresh,
              typename Image2::value_type maxVal = 255)
  {
    ImLocalThreshold(srcImageRange(in), destImage(out), ws, thresh, maxVal);
  }

  template<class Iterator1, class Accessor1, class Iterator2, class Accessor2>
  inline
  void ImLocalThreshold(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                vigra::pair<Iterator2, Accessor2> dest,
                vigra::Diff2D ws,
                typename Iterator1::value_type thresh,
                typename Iterator2::value_type maxVal = 255)
  {
    ThresholdFunctor<float,
             typename Iterator1::value_type,
             typename Iterator2::value_type> f((float)thresh, maxVal, 0);

    ImLocalAverageOperator(src.first, src.second, src.third,
                  dest.first, dest.second,
                  ws,
                  f);
  }

  // ImLocalAverage
  template<class Image1, class Image2>
  inline
  void ImLocalAverage(Image1 const & in, Image2 & out, vigra::Diff2D ws)
  {
    ImLocalAverage(srcImageRange(in), destImage(out), ws);
  }

  template<class Iterator1, class Accessor1, class Iterator2, class Accessor2>
  inline
  void ImLocalAverage(vigra::triple<Iterator1, Iterator1, Accessor1> src,
              vigra::pair<Iterator2, Accessor2> dest,
              vigra::Diff2D ws)
  {
    TrivialValueFunctor<float,
               typename Iterator1::value_type,
               typename Iterator2::value_type> f;

    ImLocalAverageOperator(src.first, src.second, src.third,
                  dest.first, dest.second,
                  ws,
                  f);
  }

  // ImLocalAverage
  template<class Image1, class Image2>
  inline
  void ImBackgroundSubtraction(Image1 const & in, Image2 & out, vigra::Diff2D ws)
  {
    ImBackgroundSubtraction(srcImageRange(in), destImage(out), ws);
  }

  template<class Iterator1, class Accessor1, class Iterator2, class Accessor2>
  inline
  void ImBackgroundSubtraction(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                   vigra::pair<Iterator2, Accessor2> dest,
                   vigra::Diff2D ws)
  {

    ImLocalAverageOperator(src.first, src.second, src.third,
                  dest.first, dest.second,
                  ws,
                  minusClipp<typename Iterator1::value_type,
                          float>());
  }

};

#endif /*INTEGRAL_IMAGES_HXX_*/
