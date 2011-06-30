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


#ifndef MORPHO_WATERSHED_HXX_
#define MORPHO_WATERSHED_HXX_

namespace cecog {
namespace morpho{

  //////////////////
  // ImWatershed
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE,
       class MinmaxFunctor,
       class PriorityFunctor>
  void ImWatershed(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
           Iterator2 destUpperLeft, Accessor2 desta,
           NBTYPE & nbOffset,
           MinmaxFunctor minmax,
           PriorityFunctor priority
           )
  {
    clock_t startTime = clock();

    // for the work image (negative labels are allowed)
    const int WS_QUEUED = -1;
    const int WS_NOT_PROCESSED = 0;
    const int WS_WSLABEL = -2;
    // for the output image: negative labels are not allowed).
    const int OUT_WSLABEL = 0;

    unsigned long insertionOrder = 0;

    typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
    typedef typename NBTYPE::SIZETYPE SIZETYPE;
    typedef typename Accessor1::value_type VALUETYPE;

    typedef Pixel2D<VALUETYPE> PIX;


    int width  = srcLowerRight.x - srcUpperLeft.x;
    int height = srcLowerRight.y - srcUpperLeft.y;

    vigra::BasicImage<int> labelImage(width, height);
    vigra::BasicImage<int>::Iterator labUpperLeft = labelImage.upperLeft();
    vigra::BasicImage<int>::Accessor lab;
    typedef int LABTYPE;

    ImMinMaxLabel(srcUpperLeft, srcLowerRight, srca,
                 labUpperLeft, lab,
               minmax,
               nbOffset);

    std::priority_queue<PIX, std::vector<PIX>, PriorityFunctor> PQ(priority);
    std::queue<Diff2D> Q;

    Diff2D o0(0,0);

    VALUETYPE maxval = srca(srcUpperLeft, o0);

    // initialization of the hierarchical queue
    for(o0.y = 0; o0.y < height; ++o0.y)
    {
      for(o0.x = 0; o0.x < width; ++o0.x)

      {

        maxval = std::max(srca(srcUpperLeft, o0), maxval);

        LABTYPE label = lab(labUpperLeft, o0);
        desta.set(label, destUpperLeft, o0);
        if(label > WS_NOT_PROCESSED)
        {
          // look to the neighborhood.
          for(ITERATORTYPE iter = nbOffset.begin();
            iter != nbOffset.end();
            ++iter)
          {
            Diff2D o1 = o0 + *iter;
            // if the neighbor is not outside the image
            // and if it has no label and if it is not in the queue
            if(    (!nbOffset.isOutsidePixel(o1))
              && (lab(labUpperLeft, o1) == WS_NOT_PROCESSED))
            {
              VALUETYPE priority = std::max(srca(srcUpperLeft, o1), srca(srcUpperLeft, o0));
              PQ.push(PIX(priority, o1, insertionOrder++));
              lab.set(WS_QUEUED, labUpperLeft, o1);
            }
          } // end for neighborhood
        } // end if label
      } // end x-loop
    } // end y-loop

    // until the hierarchical queue is empty ...
    while(!PQ.empty())
    {
      PIX px = PQ.top();
      PQ.pop();
      Diff2D o0 = px.offset;

      // normal flooding procedure
      int label1 = WS_NOT_PROCESSED;
      int label2 = WS_NOT_PROCESSED;

      VALUETYPE currentval = px.value;

      // look to the neighborhood to determine the label of pixel o0.
      for(ITERATORTYPE iter = nbOffset.begin();
        iter != nbOffset.end();
        ++iter)
      {
        Diff2D o1 = o0 + *iter;
        if(!nbOffset.isOutsidePixel(o1))
        {
          LABTYPE label_o1 = lab(labUpperLeft, o1);
          // first case: pixel has not been processed.
          if(label_o1 == WS_NOT_PROCESSED)
          {
            VALUETYPE priority = std::max(srca(srcUpperLeft, o1), currentval);
            PQ.push(PIX(priority, o1, insertionOrder++));
            lab.set(WS_QUEUED, labUpperLeft, o1);
          }

          // second case: neighbor pixel is already in the queue:
          // nothing is to be done, then.

          // third case: the neighbor has a label
           if(label_o1 > WS_NOT_PROCESSED)
          {
            label2 = label_o1;

            if(label1 == 0)
            {
              // in this case, the label is the first
              // which has been found in the neighborhood.
              label1 = label2;

              lab.set(label1, labUpperLeft, o0);
              desta.set(label1, destUpperLeft, o0);
            }
            else
            {
              // in this case, a label has already been assigned to o0.
              // o0 is part of the watershed line.
              if(label1 != label2)
              {
                lab.set(WS_WSLABEL, labUpperLeft, o0);
                desta.set(OUT_WSLABEL, destUpperLeft, o0);
              }

            }

          }
        }
      } // end for neighborhood

      // if there was no label assigned to the pixel
      // (this can happen in some pathological but not uncommon situations)
      if(label1 == WS_NOT_PROCESSED)
      {
        if(currentval < maxval) {
            PQ.push(PIX(currentval+1, o0, insertionOrder++));
            lab.set(WS_QUEUED, labUpperLeft, o0);
        }
        else {
            Q.push(o0);
        }
      }

    } // end of PRIORITY QUEUE

    while(!Q.empty()) {
       Diff2D o0 = Q.front(); Q.pop();
       desta.set(OUT_WSLABEL, destUpperLeft, o0);
    }

  } // end of function

  /////////////////
  // Watershed
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  void ImWatershed(vigra::triple<Iterator1, Iterator1, Accessor1> src,
             vigra::pair<Iterator2, Accessor2> dest,
             NBTYPE & neighborOffset)
  {

    typedef typename Accessor1::value_type val_type;
    typedef Pixel2D<val_type> PIX;

    ImWatershed(src.first, src.second, src.third,
              dest.first, dest.second,
             neighborOffset,
              IsSmaller<typename Accessor1::value_type, typename Accessor1::value_type>(),
              PriorityBottomUp<val_type>());

  }

  template<class Image1, class Image2, class NBTYPE>
  void ImWatershed(const Image1 & imin, Image2 & imout, NBTYPE & nbOffset)
  {
    ImWatershed(srcImageRange(imin), destImage(imout), nbOffset);
  }

  /////////////////
  // Thalweg
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  void ImThalweg(vigra::triple<Iterator1, Iterator1, Accessor1> src,
           vigra::pair<Iterator2, Accessor2> dest,
           NBTYPE & neighborOffset)
  {
    typedef typename Accessor1::value_type val_type;
    typedef Pixel2D<val_type> PIX;

    ImWatershed(src.first, src.second, src.third,
              dest.first, dest.second,
              neighborOffset,
              IsGreater<val_type, val_type>(),
              PriorityTopDown<val_type>());
  }

  template<class Image1, class Image2, class NBTYPE>
  void ImThalweg(const Image1 & imin, Image2 & imout, NBTYPE & nbOffset)
  {
    ImThalweg(srcImageRange(imin), destImage(imout), nbOffset);
  }

  /////////////////////////
  // ImConstrainedWatershed
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class Iterator3, class Accessor3,
       class NBTYPE,
       class PriorityFunctor>
  void ImConstrainedWatershed(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                 Iterator2 markerUpperLeft, Iterator2 markerLowerRight, Accessor2 marka,
                 Iterator3 destUpperLeft, Accessor3 desta,
                 NBTYPE & nbOffset,
                 PriorityFunctor priority
                 )
  {
    // for the work image (negative labels are allowed)
    const int WS_QUEUED = -1;
    const int WS_NOT_PROCESSED = 0;
    const int WS_WSLABEL = -2;
    // for the output image: negative labels are not allowed).
    const int OUT_WSLABEL = 0;

    unsigned long insertionOrder = 0;

    typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
    typedef typename NBTYPE::SIZETYPE SIZETYPE;
    typedef typename Accessor1::value_type VALUETYPE;

    typedef Pixel2D<VALUETYPE> PIX;

    int width  = srcLowerRight.x - srcUpperLeft.x;
    int height = srcLowerRight.y - srcUpperLeft.y;

    vigra::BasicImage<int> labelImage(width, height);
    vigra::BasicImage<int>::Iterator labUpperLeft = labelImage.upperLeft();
    vigra::BasicImage<int>::Accessor lab;

    ImLabel(markerUpperLeft, markerLowerRight, marka,
        labUpperLeft, lab,
        nbOffset);

    std::priority_queue<PIX, std::vector<PIX>, PriorityFunctor> PQ(priority);
    std::queue<Diff2D> Q;

    Diff2D o0(0,0);

    VALUETYPE maxval = srca(srcUpperLeft, o0);

    // initialization of the hierarchical queue
    for(o0.y = 0; o0.y < height; ++o0.y)
    {
      for(o0.x = 0; o0.x < width; ++o0.x)
      {
        desta.set(lab(labUpperLeft, o0), destUpperLeft, o0);
        if(lab(labUpperLeft, o0) > WS_NOT_PROCESSED)
        {
          // look to the neighborhood.
          for(SIZETYPE i = 0; i < nbOffset.numberOfPixels(); ++i)
          {
            // if the neighbor is not outside the image
            // and if it has no label and if it is not in the queue
            if(    (!nbOffset.isOutsidePixel(o0, nbOffset[i]))
              && (lab(labUpperLeft, o0 + nbOffset[i]) == WS_NOT_PROCESSED))
            {
              Diff2D o1 = o0 + nbOffset[i];
              VALUETYPE priority = std::max(srca(srcUpperLeft, o1), srca(srcUpperLeft, o0));
              PQ.push(PIX(priority, o1, insertionOrder++));
              lab.set(WS_QUEUED, labUpperLeft, o1);
            }
          } // end for neighborhood
        } // end if label
      } // end x-loop
    } // end y-loop

    // until the hierarchical queue is empty ...
    while(!PQ.empty())
    {
      PIX px = PQ.top();
      PQ.pop();
      Diff2D o0 = px.offset;

      // normal flooding procedure
      int label1 = WS_NOT_PROCESSED;
      int label2 = WS_NOT_PROCESSED;

      // the current flooding value is taken from the queue entry.
      // it is not necessarily the same value as in the original image,
      // because some lower regions might not have been flooded
      // (either because of a buttonhole or because of the constraint).
      VALUETYPE currentval = px.value;

      // look to the neighborhood to determine the label of pixel o0.
      for(SIZETYPE i = 0; i < nbOffset.numberOfPixels(); ++i)
      {
        if(!nbOffset.isOutsidePixel(o0, nbOffset[i]))
        {
          Diff2D o1 = o0 + nbOffset[i];
          // first case: pixel has not been processed.
          if(lab(labUpperLeft, o1) == WS_NOT_PROCESSED)
          {
            VALUETYPE priority = std::max(srca(srcUpperLeft, o1), currentval);
            PQ.push(PIX(priority, o1, insertionOrder++));
            lab.set(WS_QUEUED, labUpperLeft, o1);
          }

          // second case: neighbor pixel is already in the queue:
          // nothing is to be done, then.

          // third case: the neighbor has a label
           if(lab(labUpperLeft, o1) > WS_NOT_PROCESSED)
          {
            label2 = lab(labUpperLeft, o1);

            if(label1 == 0)
            {
              // in this case, the label is the first
              // which has been found in the neighborhood.
              label1 = label2;

              lab.set(label1, labUpperLeft, o0);
              desta.set(label1, destUpperLeft, o0);
            }
            else
            {
              // in this case, a label has already been assigned to o0.
              // o0 is part of the watershed line.
              if(label1 != label2)
              {
                lab.set(WS_WSLABEL, labUpperLeft, o0);
                desta.set(OUT_WSLABEL, destUpperLeft, o0);
              }
            }

          }
        }
      } // end for neighborhood

      // if there was no label assigned to the pixel
      // (this can happen in some pathological but not uncommon situations)
      if(label1 == WS_NOT_PROCESSED)
      {
        if(currentval < maxval) {
          // in this case the pixel is pushed back to the queue with
          // increased priority level (so that it will be checked out again
          // at the next grey level).
            PQ.push(PIX(currentval+1, o0, insertionOrder++));
            lab.set(WS_QUEUED, labUpperLeft, o0);
        }
        else {
          // if the maximum level is already reached, the pixel remains
          // outside the queue and is pushed to the final non-hierarchical queue.
            Q.push(o0);
        }
      }

    } // end of PRIORITY QUEUE

    // all points in the rest queue are given the watershedline-label.
    while(!Q.empty()) {
       Diff2D o0 = Q.front(); Q.pop();
       desta.set(OUT_WSLABEL, destUpperLeft, o0);
    }

  } // end of function

  /////////////////////////
  // ImConstrainedWatershed
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class Iterator3, class Accessor3,
       class NBTYPE,
       class PriorityFunctor>
  void ImConstrainedWatershedOpt(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                 Iterator2 markerUpperLeft, Iterator2 markerLowerRight, Accessor2 marka,
                 Iterator3 destUpperLeft, Accessor3 desta,
                 NBTYPE & nbOffset,
                 PriorityFunctor priority
                 )
  {
    // for the work image (negative labels are allowed)
    const int WS_QUEUED = -1;
    const int WS_NOT_PROCESSED = 0;
    const int WS_WSLABEL = -2;
    // for the output image: negative labels are not allowed).
    const int OUT_WSLABEL = 0;

    unsigned long insertionOrder = 0;

    typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
    typedef typename NBTYPE::SIZETYPE SIZETYPE;
    typedef typename Accessor1::value_type VALUETYPE;

    typedef Pixel2D<VALUETYPE> PIX;

    int width  = srcLowerRight.x - srcUpperLeft.x;
      int height = srcLowerRight.y - srcUpperLeft.y;

    vigra::BasicImage<int> labelImage(width, height);
    vigra::BasicImage<int>::Iterator labUpperLeft = labelImage.upperLeft();
    vigra::BasicImage<int>::Accessor lab;
    typedef int LABTYPE;

    ImLabel(markerUpperLeft, markerLowerRight, marka,
          labUpperLeft, lab,
        nbOffset);
    //globalDebEnv.DebugWriteImage(labelImage, "label");

    std::priority_queue<PIX, std::vector<PIX>, PriorityFunctor> PQ(priority);

    Diff2D o0(0,0);

    // initialization of the hierarchical queue
    for(o0.y = 0; o0.y < height; ++o0.y)
    {
      for(o0.x = 0; o0.x < width; ++o0.x)
      {
        LABTYPE  label_o0 = lab(labUpperLeft, o0);
        desta.set(label_o0, destUpperLeft, o0);
        if(label_o0 > WS_NOT_PROCESSED)
        {
          // look to the neighborhood.
          for(ITERATORTYPE iter = nbOffset.begin();
            iter != nbOffset.end();
            ++iter)
          {
            Diff2D o1 = o0 + *iter;

            // if the neighbor is not outside the image
            // and if it has no label and if it is not in the queue
            if(    (!nbOffset.isOutsidePixel(o1))
              && (lab(labUpperLeft, o1) == WS_NOT_PROCESSED))
            {
              VALUETYPE priority = std::max(srca(srcUpperLeft, o1), srca(srcUpperLeft, o0));
              PQ.push(PIX(priority, o1, insertionOrder++));
              lab.set(WS_QUEUED, labUpperLeft, o1);
            }
          } // end for neighborhood
        } // end if label
      } // end x-loop
    } // end y-loop

    // until the hierarchical queue is empty ...
    while(!PQ.empty())
    {
      PIX px = PQ.top();
      PQ.pop();
      Diff2D o0 = px.offset;

      // normal flooding procedure
      int label1 = WS_NOT_PROCESSED;
      int label2 = WS_NOT_PROCESSED;

      // look to the neighborhood to determine the label of pixel o0.
      for(ITERATORTYPE iter = nbOffset.begin();
        iter != nbOffset.end();
        ++iter)
      {
        Diff2D o1 = o0 + *iter;
        if(!nbOffset.isOutsidePixel(o1))
        {
          label2 = lab(labUpperLeft, o1);
          // first case: pixel has not been processed.
          if(label2 == WS_NOT_PROCESSED)
          {
            // the priority is at least the current pixel value (value of o0).
            VALUETYPE priority = std::max(srca(srcUpperLeft, o1), srca(srcUpperLeft, o0));
            PQ.push(PIX(priority, o1, insertionOrder++));
            lab.set(WS_QUEUED, labUpperLeft, o1);
          }

          // second case: neighbor pixel is already in the queue:
          // nothing is to be done, then.

          // third case: the neighbor has a label
           if(label2 > WS_NOT_PROCESSED)
          {
            if(label1 == 0)
            {
              // in this case, the label is the first
              // which has been found in the neighborhood.
              label1 = label2;

              lab.set(label1, labUpperLeft, o0);
              desta.set(label1, destUpperLeft, o0);
            }
            else
            {
              // in this case, a label has already been assigned to o0.
              // o0 is part of the watershed line.
              if(label1 != label2)
              {
                lab.set(WS_WSLABEL, labUpperLeft, o0);
                desta.set(OUT_WSLABEL, destUpperLeft, o0);
              }
            }

          }
        }
      } // end for neighborhood

      // if the pixel has not been assigned a label
      if(label1 == WS_NOT_PROCESSED)
      {
        // we know that this is not correct, but we think
        // that the differences do not concern many pixels.
        lab.set(WS_WSLABEL, labUpperLeft, o0);
        desta.set(OUT_WSLABEL, destUpperLeft, o0);
      }

    } // end of PRIORITY QUEUE

  } // end of function

  /////////////////
  // Watershed
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class Iterator3, class Accessor3,
       class NBTYPE>
  void ImConstrainedWatershed(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                vigra::triple<Iterator2, Iterator2, Accessor2> marker,
                   vigra::pair<Iterator3, Accessor3> dest,
                  NBTYPE & neighborOffset)
  {
    typedef typename Accessor1::value_type val_type;

    ImConstrainedWatershed(src.first, src.second, src.third,
                 marker.first, marker.second, marker.third,
                     dest.first, dest.second,
                     neighborOffset,
                         PriorityBottomUp<val_type>());
  }

  template<class Image1, class Image2, class Image3, class NBTYPE>
  void ImConstrainedWatershed(const Image1 & imin, const Image2 & marker, Image3 & imout, NBTYPE & nbOffset)
  {
    ImConstrainedWatershed(srcImageRange(imin), srcImageRange(marker), destImage(imout), nbOffset);
  }

};
};
#endif /*MORPHO_WATERSHED_HXX_*/
