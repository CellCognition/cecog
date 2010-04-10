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


#ifndef MORPHO_SKELETON_HXX_
#define MORPHO_SKELETON_HXX_

#include "project_definitions.hxx"
#include "vigra/distancetransform.hxx"

namespace cecog {
namespace morpho {

    // simpleEight: functor for the calculation of a homotopic skeleton.
    template<class Image>
    class simpleEight
    {
        public:

        typedef typename Image::Accessor Accessor;
        typedef typename Image::Iterator Iterator;
        typedef typename neighborhood2D::ITERATORTYPE nb_iterator_type;

        simpleEight(vigra::Diff2D imgSize): nb(WITHOUTCENTER8, imgSize)
        {}

        const neighborhood2D nb;
        Accessor ima;

        bool operator()(const Iterator & destUpperLeft, const vigra::Diff2D offset)
        {
            // for pixels on the image border, we cannot decide if
            // they are simple or not. Therefore they are considered
            // as not simple. The best is to make sure that the binary image
            // for which the skeleton is calculated has a 1 pixel wide margin.
            if(!nb.isBorderOrOutsidePixel(offset))
            {
                if(ima(destUpperLeft) != 0)
                {
                    for(int i = 0; i != nb.numberOfPixels(); ++i)
                    {
                        if( (ima(destUpperLeft + nb[i]) == 0) &&
                            (ima(destUpperLeft + nb[(i + 1) % nb.numberOfPixels()]) == 0) &&
                            (ima(destUpperLeft + nb[(i + 2) % nb.numberOfPixels()]) == 0) &&
                            (ima(destUpperLeft + nb[(i + 4) % nb.numberOfPixels()]) != 0) &&
                            (ima(destUpperLeft + nb[(i + 5) % nb.numberOfPixels()]) != 0) &&
                            (ima(destUpperLeft + nb[(i + 6) % nb.numberOfPixels()]) != 0) )
                         {
                            return true;
                         }
                    }
                }
            }
            return false;
        }
    };


    // ImAnchoredSkeleton: calculates a fast skeleton of a binary image.
    // first image: binary input image for which the skeleton is to be calculated.
    // second image: output image
    // third image: anchor image containing the pixels which should not be removed
    // of the input image; for instance the skeleton of maximal balls.
    // isSimplePoint is the functor to be used (different for different connections).
    // The connection (neighborhood) is defined in the isSimplePoint functor.
    // Example: simpleEight<cecog::Image<8> > simpleFunc(info.size());
    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class Iterator3, class Accessor3,
             class Functor >
    void ImAnchoredSkeleton(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                            Iterator2 destUpperLeft, Accessor2 desta,
                            Iterator3 ancUpperLeft, Accessor3 anca,
                            Functor isSimplePoint)
    {
        typedef typename Functor::nb_iterator_type ITERATORTYPE;
        typedef typename Accessor1::value_type value_type;

        const value_type in_queue = 1;
        using vigra::Diff2D;

        std::queue<Diff2D> Q;

        vigra::Diff2D o0(0,0);
        vigra::Diff2D imgSize = srcLowerRight - srcUpperLeft;

        Iterator1 srcul(srcUpperLeft);
        Iterator2 destul(destUpperLeft);
        Iterator3 ancul(ancUpperLeft);

        // initialization
        for(o0.y = 0; o0.y != imgSize.y; ++srcul.y, ++destul.y, ++ancul.y, ++o0.y)
        {
            Iterator1 scurrent(srcul);
            Iterator2 dcurrent(destul);
            Iterator3 acurrent(ancul);
            for(o0.x = 0; o0.x != imgSize.x; ++scurrent.x, ++dcurrent.x, ++acurrent.x, ++o0.x)
            {
                value_type value=srca(scurrent);
                desta.set(value, dcurrent);

                if( (value > 0) && (!anca(acurrent)) )
                {
                    // if the pixel is not set in the anchor image,
                    // the pixel is put into the queue, if it has
                    // a neighbor not belonging to the object.
                    bool destructible = isSimplePoint(scurrent, o0);
                    if(destructible)
                    {
                        Q.push(o0);
                        desta.set(in_queue, dcurrent);
                    }

                }
            } // end for x
        } // end for y


        // entering the queue
        while(!Q.empty())
        {
            Diff2D o0 = Q.front(); Q.pop();

            Iterator2 currentIterator = destUpperLeft + o0;

            if(desta(currentIterator))
            {
                bool destructible = isSimplePoint(currentIterator, o0);

                if(destructible && !anca(ancUpperLeft, o0))
                {
                    desta.set(0, destUpperLeft, o0);
                    for(ITERATORTYPE iter = isSimplePoint.nb.begin();
                        iter != isSimplePoint.nb.end();
                        ++iter)
                    {
                        vigra::Diff2D o1 = o0 + *iter;

                        if( (desta(destUpperLeft, o1) != in_queue) &&
                            (isSimplePoint((destUpperLeft + o1), o1)) )
                        {
                            Q.push(o1);
                            desta.set(in_queue, destUpperLeft, o1);
                        }
                    }
                } // end if: destructible
                else
                    desta.set(255, currentIterator);
            } // end if dest(currentIterator)

        } // end while Q


        // final loop
        Iterator2 destLowerRight(destUpperLeft + imgSize);
        for(o0.y = 0; destUpperLeft.y != destLowerRight.y; ++destUpperLeft.y, ++o0.y)
        {
            Iterator2 dcurrent(destUpperLeft);
            for(o0.x = 0; dcurrent.x != destLowerRight.x; ++dcurrent.x, ++o0.x)
            {
                if(desta(dcurrent) && isSimplePoint(dcurrent, o0))
                   desta.set(0, dcurrent);
            } // end for x
        } // end for y
    }

    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class NBTYPE>
    void ImMaxBallSkeletonFromDistanceFunction(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                                               Iterator2 destUpperLeft, Accessor2 desta,
                                               NBTYPE nb,
                                               typename Accessor1::value_type markValue=255)
    {
        typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
        typedef typename Accessor1::value_type value_type;
        vigra::Diff2D o0(0,0);
        vigra::Diff2D imgSize = srcLowerRight - srcUpperLeft;

        for(o0.y = 0; o0.y != imgSize.y; ++o0.y)
        {
            for(o0.x = 0; o0.x != imgSize.x; ++o0.x)
            {
                value_type value=srca(srcUpperLeft, o0);

                if(value > 0)
                {
                    unsigned counter=0;
                    for(ITERATORTYPE iter = nb.begin();
                        iter != nb.end();
                        ++iter)
                    {
                        vigra::Diff2D o1 = o0 + *iter;
                        if(!nb.isOutsidePixel(o1))
                        {
                            value_type nbval(srca(srcUpperLeft, o1));
                            if(nbval <= value)
                                counter++;
                            else
                                break;
                        }
                    }
                    if(counter == nb.numberOfPixels() )
                        desta.set(markValue, destUpperLeft, o0);
                }
            }
        }

    }

    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class Iterator3, class Accessor3,
             class Functor>
    void ImAnchoredSkeleton(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                            vigra::pair<Iterator2, Accessor2> dest,
                            vigra::pair<Iterator3, Accessor3> anc,
                            Functor isSimplePoint)
    {
        ImAnchoredSkeleton(src.first, src.second, src.third,
                           dest.first, dest.second,
                           anc.first, anc.second,
                           isSimplePoint);
    }

    template<class Image1, class Image2, class Image3, class Functor>
    void ImAnchoredSkeleton(Image1 &imin, Image2 &imout, Image3 &anchor,
                            Functor isSimplePoint)
    {
        ImAnchoredSkeleton(srcImageRange(imin), destImage(imout), srcImage(anchor),
                           isSimplePoint);
    }


    ////////////////////////////////////////
    // ImMaxBallSkeletonFromDistanceFunction
    template<class Iterator1, class Accessor1,
             class Iterator2, class Accessor2,
             class NBTYPE>
    void ImMaxBallSkeletonFromDistanceFunction(
        vigra::triple<Iterator1, Iterator1, Accessor1> src,
        vigra::pair<Iterator2, Accessor2> dest,
        NBTYPE & neighborOffset,
        typename Accessor1::value_type markVal=255
        )
    {
        ImMaxBallSkeletonFromDistanceFunction(src.first, src.second, src.third,
                                              dest.first, dest.second,
                                              neighborOffset, markVal);
    }

    ////////////////////////////////////////
    // ImMaxBallSkeletonFromDistanceFunction
    template<class Image1, class Image2>
    void ImMaxBallSkeleton(const Image1 &imin, Image2 &imout, int norm=1)
    {

        vigra::IImage distance(imin.size());

        vigra::distanceTransform(srcImageRange(imin), destImage(distance), 255, norm);

        globalDebEnv.DebugWriteImage(distance, "distance");

        neighborhood2D nb(WITHOUTCENTER8, distance.size());
        ImMaxBallSkeletonFromDistanceFunction(srcImageRange(distance),
                                              destImage(imout), nb, 255);
    }


};
};

#endif /*MORPHO_SKELETON_HXX_*/
