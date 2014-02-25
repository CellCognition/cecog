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

//#include "project_definitions.hxx"

namespace cecog
{
  template<class T, class IN_, class OUT_>
  class ThresholdFunctor
  {
    public:
		ThresholdFunctor(T const &threshold, OUT_ const &markVal, OUT_ const &zeroVal) :
               threshold_(threshold), markVal_(markVal), zeroVal_(zeroVal)
               {}

		OUT_ operator()(IN_ const &inVal, T const &val)
      {
        return( ( (T)inVal - val >= threshold_) ? markVal_ : zeroVal_);
      }

    private:
      T threshold_;
	  OUT_ markVal_, zeroVal_;
  };

  
  template<class IN_, class OUT_>
  class ThresholdFunctorUpperLower
  {
    public:
		ThresholdFunctorUpperLower(IN_ const &lower, IN_ const &upper, OUT_ const &markVal, OUT_ const &zeroVal) :
        lower_(lower), upper_(upper), markVal_(markVal), zeroVal_(zeroVal)
        {}

		OUT_ operator()(IN_ const &inVal)
      {
        return( ( (inVal >= lower_) && (inVal <=upper_)) ? markVal_ : zeroVal_);
      }

    private:
      IN_ lower_, upper_;
	  OUT_ markVal_, zeroVal_;
  };

  template<class T, class IN_, class OUT_>
  class TrivialValueFunctor
  {
    public:
      TrivialValueFunctor(){}
      OUT_ operator()(IN_ const &inVal, T const &val)
      {
        return( (OUT_)val );
      }
  };

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


  template<class T, class S>
  struct minusClipp
  {
    typedef typename vigra::NumericTraits<T> NumTraits_T;
    typedef typename vigra::NumericTraits<S> NumTraits_S;

    // vigra::NumericTraits<T>::RealPromote is the type
    // which can be used for multiplication/division for a type T.
    typedef typename vigra::NumericTraits<T>::RealPromote SUMTYPE;

    minusClipp()
    {}

    T operator()(T const & a, S const & b) const
    {
      // a of type T and b of type S are both represented as "toRealPromote" (e.g. float).
      // the conversion into type T is done by the method NumTraits_T::fromRealPromote.
      const SUMTYPE sum = NumTraits_T::toRealPromote(a) - NumTraits_S::toRealPromote(b);
      return(NumTraits_T::fromRealPromote(sum));
    }
  };

  // the functor SelectListOfValues checks if the pixel value
  // is in a list of values. If it is, the pixel is put to zero (noVal),
  // if not, the pixel is put to yesVal.
  template<class IN_, class OUT_>
  struct DeleteListOfValues
  {
  public:
    typedef typename std::vector<IN_> VALUELIST;

    // yesVal: value the pixel gets if its grey level is in the value list
    // noVal: value te pixel gets, if it is not in the value list.
    DeleteListOfValues(const VALUELIST &values, const OUT_ &yesVal, const OUT_ &noVal)
    : valueList_(values), yesVal_(yesVal), noVal_(noVal)
    {}


    OUT_ operator()(const IN_ &a) const
    {
//      for(typename VALUELIST::size_type i = 0; i != valueList_.size(); ++i)
//      {
//        if(a==(valueList_[i]))
//          return(noVal_);
//      }

      // As the method has been declared const,
      // we must use the const_iterator (if not: compiler error),
      // in order to be sure not to change any class member.
      for(typename VALUELIST::const_iterator iter=valueList_.begin();
        iter != valueList_.end();
        ++iter)
      {
        // a is in the list
        if(a==(*iter))
          return(yesVal_);
      }
      // a has not been in the list
      return(noVal_);
    }

  private:
    VALUELIST valueList_;
    OUT_ yesVal_;
    OUT_ noVal_;
  };

  template <class VALUETYPE>
  class FindSquaredSum
  {
    public:
    //typedef VALUETYPE argument_type;
    //typedef typename NumericTraits<VALUETYPE>::Promote result_type;

    //FindSquaredSum() : sum_(NumericTraits<result_type>::zero()) {}
    FindSquaredSum() : sum_(0.0) {}

    void reset() {
      sum_ = 0.0; //NumericTraits<result_type>::zero();
    }

    void operator()(VALUETYPE const & v) {
      sum_ += (double) (v * v);
    }

      /* void operator()(FindSquaredSum const & v)
      {
          sum_   += v.sum_;
      } */

    double sum() const {
      return sum_;
    }

    double operator()() const {
      return sum_;
    }

    double sum_;
  };

  template <class VALUETYPE>
  class FindAbsSum
  {
    public:
    //typedef VALUETYPE argument_type;
    //typedef typename NumericTraits<VALUETYPE>::Promote result_type;

    //FindSquaredSum() : sum_(NumericTraits<result_type>::zero()) {}
    FindAbsSum() : sum_(0.0) {}

    void reset() {
      sum_ = 0.0; //NumericTraits<result_type>::zero();
    }

    void operator()(VALUETYPE const & v) {
      sum_ += (double) abs(v);
      //cout << "Absolute Sum :"<< (double)v << " " << (double)abs(v) << " " << sum_ << std::endl;
    }

      /* void operator()(FindSquaredSum const & v)
      {
          sum_   += v.sum_;
      } */

    double sum() const {
      return sum_;
    }

    double operator()() const {
      return sum_;
    }

    double sum_;
  };

};

#endif /*FUNCTORS_HXX_*/
