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


#ifndef CECOG_FDIFF2D
#define CECOG_FDIFF2D


namespace cecog
{

  class FDiff2D
  {
  public:
    typedef FDiff2D PixelType;
    typedef FDiff2D value_type;
    typedef FDiff2D const &       reference;
    typedef FDiff2D               index_reference;
    typedef FDiff2D const *       pointer;
    typedef FDiff2D               difference_type;

    FDiff2D()
      : x(0), y(0)
    {}

    FDiff2D(double ax, double ay)
      : x(ax), y(ay)
    {}

    FDiff2D(FDiff2D const & v)
      : x(v.x), y(v.y)
    {}

    FDiff2D & operator=(FDiff2D const & v)
    {
      if(this != &v)
      {
        x = v.x;
        y = v.y;
      }
      return *this;
    }


    FDiff2D operator-() const
    {
      return FDiff2D(-x, -y);
    }

    FDiff2D & operator+=(FDiff2D const & offset)
    {
      x += offset.x;
      y += offset.y;
      return *this;
    }

    FDiff2D & operator-=(FDiff2D const & offset)
    {
      x -= offset.x;
      y -= offset.y;
      return *this;
    }

    FDiff2D & operator*=(double factor)
    {
      x = x * factor;
      y = y * factor;
      return *this;
    }

    FDiff2D & operator/=(double factor)
    {
      x = x / factor;
      y = y / factor;
      return *this;
    }

    FDiff2D operator*(double factor) const
    {
      return FDiff2D(x * factor, y * factor);
    }

    FDiff2D operator/(double factor) const
    {
      return FDiff2D(x / factor, y / factor);
    }

    inline
    double squaredMagnitude() const
    {
      return x*x + y*y;
    }

    inline
    double magnitude() const
    {
      return sqrt(squaredMagnitude());
    }

    bool operator==(FDiff2D const & r) const
    {
      return (x == r.x) && (y == r.y);
    }

    bool operator!=(FDiff2D const & r) const
    {
      return (x != r.x) || (y != r.y);
    }

    double x;
    double y;

    reference operator*() const
    {
      return *this;
    }

  };

  inline FDiff2D operator-(FDiff2D const &a, FDiff2D const &b)
  {
    return FDiff2D(a.x - b.x, a.y - b.y);
  }

  inline FDiff2D operator+(FDiff2D const &a, FDiff2D const &b)
  {
    return FDiff2D(a.x + b.x, a.y + b.y);
  }

// inline FDiff2D operator*(FDiff2D const &a, FDiff2D const &b)
// {
//     return FDiff2D(a.x * b.x, a.y * b.y);
// }

// inline FDiff2D operator/(FDiff2D const &a, FDiff2D const &b)
// {
//     return FDiff2D(a.x / b.x, a.y / b.y);
// }

}
#endif // CECOG_FDIFF2D
