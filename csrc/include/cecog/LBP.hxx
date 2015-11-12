#ifndef __LBP_h
#define __LBP_h
/******************************************************
 Local Binary Patterns (LBPs)
 coded by Xiwei ZHANG
 nov. 2015, CBIO
 
 =======================================================================
 ### Codes are based on the articles :
 1. Ojala, T., Pietikäinen, M., & Mäenpää, T. (2002). Multiresolution gray-scale and rotation invariant texture classification with local binary patterns. Pattern Analysis and Machine Intelligence, IEEE Transactions on, 24(7), 971-987.
 2. Huang, D., Shan, C., Ardabilian, M., Wang, Y., & Chen, L. (2011). Local binary patterns and its application to facial image analysis: a survey. Systems, Man, and Cybernetics, Part C: Applications and Reviews, IEEE Transactions on, 41(6), 765-781.
 
 
 =======================================================================
 ### To use this file, call function: LBPImage(...)
 ### It is an overloaded function. You have two possibilites to use it
 
 1. Compute LBP on the entire given image
 LBPImage( input_image, output_image, R, P, isPadding, isInterpolate)
    - input_image: vigra::MultiArrayView<2, UInt8>  (The image which you want to compute LBP on. Note image type should be UInt8)
    - output_image: vigra::MultiArrayView<2, UInt8> (The output image, each pixel is the correponding LBP decimal value. Note only works with P = 8)
    - R: int (The radius of the LBP)
    - P: int (The number of sample points. Strongly recommanded 8)
    - isPadding: bool (Extending the image border by mirroring. If disabled, the border region inside R width, will not be computed)
    - isInterpolate: bool (Use a linear interpolate for the points sampled on the circle. If disabled, only the pixel with the approximate coordinates is considered)
 
 
 2. Compute LBP on the region where the mask image value larger than zero
 LBPImage( input_image, mask_image, output_image, R, P, isInterpolate)
    - mask_image: vigra::MultiArrayView<2, UInt8> (Set pixel value larger than zero, where you want to compute the LBP)
 
 ### The return value is a vector<float>, which is the normalized histogram of the LBP features
 

 
 =======================================================================
 ### Some notes about this code:
 ### An exhaustive mapping matrix <valMap> is given at the beginning of the code.
 ### It is only used in the case of P=8, which is strongly recommanded.
 
 If coded by 8-bits (8 neighbors), there will be 256 values.
 If rotation invariant, the number is reduced to 36 values.
 According to Ojala. et al., the uniform patterns are only 8, which are:
    00000000 -> 0
    00000001 -> 1
    00000011 -> 3
    00000111 -> 7
    00001111 -> 15
    00011111 -> 31
    00111111 -> 63
    01111111 -> 127
    11111111 -> 255

 Thus, to the simplicity, the decimal values are coded as following:
 valMap[36]
 uniform patterns: 
 0:0, 1:1, 3:2, 7:3, 15:4, 31:5, 63:6, 127:7, 255:8
 
 other patterns:
 5:9, 9:10, 11:11, 13:12, 17:13, 19:14, 21:15, 23:16, 25:17, 27:18, 29:19, 37:20,
 39:21, 43:22, 45:23, 47:24, 51:25, 53:26, 55:27, 59:28, 61:29, 85:30, 87:31, 91:32,
 95:33, 111:34, 119:35

 *****************************************************/

//#include "utility_z.hxx"
#include <vector>
#include "vigra/multi_array.hxx"
#include "cecog/shared_objects.hxx"
#include "cecog/containers.hxx"


using namespace cecog;

const float PI = 3.1415;

const int valMap[256] = {
//   0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
     0,  1, -1,  2, -1,  9, -1,  3, -1, 10, -1, 11, -1, 12, -1,  4,  // 0
    -1, 13, -1, 14, -1, 15, -1, 16, -1, 17, -1, 18, -1, 19, -1,  5,  // 16
    -1, -1, -1, -1, -1, 20, -1, 21, -1, -1, -1, 22, -1, 23, -1, 24,  // 32
    -1, -1, -1, 25, -1, 26, -1, 27, -1, -1, -1, 28, -1, 29, -1,  6,  // 48
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 64
    -1, -1, -1, -1, -1, 30, -1, 31, -1, -1, -1, 32, -1, -1, -1, 33,  // 80
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34,  // 96
    -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1,  7,  // 112
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 128
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 144
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 160
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 176
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 192
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 208
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  // 224
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  8,  // 240
};

template<typename _UINT>
inline _UINT rotLeft (_UINT val, size_t n){
    return (val << n) | (val >> (sizeof(_UINT) * CHAR_BIT - n));
}

template <class T>
struct pixel {
    T x;
    T y;
    
    pixel(T X, T Y) { x = X; y = Y;}
};


/****************************
 Suppoing the center point is (0,0)
 Get the sampled circular neighbor points
 *****************************/
std::vector<pixel<int> > const getNBList(int R, int P){
    std::vector<pixel<int> > nblist;
    
    float step = 2 * PI / P;
    for (int i=0; i<P; ++i){
        float X = roundf ( R * cos(i * step) );
        float Y = roundf ( R * sin(i * step) );
        pixel<int> pp(X, Y);
        nblist.push_back(pp);
    }
    return nblist;
}

std::vector<pixel<float> > const getNBListFloat(int R, int P){
    std::vector<pixel<float> > nblist;
    
    float step = 2 * PI / P;
    for (int i=0; i<P; ++i){
        float X = R * cos(i * step);
        float Y = R * sin(i * step);
        pixel<float> pp(X, Y);
        nblist.push_back(pp);
    }
    return nblist;
}


template <typename C1>
inline int array2Dec( C1 * ptr, size_t size){
    int vout(0);
    double count(0.f);
    for (size_t n=0; n<size; ++n) {
        vout += pow(2.0, count) * (*(ptr + n));
        count ++;
    }
    return vout;
}

template <class T>
int getValueInterpotlate(MultiArrayView<2, UInt8> const imin, float x, float y){
    int X0 = (int)x;
    int Y0 = (int)y;
    int X1 = X0 + 1;
    int Y1 = Y0 + 1;
    return
    T (roundf( (X1 - x) * (Y1 - y) * imin(X0, Y0) +
          (x - X0) * (Y1 - y) * imin(X1, Y0) +
          (y - Y0) * (X1 - x) * imin(X0, Y1) +
          (x - X0) * (y - Y0) * imin(X1, Y1) ) );
}


//// !!!! NOT used for cecog !!!!!!!!! Check the other funcion
//// Overload function Whole image or crop LBP compute
std::vector<float> LBPImage (MultiArrayView<2, UInt8> const imin,  MultiArrayView<2, UInt8> imout, int const R, int const P, bool isPadding, bool isInterplt){
    
    std::vector<pixel <float> > nblistF;
    std::vector<pixel <int> > nblistI;

    if (isInterplt)
        nblistF = getNBListFloat(R,P);
    else
        nblistI = getNBList(R,P);

    int n_val(0);
    if (P==8)
        n_val = 36;
    else
        n_val = int(pow(2.0, double(P)));
    std::vector<float> histogram(n_val, 0.0);

    
    //// Padding image
    if (isPadding){
        size_t W = imin.shape()[0];
        size_t H = imin.shape()[1];
        size_t WPad = W + R*2;
        size_t HPad = H + R*2;
        MultiArray<2, UInt8>  iminPad( WPad, HPad);
        MultiArray<2, UInt8>  imPadtemp2( WPad, HPad);
        
        iminPad.init(0);
        MultiArrayView <2, UInt8> subarray = iminPad.subarray(Shape2(R, R), Shape2(R+W, R+H));
        subarray = imin;
        for (size_t t=0; t<R; ++t ) {
            iminPad.bind<0>(t) = iminPad.bind<0>(2*R-t-1);
            iminPad.bind<0>(t+W+R) = iminPad.bind<0>(W+R-t-1);
            iminPad.bind<1>(t) = iminPad.bind<1>(2*R-t-1);
            iminPad.bind<1>(t+H+R) = iminPad.bind<1>(H+R-t-1);
        }

        int * compareResult = new int [P];
        for (size_t y=0; y<H; ++y) {
            for (size_t x=0; x<W; ++x) {
                for (size_t k=0; k<P; ++k) {
                    if (isInterplt) {
                        compareResult[k] = iminPad(x+R, y+R) <= getValueInterpotlate<uint8_t>(iminPad, x+R+nblistF[k].x, y+R+nblistF[k].y) ? 1 : 0;
                    }
                    else
                        compareResult[k] = iminPad(x+R, y+R) <= iminPad(x+R+nblistI[k].x, y+R+nblistI[k].y) ? 1 : 0;
                }
                
                uint8_t decVal = array2Dec<int>(compareResult, P);
                uint8_t minVal = decVal;
                
                for (size_t n=1; n<P; ++n) {
                    if (minVal > rotLeft<uint8_t>(decVal, n))
                        minVal = rotLeft<uint8_t>(decVal, n);
                }
                imout(x, y) = valMap[ minVal ];
                histogram[valMap[ minVal ]] ++;
            }
        }
        // exportImage(imout, ImageExportInfo("output/temp2.png"));
        
        delete[] compareResult;
        
    }
    
    //// NOT Padding image
    else{
        size_t W = imin.shape()[0];
        size_t H = imin.shape()[1];
        
        int * compareResult = new int [P];
        for (size_t y=R; y<H-R; ++y) {
            for (size_t x=R; x<W-R; ++x) {
                for (size_t k=0; k<P; ++k) {
                    if (isInterplt) {
                        compareResult[k] = imin(x, y) <= getValueInterpotlate<uint8_t>(imin, x+nblistF[k].x, y+nblistF[k].y) ? 1 : 0;
                    }
                    else{
                        compareResult[k] = imin(x, y) <= imin(x+nblistI[k].x, y+nblistI[k].y) ? 1 : 0;
                    }
                }
                
                uint8_t decVal = array2Dec<int>(compareResult, P);
                uint8_t minVal = decVal;
                
                for (size_t n=1; n<P; ++n) {
                    if (minVal > rotLeft<uint8_t>(decVal, n))
                        minVal = rotLeft<uint8_t>(decVal, n);
                }
                imout(x, y) = valMap[ minVal ];
                histogram[valMap[ minVal ]] ++;
            }
        }
        exportImage(imout, ImageExportInfo("output/temp2.png"));
        
        delete[] compareResult;
    }
    
    float sumV(0.0);
    for (size_t k=0; k<histogram.size(); ++k) {
        sumV += histogram[k];
    }
    for (size_t k=0; k<histogram.size(); ++k) {
        histogram[k] /= sumV;
        std::cout<<k<<" "<<histogram[k]<<std::endl;
    }
    return histogram;
}


//// overload function with mask image
template <class T1, class S1>
std::vector<float> LBPImage (MultiArrayView<2, UInt8> const imin, MultiArrayView<2, T1, S1> const immask, int label, int const R, int const P, bool isInterplt){
    
    std::vector<pixel <float> > nblistF;
    std::vector<pixel <int> > nblistI;
    
    if (isInterplt)
        nblistF = getNBListFloat(R,P);
    else
        nblistI = getNBList(R,P);
    
    int n_val(0);
    if (P==8)
        n_val = 36;
    else
        n_val = int(pow(2.0, double(P)));
    std::vector<float> histogram(n_val, 0.0);
    
    size_t W = imin.shape()[0];
    size_t H = imin.shape()[1];
    
    int toto(0);
    int * compareResult = new int [P];
    for (size_t y=R; y<H-R; ++y) {
        for (size_t x=R; x<W-R; ++x) {
            if (immask(x,y) != label) continue;
            toto ++;
            for (size_t k=0; k<P; ++k) {
                if (isInterplt) {
                    compareResult[k] = imin(x, y) <= getValueInterpotlate<uint8_t>(imin, x+nblistF[k].x, y+nblistF[k].y) ? 1 : 0;
                }
                else{
                    compareResult[k] = imin(x, y) <= imin(x+nblistI[k].x, y+nblistI[k].y) ? 1 : 0;
                }
            }
            
            uint8_t decVal = array2Dec<int>(compareResult, P);
            uint8_t minVal = decVal;
            
            for (size_t n=1; n<P; ++n) {
                if (minVal > rotLeft<uint8_t>(decVal, n))
                    minVal = rotLeft<uint8_t>(decVal, n);
            }
            // imout(x, y) = valMap[ minVal ];
            histogram[valMap[ minVal ]] ++;
        }
    }
    
    delete[] compareResult;

    
    float sumV(0.0);
    for (size_t k=0; k<histogram.size(); ++k) {
        sumV += histogram[k];
    }
    for (size_t k=0; k<histogram.size(); ++k) {
        histogram[k] /= sumV;
    }
    return histogram;
}


void CalculateFeaturesLBP(MultiArrayView<2, UInt8> const img_MA, MultiArrayView<2, int> const img_label_MA, ROIObject &o, int const label, std::vector<unsigned> const & lbpSizeVec, int extBorder = 10){
    //// crop to subimage
    int width = img_MA.shape()[0];
    int height = img_MA.shape()[1];

    int x_start = max ( (o.roi.upperLeft.x - extBorder), 0);
    int x_end = min( (o.roi.lowerRight.x + extBorder), width);
    int y_start = max( (o.roi.upperLeft.y - extBorder), 0);
    int y_end = min( (o.roi.lowerRight.y + extBorder), height);
    
    std::vector<float> lbp_histogram;
    
    MultiArrayView <2, UInt8> img_MAsub = img_MA.subarray(Shape2(x_start, y_start), Shape2(x_end, y_end));
    MultiArrayView <2, int> img_label_MAsub = img_label_MA.subarray(Shape2(x_start, y_start), Shape2(x_end, y_end));
    
    vigra::exportImage(img_MAsub, ImageExportInfo("/Users/xiwei_zhang/work/temp/totosub.png"));
    
    for (size_t k=0; k<lbpSizeVec.size(); ++k) {
        lbp_histogram = LBPImage(img_MAsub, img_label_MAsub, label, lbpSizeVec[k], 8, true);
        float sumV(0);
        //// output LBP features 0 - 8 to o.features, which are the most significant patterns.
        for (size_t l=0; l<9; ++l) {
            o.features["LBP_" + std::to_string(lbpSizeVec[k]) + "_" + std::to_string(l)] = lbp_histogram[l];
            sumV += lbp_histogram[l];
        }
        //// output the rest as a sum into the 9th feature
        o.features["LBP_" + std::to_string(lbpSizeVec[k]) + "_" + std::to_string(10)] = (1 - sumV);
    }

}

#endif
