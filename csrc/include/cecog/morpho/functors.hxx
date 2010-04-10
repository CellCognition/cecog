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


#ifndef FUNCTORS_HXX_
#define FUNCTORS_HXX_

namespace cecog
{
namespace morpho
{

  // HELP FUNCTORS
  template<class T, class S>
  struct IsGreaterEqual
  {
    IsGreaterEqual(){}
    bool operator()(T const &a, S const &b)
    {
      return( (a >= b));
    }
  };

  template<class T, class S>
  struct IsSmallerEqual
  {
    IsSmallerEqual(){}
    bool operator()(T const &a, S const &b)
    {
      return( (a <= b));
    }
  };

  template<class T, class S>
  struct IsGreater
  {
    IsGreater(){}

    bool operator()(T const &a, S const &b)
    {
      return( (a > b));
    }
  };

  template<class T, class S>
  struct IsSmaller
  {
    IsSmaller(){}
    bool operator()(T const &a, S const &b)
    {
      return( (a < b));
    }
  };

  template<class T, class S>
  struct IsEqual
  {
    bool operator()(T const &a, S const &b)
    {
      return(a==b);
    }
  };

  template<class T, class S>
  struct IsUnequal
  {
    bool operator()(T const &a, S const &b)
    {
      return(a!=b);
    }
  };

  // MinFunctor returns the minimum of two numbers.
  template<class T>
  struct MinFunctor
  {
    const T neutralValue;
    MinFunctor() : neutralValue(vigra::NumericTraits<T>::maxConst) {}
    T operator()(T const &a, T const &b)
    {
      return( (a < b)?a:b );
    }
  };

  // MaxFunctor returns the maximum of two numbers.
  template<class T>
  struct MaxFunctor
  {
    const T neutralValue;
    MaxFunctor() : neutralValue(vigra::NumericTraits<T>::minConst) {}
    T operator()(T const &a, T const &b)
    {
      return( (a > b)?a:b );
    }
  };

  // minus and plus with clipping.
  template<class T>
  struct minusConstantClipp
  {
    typedef typename vigra::NumericTraits<T> NumTraits;
    typedef typename vigra::NumericTraits<T>::Promote SUMTYPE;

    T c;

    minusConstantClipp(T const & val) : c(val)
    {}

    T operator()(T const & a) const
    {
      SUMTYPE sum = NumTraits::toPromote(a) - NumTraits::toPromote(c);
      return(NumTraits::fromPromote(sum));
    }
  };

  template<class T>
  struct plusConstantClipp
  {
    typedef typename vigra::NumericTraits<T> NumTraits;
    typedef typename vigra::NumericTraits<T>::Promote SUMTYPE;

    T c;

    plusConstantClipp(T const & val) : c(val)
    {}

    T operator()(T const & a) const
    {
      SUMTYPE sum = NumTraits::toPromote(c) + NumTraits::toPromote(a);
      return(NumTraits::fromPromote(sum));
    }
  };

  template<class T>
  struct plusClipp
  {
    typedef typename vigra::NumericTraits<T> NumTraits;
    typedef typename vigra::NumericTraits<T>::Promote SUMTYPE;

    plusClipp()
    {}

    T operator()(T const & a, T const & b) const
    {
      SUMTYPE sum = NumTraits::toPromote(a) + NumTraits::toPromote(b);
      return(NumTraits::fromPromote(sum));
    }
  };

};
};

#endif /*FUNCTORS_HXX_*/
