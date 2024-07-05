"""This script uncompresses an internally bzip compressed NEXRAD Level II File

    python debz.py <input_filename> <output_filename>
"""
from __future__ import print_function
import struct
import bz2
import sys
import os


def main(argv):
    """Our main logic for the provided arguments"""
    if len(argv) != 3:
        print("Usage: python debz.py <input_filename> <output_filename>")
        return
    oldfn = argv[1]
    newfn = argv[2]
    if os.path.isfile(newfn):
        print("Error: refusing to overwrite existing file '%s'" % (newfn, ))
        return
    output = open(newfn, 'wb')
    fobj = open(oldfn, 'rb')

    output.write(fobj.read(24))
    while True:
        sz = struct.unpack('>L', fobj.read(4))[0]
        chunk = fobj.read(sz)
        if not chunk:
            break
        output.write(bz2.decompress(chunk))
        # unsure of this
        if sz != len(chunk):
            break

    output.close()


if __name__ == '__main__':
    main(sys.argv)
