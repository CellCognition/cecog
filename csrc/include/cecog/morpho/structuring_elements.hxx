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


#ifndef STRUCTURING_ELEMENTS_HXX_
#define STRUCTURING_ELEMENTS_HXX_

#include <vector>
#include <iostream>

#include "vigra/diff2d.hxx"

namespace cecog {
namespace morpho {

  // The Pixel2D structure is used for priority queues (reconstruction, watershed & co)
  template<class ValueType>
  class Pixel2D
  {
  public:
    Pixel2D () : value(0), offset(vigra::Diff2D(0,0)), insertionOrder(0) {}

    Pixel2D (const ValueType & val, const vigra::Diff2D & loc, unsigned long insOrder = 0)
     : value(val), offset(loc), insertionOrder(insOrder)
    {}

    bool operator>(const Pixel2D & p1) const
    {
      bool res = (value == p1.value);
      if(res)
        return(insertionOrder > p1.insertionOrder);
      else
        return(value > p1.value);
    }

    bool operator<(const Pixel2D & p1) const
    {
      bool res = (value == p1.value);
      if(res)
        return(insertionOrder > p1.insertionOrder);
      else
        return(value < p1.value);
    }

    ValueType value;
    vigra::Diff2D offset;
    unsigned long insertionOrder;
  };

  // Priority for algorithms starting with local maxima.
  template<class T>
  struct PriorityTopDown
  {
    inline bool operator()(const Pixel2D<T> & p1, const Pixel2D<T> &p2)
    {
      return p1 < p2;
    }
  };

  // Priority for algorithms starting with local minima.
  template<class T>
  struct PriorityBottomUp
  {
    inline bool operator()(const Pixel2D<T> & p1, const Pixel2D<T> &p2)
    {
      return p1 > p2;
    }
  };

  using vigra::Diff2D;

  const Diff2D NB8_WC[9] = {  Diff2D( 0, 0),
                      Diff2D( 1, 0),
                     Diff2D( 1, 1),
                     Diff2D( 0, 1),
                     Diff2D(-1, 1),
                   Diff2D(-1, 0),
                   Diff2D(-1,-1),
                   Diff2D( 0,-1),
                   Diff2D( 1,-1) };

  const Diff2D SEG_Y[3] = {  Diff2D( 0, -1),
                    Diff2D( 0, 0),
                    Diff2D( 0, 1) };

  const Diff2D SEG_X[3] = {  Diff2D( -1, 0),
                    Diff2D(  0, 0),
                    Diff2D(  1, 0) };

  const Diff2D NB4_WC[5] = {  Diff2D( 0, 0),
                      Diff2D( 1, 0),
                     Diff2D( 0, 1),
                   Diff2D(-1, 0),
                   Diff2D( 0,-1)};

  const Diff2D NB8[8] = { Diff2D( 1, 0),
                   Diff2D( 1, 1),
                   Diff2D( 0, 1),
                   Diff2D(-1, 1),
                 Diff2D(-1, 0),
                 Diff2D(-1,-1),
                 Diff2D( 0,-1),
                 Diff2D( 1,-1) };

  const Diff2D NB4[4] = { Diff2D( 1, 0),
                   Diff2D( 0, 1),
                 Diff2D(-1, 0),
                 Diff2D( 0,-1)};

  class NeighborDefinition {
  public:
    const Diff2D *nbList;
    const unsigned int nbPixels;
    NeighborDefinition(const Diff2D *l, unsigned int n)
      : nbList(l), nbPixels(n) {}
  };

  const NeighborDefinition WITHCENTER8(NB8_WC, 9);
  const NeighborDefinition WITHCENTER4(NB4_WC, 5);
  const NeighborDefinition WITHOUTCENTER8(NB8, 8);
  const NeighborDefinition WITHOUTCENTER4(NB4, 4);

  const NeighborDefinition XSEGMENT(SEG_X, 3);
  const NeighborDefinition YSEGMENT(SEG_Y, 3);

  class neighborPixels {
  protected:
    std::vector<Diff2D> support;
    unsigned long nbPixels_;

    // for border treatment
    Diff2D minOffset_;
    Diff2D maxOffset_;

  public:
    typedef std::vector<Diff2D>::iterator ITERATORTYPE;
    typedef std::vector<Diff2D>::size_type SIZETYPE;

    // Constructors:
    neighborPixels(std::vector<Diff2D> supportParam):
            support(supportParam), nbPixels_(supportParam.size())
               {
                 CalculateExtension();
               }

    neighborPixels(const Diff2D *beg, const Diff2D *end):
            support(beg, end), nbPixels_(end - beg)
               {
                 CalculateExtension();
               }

    neighborPixels(const Diff2D *beg, int nbPixels):
            support(beg, beg + nbPixels), nbPixels_(nbPixels)
               {
                 CalculateExtension();
               }

    neighborPixels(const NeighborDefinition &nd):
            support(nd.nbList, nd.nbList + nd.nbPixels), nbPixels_(nd.nbPixels)
               {
                 CalculateExtension();
               }

    Diff2D minOffset() { return(minOffset_); }

    Diff2D maxOffset() { return(maxOffset_); }

    // Calculate the maximal extensions of the structuring element.
    void CalculateExtension()
    {
      if(!support.empty())
      {
        minOffset_ = *(support.begin());
        maxOffset_ = *(support.begin());

        for(ITERATORTYPE iter = support.begin();
          iter != support.end();
          ++iter)
          {
            minOffset_.x = std::min(minOffset_.x, (*iter).x);
            minOffset_.y = std::min(minOffset_.y, (*iter).y);
            maxOffset_.x = std::max(maxOffset_.x, (*iter).x);
            maxOffset_.y = std::max(maxOffset_.y, (*iter).y);
          }
      }
    }

    ITERATORTYPE begin() { return(support.begin()); }

    ITERATORTYPE end() { return(support.end()); }

    void output()
    {

      std::cout << "Coordinates of the SE: " << std::endl;
      for(std::vector<Diff2D>::iterator iter = support.begin();
        iter != support.end();
        ++iter)
        {
          std::cout << "(" << (*iter).x << ", " << (*iter).y << ")  " ;
        }
      std::cout << std::endl;
      std::cout << "Maximal Extensions of the SE: " << std::endl;
      std::cout << "maxOffset: " << maxOffset_.x << " " << maxOffset_.y << std::endl;
      std::cout << "minOffset:  " << minOffset_.x << " " << minOffset_.y << std::endl;
      return;
    }

    unsigned long numberOfPixels() {return(nbPixels_);}

    const Diff2D &operator[](int i)
    {
      return(support[i]);
    }

  };

  class structuringElement2D : public neighborPixels
  {

    public:
      structuringElement2D(std::vector<Diff2D> supportParam, int sizeParam = 1):
                 neighborPixels(supportParam), size(sizeParam)
                 {}

      structuringElement2D(const Diff2D *beg, const Diff2D *end, int sizeParam = 1):
                 neighborPixels(beg, end), size(sizeParam)
                 {}

      structuringElement2D(const Diff2D *beg, int nbPixels, int sizeParam = 1):
                 neighborPixels(beg, nbPixels), size(sizeParam)
                 {}

      structuringElement2D(const NeighborDefinition &nd, int sizeParam = 1):
                 neighborPixels(nd), size(sizeParam)
                 {}

      int size;
  };

  class neighborhood2D : public neighborPixels
  {
  public:

    neighborhood2D(std::vector<Diff2D> supportParam, Diff2D imageSize):
      neighborPixels(supportParam), imageSize_(imageSize)
    {}

    neighborhood2D(const Diff2D *beg, const Diff2D *end,
             const Diff2D &imageSize):
      neighborPixels(beg, end), imageSize_(imageSize)
    {}

    neighborhood2D(const Diff2D *beg,
             int nbPixels,
             const Diff2D &imageSize):
      neighborPixels(beg, nbPixels), imageSize_(imageSize)
    {}

    neighborhood2D(const NeighborDefinition &nd,
             const Diff2D &imageSize):
      neighborPixels(nd), imageSize_(imageSize)
    {}


    bool isBorderPixel(const Diff2D &pixel)
    {
      return( (pixel.x == 0) || (pixel.x == imageSize_.x - 1) ||
          (pixel.y == 0) || (pixel.y == imageSize_.y - 1) );
    }

    bool isOutsidePixel(const Diff2D &pixel, const Diff2D &offset)
    {
      return( ((pixel + offset).x < 0) || ((pixel + offset).x > imageSize_.x - 1) ||
          ((pixel + offset).y < 0) || ((pixel + offset).y > imageSize_.y - 1) );
    }

    bool isOutsidePixel(const Diff2D &pixel)
    {
      return( (pixel.x < 0) || (pixel.x > imageSize_.x - 1) ||
          (pixel.y < 0) || (pixel.y > imageSize_.y - 1) );
    }
  private:
    Diff2D imageSize_;
  };

};
};

#endif /*STRUCTURING_ELEMENTS_HXX_*/
