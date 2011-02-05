import sys
import tables

assert (len(sys.argv) == 3), "Usage: uncompressed.h5 compressed.h5"
filt = tables.filters.Filters(complevel=3, complib="zlib", shuffle=True)
h5 = tables.openFile(sys.argv[1])
h5.copyFile(sys.argv[2], filters=filt)


