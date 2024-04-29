"""Fake me a NEXRAD station ID and time!

  python l2munger.py <newstation> YYYY/MM/DD HH:MI:SS <oldfile>

This only rewrites the Volume Scan Time and not the product times :/

"""
from __future__ import print_function
import bz2
import sys
import os
import gzip
import struct
import datetime


def fake(filename, new_stid, new_dt):
    """Heavily borrow metpy's code!"""
    if filename.endswith('.bz2'):
        fobj = bz2.BZ2File(filename, 'rb')
    elif filename.endswith('.gz'):
        fobj = gzip.GzipFile(filename, 'rb')
    else:
        fobj = open(filename, 'rb')
    version = struct.unpack('9s', fobj.read(9))[0]
    vol_num = struct.unpack('3s', fobj.read(3))[0]
    date = struct.unpack('>L', fobj.read(4))[0]
    time_ms = struct.unpack('>L', fobj.read(4))[0]
    stid = struct.unpack('4s', fobj.read(4))[0]
    orig_dt = datetime.datetime.utcfromtimestamp((date - 1) * 86400. +
                                                 time_ms * 0.001)

    seconds = (new_dt - datetime.datetime(1970, 1, 1)).total_seconds()
    new_date = int(seconds / 86400) + 1
    new_time_ms = int(seconds % 86400) * 1000
    newfn = "%s%s" % (new_stid, new_dt.strftime("%Y%m%d_%H%M%S"))
    if os.path.isfile(newfn):
        print("Abort: Refusing to overwrite existing file: '%s'" % (newfn, ))
        return
    print(new_date)
    print(date)
    output = open(newfn, 'wb')
    output.write(struct.pack('9s', version.encode('utf-8')))
    output.write(struct.pack('3s', vol_num.encode('utf-8')))
    output.write(struct.pack('>L', new_date))
    output.write(struct.pack('>L', new_time_ms))
    output.write(struct.pack('4s', new_stid.encode('utf-8')))
    output.write(fobj.read())
    output.close()


def main(argv):
    """Our main function called with arguments"""
    if len(argv) != 5:
        print("Usage: python l2munger.py <newid> YYYY/MM/DD HH:MI:SS <file>")
        return
    new_stid = argv[1]
    new_dt = datetime.datetime.strptime("%s %s" % (argv[2], argv[3]),
                                        '%Y/%m/%d %H:%M:%S')
    filename = argv[4]
    fake(filename, new_stid, new_dt)

if __name__ == '__main__':
    main(sys.argv)
