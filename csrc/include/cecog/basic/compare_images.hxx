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


#ifndef COMPARE_IMAGES_HXX_
#define COMPARE_IMAGES_HXX_

#include "project_definitions.hxx"
#include "cecog/basic/functors.hxx"

namespace cecog
{

  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class Iterator3, class Accessor3,
       class Iterator4, class Accessor4,
       class Iterator5, class Accessor5,
       class CompFunc>
  void ImCompare(Iterator1 srcUpperLeft1, Iterator1 srcLowerRight1, Accessor1 srca1,
            Iterator2 srcUpperLeft2, Accessor2 srca2,
              Iterator3 destUpperLeft, Accessor3 desta,
             Iterator4 trueUpperLeft, Accessor4 ta,
             Iterator5 falseUpperLeft, Accessor5 fa,
             CompFunc f)
  {
    vigra::Diff2D imSize = srcLowerRight1 - srcUpperLeft1;
    vigra::Diff2D o0(0,0);

    for(o0.y = 0; o0.y < imSize.y; ++o0.y)
    {
      for(o0.x = 0; o0.x < imSize.x; ++o0.x)
      {
        if(f(srca1(srcUpperLeft1, o0), srca2(srcUpperLeft2, o0)))
          desta.set(ta(trueUpperLeft, o0), destUpperLeft, o0);
        else
          desta.set(fa(falseUpperLeft, o0), destUpperLeft, o0);
      }
    }
  }

  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class Iterator3, class Accessor3,
       class Iterator4, class Accessor4,
       class Iterator5, class Accessor5,
       class CompFunc>
  void ImCompare(vigra::triple<Iterator1, Iterator1, Accessor1> src1,
           vigra::pair<Iterator2, Accessor2> src2,
           vigra::pair<Iterator3, Accessor3> dest,
           vigra::pair<Iterator4, Accessor4> tval,
           vigra::pair<Iterator5, Accessor5> fval,
           CompFunc f)
  {
    ImCompare(src1.first, src1.second, src1.third,
          src2.first, src2.second,
          dest.first, dest.second,
          tval.first, tval.second,
          fval.first, fval.second,
          f);
  }


  // ImCompare comes in different versions:
  // - imin1: always an image (input image)
  // - imout: always an image  (output image)
  // - all other parameters can switch between a numeric constant and an image.
  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           typename Image1::value_type compVal,
           Image3 & imout,
             typename Image3::value_type trueVal,
             typename Image3::value_type falseVal,
             CompFunc f)
  {
    typedef typename Image3::value_type ValueType;
    typedef typename Image1::value_type CompValType;

    ImCompare(vigra::srcImageRange(imin1),
           vigra::srcIter(vigra::ConstValueIterator<CompValType>(compVal)),
          vigra::destImage(imout),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(trueVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(falseVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          f);
  }


  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           const Image1 & imin2,
           Image3 & imout,
             typename Image3::value_type trueVal,
             typename Image3::value_type falseVal,
             CompFunc f)
  {
    typedef typename Image3::value_type ValueType ;

    ImCompare(vigra::srcImageRange(imin1),
          vigra::srcImage(imin2),
          vigra::destImage(imout),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(trueVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(falseVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          f);
  }

  // trueVal is an image
  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           typename Image1::value_type compVal,
           Image3 & imout,
             const Image3 & trueVal,
             typename Image3::value_type falseVal,
             CompFunc f)
  {
    typedef typename Image1::value_type CompValType;
    typedef typename Image3::value_type ValueType;

    ImCompare(vigra::srcImageRange(imin1),
           vigra::srcIter(vigra::ConstValueIterator<CompValType>(compVal)),
          vigra::destImage(imout),
          vigra::srcImage(trueVal),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(falseVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          f);
  }

  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           const Image1 & imin2,
           Image3 & imout,
             const Image3 & trueVal,
             typename Image3::value_type falseVal,
             CompFunc f)
  {
    typedef typename Image3::value_type ValueType;

    ImCompare(vigra::srcImageRange(imin1),
          vigra::srcImage(imin2),
          vigra::destImage(imout),
          vigra::destImage(trueVal),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(falseVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          f);
  }

  // falseVal is an image
  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           typename Image1::value_type compVal,
           Image3 & imout,
             typename Image3::value_type trueVal,
             const Image3 & falseVal,
             CompFunc f)
  {
    typedef typename Image1::value_type CompValType;
    typedef typename Image3::value_type ValueType;

    ImCompare(vigra::srcImageRange(imin1),
           vigra::srcIter(vigra::ConstValueIterator<CompValType>(compVal)),
          vigra::destImage(imout),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(trueVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          vigra::srcImage(falseVal),
          f);
  }

  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           const Image1 & imin2,
           Image3 & imout,
             typename Image3::value_type trueVal,
             const Image3 & falseVal,
             CompFunc f)
  {
    typedef typename Image3::value_type ValueType;

    ImCompare(vigra::srcImageRange(imin1),
          vigra::srcImage(imin2),
          vigra::destImage(imout),
          vigra::srcIter(vigra::ConstValueIterator<ValueType>(trueVal)), //vigra::StandardConstValueAccessor<Image3::value_type>),
          vigra::srcImage(falseVal),
          f);
  }

  // trueVal is an image
  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           typename Image1::value_type compVal,
           Image3 & imout,
             const Image3 & trueVal,
             const Image3 & falseVal,
             CompFunc f)
  {
    typedef typename Image1::value_type CompValType;

    ImCompare(vigra::srcImageRange(imin1),
           vigra::srcIter(vigra::ConstValueIterator<CompValType>(compVal)),
          vigra::destImage(imout),
          vigra::srcImage(trueVal),
          vigra::srcImage(falseVal),
          f);
  }

  template<class Image1,
       class Image3,
       class CompFunc>
  void ImCompare(const Image1 & imin1,
           const Image1 & imin2,
           Image3 & imout,
             const Image3 & trueVal,
             const Image3 & falseVal,
             CompFunc f)
  {
    ImCompare(vigra::srcImageRange(imin1),
          vigra::srcImage(imin2),
          vigra::destImage(imout),
          vigra::srcImage(trueVal),
          vigra::srcImage(falseVal),
          f);
  }

};
#endif /*COMPARE_IMAGES_HXX_*/
