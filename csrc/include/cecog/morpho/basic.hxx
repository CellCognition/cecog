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


#ifndef BASIC_MORPHO_HXX_
#define BASIC_MORPHO_HXX_

//#include "project_definitions.hxx"

#include "cecog/morpho/structuring_elements.hxx"
#include "cecog/basic/functors.hxx"
#include "cecog/basic/compare_images.hxx"


namespace cecog{
namespace morpho{

template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement,
     class Functor>
void ImSEOperation( Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
          Iterator2 destUpperLeft, Accessor2 desta,
          SElement & se,
          Functor f)
{
  typename Accessor1::value_type neutralElement = f.neutralValue;
  typename Accessor1::value_type localMax;

  // border treatment
  // offsets correspond to the maximal extension of the SE.
  Diff2D minOffset = se.minOffset();
  Diff2D maxOffset = se.maxOffset();

  const Iterator1 upperLeftCorner = srcUpperLeft;
  const Iterator1 lowerRightCorner = srcLowerRight;
  const Iterator1 upperLeftCritical = srcUpperLeft - minOffset;
  const Iterator1 lowerRightCritical = srcLowerRight - maxOffset;

  for(; srcUpperLeft.y < upperLeftCritical.y; ++srcUpperLeft.y, ++destUpperLeft.y)
  {
    Iterator1 scurrent = srcUpperLeft;
    Iterator2 dcurrent = destUpperLeft;

    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x)
    {
      localMax = neutralElement;
      for(typename SElement::ITERATORTYPE iter = se.begin();
        iter != se.end();
        ++iter)
        {
          if(    ( (scurrent + *iter).y >= upperLeftCorner.y)
            && ( (scurrent + *iter).x >= upperLeftCorner.x)
            && ( (scurrent + *iter).x < lowerRightCorner.x))
            localMax = f(localMax, srca(scurrent + *iter));
        }
      desta.set(localMax, dcurrent);
    } // end of x loop
  } // end for the first y-loop.

  for(; srcUpperLeft.y < lowerRightCritical.y; ++srcUpperLeft.y, ++destUpperLeft.y)
  {
    Iterator1 scurrent = srcUpperLeft;
    Iterator2 dcurrent = destUpperLeft;

    // x-loop: the left side
    for(; scurrent.x < upperLeftCritical.x; ++scurrent.x, ++dcurrent.x)
    {
      localMax = neutralElement;
      for(typename SElement::ITERATORTYPE iter = se.begin();
        iter != se.end();
        ++iter)
        {
          if( (scurrent + *iter).x >= upperLeftCorner.x )
            localMax = f(localMax, srca(scurrent + *iter));
        }
      desta.set(localMax, dcurrent);
    } // end of x loop (left)

    for(; scurrent.x < lowerRightCritical.x; ++scurrent.x, ++dcurrent.x)
    {
      localMax = neutralElement;
      for(typename SElement::ITERATORTYPE iter = se.begin();
        iter != se.end();
        ++iter)
        {
          localMax = f(localMax, srca(scurrent + *iter));
        }
      desta.set(localMax, dcurrent);
    } // end of the middle x loop

    // the right side
    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x)
    {
      localMax = neutralElement;
      for(typename SElement::ITERATORTYPE iter = se.begin();
        iter != se.end();
        ++iter)
        {
          if( (scurrent + *iter).x < lowerRightCorner.x)
            localMax = f(localMax, srca(scurrent + *iter));
        }
      desta.set(localMax, dcurrent);
    } // end of the right x loop


  } // end of y loop (middle)

  // y-loop: lower
  for(; srcUpperLeft.y < srcLowerRight.y; ++srcUpperLeft.y, ++destUpperLeft.y)
  {
    Iterator1 scurrent = srcUpperLeft;
    Iterator2 dcurrent = destUpperLeft;

    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x)
    {
      localMax = neutralElement;
      for(typename SElement::ITERATORTYPE iter = se.begin();
        iter != se.end();
        ++iter)
        {
          if(    ( (scurrent + *iter).y < lowerRightCorner.y)
            && ( (scurrent + *iter).x < lowerRightCorner.x)
            && ( (scurrent + *iter).x >= upperLeftCorner.x) )
            localMax = f(localMax, srca(scurrent + *iter));
        }
      desta.set(localMax, dcurrent);
    } // end of x loop
  } // end for the lower y-loop.

} // end of ImSEOperation

/////////////////////////////////////////////////////////////////////////
// EROSION AND DILATION
/////////////////////////////////////////////////////////////////////////

// Morphological dilation
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImDilate(vigra::triple<Iterator1, Iterator1, Accessor1> src,
          vigra::triple<Iterator2, Iterator2, Accessor2> dest,
          SElement se)
{
    vigra::BasicImage<typename Accessor2::value_type> temp(dest.second - dest.first);

  if(se.size > 0)
    ImSEOperation(src.first, src.second, src.third,
                     dest.first, dest.third,
                      se,
                     MaxFunctor<typename Accessor1::value_type>());

  // a morphological dilation with se of size n
  // corresponds to n morphological dilations with size 1.
  for(int i = 1; i < se.size; i++)
  {
    if(i%2 == 0)
      ImSEOperation(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                       dest.first, dest.third,
                       se,
                      MaxFunctor<typename Accessor1::value_type>());
        else
       ImSEOperation(dest.first, dest.second, dest.third,
                       temp.upperLeft(), temp.accessor(),
                       se,
                      MaxFunctor<typename Accessor1::value_type>());
  }

       if(se.size%2 == 0)
         vigra::copyImage(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                       dest.first, dest.third);

} // end of dilation

// Morphological erosion
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImErode(vigra::triple<Iterator1, Iterator1, Accessor1> src,
         vigra::triple<Iterator2, Iterator2, Accessor2> dest,
         SElement se)
{
    vigra::BasicImage<typename Accessor2::value_type> temp(dest.second - dest.first);

  if(se.size > 0)
    ImSEOperation(src.first, src.second, src.third,
                     dest.first, dest.third,
                      se,
                     MinFunctor<typename Accessor1::value_type>());

  // a morphological erosion with se of size n
  // corresponds to n morphological erosions with size 1.
  for(int i = 1; i < se.size; i++)
  {
    if(i%2 == 0)
      ImSEOperation(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                       dest.first, dest.third,
                       se,
                      MinFunctor<typename Accessor1::value_type>());
        else
       ImSEOperation(dest.first, dest.second, dest.third,
                       temp.upperLeft(), temp.accessor(),
                       se,
                      MinFunctor<typename Accessor1::value_type>());
  }

       if(se.size%2 == 0)
         vigra::copyImage(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                       dest.first, dest.third);

} // end of erosion


// Fast Morphological Erosion with a square
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2>
void ImFastSquareErode(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                vigra::triple<Iterator2, Iterator2, Accessor2> dest,
                int size)
{
    vigra::BasicImage<typename Accessor2::value_type> temp(dest.second - dest.first);
  structuringElement2D sex(XSEGMENT , size);
  structuringElement2D sey(YSEGMENT , size);

  if(size > 0)
  {
    ImSEOperation(src.first, src.second, src.third,
                      temp.upperLeft(), temp.accessor(),
                      sex,
                     MinFunctor<typename Accessor1::value_type>());
    ImSEOperation(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                  dest.first, dest.third,
                  sey,
                    MinFunctor<typename Accessor1::value_type>());
      }

  // a morphological erosion with se of size n
  // corresponds to n morphological erosions with size 1.
  for(int i = 1; i < size; i++)
  {
    ImSEOperation(dest.first, dest.second, dest.third,
                   temp.upperLeft(), temp.accessor(),
                   sex,
                  MinFunctor<typename Accessor1::value_type>());
        ImSEOperation(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                   dest.first, dest.third,
                   sey,
                  MinFunctor<typename Accessor1::value_type>());
  }
} // end of fast erosion

// Fast Morphological Dilation with a square
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2>
void ImFastSquareDilate(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                 vigra::triple<Iterator2, Iterator2, Accessor2> dest,
                  int size)
{
    vigra::BasicImage<typename Accessor2::value_type> temp(dest.second - dest.first);
  structuringElement2D sex(XSEGMENT , size);
  structuringElement2D sey(YSEGMENT , size);

  if(size > 0)
  {
    ImSEOperation(src.first, src.second, src.third,
                      temp.upperLeft(), temp.accessor(),
                      sex,
                     MaxFunctor<typename Accessor1::value_type>());
    ImSEOperation(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                  dest.first, dest.third,
                  sey,
                    MaxFunctor<typename Accessor1::value_type>());
      }

  for(int i = 1; i < size; i++)
  {
    ImSEOperation(dest.first, dest.second, dest.third,
                   temp.upperLeft(), temp.accessor(),
                   sex,
                  MaxFunctor<typename Accessor1::value_type>());
        ImSEOperation(temp.upperLeft(), temp.lowerRight(), temp.accessor(),
                   dest.first, dest.third,
                   sey,
                  MaxFunctor<typename Accessor1::value_type>());
  }
} // end of fast dilation

/////////////////////////////////////////////////////////////////////////
// OPENING AND CLOSING
/////////////////////////////////////////////////////////////////////////

// Morphological opening
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImOpen(vigra::triple<Iterator1, Iterator1, Accessor1> src,
      vigra::triple<Iterator2, Iterator2, Accessor2> dest, SElement se)
{
    vigra::BasicImage<typename Accessor1::value_type> temp(src.second - src.first);
  ImErode(src, vigra::destImageRange(temp), se);
  ImDilate(vigra::srcImageRange(temp), dest, se);
} // end of opening

// Morphological closing
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImClose(vigra::triple<Iterator1, Iterator1, Accessor1> src,
      vigra::triple<Iterator2, Iterator2, Accessor2> dest, SElement se)
{
    vigra::BasicImage<typename Accessor1::value_type> temp(src.second - src.first);
  ImDilate(src, vigra::destImageRange(temp), se);
  ImErode(vigra::srcImageRange(temp), dest, se);
} // end of closing

// Morphological gradient
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImMorphoGradient(vigra::triple<Iterator1, Iterator1, Accessor1> src,
            vigra::triple<Iterator2, Iterator2, Accessor2> dest,
            SElement se,
            typename Accessor2::value_type markerVal = 255)
{
  typedef typename Accessor1::value_type INTYPE;
  typedef typename Accessor2::value_type OUTTYPE;

    vigra::BasicImage<INTYPE> dil(src.second - src.first);
    vigra::BasicImage<INTYPE> ero(src.second - src.first);
  ImDilate(src, vigra::destImageRange(dil), se);
  ImErode(src, vigra::destImageRange(ero), se);
  vigra::combineTwoImages(srcImageRange(dil), srcImage(ero),
              destIter(dest.first, dest.third),
              std::minus<INTYPE>() );

} // end of closing

// External gradient
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImExternalGradient(vigra::triple<Iterator1, Iterator1, Accessor1> src,
              vigra::triple<Iterator2, Iterator2, Accessor2> dest,
              SElement se,
              typename Accessor2::value_type markerVal = 255)
{
  typedef typename Accessor1::value_type INTYPE;
  typedef typename Accessor2::value_type OUTTYPE;

    vigra::BasicImage<INTYPE> dil(src.second - src.first);
    ImDilate(src, vigra::destImageRange(dil), se);
  vigra::combineTwoImages(srcImageRange(dil),
              srcIter(src.first, src.third),
              destIter(dest.first, dest.third),
              std::minus<INTYPE>() );

}

// Internal gradient
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImInternalGradient(vigra::triple<Iterator1, Iterator1, Accessor1> src,
              vigra::triple<Iterator2, Iterator2, Accessor2> dest,
              SElement se,
              typename Accessor2::value_type markerVal = 255)
{
  typedef typename Accessor1::value_type INTYPE;
  typedef typename Accessor2::value_type OUTTYPE;

    vigra::BasicImage<INTYPE> ero(src.second - src.first);
    ImErode(src, vigra::destImageRange(ero), se);
  vigra::combineTwoImages(srcIterRange(src.first, src.second, src.third),
              srcImage(ero),
              destIter(dest.first, dest.third),
              std::minus<INTYPE>() );

}

// White Top hat
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImWhiteTophat(vigra::triple<Iterator1, Iterator1, Accessor1> src,
           vigra::triple<Iterator2, Iterator2, Accessor2> dest,
           SElement se,
           typename Accessor2::value_type markerVal = 255)
{
  typedef typename Accessor1::value_type INTYPE;
  typedef typename Accessor2::value_type OUTTYPE;

    vigra::BasicImage<INTYPE> opened(src.second - src.first);
    ImOpen(src, vigra::destImageRange(opened), se);
  vigra::combineTwoImages(srcIterRange(src.first, src.second, src.third),
              srcImage(opened),
              destIter(dest.first, dest.third),
              std::minus<INTYPE>() );

}

// Black Top hat
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImBlackTophat(vigra::triple<Iterator1, Iterator1, Accessor1> src,
           vigra::triple<Iterator2, Iterator2, Accessor2> dest,
           SElement se,
           typename Accessor2::value_type markerVal = 255)
{
  typedef typename Accessor1::value_type INTYPE;
  typedef typename Accessor2::value_type OUTTYPE;

    vigra::BasicImage<INTYPE> closed(src.second - src.first);
    ImClose(src, vigra::destImageRange(closed), se);
  vigra::combineTwoImages(srcImageRange(closed),
              srcIter(src.first, src.third),
              destIter(dest.first, dest.third),
              std::minus<INTYPE>() );

}


// Supremum of two images
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2>
void ImSupremum(vigra::triple<Iterator1, Iterator1, Accessor1> a,
    vigra::pair<Iterator1, Accessor1> b,
    vigra::pair<Iterator2, Accessor2> out)
{
  typedef typename Accessor1::value_type INTYPE;

  //vigra::combineTwoImages(a, b, out, MaxFunctor<INTYPE>() );
  //vigra::combineTwoImages(a, b, out, std::minus<INTYPE>() );
  vigra::combineTwoImages(a, b, out,
      ifThenElse(Arg1() < Arg2(), Arg2(), Arg1()) );

}

// Infimum of two images
template<class Iterator1, class Accessor1,
    class Iterator2, class Accessor2>
void ImInfimum(vigra::triple<Iterator1, Iterator1, Accessor1> a,
    vigra::pair<Iterator1, Accessor1> b,
    vigra::pair<Iterator2, Accessor2> out)
{
  typedef typename Accessor1::value_type INTYPE;

  //vigra::combineTwoImages(a, b, out, MinFunctor<INTYPE> );
  vigra::combineTwoImages(a, b, out,
      ifThenElse(Arg1() < Arg2(), Arg1(), Arg2()) );
}


// Overloaded operators.
template<class Image1>
void ImSupremum(const Image1 & a, const Image1 & b, Image1 & imout)
{
  ImSupremum(srcImageRange(a), srcImage(b), destImage(imout));
}

template<class Image1>
void ImInfimum(const Image1 & a, const Image1 & b, Image1 & imout)
{
  ImInfimum(srcImageRange(a), srcImage(b), destImage(imout));
}

template<class Image1, class Image2, class SElement>
void ImInternalGradient(const Image1 & imin, Image2 & imout, SElement se)
{
  ImInternalGradient(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImExternalGradient(const Image1 & imin, Image2 & imout, SElement se)
{
  ImExternalGradient(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImMorphoGradient(const Image1 & imin, Image2 & imout, SElement se)
{
  ImMorphoGradient(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImErode(const Image1 & imin, Image2 & imout, SElement se)
{
  ImErode(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImDilate(const Image1 & imin, Image2 & imout, SElement se)
{
  ImDilate(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImDilate2(const Image1 & imin, Image2 & imout, SElement se)
{
  ImDilate(imin, imout, se);
}

// Fast Square Erode and Dilate
template<class Image1, class Image2>
void ImFastSquareErode(const Image1 & imin, Image2 & imout, int size)
{
  ImFastSquareErode(srcImageRange(imin), destImageRange(imout), size);
}

template<class Image1, class Image2>
void ImFastSquareDilate(const Image1 & imin, Image2 & imout, int size)
{
  ImFastSquareDilate(srcImageRange(imin), destImageRange(imout), size);
}

// Open and close
template<class Image1, class Image2, class SElement>
void ImOpen(const Image1 & imin, Image2 & imout, SElement se)
{
  ImOpen(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImClose(const Image1 & imin, Image2 & imout, SElement se)
{
  ImClose(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImWhiteTophat(const Image1 & imin, Image2 & imout, SElement se)
{
  ImWhiteTophat(srcImageRange(imin), destImageRange(imout), se);
}

template<class Image1, class Image2, class SElement>
void ImBlackTophat(const Image1 & imin, Image2 & imout, SElement se)
{
  ImBlackTophat(srcImageRange(imin), destImageRange(imout), se);
}


//////////////////////////////
// ToggleMapping help function
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class Iterator3, class Accessor3,
     class Iterator4, class Accessor4>
void ToggleMappingHelpFunction(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                     Iterator2 extUpperLeft, Accessor2 exta,
                     Iterator3 antiExtUpperLeft, Accessor3 antiexta,
                     Iterator4 destUpperLeft, Accessor4 desta)
{
  typedef typename Accessor1::value_type value_type;

  for(; srcUpperLeft.y < srcLowerRight.y; ++srcUpperLeft.y,
                      ++extUpperLeft.y,
                      ++antiExtUpperLeft.y,
                      ++destUpperLeft.y)
  {
    Iterator1 scurrent(srcUpperLeft);
    Iterator2 extcurrent(extUpperLeft);
    Iterator3 antiextcurrent(antiExtUpperLeft);
    Iterator4 dcurrent(destUpperLeft);

    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++extcurrent.x,
                      ++antiextcurrent.x, ++dcurrent.x)
    {
      value_type ex = exta(extcurrent);
      value_type antiex = antiexta(antiextcurrent);
      value_type val = srca(scurrent);

      if( (val-antiex) < (ex-val) )
        desta.set(antiex, dcurrent);
      else
        desta.set(ex, dcurrent);
    }
  }
}

template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class Iterator3, class Accessor3,
     class Iterator4, class Accessor4>
void ToggleMappingHelpFunction(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                 vigra::pair<Iterator2, Accessor2> f1,
                 vigra::pair<Iterator3, Accessor3> f2,
                 vigra::pair<Iterator4, Accessor4> dest)
{
  ToggleMappingHelpFunction(src.first, src.second, src.third,
                f1.first, f1.second,
                f2.first, f2.second,
                dest.first, dest.second);
}

template<class Image1, class Image2, class SElement>
void ImToggleMapping(const Image1 &imin, Image2&imout, SElement se, int mode=1)
{
  typedef typename Image1::value_type value_type;

  Image1 filtered1(imin.size()), filtered2(imin.size());

  switch(mode)
  {
    case 1: ImErode(imin, filtered1, se);
        ImDilate(imin, filtered2, se);
        break;
    case 2: ImFastSquareErode(imin, filtered1, se.size);
        ImFastSquareDilate(imin, filtered2, se.size);
        break;
    case 3: ImOpen(imin, filtered1, se);
        ImClose(imin, filtered2, se);
        break;
    default:vigra::copyImage(srcImageRange(imin), destImage(filtered1));
        vigra::copyImage(srcImageRange(imin), destImage(filtered2));
        cout << "This Toggle Mapping mode is not defined." << endl;
        break;
  }

  ToggleMappingHelpFunction(srcImageRange(imin),
                srcImage(filtered2),
                srcImage(filtered1),
                destImage(imout));

}

template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class Functor1, class Functor2,
     class SElement>
inline
void BorderPixelElementaryToggleMappingOperation(Iterator1 &scurrent, Accessor1 &srca,
                         Iterator2 &dcurrent, Accessor2 &desta,
                         const Iterator1 &upperLeftCorner,
                         const Iterator1 &lowerRightCorner,
                         Functor1 extOp, Functor2 antiExtOp,
                         SElement &se)
{
  typedef typename Accessor1::value_type value_type;

  value_type localMax = extOp.neutralValue;
  value_type localMin = antiExtOp.neutralValue;

  const value_type value=srca(scurrent);

  for(typename SElement::ITERATORTYPE iter = se.begin();
    iter != se.end();
    ++iter)
    {
      if(    ( (scurrent + *iter).y >= upperLeftCorner.y)
        && ( (scurrent + *iter).x >= upperLeftCorner.x)
        && ( (scurrent + *iter).y < lowerRightCorner.y)
        && ( (scurrent + *iter).x < lowerRightCorner.x) )
      {
        localMax = extOp(localMax, srca(scurrent + *iter));
        localMin = antiExtOp(localMin, srca(scurrent + *iter));
      }
    }

  if(value - localMin < localMax -value)
    desta.set(localMin, dcurrent);
  else
    desta.set(localMax, dcurrent);

} // end of Borderpixel operation.

template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class Functor1, class Functor2,
     class SElement>
inline
void PixelElementaryToggleMappingOperation(Iterator1 &scurrent, Accessor1 &srca,
                          Iterator2 &dcurrent, Accessor2 &desta,
                       Functor1 max, Functor2 min,
                       SElement &se)
{

  typedef typename Accessor1::value_type value_type;
  value_type localMax = max.neutralValue;
  value_type localMin = min.neutralValue;
  const value_type value=srca(scurrent);

  for(typename SElement::ITERATORTYPE iter = se.begin();
    iter != se.end();
    ++iter)
    {
      localMax = max(localMax, srca(scurrent + *iter));
      localMin = min(localMin, srca(scurrent + *iter));
    }

  if(value - localMin < localMax -value)
    desta.set(localMin, dcurrent);
  else
    desta.set(localMax, dcurrent);

} // end of Borderpixel operation.


// ImFastToggleMapping
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImFastToggleMapping(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
             Iterator2 destUpperLeft, Accessor2 desta,
             SElement & se)
{
  typedef typename Accessor1::value_type value_type;

  // border treatment
  // offsets correspond to the maximal extension of the SE.
  Diff2D minOffset = se.minOffset();
  Diff2D maxOffset = se.maxOffset();

  const Iterator1 upperLeftCorner = srcUpperLeft;
  const Iterator1 lowerRightCorner = srcLowerRight;
  const Iterator1 upperLeftCritical = srcUpperLeft - minOffset;
  const Iterator1 lowerRightCritical = srcLowerRight - maxOffset;

  for(; srcUpperLeft.y < upperLeftCritical.y; ++srcUpperLeft.y, ++destUpperLeft.y)
  {
    Iterator1 scurrent = srcUpperLeft;
    Iterator2 dcurrent = destUpperLeft;

    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x)
    {
      BorderPixelElementaryToggleMappingOperation(
        scurrent, srca, dcurrent, desta,
        upperLeftCorner, lowerRightCorner,
        MaxFunctor<value_type>(), MinFunctor<value_type>(), se);
    } // end of x loop
  } // end for the first y-loop.

  for(; srcUpperLeft.y < lowerRightCritical.y; ++srcUpperLeft.y, ++destUpperLeft.y)
  {
    Iterator1 scurrent = srcUpperLeft;
    Iterator2 dcurrent = destUpperLeft;

    // x-loop: the left side
    for(; scurrent.x < upperLeftCritical.x; ++scurrent.x, ++dcurrent.x)
    {
      BorderPixelElementaryToggleMappingOperation(
        scurrent, srca, dcurrent, desta,
        upperLeftCorner, lowerRightCorner,
        MaxFunctor<value_type>(), MinFunctor<value_type>(), se);
//					extOp, antiExtOp, se);
    } // end of x loop (left)

    for(; scurrent.x < lowerRightCritical.x; ++scurrent.x, ++dcurrent.x)
    {
      PixelElementaryToggleMappingOperation(
        scurrent, srca, dcurrent, desta,
        MaxFunctor<value_type>(), MinFunctor<value_type>(), se);
//					extOp, antiExtOp, se);
    } // end of the middle x loop

    // the right side
    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x)
    {
      BorderPixelElementaryToggleMappingOperation(
        scurrent, srca, dcurrent, desta,
        upperLeftCorner, lowerRightCorner,
        MaxFunctor<value_type>(), MinFunctor<value_type>(), se);
//					extOp, antiExtOp, se);
    } // end of the right x loop


  } // end of y loop (middle)

  // y-loop: lower
  for(; srcUpperLeft.y < srcLowerRight.y; ++srcUpperLeft.y, ++destUpperLeft.y)
  {
    Iterator1 scurrent = srcUpperLeft;
    Iterator2 dcurrent = destUpperLeft;

    for(; scurrent.x < srcLowerRight.x; ++scurrent.x, ++dcurrent.x)
    {
      BorderPixelElementaryToggleMappingOperation(
        scurrent, srca, dcurrent, desta,
        upperLeftCorner, lowerRightCorner,
        MaxFunctor<value_type>(), MinFunctor<value_type>(), se);
//					extOp, antiExtOp, se);
    } // end of x loop
  } // end for the lower y-loop.

} // end of ImSEOperation

// Erosion-Dilation Toggle Mappings
template<class Iterator1, class Accessor1,
     class Iterator2, class Accessor2,
     class SElement>
void ImFastToggleMapping(vigra::triple<Iterator1, Iterator1, Accessor1> src,
             vigra::pair<Iterator2, Accessor2> dest, SElement &se)
{
  ImFastToggleMapping(src.first, src.second, src.third,
                dest.first, dest.second,
                se);
} // end of toggle mapping

template<class Image1, class Image2, class SElement>
void ImFastToggleMapping(const Image1 &imin, Image2 &imout, SElement &se)
{
  ImFastToggleMapping(srcImageRange(imin), destImage(imout), se);
}

// Subtraction between image and a constant
template<class IMAGE>
void ImSubtractConst(IMAGE const & src, IMAGE & dest, int v){
    typename IMAGE::const_traverser it1C = src.upperLeft();
    typename IMAGE::traverser it2C = dest.upperLeft();
    typename IMAGE::const_traverser it1End = src.lowerRight();

    if (v > 255) v = 255;
    if (v < 0) v = 0;
    int w = it1End.x - it1C.x;
    int h = it1End.y - it1C.y;

    for (int x=0; x<w; ++x){
        for (int y=0; y<h; ++y){
            *(it2C + Diff2D(x,y)) = *(it1C + Diff2D(x,y)) > v ?
                        (*(it1C + Diff2D(x,y)) - v) : 0 ;
        }
    }
}

// Add between image and a constant
template<class IMAGE>
void ImAddConst(IMAGE const & src, IMAGE & dest, int v){
    typename IMAGE::const_traverser it1C = src.upperLeft();
    typename IMAGE::traverser it2C = dest.upperLeft();
    typename IMAGE::const_traverser it1End = src.lowerRight();

    if (v > 255) v = 255;
    if (v < 0) v = 0;
    int w = it1End.x - it1C.x;
    int h = it1End.y - it1C.y;

    for (int x=0; x<w; ++x){
        for (int y=0; y<h; ++y){
            *(it2C + Diff2D(x,y)) = (*(it1C + Diff2D(x,y)) + v) > 255 ?
                               255 : (*(it1C + Diff2D(x,y)) + v) ;
        }
    }
}


};
};

#endif /*BASIC_MORPHO_HXX_*/
