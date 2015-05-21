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


#ifndef CECOG_READOUT
#define CECOG_READOUT

#include <map>
#include <string>
#include <assert.h>

#include "vigra/stdimage.hxx"
#include "vigra/impex.hxx"
#include "vigra/inspectimage.hxx"
#include "vigra/transformimage.hxx"
#include "vigra/flatmorphology.hxx"
#include "vigra/resizeimage.hxx"

#include "cecog/containers.hxx"
#include "cecog/images.hxx"
#include "cecog/segmentation.hxx"
#include "cecog/seededregion.hxx"
#include "cecog/transforms.hxx"



namespace cecog
{


  // wrapper to convert vigra::UnStrided array to vigra::BasicImage<vigra::RGBValue<T> >
  // could be part of a super-class, which holds the metadata as well
  template <class T>
  vigra::BasicImage<vigra::RGBValue<T> > makeRGBImage(vigra::ArrayVector< vigra::BasicImageView<T> > const & oImageVector,
                                                      vigra::ArrayVector< vigra::RGBValue<T> > const & oChannelVector,
                                                      vigra::ArrayVector< float > const & oAlphaVector)
  {
    vigra_precondition(oImageVector.size() > 0,
                       "makeRGBImage: List of images must contain at least one item!");
    vigra_precondition((oImageVector.size() == oChannelVector.size()) &&
                       (oChannelVector.size() == oAlphaVector.size()),
                       "makeRGBImage: List of images must have same size as list of RGBValues");

    int iDimX = oImageVector[0].width();
    int iDimY = oImageVector[0].height();
    int iDimC = oImageVector.size();

    vigra::BasicImage< vigra::RGBValue<T> > imgRGB(iDimX, iDimY);

    for (int iC=0; iC < iDimC; iC++)
    {
      vigra::RGBValue<T> rgb = oChannelVector[iC];
      float fAlpha = oAlphaVector[iC];

      vigra::BasicImageView<T> iview2D = oImageVector[iC];

      // we could probably also do a combineTwoImages here
      typename vigra::BasicImageView<T>::const_iterator itImgBegin = iview2D.begin();
      typename vigra::BasicImage<vigra::RGBValue<T> >::ScanOrderIterator itImgRGBBegin = imgRGB.begin();
      for (; itImgBegin != iview2D.end() && itImgRGBBegin != imgRGB.end(); itImgBegin++, itImgRGBBegin++)
        // loop over r,g,b: do the RGB-blending
        for (int m=0; m < 3; m++)
        {
          // scale the current pixel by means of its channel component
          // FIXME: scaling is limited to uint8, so template generalization is broken here
          uint8 newv = uint16(fAlpha * (*itImgBegin) / 255.0 * rgb[m]) % 256;
          // do a max-blending with any value already assigned to this pixel
          (*itImgRGBBegin)[m] = std::max((*itImgRGBBegin)[m], newv);
        }
    }
    return imgRGB;
  }

  template <class T>
  vigra::BasicImage<vigra::RGBValue<T> > makeRGBImage(vigra::ArrayVector< vigra::BasicImageView<T> > const & oImageVector,
                                                      vigra::ArrayVector< vigra::RGBValue<T> > const & oChannelVector)
  {
    vigra::ArrayVector< float > oAlphaVector;
    for (size_t iIdx=0; iIdx < oChannelVector.size(); iIdx++)
      oAlphaVector.push_back(1.0);
    return makeRGBImage(oImageVector, oChannelVector, oAlphaVector);
  }

  template <class T>
  vigra::BasicImage<vigra::RGBValue<T> > makeRGBImageC(vigra::BasicImageView< vigra::RGBValue <T> > const & oImageColor,
														vigra::BasicImageView<T> const & oImageGrey,
                                                      vigra::ArrayVector< vigra::RGBValue<T> > const & oChannelVector,
                                                      vigra::ArrayVector< float > const & oAlphaVector)
  {
    vigra_precondition(oAlphaVector.size() > 0,
                       "makeRGBImage: List of images must contain at least one item!");
    vigra_precondition(oAlphaVector.size() == 2,
                       "makeRGBImage: List of images must have same size as list of RGBValues");

    int iDimX = oImageColor.width();
    int iDimY = oImageColor.height();
    //int iDimC = oAlphaVector.size();

    vigra::BasicImage< vigra::RGBValue<T> > imgRGB(iDimX, iDimY);

	
	vigra::RGBValue<T> rgbC = oChannelVector[0];
	vigra::RGBValue<T> rgbG = oChannelVector[1];
	float fAlphaC = oAlphaVector[0];
	float fAlphaG = oAlphaVector[1];
	
	vigra::BasicImageView< vigra::RGBValue <T> > iview2DC = oImageColor;
	vigra::BasicImageView<T> iview2DG = oImageGrey;
	
	// we could probably also do a combineTwoImages here
	typename vigra::BasicImageView< vigra::RGBValue <T> >::const_iterator itImgBeginC = iview2DC.begin();
	typename vigra::BasicImageView<T>::const_iterator itImgBeginG = iview2DG.begin();
	typename vigra::BasicImage<vigra::RGBValue<T> >::ScanOrderIterator itImgRGBBegin = imgRGB.begin();
	for (; itImgBeginC != iview2DC.end() && itImgRGBBegin != imgRGB.end(); itImgBeginC++, itImgBeginG++, itImgRGBBegin++)
	// loop over r,g,b: do the RGB-blending
	for (int m=0; m < 3; m++)
	{
	  // scale the current pixel by means of its channel component
	  // FIXME: scaling is limited to uint8, so template generalization is broken here
	  uint8 newvC = uint16(fAlphaC * ((*itImgBeginC)[m]) / 255.0 * rgbC[m]) % 256;
	  uint8 newvG = uint16(fAlphaG * (*itImgBeginG) / 255.0 * rgbG[m]) % 256;
	  // do a max-blending with any value already assigned to this pixel
	  
	  (*itImgRGBBegin)[m] = std::max(newvC, newvG);
	}

	
    return imgRGB;
  }





  class ArrayStitcher
  {
  public:

    ArrayStitcher(int iDimX, int iDimY, int imgWidth, int imgHeight, float fScale=1.0)
      : iDimX(iDimX), iDimY(iDimY),
        imgWidth(imgWidth), imgHeight(imgHeight),
        fScale(fScale)
    {
      iScaledWidth = imgWidth * fScale;
      iScaledHeight = imgHeight * fScale;
      imgRGBStiched.resize(iScaledWidth * iDimX, iScaledHeight * iDimY);
    }

    void addImage(vigra::BRGBImage const &imgRGB, int iPosX, int iPosY, int iFrameSize=1, RGBValue oFrameColor=YELLOW)
    {
      vigra::BRGBImage imgRGBScaled(iScaledWidth, iScaledHeight);
      vigra::resizeImageLinearInterpolation(srcImageRange(imgRGB), destImageRange(imgRGBScaled));

      // draw the frame
      for (int f=0; f < iFrameSize; f++)
      {
        drawRectangle(imgRGBScaled.upperLeft()  + vigra::Diff2D(f,f),
                      imgRGBScaled.lowerRight() - vigra::Diff2D(f,f),
                      imgRGBScaled.accessor(),
                      oFrameColor);
      }

      vigra::copyImage(imgRGBScaled.upperLeft(),
                       imgRGBScaled.lowerRight(),
                       imgRGBScaled.accessor(),
                       imgRGBStiched.upperLeft() + vigra::Diff2D(iPosX*iScaledWidth, iPosY*iScaledHeight),
                       imgRGBStiched.accessor());
    }

    vigra::BRGBImage getStitchedImage()
    {
      return imgRGBStiched;
    }

  private:
    int iDimX;
    int iDimY;
    int imgWidth;
    int imgHeight;
    int iScaledWidth;
    int iScaledHeight;
    float fScale;
    vigra::BRGBImage imgRGBStiched;
  };

  vigra::MultiArray<4, uint8> transformImageListToArray4D(std::vector<vigra::BImage> const &vImages,
                                                          int iDim3, int iDim4)
  {
    vigra_precondition(vImages.size() == static_cast<unsigned>(iDim3*iDim4),
        "transformImageListToArrayView4D: size of image list must match dimensions!");

    vigra_precondition(vImages.size() > 0,
        "transformImageListToArrayView4D: size of image list must be > 0!");

    typedef vigra::MultiArray<4, uint8> Array4D;
    typedef vigra::MultiArrayView<3, uint8> ArrayView3D;
    typedef vigra::MultiArrayView<2, uint8> ArrayView2D;

    int iDimX = vImages[0].width();
    int iDimY = vImages[0].height();

    Array4D array4D(Array4D::difference_type(iDimX, iDimY, iDim3, iDim4));
    std::vector<vigra::BImage>::const_iterator itImageList = vImages.begin();

    for (int i4=0; i4 < iDim4; i4++)
    {
      ArrayView3D view3D = array4D.bindOuter(i4);
      for (int i3=0; i3 < iDim3; i3++)
      {
        ArrayView2D view2D = view3D.bindOuter(i3);
        vigra::BasicImageView<uint8> imgView2D = makeBasicImageView(view2D);
        copyImage(srcImageRange(*itImageList), destImage(imgView2D));
        itImageList++;
      }
    }

    return array4D;
  }


}

#endif // CECOG_READOUT
