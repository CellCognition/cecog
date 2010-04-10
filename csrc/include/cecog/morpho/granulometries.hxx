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


#ifndef MORPHO_GRANULOMETRIES_HXX_
#define MORPHO_GRANULOMETRIES_HXX_

#include "vigra/flatmorphology.hxx"
#include "project_definitions.hxx"

namespace cecog {
namespace morpho{

    template<class value_type>
    class GranulometryMeasure
    {
    public:

        typedef unsigned area_type;
        typedef unsigned volume_type;

        typedef int volume_diff_type;
        typedef int area_diff_type;

        typedef double norm_type;

        GranulometryMeasure() : volumeIn_(0), volumeOut_(0), areaIn_(0), areaOut_(0)
        {}

        void operator()(const value_type &a, const value_type &b)
        {
            // b is the transformed value.
            if(a > 0)
                areaIn_++;
            if(b > 0)
                areaOut_++;
            volumeIn_  += a;
            volumeOut_ += b;

            // alternative (in order to decorrelate volume and area somehow):
            //if( (a > 0) and (b > 0) )
            //{
                // we calculate and compare the volume
                // only for pixels which are in the input image
                // and in the output image.
                //volumeIn_  += a;
                //volumeOut_ += b;
            //}
        }

        area_type areaIn() const
        {
            return areaIn_;
        }

        area_type areaOut() const
        {
            return areaOut_;
        }

        volume_type volumeIn() const
        {
            return volumeIn_;
        }

        volume_type volumeOut() const
        {
            return volumeOut_;
        }

        volume_diff_type volumeDiff() const
        {
            return(volumeOut_ - volumeIn_);
        }


        // volume normalized output
        norm_type volumeNormOut() const
        {
            return((double)volumeOut_/(double)volumeIn_);
        }

        norm_type volumeDiffNorm() const
        {
            return(fabs( (double)volumeOut_ - (double)volumeIn_)/(double)volumeIn_);
        }


        // area normalized output
        norm_type areaNormOut() const
        {
            return((double)areaOut_/(double)areaIn_);
        }

        norm_type areaDiffNorm() const
        {
            return(fabs( (double)areaOut_ - (double)areaIn_)/(double)areaIn_);
        }

        void reset()
        {
            volumeIn_ = 0;
            volumeOut_ = 0;
            areaIn_ = 0;
            areaOut_ = 0;
        }

    private:

        unsigned volumeIn_, volumeOut_;
        unsigned areaIn_, areaOut_;
    };

    template<class Image1>
    void ImOpenGranulometry(const Image1 & imin,
                            std::vector<unsigned> &seSizes,
                            std::vector<double> &area, std::vector<double> &volume,
                            unsigned objLabel = 0)
    {
        typedef typename Image1::value_type value_type;

        if(seSizes.size() == 0)
            return;

        area.clear();
        volume.clear();

        GranulometryMeasure<value_type> granu;

        Image1 temp(imin.size());
        Image1 open(imin.size());

        for(std::vector<unsigned>::size_type i = 0;
            i != seSizes.size(); ++i)
        {
            if(i==0)
                vigra::discErosion(srcImageRange(imin), destImage(temp), seSizes[i]);
            else
                vigra::discErosion(srcImageRange(open), destImage(temp), seSizes[i]);

            vigra::discDilation(srcImageRange(temp), destImage(open), seSizes[i]);
            granu.reset();
            vigra::inspectTwoImages(srcImageRange(imin), srcImage(open), granu);

            area.push_back(granu.areaDiffNorm());
            volume.push_back(granu.volumeDiffNorm());

        }

    }

    template<class Image1>
    void ImCloseGranulometry(const Image1 &imin, std::vector<unsigned> &seSizes,
                             std::vector<double> &area, std::vector<double> &volume,
                             unsigned objLabel = 0)

    {
        typedef typename Image1::value_type value_type;

        if(seSizes.size() == 0)
            return;

        area.clear();
        volume.clear();

        GranulometryMeasure<value_type> granu;

        Image1 temp(imin.size());
        Image1 close(imin.size());

        for(std::vector<unsigned>::size_type i = 0;
            i != seSizes.size(); ++i)
        {
            if(i==0)
                vigra::discDilation(srcImageRange(imin), destImage(temp), seSizes[i]);
            else
                vigra::discDilation(srcImageRange(close), destImage(temp), seSizes[i]);
            vigra::discErosion(srcImageRange(temp), destImage(close), seSizes[i]);

            granu.reset();
            vigra::inspectTwoImages(srcImageRange(imin), srcImage(close), granu);

            area.push_back(granu.areaDiffNorm());
            volume.push_back(granu.volumeDiffNorm());
        }

    }

};
};
#endif /*MORPHO_GRANULOMETRIES_HXX_*/
