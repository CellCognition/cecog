
import netCDF4
from pdk.datetimeutils import StopWatch


filename = '/Users/miheld/data/CellCognition/nc4_test/W12P01.nc4'
dataset = netCDF4.Dataset(filename, 'r')

f = len(dataset.dimensions['frames'])
c = len(dataset.dimensions['channels'])
h = len(dataset.dimensions['height'])
w = len(dataset.dimensions['width'])
r = len(dataset.dimensions['regions'])
print f,c,h,w,r

# test1: take only label images: 24.3 MB, 2m 19s 477ms
#s = StopWatch()
#filename1 = '/Users/miheld/data/CellCognition/nc4_test/W12P01_test1.nc4'
#ds1 = netCDF4.Dataset(filename1, 'w')
#
#ds1.createDimension('frames', f)
#ds1.createDimension('channels', c)
#ds1.createDimension('height', h)
#ds1.createDimension('width', w)
#ds1.createDimension('regions', r)
#
#
#var = ds1.createVariable('label_images', 'i2',
#                         ('frames', 'regions', 'height', 'width'),
#                         zlib='True',
#                         chunksizes=(1,1,h,w))
#for i in range(f):
#    print '%03d / %03d' % (i, f)
#    var[i,:] = dataset.variables['label_images'][i,:]
#
#ds1.close()
#print s


# test2: take only one region: 20.9 MB, 33s 336ms
#s = StopWatch()
#filename1 = '/Users/miheld/data/CellCognition/nc4_test/W12P01_test2.nc4'
#ds1 = netCDF4.Dataset(filename1, 'w')
#
#ds1.createDimension('frames', f)
#ds1.createDimension('channels', c)
#ds1.createDimension('height', h)
#ds1.createDimension('width', w)
#ds1.createDimension('regions', 1)
#
#var = ds1.createVariable('label_images', 'i2',
#                         ('frames', 'regions', 'height', 'width'),
#                         zlib='True',
#                         chunksizes=(1,1,h,w))
#for i in range(f):
#    print '%03d / %03d' % (i, f)
#    var[i,:] = dataset.variables['label_images'][i,0,:]
#
#ds1.close()
#print s


# test3: one region, shuffle=False: 14.9 MB, 31s 150ms
#s = StopWatch()
#filename1 = '/Users/miheld/data/CellCognition/nc4_test/W12P01_test3.nc4'
#ds1 = netCDF4.Dataset(filename1, 'w')
#
#ds1.createDimension('frames', f)
#ds1.createDimension('channels', c)
#ds1.createDimension('height', h)
#ds1.createDimension('width', w)
#ds1.createDimension('regions', 1)
#
#var = ds1.createVariable('label_images', 'i2',
#                         ('frames', 'regions', 'height', 'width'),
#                         zlib='True',
#                         shuffle=False,
#                         chunksizes=(1,1,h,w))
#for i in range(f):
#    print '%03d / %03d' % (i, f)
#    var[i,:] = dataset.variables['label_images'][i,0,:]
#
#ds1.close()
#print s


# test4: one regions, shuffle=False, two frames chunk: 14.9 MB, 29s 897ms
# 10 frames chunk, shuffle=False: 14.9 MB, 29s 897ms
# 10 frames chunk, shuffle=False, complevel=9: 13.7 MB, 2m 19s 546ms
# 10 frames chunk, shuffle=False, no regions dimension: 14.9 MB, 30s 275ms
# 10 frames chunk, shuffle=True: 20.5 MB, 30s 275ms
#s = StopWatch()
#filename1 = '/Users/miheld/data/CellCognition/nc4_test/W12P01_test4.nc4'
#ds1 = netCDF4.Dataset(filename1, 'w')
#
#ds1.createDimension('frames', f)
#ds1.createDimension('channels', c)
#ds1.createDimension('height', h)
#ds1.createDimension('width', w)
#ds1.createDimension('regions', 1)
#
#var = ds1.createVariable('label_images', 'i2',
#                         ('frames', 'regions', 'height', 'width'),
#                         zlib='True',
#                         shuffle=True,
#                         chunksizes=(10,1,h,w))
#for i in range(f):
#    print '%03d / %03d' % (i, f)
#    var[i,:] = dataset.variables['label_images'][i,0,:]
#
#ds1.close()
#print s


# test5: all regions, shuffle=False, two frames chunk: 18.3 MB, 2m 3s 354ms
#s = StopWatch()
#filename1 = '/Users/miheld/data/CellCognition/nc4_test/W12P01_test5.nc4'
#ds1 = netCDF4.Dataset(filename1, 'w')
#
#ds1.createDimension('frames', f)
#ds1.createDimension('channels', c)
#ds1.createDimension('height', h)
#ds1.createDimension('width', w)
#ds1.createDimension('regions', r)
#
#var = ds1.createVariable('label_images', 'i2',
#                         ('frames', 'regions', 'height', 'width'),
#                         zlib='True',
#                         shuffle=False,
#                         chunksizes=(2,2,h,w))
#for i in range(f):
#    print '%03d / %03d' % (i, f)
#    var[i,:] = dataset.variables['label_images'][i,:]
#
#ds1.close()
#print s


# test6: take only raw images, shuffle=True: 249.9 MB, 1m 35s 27ms
# test6: take only raw images, shuffle=False: 249.9 MB, 1m 32s 617ms
# test6: take only raw images, shuffle=False, chunk 10 f: 249.7 MB, 1m 33s 809ms
# test6: take only raw images, shuffle=False, no channel, chunk 10 f: 249.7 MB, 1m 32s 548ms
#s = StopWatch()
#filename1 = '/Users/miheld/data/CellCognition/nc4_test/W12P01_test6.nc4'
#ds1 = netCDF4.Dataset(filename1, 'w')
#
#ds1.createDimension('frames', f)
#ds1.createDimension('channels', c)
#ds1.createDimension('height', h)
#ds1.createDimension('width', w)
#ds1.createDimension('regions', r)
#
#
#var = ds1.createVariable('raw_images', 'u1',
#                         ('frames', 'height', 'width'),
#                         zlib='True',
#                         shuffle=True,
#                         chunksizes=(10,h,w))
#for i in range(f):
#    print '%03d / %03d' % (i, f)
#    var[i,:] = dataset.variables['raw_images'][i,0,:]
#
#ds1.close()
#print s



s = StopWatch()
filename1 = '/Users/miheld/data/CellCognition/nc4_test/test_features.nc4'
ds1 = netCDF4.Dataset(filename1, 'w')

ds1.createDimension('frames', f)
ds1.createDimension('channels', c)
ds1.createDimension('height', h)
ds1.createDimension('width', w)
ds1.createDimension('regions', r)


var = ds1.createVariable('raw_images', 'u1',
                         ('frames', 'height', 'width'),
                         zlib='True',
                         shuffle=True,
                         chunksizes=(10,h,w))
for i in range(f):
    print '%03d / %03d' % (i, f)
    var[i,:] = dataset.variables['raw_images'][i,0,:]

ds1.close()
print s


dataset.close()