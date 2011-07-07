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


#ifndef MORPHO_GEODESY_HXX_
#define MORPHO_GEODESY_HXX_

#include "project_definitions.hxx"

#include "cecog/morpho/structuring_elements.hxx"
#include "cecog/basic/functors.hxx"

#include "vigra/pixelneighborhood.hxx"

namespace cecog {
namespace morpho {

  #define PIXELDONE 1
  #define PIXELUNDONE 0

  ///////////////////////////////////////////
  // MIN AND MAX: label/stack
  ///////////////////////////////////////////
  template<class Iterator1, class Accessor1,
       class Functor, class NBTYPE>
  void ImMinMaxStack(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
             Functor f,
             NBTYPE & nbOffset,
             std::stack<vigra::Diff2D> & resStack)
  {
    std::queue<Diff2D> Q;

    int width  = srcLowerRight.x - srcUpperLeft.x;
      int height = srcLowerRight.y - srcUpperLeft.y;

    typedef typename Accessor1::value_type VALUETYPE;
    typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
    typedef typename NBTYPE::SIZETYPE SIZETYPE;

    //cecog::Image<8> controlImage(width, height);
    //cecog::Image<8>::Iterator controlUpperLeft = controlImage.upperLeft();

    vigra::BImage controlImage(width, height);
    vigra::BImage::Iterator controlUpperLeft = controlImage.upperLeft();
    vigra::BImage::Accessor ca;

    Diff2D o0(0,0);

    for(o0.y = 0; o0.y < height; ++o0.y)
    {
      for(o0.x = 0; o0.x < width; ++o0.x)
      {
        if(ca(controlUpperLeft,o0) == PIXELUNDONE)
        {
          bool minmax = true;
          ca.set(PIXELDONE, controlUpperLeft, o0);
          Q.push(o0);
          while(!Q.empty())
          {
            // take the first pixel out of the queue.
            Diff2D o1 = Q.front(); Q.pop();

            // look to the neighborhood.
            for(ITERATORTYPE iter = nbOffset.begin();
              iter != nbOffset.end();
              ++iter)
            {
              Diff2D o2 = o1 + *iter;

              // if the neighbor is not outside the image
              if(!nbOffset.isOutsidePixel(o2))
              {
                VALUETYPE val_o1 = srca(srcUpperLeft,o1);
                VALUETYPE val_o2 = srca(srcUpperLeft,o2);
                if(f(val_o2, val_o1))
                  minmax = false;
                if( val_o1 == val_o2 && (ca(controlUpperLeft,o2) == PIXELUNDONE))
                {
                  ca.set(PIXELDONE, controlUpperLeft, o2);
                  Q.push(o2);
                }
              }  // end if not outside pixel
            }  // end for (neighborhood)
          } // end while !Q.empty()
          if(minmax)
            resStack.push(o0);
        } // end if controlimage != DONE
      } // end x-loop
    }  // end y-loop
  } // end of function ImMinMaxStack


        ///////////////////////////////////////////
    // MIN AND MAX: label/stack with mask
    ///////////////////////////////////////////
    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class Functor, class NBTYPE>
    void ImMinMaxStack(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                       Iterator2 maskUpperLeft, Accessor2 maska,
                       Functor f,
                       NBTYPE & nbOffset,
                       std::stack<vigra::Diff2D> & resStack,
                       typename Accessor2::value_type maskLabel)
    {
        std::queue<Diff2D> Q;

        int width  = srcLowerRight.x - srcUpperLeft.x;
        int height = srcLowerRight.y - srcUpperLeft.y;

        typedef typename Accessor1::value_type VALUETYPE;
        typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
        typedef typename NBTYPE::SIZETYPE SIZETYPE;

        //cecog::Image<8> controlImage(width, height);
        //cecog::Image<8>::Iterator controlUpperLeft = controlImage.upperLeft();

        vigra::BImage controlImage(width, height);
        vigra::BImage::Iterator controlUpperLeft = controlImage.upperLeft();
        vigra::BImage::Accessor ca;

        Diff2D o0(0,0);

        for(o0.y = 0; o0.y < height; ++o0.y)
        {
            for(o0.x = 0; o0.x < width; ++o0.x)
            {
                if( (maska(maskUpperLeft, o0) == maskLabel)
                    && (ca(controlUpperLeft,o0) == PIXELUNDONE) )
                {
                    bool minmax = true;
                    ca.set(PIXELDONE, controlUpperLeft, o0);
                    Q.push(o0);
                    while(!Q.empty())
                    {
                        // take the first pixel out of the queue.
                        Diff2D o1 = Q.front(); Q.pop();

                        // look to the neighborhood.
                        for(ITERATORTYPE iter = nbOffset.begin();
                            iter != nbOffset.end();
                            ++iter)
                        {
                            Diff2D o2 = o1 + *iter;

                            // if the neighbor is not outside the image
                            if( (!nbOffset.isOutsidePixel(o2)) &&
                                (maska(maskUpperLeft, o2) == maskLabel) )
                            {
                                VALUETYPE val_o1 = srca(srcUpperLeft,o1);
                                VALUETYPE val_o2 = srca(srcUpperLeft,o2);
                                if(f(val_o2, val_o1))
                                    minmax = false;
                                if( val_o1 == val_o2 && (ca(controlUpperLeft,o2) == PIXELUNDONE))
                                {
                                    ca.set(PIXELDONE, controlUpperLeft, o2);
                                    Q.push(o2);
                                }
                            }  // end if not outside pixel
                        }  // end for (neighborhood)
                    } // end while !Q.empty()
                    if(minmax)
                        resStack.push(o0);
                } // end if controlimage != DONE
            } // end x-loop
        }  // end y-loop
    } // end of function ImMinMaxStack


  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class Functor, class NBTYPE>
  int ImMinMaxLabel(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
             Iterator2 destUpperLeft, Accessor2 desta,
             Functor f,
             NBTYPE & nbOffset)
  {
    std::stack<Diff2D> resStack;
    std::queue<Diff2D> Q;

    typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
    typedef typename NBTYPE::SIZETYPE SIZETYPE;

    // puts one point per maximum/minimum into the stack.
    ImMinMaxStack(srcUpperLeft, srcLowerRight, srca,
               f, nbOffset, resStack);

    int maxLabel = resStack.size();
    int numberOfMinMax = maxLabel;

    if(maxLabel > pow(2, 8* sizeof(typename Accessor2::value_type)) - 1)
    {
      cout << "warning in ImMinMaxLabel: unappropriate output image value type." << endl;
      maxLabel = 1;
    }

    typedef typename Accessor2::value_type OUTTYPE;

    while(!resStack.empty())
    {
      Diff2D o0 = resStack.top();
      resStack.pop();
      desta.set(maxLabel, destUpperLeft, o0);
      Q.push(o0);
      while(!Q.empty())
      {
        // take the first pixel out of the queue.
        Diff2D o1 = Q.front(); Q.pop();

        // look to the neighborhood.
        for(ITERATORTYPE iter = nbOffset.begin();
          iter != nbOffset.end();
          ++iter)
        {
          Diff2D o2 = o1 + *iter;
          if(!nbOffset.isOutsidePixel(o2))
          {
            if( (srca(srcUpperLeft,o1) == srca(srcUpperLeft,o2)) && (desta(destUpperLeft,o2) == PIXELUNDONE))
            {
              desta.set((OUTTYPE)maxLabel, destUpperLeft, o2);
              Q.push(o2);
            }
          }
        } // end of for (neighborhood)
      } // end of while (queue)
      maxLabel = std::max(maxLabel-1, 1);
    } // end of while (stack)

    return(numberOfMinMax);
  }  // end function


    ///////////////////////////
    // Im MinMaxLabel with mask
    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class Iterator3, class Accessor3,
             class Functor, class NBTYPE>
    int ImMinMaxLabel(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                      Iterator2 destUpperLeft, Accessor2 desta,
                      Iterator3 maskUpperLeft, Accessor3 maska,
                      Functor f,
                      NBTYPE & nbOffset,
                      typename Accessor3::value_type maskLabel)
    {
        std::stack<Diff2D> resStack;
        std::queue<Diff2D> Q;

        typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
        typedef typename NBTYPE::SIZETYPE SIZETYPE;

        // puts one point per maximum/minimum into the stack.
        ImMinMaxStack(srcUpperLeft, srcLowerRight, srca,
                      maskUpperLeft, maska,
                      f, nbOffset, resStack,
                      maskLabel);

        int maxLabel = resStack.size();
        int numberOfMinMax = maxLabel;

        if(maxLabel > pow((double)2, (int)(8* sizeof(typename Accessor2::value_type)) - 1))
        {
            cout << "warning in ImMinMaxLabel: unappropriate output image value type." << endl;
            maxLabel = 1;
        }

        typedef typename Accessor2::value_type OUTTYPE;

        while(!resStack.empty())
        {
            Diff2D o0 = resStack.top();
            resStack.pop();
            desta.set(maxLabel, destUpperLeft, o0);
            Q.push(o0);
            while(!Q.empty())
            {
                // take the first pixel out of the queue.
                Diff2D o1 = Q.front(); Q.pop();

                // look to the neighborhood.
                for(ITERATORTYPE iter = nbOffset.begin();
                    iter != nbOffset.end();
                    ++iter)
                {
                    Diff2D o2 = o1 + *iter;
                    if( (!nbOffset.isOutsidePixel(o2)) &&
                        (maska(maskUpperLeft, o2) == maskLabel) )
                    {
                        if( (srca(srcUpperLeft,o1) == srca(srcUpperLeft,o2)) && (desta(destUpperLeft,o2) == PIXELUNDONE))
                        {
                            desta.set((OUTTYPE)maxLabel, destUpperLeft, o2);
                            Q.push(o2);
                        }
                    }
                } // end of for (neighborhood)
            } // end of while (queue)
            maxLabel = std::max(maxLabel-1, 1);
        } // end of while (stack)

        return(numberOfMinMax);
    }  // end function


  ////////////////////////////////////////////////////////////////////////////////////

  ////////////////
  // ImMinimaStack
  template<class Iterator1, class Accessor1, class NBTYPE>
  void ImMinimaStack(vigra::triple<Iterator1, Iterator1, Accessor1> src,
               NBTYPE & neighborOffset,
               std::stack<vigra::Diff2D> & resultStack)
  {

    ImMinMaxStack(src.first, src.second, src.third,
               IsSmaller<typename Accessor1::value_type, typename Accessor1::value_type>(),
               neighborOffset,
               resultStack);

  }

  ////////////////
  // ImMaximaStack
  template<class Iterator1, class Accessor1, class NBTYPE>
  void ImMaximaStack(vigra::triple<Iterator1, Iterator1, Accessor1> src,
               NBTYPE & neighborOffset,
               std::stack<Diff2D> & resultStack)
  {
    ImMinMaxStack(src.first, src.second, src.third,
               IsGreater<typename Accessor1::value_type, typename Accessor1::value_type>(),
               neighborOffset,
               resultStack);
  }

  ////////////////
  // ImMinimaLabel
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  int ImMinimaLabel(vigra::triple<Iterator1, Iterator1, Accessor1> src,
               vigra::pair<Iterator2, Accessor2> dest,
               NBTYPE & neighborOffset)
  {

    return(ImMinMaxLabel(src.first, src.second, src.third,
                     dest.first, dest.second,
                    IsSmaller<typename Accessor1::value_type, typename Accessor1::value_type>(),
                    neighborOffset));
  }

    //////////////////////////
    // ImMinimaLabel with mask
    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class NBTYPE>
    int ImMinimaLabel(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                       vigra::pair<Iterator2, Accessor2> dest,
                       NBTYPE & neighborOffset,
                       typename Accessor2::value_type maskLabel = 255)
    {

        return(ImMinMaxLabel(src.first, src.second, src.third,
                             dest.first, dest.second,
                             IsSmaller<typename Accessor1::value_type, typename Accessor1::value_type>(),
                             neighborOffset,
                             maskLabel));
    }

  ////////////////
  // ImMaximaLabel
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  int ImMaximaLabel(vigra::triple<Iterator1, Iterator1, Accessor1> src,
               vigra::pair<Iterator2, Accessor2> dest,
               NBTYPE & neighborOffset)
  {

    return(ImMinMaxLabel(src.first, src.second, src.third,
                     dest.first, dest.second,
                    IsGreater<typename Accessor1::value_type, typename Accessor1::value_type>(),
                   neighborOffset) );
  }

    //////////////////////////
    // ImMaximaLabel with mask
    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class Iterator3, class Accessor3,
             class NBTYPE>
    int ImMaximaLabel(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                       vigra::pair<Iterator2, Accessor2> dest,
                       vigra::pair<Iterator3, Accessor3> mask,
                       NBTYPE & neighborOffset,
                       typename Accessor2::value_type maskLabel = 255)
    {

        return(ImMinMaxLabel(src.first, src.second, src.third,
                             dest.first, dest.second,
                             mask.first, mask.second,
                             IsGreater<typename Accessor1::value_type, typename Accessor1::value_type>(),
                             neighborOffset,
                             maskLabel) );
    }

  /////////////////
  // reconstruction
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE,
       class Functor1,
       class Functor2,
       class PriorFunctor>
  void ImReconstruction(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                 Iterator2 maskUpperLeft, Accessor2 maska,
                NBTYPE nbOffset,
                Functor1 minmax, Functor2 maskOp, PriorFunctor priority)
  {
    typedef typename Accessor1::value_type VALUETYPE;
    typedef Pixel2D<VALUETYPE> PIX;
    std::priority_queue<PIX, std::vector<PIX>, PriorFunctor> PQ(priority);

    std::stack<vigra::Diff2D> maxStack;

    int width  = srcLowerRight.x - srcUpperLeft.x;
      int height = srcLowerRight.y - srcUpperLeft.y;
    unsigned long insertionOrder = 0;

    vigra::BImage controlImage(width, height);
    vigra::BImage::Iterator controlUpperLeft = controlImage.upperLeft();
    vigra::BImage::Accessor ca;

    typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
    typedef typename NBTYPE::SIZETYPE SIZETYPE;

    // the functor minmax is:
    // - for underbuild : isGreaterFunctor
    // - for overbuild  : isSmallerFunctor
    ImMinMaxStack(srcUpperLeft, srcLowerRight, srca,
               minmax, nbOffset,
               maxStack);

    // The minima are written to a priority queue.
    // for overbuild, the priorities has to be negative.
    while(!maxStack.empty())
    {
      Diff2D o0 = maxStack.top();
      maxStack.pop();
      PIX px(srca(srcUpperLeft, o0), o0, insertionOrder++);
      PQ.push(px);
    }

    // loop on the priority queue
    while(!PQ.empty())
    {
      PIX px = PQ.top();
      PQ.pop();

      // the value is set to the max<for underbuild>/min<for overbuild>
      // of priority and actual value.
      // in this way we avoid that a pixel can obtain a lower/higher
      // value as it has obtained already (from a different maximum/minimum).
      // maskOp is minimum for underbuild and maximum for overbuild.
      // px.value is the actual priority of the pixel.
      // the functor minmax is:
      // - for underbuild : isGreaterFunctor
      // - for overbuild  : isSmallerFunctor
      if(minmax(px.value, srca(srcUpperLeft, px.offset)))
        srca.set(px.value, srcUpperLeft, px.offset);

      for(ITERATORTYPE iter = nbOffset.begin();
        iter != nbOffset.end();
        ++iter)
      {
        Diff2D o1 = px.offset + *iter;
        if(    (!nbOffset.isOutsidePixel(o1))
            && (ca(controlUpperLeft, o1) != PIXELDONE) )
        {
          //PQ.push(PIX(std::min(srca(srcUpperLeft, px.offset), maska(maskUpperLeft, o1) ), o1));
          PQ.push(PIX(maskOp(srca(srcUpperLeft, px.offset), maska(maskUpperLeft, o1)), o1, insertionOrder++ ));
          ca.set(PIXELDONE, controlUpperLeft, o1);
        }
      }
    }
  }

  /////////////////
  // underbuild
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  void ImUnderBuild(vigra::triple<Iterator1, Iterator1, Accessor1> src,
              vigra::pair<Iterator2, Accessor2> mask,
              NBTYPE & neighborOffset)
  {
    ImReconstruction(src.first, src.second, src.third,
                   mask.first, mask.second, neighborOffset,
                   IsGreater<typename Accessor1::value_type, typename Accessor1::value_type>(),
                   MinFunctor<typename Accessor1::value_type>(),
//                   Pixel2D<typename Accessor1::value_type>::PriorityTopDown());
                   PriorityTopDown<typename Accessor1::value_type>());
  }

  /////////////////
  // overbuild
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  void ImOverBuild(vigra::triple<Iterator1, Iterator1, Accessor1> src,
              vigra::pair<Iterator2, Accessor2> mask,
              NBTYPE & neighborOffset)
  {
    ImReconstruction(src.first, src.second, src.third,
                   mask.first, mask.second, neighborOffset,
                   IsSmaller<typename Accessor1::value_type, typename Accessor1::value_type>(),
                   MaxFunctor<typename Accessor1::value_type>(),
//                   Pixel2D<typename Accessor1::value_type>::PriorityBottomUp());
                   PriorityBottomUp<typename Accessor1::value_type>());
  }

  //////////////////
  // Close by recons
  template<class Image1, class Image2,
       class SETYPE, class NBTYPE>
  void ImCloseByRecons(Image1 & src,
                Image2 & dest,
                SETYPE & SE,
                NBTYPE & neighborOffset)
  {
    ImDilate(srcImageRange(src), destImageRange(dest), SE);
    ImOverBuild(destImageRange(dest), srcImage(src), neighborOffset);
  }

  //////////////////
  // Open by recons
  template<class Image1, class Image2,
       class SETYPE, class NBTYPE>
  void ImOpenByRecons(Image1 & src,
               Image2 & dest,
               SETYPE & SE,
               NBTYPE & neighborOffset)
  {
    ImErode(srcImageRange(src), destImageRange(dest), SE);
    ImUnderBuild(destImageRange(dest), srcImage(src), neighborOffset);
  }

  //////////////////
  // dynamic filtering
  template<class Image1, class Image2, class NBTYPE>
  void ImDynamicOpen(Image1 & src,
               Image2 & dest,
               typename Image1::value_type h,
               NBTYPE & neighborOffset)
  {
    minusConstantClipp<typename Image1::value_type> f(h);
    transformImage(srcImageRange(src), destImage(dest), f);
    ImUnderBuild(destImageRange(dest), srcImage(src), neighborOffset);
  }

  template<class Image1, class Image2, class NBTYPE>
  void ImDynamicClose(Image1 & src,
                Image2 & dest,
                typename Image1::value_type h,
                NBTYPE & neighborOffset)
  {
    plusConstantClipp<typename Image1::value_type> f(h);
    transformImage(srcImageRange(src), destImage(dest), f);
    ImOverBuild(destImageRange(dest), srcImage(src), neighborOffset);
  }

  template<class Image1, class Image2, class NBTYPE>
  int ImMaximaLabel(const Image1 & imin, Image2 & imout, NBTYPE & neighborOffset)
  {
    return(ImMaximaLabel(srcImageRange(imin), destImage(imout), neighborOffset) );
  }

  template<class Image1, class Image2, class NBTYPE>
  int ImMinimaLabel(const Image1 & imin, Image2 & imout, NBTYPE & neighborOffset)
  {
    return(ImMinimaLabel(srcImageRange(imin), destImage(imout), neighborOffset) );
  }

  template<class Image1, class Image2, class NBTYPE>
  void ImOverBuild(Image1 & iminout, const Image2 & mask, NBTYPE & neighborOffset)
  {
    ImOverBuild(destImageRange(iminout), srcImage(mask), neighborOffset);
  }

  template<class Image1, class Image2, class NBTYPE>
  void ImUnderBuild(Image1 & iminout, const Image2 & mask, NBTYPE & neighborOffset)
  {
    ImUnderBuild(destImageRange(iminout), srcImage(mask), neighborOffset);
  }

  template<class Image1, class NBTYPE>
  void ImLevelling(const Image1 &imin, Image1 &filtered, Image1 &imout, NBTYPE &neighborOffset)
  {
    typedef typename Image1::value_type value_type;
    value_type maxVal = (value_type)(Image1::PixelTypeTraits::greylevels - 1);

    Image1 marker1(imin.size()), marker2(imin.size());

    ImCompare(vigra::srcImageRange(imin),
          vigra::srcImage(filtered),
          vigra::destImage(marker1),
          vigra::srcImage(filtered),
          vigra::srcIter(vigra::ConstValueIterator<value_type>(0)),
          IsGreater<value_type, value_type>());
    ImUnderBuild(destImageRange(marker1), srcImage(imin), neighborOffset);

    ImCompare(vigra::srcImageRange(imin),
          vigra::srcImage(filtered),
          vigra::destImage(marker2),
          vigra::srcIter(vigra::ConstValueIterator<value_type>(maxVal)),
          vigra::srcImage(filtered),
          IsGreater<value_type, value_type>());
    ImOverBuild(destImageRange(marker2), srcImage(imin), neighborOffset);

    ImCompare(vigra::srcImageRange(imin),
          vigra::srcImage(filtered),
          vigra::destImage(imout),
          vigra::srcImage(marker1),
          vigra::srcImage(marker2),
          IsGreater<value_type, value_type>()
          );


//    ImCompare(imin, filtered, imout, marker1, marker2,
//          IsGreater<value_type, value_type>());
    return;

  }
};
};

#endif /*MORPHO_GEODESY_HXX_*/
