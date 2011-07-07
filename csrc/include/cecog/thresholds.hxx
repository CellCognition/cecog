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


#ifndef CECOG_THRESHOLDS
#define CECOG_THRESHOLDS

#include <vector>

#include "vigra/impex.hxx"
#include "vigra/stdimage.hxx"
#include "vigra/transformimage.hxx"


namespace cecog
{

  /**
   * Handling and caching of window average
   * CALCULATE_STD=0 optimizes the algorithm at compile time,
   * otherwise the std is computed along with the mean
   */
  template <class IMAGE, int CALCULATE_STD=0>
  class FastWindowAverage
  {
  public:
    typedef std::vector<long int> Columns;

    // constructor
    FastWindowAverage(IMAGE const &imgIn,
                      int rsize)
      : sum_values(0), ssum_values(0), count(0),
        imgIn(imgIn),
        rsize(rsize), size(rsize+1)
    {
      width = imgIn.width();
      height = imgIn.height();
      // pre-average: sum and count separately
      typename IMAGE::value_type pvalue;
      for (int x=0; x < width; ++x)
      {
        int col_sum = 0;
        long int scol_sum = 0;
        for (int y = 0; y <= rsize; ++y)
        {
          pvalue = imgIn(x, y);
          col_sum += pvalue;
          if (CALCULATE_STD)
            scol_sum += pvalue*pvalue;
        }
        if (x <= rsize)
        {
          sum_values += col_sum;
          if (CALCULATE_STD)
            ssum_values += scol_sum;
        }
        columns.push_back(col_sum);
        if (CALCULATE_STD)
          scolumns.push_back(scol_sum);
      }
      assert(columns.size() == width);
      count = size*size;
      current_size = size;
      c_in  =  rsize;
      c_out = -rsize;
      r_in  =  rsize;
      r_out = -rsize;
    };

    // update the pixel sum by column:
    // take sum of last column out and sum of next first column in
    inline
    void nextColumn()
    {
      c_in++;
      if (c_in < width)
      {
        sum_values += columns[c_in];
        if (CALCULATE_STD)
          ssum_values += scolumns[c_in];
        count += current_size;
      }
      if (c_out >= 0)
      {
        sum_values -= columns[c_out];
        if (CALCULATE_STD)
          ssum_values -= scolumns[c_out];
        count -= current_size;
      }
      c_out++;
    }

    // update the pixel sum by row:
    // take sum of last row out and sum of next first row in
    inline
    void scanNextRow()
    {
      sum_values = 0;
      ssum_values = 0;
      r_in++;
      bool bIn = false;
      bool bOut = false;
      if (r_in < height)
      {
        bIn = true;
        count += size;
        current_size++;
      }
      if (r_out >= 0)
      {
        bOut = true;
        count -= size;
        current_size--;
      }

      Columns::iterator it = columns.begin();
      Columns::iterator sit = scolumns.begin();
      typename IMAGE::value_type pvalue;
      for (int x = 0; x < width; ++x, ++it)
      {
        if (bIn)
        {
          pvalue = imgIn(x, r_in);
          *it  += pvalue;
          if (CALCULATE_STD)
            *sit += pvalue*pvalue;
        }
        if (bOut)
        {
          pvalue = imgIn(x, r_out);
          *it  -= pvalue;
          if (CALCULATE_STD)
            *sit -= pvalue*pvalue;
        }
        if (x <= rsize)
        {
          sum_values  += *it;
          if (CALCULATE_STD)
            ssum_values += *sit;
        }
      }
      r_out++;
      c_in  =  rsize;
      c_out = -rsize;
      if (CALCULATE_STD)
        sit++;
    }

    // calculates average gray level online by sum and count of gray
    // levels (at the current window position)
    inline
    float mean() const
    {
      return sum_values / float(count);
    }

    inline
    float std() const
    {
      if (CALCULATE_STD)
        return sqrt((ssum_values - sum_values*sum_values / float(count)) / float(count-1));
      else
        throw "Error: class was not compiled for std-calculation!";
    }

  protected:
    long int sum_values, ssum_values, count, current_size;
    int rsize, width, height, size, c_in, c_out, r_in, r_out;
    Columns columns, scolumns;
    const IMAGE &imgIn;
  };


  template <class IMAGE, class BIMAGE, int CALCULATE_STD=0>
  class WindowAverageThreshold
  {
  public:

    WindowAverageThreshold(IMAGE const &imgIn,
                           BIMAGE &imgBin,
                           unsigned iRSize,
                           typename IMAGE::value_type contrastLimit=vigra::NumericTraits<typename IMAGE::value_type>::zero(),
                           typename IMAGE::value_type lower=vigra::NumericTraits<typename IMAGE::value_type>::min(),
                           typename IMAGE::value_type higher=vigra::NumericTraits<typename IMAGE::value_type>::max())
    : imgIn(imgIn), imgBin(imgBin),
      iRSize(iRSize),
      contrastLimit(contrastLimit), lower(lower), higher(higher),
      oFWA(imgIn, iRSize)
    {}

    void operator()()
    {
      // initialize the window at the first position (upperleft)
      windowThresholdLoop_();
    }

  protected:

    virtual inline
    bool pixelCondition_(typename IMAGE::value_type const &pixelValue) const
    {
      return ((pixelValue - oFWA.mean() >= contrastLimit) &&
              (pixelValue >= lower) && (pixelValue <= higher));
    }

    /**
     * Calculates the Local Adaptive Threshold based on a sliding average window
     * by caching sums of rows and columns.
     * Image can be expanded on upperleft and lowerright about window/2 (and
     * shrinked afterwards) to handle border-problem.
     */
    void windowThresholdLoop_()
    {
      // set binary image to 'background'
      //binary = 0;

      // iterators and accessor of the source image
      typedef typename IMAGE::const_traverser Traverser;
      typedef typename IMAGE::ConstAccessor  Accessor;
      Traverser si_base(imgIn.upperLeft());
      Traverser send(imgIn.lowerRight());
      Accessor  src(imgIn.accessor());

      int width   = imgIn.width();
      int height  = imgIn.height();

      // iterators and accessor of the binary image
      typename BIMAGE::traverser bi_base(imgBin.upperLeft());
      typename BIMAGE::Accessor  bin(imgBin.accessor());

      vigra::Diff2D diff(iRSize, iRSize);

      Traverser si(si_base);
      typename BIMAGE::traverser bi(bi_base);

      // loop over all image rows
      for (int y=0; y < height; ++y, ++si.y, ++bi.y)
      {
        // reset x-coordinates
        si.x = si_base.x;
        bi.x = bi_base.x;

        // update the window by row (from the second row on)
        if (y)
          oFWA.scanNextRow();

        // loop over all image columns
        for (int x=0; x < width; ++x, ++si.x, ++bi.x)
        {
          // update the window by column (from the second column on)
          if (x)
            oFWA.nextColumn();
          typename Accessor::value_type oPixelValue = src(si);
          if (pixelCondition_(oPixelValue))
            bin.set(255, bi);
        }
      }
    }

    FastWindowAverage<IMAGE, CALCULATE_STD> oFWA;
    const IMAGE &imgIn;
    BIMAGE &imgBin;
    unsigned iRSize;
    typename IMAGE::value_type contrastLimit, lower, higher;
  };



  template <class IMAGE, class BIMAGE>
  class WindowStdThreshold : public WindowAverageThreshold<IMAGE, BIMAGE, 1>
  {
  public:

    typedef WindowAverageThreshold<IMAGE, BIMAGE, 1> BaseType;

    WindowStdThreshold(IMAGE const &imgIn,
                       BIMAGE &imgBin,
                       unsigned iRSize,
                       float fStdTreshold,
                       typename IMAGE::value_type contrastLimit=vigra::NumericTraits<typename IMAGE::value_type>::zero())
    : BaseType(imgIn, imgBin, iRSize, contrastLimit),
      fStdTreshold(fStdTreshold)
    {}

  protected:

    virtual inline
    bool pixelCondition_(typename IMAGE::value_type const &pixelValue) const
    {
      return (this->oFWA.std() >= fStdTreshold ||
              this->oFWA.mean() >= this->contrastLimit);
    }

    float fStdTreshold;
  };


  template <class IMAGE, class BIMAGE>
  void windowAverageThreshold(IMAGE const &imgIn,
                              BIMAGE &imgBin,
                              unsigned iRSize,
                              typename IMAGE::value_type contrastLimit=vigra::NumericTraits<typename IMAGE::value_type>::zero(),
                              typename IMAGE::value_type lower=vigra::NumericTraits<typename IMAGE::value_type>::min(),
                              typename IMAGE::value_type higher=vigra::NumericTraits<typename IMAGE::value_type>::max())
  {
    WindowAverageThreshold<IMAGE, BIMAGE>(imgIn, imgBin, iRSize,
                                          contrastLimit, lower, higher)();
  }

  template <class IMAGE, class BIMAGE>
  void windowStdThreshold(IMAGE const &imgIn,
                          BIMAGE &imgBin,
                          unsigned iRSize,
                          float fStdThreshold,
                          typename IMAGE::value_type contrastLimit=vigra::NumericTraits<typename IMAGE::value_type>::zero())
  {
    WindowStdThreshold<IMAGE, BIMAGE>(imgIn, imgBin, iRSize, fStdThreshold,
                                      contrastLimit)();
  }

  class OtsuThreshold
  {
  public:

    long operator()(std::vector<double> const &prob)
    {
      const long VCOUNT = prob.size();

      /* find best threshold by computing moments for all thresholds */
      double m0Low, m0High, m1Low, m1High, varLow, varHigh;
      double varWithin, varWMin;
      long thresh;
      long i, j, n;
      long nHistM1 = VCOUNT - 1;

      for (i = 1, thresh = 0, varWMin = LONG_MAX; i < nHistM1; ++i)
      {
        m0Low = m0High = m1Low = m1High = varLow = varHigh = 0.0;
        for (j = 0; j <= i; j++) {
          m0Low += prob[j];
          m1Low += j * prob[j];
        }
        m1Low = (m0Low != 0.0) ? m1Low / m0Low : i;
        for (j = i + 1; j < VCOUNT; j++)
        {
          m0High += prob[j];
          m1High += j * prob[j];
        }
        m1High = (m0High != 0.0) ? m1High / m0High : i;
        for (j = 0; j <= i; j++)
          varLow += (j - m1Low) * (j - m1Low) * prob[j];
        for (j = i + 1; j < VCOUNT; j++)
          varHigh += (j - m1High) * (j - m1High) * prob[j];

        varWithin = m0Low * varLow + m0High * varHigh;
        if (varWithin < varWMin)
        {
          varWMin = varWithin;
          thresh = i;
        }
      }
      return thresh;
    }
  };

  long otsuThreshold(std::vector<double> const &prob)
  {
    return OtsuThreshold()(prob);
  }

}

#endif // CECOG_THRESHOLDS
