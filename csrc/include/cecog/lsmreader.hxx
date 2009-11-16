/*******************************************************************************

                          The CellCognition Project
                   Copyright (c) 2006 - 2009 Michael Held
                    Gerlich Lab, ETH Zurich, Switzerland

            CellCognition is distributed under the LGPL license.
                      See the LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL: https://svn.cellcognition.org/mito/trunk/include/mito/reader/wrap_lsm#$

#ifndef CECOG_LSMREADER_HXX_
#define CECOG_LSMREADER_HXX_

#include <map>
#include <sys/fcntl.h>
#include <unistd.h>
#include <stdio.h>

// libtiff declarations
extern "C"
{
#include <tiff.h>
#include <tiffio.h>
}

#include "vigra/stdimage.hxx"
#include "vigra/impex.hxx"
#include "vigra/multi_impex.hxx"
#include "vigra/multi_array.hxx"
#include "vigra/multi_pointoperators.hxx"
#include "vigra/error.hxx"
#include "vigra/sized_int.hxx"

#include "boost/config.hpp"
#include "boost/detail/endian.hpp"


namespace cecog
{

  /* helper function to extract any type of integer from a buffer and
   * converts by endianess
   * FIXME: could be put in a general class as static method
   */
  template <class T>
  T get_number_from_array(void *p, int offset, int size, bool little_endian=true)
  {
    T v = 0;
    int bit_shift;
    for (int i=0; i < size; i++)
    {
      bit_shift = (little_endian) ? i*8 : (size-i-1)*8;
      v += *((uint8*)p + offset + i) << bit_shift;
    }
    return (T)v;
  }

  /* helper function to extract an 8 byte double from a buffer and
   * converts by endianess (union requires to run on a little endian system)
   * FIXME: could be put in a general class as static method
   */
  double get_double_from_array(void *p, int offset, bool little_endian=true)
  {
    // expecting the machine to run in LITTLE_ENDIAN mode
    // (there seems to be no compiler/system flag for this, just a test)
    union BytesDouble
    {
      uint8 Bytes[8];
      double Double;
    } m;
    int order;
    for (int i=0; i < 8; i++)
    {
      #if defined(BOOST_LITTLE_ENDIAN)
        order = (little_endian) ? i : 7-i;
      #elif defined(BOOST_BIG_ENDIAN)
        order = (!little_endian) ? i : 7-i;
      #else
        #error Can not handle endianness.
      #endif
      m.Bytes[order] = *((uint8*)p + offset + i);
    }
    return m.Double;
  }

  /* helper function to extract any type of integer from a file by
   * file descriptor and converts by endianess
   * FIXME: could be put in a general class as static method
   */
  template <class T>
  T get_number_from_file(int fds, int size, bool little_endian=true)
  {
    int8 data[size];
    int rsize = read(fds, data, size);
    assert(rsize == size);
    return get_number_from_array<T>(data, 0, size, little_endian);
  }

  /* helper function to extract an 8 byte double from a file by
   * file descriptor and converts by endianess
   * FIXME: could be put in a general class as static method
   */
  double get_double_from_file(int fds, bool little_endian=true)
  {
    const int size = 8;
    int8 data[size];
    int rsize = read(fds, data, size);
    assert(rsize == size);
    return get_double_from_array(data, 0, little_endian);
  }

  /* helper function to convert an uint32 to vigra::RGBValue<uint8>
   * ordering (8bit each, little endian): red green blue
   * FIXME: could be put in a general class as static method
   */
  vigra::RGBValue<uint8> convert_to_rgb(uint32 n)
  {
    return vigra::RGBValue<uint8>(n & 0xff, (n >> 8) & 0xff, (n >> 16) & 0xff);
  }


  /* LSM specific meta data
   * FIXME: should be unified with a general structure for meta data
   */
  struct LsmMetaData
  {
    int iDimX, iDimY, iDimZ, iDimC, iDimT;
    std::string sPixelType, sDimOrder;

    int iThumbnailX, iThumbnailY;
    double dVoxelX, dVoxelY, dVoxelZ;
    double dTimeInterval;

    typedef std::pair<std::string, vigra::RGBValue<uint8> > t_ChannelDataItem;
    typedef std::vector<t_ChannelDataItem> t_ChannelData;
    t_ChannelData vChannelData;

    typedef std::vector<double> t_TimestampData;
    t_TimestampData vTimestampData;

    std::string toString()
    {
      char str[500];
      sprintf(str, "xyzct Order %s, Dim (%d %d %d %d %d), Voxel (%.3E %.3e %.3E), TimeInterval %.4E",
              sDimOrder.c_str(),
              iDimX, iDimY, iDimZ, iDimC, iDimT,
              dVoxelX, dVoxelY, dVoxelZ,
              dTimeInterval);
      return std::string(str);
    }

  };


  // wrapper to convert vigra::UnStrided array to vigra::BasicImage<vigra::RGBValue<T> >
  // could be part of a super-class, which holds the metadata as well
  template <class T>
  vigra::BasicImage<vigra::RGBValue<T> >
  makeRGBImage(vigra::MultiArrayView<3, T> const &oView3D,
               LsmMetaData const &oMetaData)
  {
    vigra::BasicImage<vigra::RGBValue<T> > oImageRGB(oView3D.shape(0), oView3D.shape(1));
    for (int iC=0; iC < 3; iC++)
    {
      // get the rgb-color of this channel as defined in LSM
      vigra::RGBValue<uint8> rgb = oMetaData.vChannelData[iC].second;

      vigra::MultiArrayView<2, T> oView2D = oView3D.bindOuter(iC);
      vigra::BasicImageView<T> oBView = makeBasicImageView(oView2D);

      // we could probably also do a combineTwoImages here
      typename vigra::BasicImageView<T>::iterator itImgBegin = oBView.begin();
      typename vigra::BasicImage<vigra::RGBValue<T> >::ScanOrderIterator itImgRGBBegin = oImageRGB.begin();
      for (; itImgBegin != oBView.end() && itImgRGBBegin != oImageRGB.end(); itImgBegin++, itImgRGBBegin++)
        // loop over r,g,b
        for (int m=0; m < 3; m++)
        {
          // scale the current pixel by means of its channel component
          // FIXME: scaling is limited to uint8, so template generalization is broken here
          uint8 newv = rgb[m] / 255.0 * (*itImgBegin);
          // do a max-blending with any value already assigned to this pixel
          (*itImgRGBBegin)[m] = std::max((*itImgRGBBegin)[m], newv);
        }
    }
    return oImageRGB;
  }



  /* LsmReader class
   */
  class LsmReader
  {
    public:

      typedef vigra::MultiArrayView<5, uint8> ArrayView5D;
      typedef vigra::MultiArrayView<4, uint8> ArrayView4D;
      typedef vigra::MultiArrayView<3, uint8> ArrayView3D;
      typedef vigra::MultiArrayView<2, uint8> ArrayView2D;

      typedef vigra::MultiArray<5, uint8> Array5D;
      typedef vigra::MultiArray<4, uint8> Array4D;
      typedef vigra::MultiArray<3, uint8> Array3D;
      typedef vigra::MultiArray<2, uint8> Array2D;

      //static int const ZEISS_ID = 34412;
      BOOST_STATIC_CONSTANT(int, ZEISS_ID = 34412);

      LsmMetaData metadata;

      LsmReader(std::string filename) :
        sFilepath(filename)
      {
        // #FIXME: since
        // 'TIFFSeekProc fSeekProc = TIFFGetSeekProc(pTiff);' and
        // 'TIFFReadWriteProc fReadProc = TIFFGetReadProc(pTiff);'
        // are not working properly, we have to open the file manually using a
        // fds (file descriptor) to seek/read extra data blocks
        // (TIFFFdOpen gives libtiff access to an already opened file via fds)

        fdTiff = open(filename.c_str(), O_RDONLY, 0666);
        //pTiff = TIFFOpen( filename.c_str(), "r" );
        pTiff = TIFFFdOpen(fdTiff, filename.c_str(), "r");

        if (!pTiff)
        {
          fprintf(stderr, "Unable to open LSM file '%s'.", filename.c_str());
          exit(39);
        }

        readMetadata();
      }

      ~LsmReader()
      {
        if (pTiff != NULL)
          TIFFClose(pTiff);
        if (pStripBuffer != NULL)
          _TIFFfree(pStripBuffer);
        close(fdTiff);
      }

      void readMetadata()
      {
        // the endianess is fixed to LITTLE for LSM files
        bLittleEndian = true;

        uint32 iWidth, iHeight, iBitsPerSample;

        TIFFGetField(pTiff, TIFFTAG_IMAGEWIDTH, &iWidth);
        TIFFGetField(pTiff, TIFFTAG_IMAGELENGTH, &iHeight);

        // read the LSM specific TIFFTAG
        uint16 iCount;
        char *pLsmTagData;
        if (!TIFFGetField(pTiff, ZEISS_ID, &iCount, &pLsmTagData))
        {
          fprintf(stderr, "No ZEISS TIFFTAG (ID %d) found! No valid LSM510 file!", ZEISS_ID);
          exit(40);
        }

        //for (int i=0; i < 100; i++)
        //  printf("%3d ", *((uint8*)pLsmTagData+i));

        metadata.iDimX = get_number_from_array<uint32>(pLsmTagData, 8, 4, bLittleEndian);
        metadata.iDimY = get_number_from_array<uint32>(pLsmTagData, 12, 4, bLittleEndian);
        metadata.iDimZ = get_number_from_array<uint32>(pLsmTagData, 16, 4, bLittleEndian);
        metadata.iDimC = get_number_from_array<uint32>(pLsmTagData, 20, 4, bLittleEndian);
        metadata.iDimT = get_number_from_array<uint32>(pLsmTagData, 24, 4, bLittleEndian);

        int iPixel = get_number_from_array<int>(pLsmTagData, 28, 4, bLittleEndian);
        switch (iPixel) {
          case 1: metadata.sPixelType = "uint8"; break;
          case 2: metadata.sPixelType = "uint16"; break;
          case 5: metadata.sPixelType = "float"; break;
          default: metadata.sPixelType = "uint8";
        }


        int iScanType = get_number_from_array<int>(pLsmTagData, 88, 4, bLittleEndian);
        switch (iScanType) {
          case 0: metadata.sDimOrder = "XYZCT"; break;
          case 1: metadata.sDimOrder = "XYZCT"; break;
          case 3: metadata.sDimOrder = "XYTCZ"; break;
          case 4: metadata.sDimOrder = "XYZTC"; break;
          case 5: metadata.sDimOrder = "XYTCZ"; break;
          case 6: metadata.sDimOrder = "XYZTC"; break;
          case 7: metadata.sDimOrder = "XYCTZ"; break;
          case 8: metadata.sDimOrder = "XYCZT"; break;
          case 9: metadata.sDimOrder = "XYTCZ"; break;
          default: metadata.sDimOrder = "XYZCT";
        }

        metadata.iThumbnailX = get_number_from_array<uint32>(pLsmTagData, 32, 4, bLittleEndian);
        metadata.iThumbnailY = get_number_from_array<uint32>(pLsmTagData, 36, 4, bLittleEndian);

        metadata.dVoxelX = get_double_from_array(pLsmTagData, 40, bLittleEndian);
        metadata.dVoxelY = get_double_from_array(pLsmTagData, 48, bLittleEndian);
        metadata.dVoxelZ = get_double_from_array(pLsmTagData, 56, bLittleEndian);

        uint32 iData;
        iData = get_number_from_array<uint32>(pLsmTagData, 96, 4, bLittleEndian);
        //printf("data: %d\n", iData);
        //parseOverlays(data, "OffsetVectorOverlay", little);
        iData = get_number_from_array<uint32>(pLsmTagData, 100, 4, bLittleEndian);
        //printf("data: %d\n", iData);
        //parseSubBlocks(data, "OffsetInputLut", little);
        iData = get_number_from_array<uint32>(pLsmTagData, 104, 4, bLittleEndian);
        //printf("data: %d\n", iData);
        //parseSubBlocks(data, "OffsetOutputLut", little);

        // channel intensities and names
        iData = get_number_from_array<uint32>(pLsmTagData, 108, 4, bLittleEndian);
        //printf("data: %d\n", iData);
        parseChannels(iData);

        metadata.dTimeInterval = get_double_from_array(pLsmTagData, 112, bLittleEndian);



        // timestamp block
        iData = get_number_from_array<uint32>(pLsmTagData, 132, 4, bLittleEndian);
        //printf("timestamp offset: %d\n", iData);
        parseTimestamps(iData);

        //iData = get_number_from_array<uint32>(pLsmTagData, 136, 4, bLittleEndian);
        //printf("data: %d\n", iData);


        //printf("%s\n", metadata.toString().c_str());

        // get the size of each strip (one-channel image) and the number of strips to read
        // (should be the same then TIFFTAG_SAMPLESPERPIXEL - for RGB we assume 3 strips)
        iStripSize = TIFFStripSize(pTiff);
        iStripMax = TIFFNumberOfStrips(pTiff);
        ulBufferSize = iStripSize;

        //printf("stripSize %d, stripMax %d, bufferSize %d\n", iStripSize, iStripMax, ulBufferSize);

        if ((pStripBuffer = _TIFFmalloc(ulBufferSize)) == NULL)
        {
          fprintf(stderr, "Could not allocate enough memory (%d Bytes) for the uncompressed image\n",
                  ulBufferSize);
          exit(42);
        }


        // scan all TIFF directories and filter them by width/height and subfiletype
        // (LSM stores a thumbnail for every image -> number of total images is twice as high).
        // store all valid directories in a vector, which contains the directory ID (starting with 0)
        int iDirCount = 0;
        int iSubfileType, iSubWidth, iSubHeight;
        do
        {
          TIFFGetField(pTiff, TIFFTAG_SUBFILETYPE, &iSubfileType);
          TIFFGetField(pTiff, TIFFTAG_IMAGEWIDTH, &iSubWidth);
          TIFFGetField(pTiff, TIFFTAG_IMAGELENGTH, &iSubHeight);

          // subfiletype must be zero for a raw image
          if (iSubWidth == metadata.iDimX && iSubHeight == metadata.iDimY && iSubfileType == 0)
          {
            // we assume that a valid subimage (TIFF directory entry) has the same size, strips and therefore
            // the same planar configuration
            uint16 uiPlanarConfig;
            TIFFGetField(pTiff, TIFFTAG_PLANARCONFIG, &uiPlanarConfig);
            if (uiPlanarConfig != PLANARCONFIG_SEPARATE)
            {
              fprintf(stderr, "TIFFTAG_PLANARCONFIG is NOT PLANARCONFIG_SEPARATE!\n");
              exit(41);
            }
            uint16 iSubBits;
            TIFFGetField(pTiff, TIFFTAG_BITSPERSAMPLE, &iSubBits);
            if (iSubBits != 8)
            {
              fprintf(stderr, "TIFFTAG_BITSPERSAMPLE is NOT 8 (only 8bit/channel supported)!\n");
              exit(41);
            }
            vValidDirectories.push_back(iDirCount);
          }
          iDirCount++;
        } while (TIFFReadDirectory(pTiff));

        //printf("%d dirs found (%d valid)\n", iDirCount, vValidDirectories.size());

      }

      bool readXYCImageToArrayView(int iT, int iZ, ArrayView3D &oView3D)
      {
        int iDirIndex = vValidDirectories[iT*metadata.iDimZ+iZ];
        TIFFSetDirectory(pTiff, iDirIndex);
        for (int iStripCount=0, iResult=0; iStripCount < iStripMax; iStripCount++)
        {
          ArrayView2D oView2D = oView3D.bindOuter(iStripCount);
          if ((iResult = TIFFReadEncodedStrip(pTiff, iStripCount, oView2D.data(), iStripSize)) == -1)
          {
            fprintf(stderr, "Read error on input strip number %d\n", iStripCount);
            exit(42);
          }

          //assert(oView2D.data() != NULL);
          // #FIXME!
          //for (int y=0, c=0; y < metadata.iDimY; y++)
          //  for (int x=0; y < metadata.iDimX; x++, c++)
          //    oView5D(x,y, iStripCount, iZ, iT) = *((uint8*)pStripBuffer+c);
          //memcpy(oView2D.data(), pStripBuffer, iStripSize);
          //std::uninitialized_copy(pStripBuffer, (uint8*)pStripBuffer+iStripSize, oView2D.data());

        }
        return true;
      }

      bool readXYImageToArrayView(int iT, int iZ, int iC, ArrayView2D &oView2D)
      {
        vigra_precondition(iC >= 0 && iC < metadata.iDimC,
          "LsmReader::getXYImage: Channel not valid!");
        vigra_precondition(iZ >= 0 && iZ < metadata.iDimZ,
          "LsmReader::getXYImage: Z-slice not valid!");
        vigra_precondition(iT >= 0 && iT < metadata.iDimT,
          "LsmReader::getXYImage: Timepoint not valid!");

        int iDirIndex = vValidDirectories[iT*metadata.iDimZ+iZ];
        TIFFSetDirectory(pTiff, iDirIndex);
        if ((TIFFReadEncodedStrip(pTiff, iC, oView2D.data(), iStripSize)) == -1)
          vigra_fail("LsmReader::getXYImage:TIFFReadEncodedStrip: Read error on input strip number.");

        return true;
      }


      vigra::BImage getXYImage(int iT, int iZ, int iC)
      {
        vigra_precondition(iC >= 0 && iC < metadata.iDimC,
          "LsmReader::getXYImage: Channel not valid!");
        vigra_precondition(iZ >= 0 && iZ < metadata.iDimZ,
          "LsmReader::getXYImage: Z-slice not valid!");
        vigra_precondition(iT >= 0 && iT < metadata.iDimT,
          "LsmReader::getXYImage: Timepoint not valid!");

        vigra::BImage::value_type pData[metadata.iDimX * metadata.iDimY];
        int iDirIndex = vValidDirectories[iT*metadata.iDimZ+iZ];
        TIFFSetDirectory(pTiff, iDirIndex);
        if (TIFFReadEncodedStrip(pTiff, iC, pData, iStripSize) == -1)
          vigra_fail("LsmReader::getXYImage:TIFFReadEncodedStrip: Read error on input strip number.");

        vigra::BImage imgOut(metadata.iDimX, metadata.iDimY, pData);
        return imgOut;
      }



      std::string sFilepath;

    protected:

      /* read channel colors (rgb) and names from LSM subblock
       */
      bool parseChannels(uint32 iOffset)
      {
        bool bSuccess = false;
        if (iOffset != 0)
        {
          //printf("Channel intensities and names\n");
          assert(lseek(fdTiff, iOffset, SEEK_SET) > 0);

          int32 iSize = get_number_from_file<int32>(fdTiff, 4, bLittleEndian);
          int32 iNumberColors =  get_number_from_file<int32>(fdTiff, 4, bLittleEndian);
          int32 iNumberNames  =  get_number_from_file<int32>(fdTiff, 4, bLittleEndian);
          int32 iOffsetColors =  get_number_from_file<int32>(fdTiff, 4, bLittleEndian);
          int32 iOffsetNames  =  get_number_from_file<int32>(fdTiff, 4, bLittleEndian);

          assert(iNumberColors == iNumberNames);

          // read colors (r,g,b) for each channel (offset relative to block start)
          assert(lseek(fdTiff, iOffset+iOffsetColors, SEEK_SET) > 0);
          for (int32 i=0; i < iNumberColors; i++)
          {
            int32 iRGBColor = get_number_from_file<int32>(fdTiff, 4, bLittleEndian);
            vigra::RGBValue<uint8> rgb = convert_to_rgb(iRGBColor);
            metadata.vChannelData.push_back(LsmMetaData::t_ChannelDataItem("",rgb));
            //printf("%d (%d %d %d) ", iRGBColor, rgb.red(), rgb.green(), rgb.blue());
          }
          //printf("\n");

          // read names (\0-string) for each channel (offset relative to block start)
          // #FIXME: weird read procedure, since Zeiss stores \0 in front of the
          //         actual string
          //         solution: \0-termination and string is only counted after
          //                    some useful character (here >=32)
          assert(lseek(fdTiff, iOffset+iOffsetNames, SEEK_SET) > 0);
          for (int32 i=0; i < iNumberNames; i++)
          {
            const int iSize = 300;
            char aName[iSize];
            bool found=false;
            int n = 0;
            char c;
            do
            {
              c = get_number_from_file<uint8>(fdTiff, 1, bLittleEndian);
              if (c >= 32)
                found = true;
              if (found)
              {
                aName[n] = c;
                n++;
              }
            } while ((c != '\0' || !found) && n < iSize);
            //printf("%s\n", aName);
            metadata.vChannelData[i].first = aName;
          }
          bSuccess = true;
        }
        return bSuccess;
      }

      /* read exact timestamps for timelapse acquisition from LSM subblock
       */
      bool parseTimestamps(uint32 iOffset)
      {
        bool bSuccess = false;
        if (iOffset != 0)
        {
          //printf("Timestamps\n");
          // seek to the subblock within the LSM file
          assert(lseek(fdTiff, iOffset, SEEK_SET) > 0);

          int32 iSize = get_number_from_file<int32>(fdTiff, 4, bLittleEndian);
          int32 iNum =  get_number_from_file<int32>(fdTiff, 4, bLittleEndian);
          // match the entire block size?
          assert(iSize == iNum*8+8);

          for (int32 i=0; i < iNum; i++)
          {
            double dTimestamp = get_double_from_file(fdTiff, bLittleEndian);
            metadata.vTimestampData.push_back(dTimestamp);
            //printf("%4d:%.3E ", i, dTimestamp);
          }
          bSuccess = true;
        }
        //printf("\n");
        return bSuccess;
      }

    private:
      int fdTiff;
      TIFF *pTiff;
      tdata_t pStripBuffer;
      std::vector<int> vValidDirectories;
      int iStripSize, iStripMax;
      unsigned long ulBufferSize;
      bool bLittleEndian;
  };

}

#endif // CECOG_LSMREADER_HXX_
