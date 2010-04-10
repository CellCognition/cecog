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


#ifndef CECOG_SHARED_OBJECTS
#define CECOG_SHARED_OBJECTS

#include <map>
#include <string>
#include <iostream>
#include <cstdlib>

#include "vigra/impex.hxx"
#include "vigra/stdimage.hxx"
#include "vigra/transformimage.hxx"
#include "vigra/labelimage.hxx"
#include "vigra/inspectimage.hxx"

//#include "cecog/utilities.hxx"

namespace cecog {

  // contains basic type definitions
  // and the object class, i.e. the representation of the cell nuclei.

  typedef vigra::BRGBImage::value_type RGBValue;

  typedef vigra::Diff2D Point;
  typedef std::vector<Point> Points;

  typedef std::vector<std::string> StringVector;

  typedef double FeatureValue;
  typedef std::map<std::string, FeatureValue> FeatureMap;

  typedef vigra::UInt8 uint8;
  typedef vigra::UInt16 uint16;
  typedef vigra::UInt32 uint32;

  typedef vigra::Int8 int8;
  typedef vigra::Int16 int16;
  typedef vigra::Int32 int32;


  static const int BIT_U8 = 8, BIT_S12 = 12, BIT_U12 = 120;

  static const RGBValue RED(255,0,0);
  static const RGBValue GREEN(0,255,0);
  static const RGBValue BLUE(0,0,255);
  static const RGBValue YELLOW(255,255,0);
  static const RGBValue BLACK(0,0,0);
  static const RGBValue WHITE(255,255,255);

  static const bool ASCENDING = false;
  static const bool DESCENDING = true;




  /**
   * functor to order Points by x-coordinate
   */
  template <bool DESCENDING>
  class PointXOrdering
  {
  public:
    inline
    bool operator()(Point const & a, Point const & b) const
    {
      return (DESCENDING) ? !(a.x < b.x) : (a.x < b.x);
    }
  };

  /**
   * functor to order Points by y-coordinate
   */
  template <bool DESCENDING>
  class PointYOrdering
  {
  public:
    inline
    bool operator()(Point const & a, Point const & b) const
    {
      return (DESCENDING) ? !(a.y < b.y) : (a.y < b.y);
    }
  };

  /**
   * functor to order Points by yx-coordinates (y first, x after)
   */
  template <bool DESCENDING>
  class PointYXOrdering
  {
  public:
    inline
    bool operator()(Point const & a, Point const & b) const
    {
      if (a.y == b.y)
        return PointXOrdering<DESCENDING>()(a, b);
      else
        return PointYOrdering<DESCENDING>()(a, b);
    }
  };

  /**
   * functor to order Points by xy-coordinates (x first, y after)
   */
  template <bool DESCENDING>
  class PointXYOrdering
  {
  public:
    inline
    bool operator()(Point const & a, Point const & b) const
    {
      if (a.x == b.x)
        return PointYOrdering<DESCENDING>()(a, b);
      else
        return PointXOrdering<DESCENDING>()(a, b);
    }
  };


  struct Region
  // note that the origin is in the top left corner of the associated image.
  {
    Region(int x, int y, int width, int height)
      : upperLeft(x, y),
        lowerRight(x + width, y + height),
        x(x),
        y(y),
        width(width),
        height(height),
        size(width, height),
        area(width * height)
    {}

    Region(vigra::Diff2D upperLeft, vigra::Diff2D lowerRight)
      : upperLeft(upperLeft),
        lowerRight(lowerRight),
        x(upperLeft.x),
        y(upperLeft.y),
        size(lowerRight - upperLeft),
        width(size.x),
        height(size.y),
        area(size.x * size.y)
    {}

    vigra::Diff2D upperLeft;
    vigra::Diff2D lowerRight;
    vigra::Diff2D size;
    int x;
    int y;
    int width;
    int height;
    unsigned int area;
  };


  /**
   * ROIObject is the representation for one ROI (e.g. cell nucleus)
   * - contains the geometrical description (class region)
   * - contains the feature map (all features calculated for this ROI)
   */
  class ROIObject
  {
  public:

    ROIObject(vigra::Diff2D upperLeft, vigra::Diff2D lowerRight, vigra::Diff2D center)
        : roi(upperLeft, lowerRight),
          center(center),
          roisize(0.0),
          oCenterAbs(upperLeft + center)
    {};

    ROIObject(vigra::Diff2D upperLeft, vigra::Diff2D lowerRight,
              vigra::Diff2D center, vigra::Diff2D crack_start, vigra::Diff2D crack_start2,
              double roisize)
        : roi(upperLeft, lowerRight),
          center(center),
          crack_start(crack_start),
          crack_start2(crack_start2),
          roisize(roisize),
          oCenterAbs(upperLeft + center)
    {};

    ROIObject()
        : roi(vigra::Diff2D(0,0), vigra::Diff2D(0,0)),
          center(0,0),
          roisize(0.0),
          oCenterAbs(0,0)
    {};

    vigra::Diff2D center, oCenterAbs, crack_start, crack_start2;
    FeatureMap features;
    FeatureMap measurements;
    Region roi;
    double roisize;
  };


}

#endif // CECOG_SHARED_OBJECTS
