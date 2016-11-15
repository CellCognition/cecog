/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
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


#ifndef CECOG_POLYGON
#define CECOG_POLYGON

#include "cecog/shared_objects.hxx"
#include "cecog/transforms.hxx"


namespace cecog {

  class ConvexPolygon;

  class Polygon
  {
  public:

    typedef Points::iterator iterator;
    typedef Points::const_iterator const_iterator;
    typedef Points::value_type value_type;
    typedef Points::reference reference;
    typedef Points::const_reference const_reference;
    typedef Points::size_type size_type;

    Polygon(Points poly)
      : poly(poly)
    {};

    Polygon()
    {};

    unsigned int append(value_type p)
    {
      poly.push_back(p);
      return poly.size()-1;
    }

    const_iterator begin() const
    {
      return poly.begin();
    }

    const_iterator end() const
    {
      return poly.end();
    }

    iterator begin()
    {
      return poly.begin();
    }

    iterator end()
    {
      return poly.end();
    }

    reference operator[](int idx)
    {
      return poly[idx];
    }

    const_reference operator[](int idx) const
    {
      return poly[idx];
    }

    size_type size() const
    {
      return poly.size();
    }

    ConvexPolygon convexHull();

    /**
       The orientation of two vectors (qp and rp).
       Return positive if p-q-r are clockwise, negative if ccw and zero
       if colinear.
       clockwise: 0  < angle(qp,rp) < PI    -> positive
       countercw: PI < angle(qp,rp) < 2PI   -> negative
    */
    inline
    int vectorOrientation(Point const &p, Point const &q, Point const &r)
    {
      // the determinant of vectors qp and rp
      // positive for alpha between 0 and pi
      // negative for alpha between pi and 2pi
      // with alpha the angle between (q-p) and (r-p)
      return (q.y-p.y)*(r.x-p.x) - (q.x-p.x)*(r.y-p.y);
    }

  protected:
    Points poly;
  };


  class ConvexPolygon : public Polygon
  {
  public:
    ConvexPolygon(Points poly)
      : Polygon(poly)
    {};

    /**
     * Returns if a point is inside a polygon with clockwise
     * ordered points.
     */
    bool isPointInside(Point const & r)
    {
      bool inside = true;
      const_iterator ip = poly.begin();
      for (; ip < poly.end() - 1; ++ip)
        if (r != *(ip) && r != *(ip+1) &&
          vectorOrientation(*(ip), *(ip+1), r) <= 0)
        {
          inside = false;
          break;
        }
      return inside;
    }
  };

  /**
   * Graham Scan to find the convex hull of a set of 2D points.
   */
  ConvexPolygon Polygon::convexHull()
  {
    Polygon ps = poly;
    Points pu, pl;
    sort(ps.begin(), ps.end(), PointXOrdering<ASCENDING>());

    Points::iterator ip = ps.begin();
    for (; ip != ps.end(); ++ip)
    {
      // look for ccw orientation (left turn)
      while(pu.size() > 1 &&
            vectorOrientation(*(pu.end()-2), *(pu.end()-1), *ip) <= 0)
        pu.pop_back();

      // look for cw orientation (right turn)
      while(pl.size() > 1 &&
            vectorOrientation(*(pl.end()-2), *(pl.end()-1),*ip) >= 0)
        pl.pop_back();

      pu.push_back(*ip);
      pl.push_back(*ip);
    }

    // merge lower to upper hull points (reverse ordered)
    if(pl.size() > 1)
    {
      Points::reverse_iterator rip = pl.rbegin() + 1;
      for (; rip != pl.rend()-1; ++rip)
        pu.push_back(*rip);
    }

    return ConvexPolygon(pu);
  }


  /**
   * draw a polygon contour to the image
   */
  template <class ImageIterator, class Accessor>
  inline
  void drawPolygon(Polygon const & p,
                   ImageIterator upperleft,
                   Accessor a,
                   typename Accessor::value_type value)
  {
    Polygon::const_iterator ip = p.begin();
    for (; ip < p.end() - 1; ++ip)
      drawLine(*ip, *(ip + 1), upperleft, a, value);
    a.set(value, upperleft, *(p.end()-1));
    drawLine(*(p.begin()), *(p.end()-1), upperleft, a, value);
  }


  /**
   * puts all the points of the line between p1 and p2
   * to the point-vector result.
   */
  void pushLinePoints(Point p1, Point p2, Points & result)
  {
    int x1 = p1.x;
    int y1 = p1.y;
    int x2 = p2.x;
    int y2 = p2.y;

    int dx =  abs(x2 - x1);
    int dy = -abs(y2 - y1);

    int sx=-1, sy=-1;
    if (x1 < x2) sx = 1;
    if (y1 < y2) sy = 1;

    int err = dx+dy;
    int err_prev;


    while(1){
      result.push_back(vigra::Diff2D(x1, y1));
      if (x1==x2 && y1==y2) break;
      err_prev = 2*err;
      if (err_prev >= dy) { err += dy; x1 += sx; }
      if (err_prev <= dx) { err += dx; y1 += sy; }
    }
    return;
  }


  /**
   * draws the filled contour defined by polygon p to the image
   * (value defined as a parameter)
   */
  template <class ImageIterator, class Accessor>
  inline
  void fillPolygon(Polygon const & p,
                   ImageIterator upperLeft,
                   Accessor srca,
                   typename Accessor::value_type value)
  {
    Polygon::const_iterator ip = p.begin();
    Points contourPoints;

    for (; ip < p.end() - 1; ++ip)
      pushLinePoints(*ip, *(ip + 1), contourPoints);

    contourPoints.push_back(*(p.end() - 1));
    pushLinePoints(*(p.begin()), *(p.end()-1), contourPoints);

    sort(contourPoints.begin(),
         contourPoints.end(),
         PointYXOrdering<ASCENDING>());

    Points::iterator points_iterator = contourPoints.begin();

    int  min_y = (*(contourPoints.begin() )).y;
    int max_y = (*(contourPoints.end() -1)).y;

    while(points_iterator != contourPoints.end())
    {
      int y = (*points_iterator).y;
       if( (y > min_y) && (y < max_y ) )
       {
        ImageIterator current(upperLeft + *points_iterator);

         while((*points_iterator).y == y)
           ++points_iterator;

        ImageIterator endLine(upperLeft + *(points_iterator - 1));

        for(; current != endLine; ++current.x)
          srca.set(value, current);
        srca.set(value, endLine);
       }
       else
       {
         ImageIterator current(upperLeft + *points_iterator);
        srca.set(value, current);
         ++points_iterator;
       }
    }

  }


  /**
   * whole binary image -> convex hull
   * (only one connected component in output image)
   * FIXME: shouldn't we integrate this with the Polygon/ConvexPolygon classes?
   */
  template <class Iterator1, class Iterator2,
            class Accessor1, class Accessor2,
            class NBTYPE>
  void ImConvexHull(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
                    Iterator2 destUpperLeft, Accessor2 desta,
                    typename Accessor2::value_type value,
                    NBTYPE & nbOffset)
  {
    using std::cout;
    using std::endl;

    Points point_vec;

    typedef typename NBTYPE::ITERATORTYPE nb_iterator_type;
    typedef typename Iterator1::value_type in_type;
    typedef typename Iterator2::value_type out_type;

    int width  = srcLowerRight.x - srcUpperLeft.x;
    int height = srcLowerRight.y - srcUpperLeft.y;

    vigra::Diff2D o0(0,0);

    for(o0.y = 0; o0.y < height; ++o0.y)
      for(o0.x = 0; o0.x < width; ++o0.x)
        if(srca(srcUpperLeft, o0)> 0)
        {
          bool borderpixel = false;
          for (nb_iterator_type iter = nbOffset.begin();
               iter != nbOffset.end();
               ++iter)
          {
            // test if o0 is a border pixel.
            // a border pixel is defined as having at least one background neighbor
            // or at least one neighbor outside the image
            vigra::Diff2D o1 = o0 + *iter;
            // if the neighbor is not outside the image
            if(!nbOffset.isOutsidePixel(o1))
            {
              if(srca(srcUpperLeft, o1) == 0)
                borderpixel = true;
            } else
              borderpixel = true;
          }
          if(borderpixel)
            point_vec.push_back(o0);
        }

    // calculate the convex polygon and draw it to
    // the image.
    Polygon poly(point_vec);
    ConvexPolygon convex = poly.convexHull();
    fillPolygon(convex, destUpperLeft, desta, value);
  }


  template <class Iterator1, class Accessor1,
            class Iterator2, class Accessor2,
            class NBTYPE>
  inline
  void ImConvexHull(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                    vigra::pair<Iterator2, Accessor2> dest,
                   typename Accessor2::value_type value,
                   NBTYPE & neighborOffset)
  {
    ImConvexHull(src.first, src.second, src.third,
                 dest.first, dest.second,
                 value,
                 neighborOffset);
  }


  template<class Image1, class Image2, class NB>
  inline
  void ImConvexHull(const Image1 & imin, Image2 & imout,
                   typename Image1::value_type value,
                   NB & nb)
  {
    ImConvexHull(srcImageRange(imin), destImage(imout), value, nb);
  }

} // namespace cecog

#endif // CECOG_POLYGON
