#!/usr/bin/python

#startsim.py sets up the simulation for COBRAS
#this incluse making the unique directory and downloads data
#startsim.py also writes a file to the unique directory to
#tell the front end when it is ok to start the simulation
from __future__ import print_function
import bz2
import gzip
import struct
import datetime
import shutil
import sys, json, os, time, urllib, subprocess
from urllib.request import urlretrieve
from shutil import copyfile
folder_org=sys.argv[1]
radarfiles=json.loads(sys.argv[2])
startdate=sys.argv[3]
enddate=sys.argv[4]
transposeradar=sys.argv[5]

from folders import *

#sort radar files in order
radarfiles.sort()


#python version of l2munger, the time change only does the volumn scan
#not the product time unfortunately
#therefore I took it out - twilson
def fake(filename, new_stid, downloadfolder):
    """Heavily borrow metpy's code!"""
    gzipfile = 0
    if filename.endswith('.bz2'):
        fobj = bz2.BZ2File(filename, 'rb')
    elif filename.endswith('.gz'):
        fobj = gzip.GzipFile(filename, 'rb')
        gzipfile = 1
    else:
        fobj = open(filename, 'rb')
    version = struct.unpack('9s', fobj.read(9))[0]
    vol_num = struct.unpack('3s', fobj.read(3))[0]
    date = struct.unpack('>L', fobj.read(4))[0]
    time_ms = struct.unpack('>L', fobj.read(4))[0]
    stid = struct.unpack('4s', fobj.read(4))[0]

    #added by twilson
    #unfortunately l2munger.py only changes the volume scan time and not
    #product time
    newfn = "%s%s" % (new_stid, '_transposed')
    newfn = downloadfolder + '/' + newfn
    if gzipfile == 1:
        print("Gzipping file")
        output = gzip.open(newfn, 'wb')
    else:
        output = open(newfn, 'wb')
    output.write(struct.pack('9s', version.encode('utf-8')))
    output.write(struct.pack('3s', vol_num.encode('utf-8')))
    output.write(struct.pack('>L', date))
    output.write(struct.pack('>L', time_ms))
    output.write(struct.pack('4s', new_stid.encode('utf-8')))
    output.write(fobj.read())
    output.close()

    shutil.move(newfn,filename) #added by twilson to overwrite file



def writetofile(arg):
#file for writing the date of the last downloaded file
    downloadstatus=open(downloadfolder+'/status','w')
    downloadstatus.write(str(arg))
    downloadstatus.close()

folders=[userfolder,pollfolder,downloadfolder,readyfolder]
for folder in folders:
    if not os.path.exists(folder):
        os.mkdir(folder)

#os.chdir(downloadfolder)


#splid 1d array in 2d by radar
#first put radars into array
radararray=[]
for radarfile in radarfiles:
    radar=radarfile[0:4]
    if not radar in radararray:
        radararray.append(radar)

#make first dimension of 2d array
radarfiles2d=[]
for radar in radararray:
    radarfiles2d.append([])

#make grleve2.cfg file
string='ListFile: dir.list'
for radar in radararray:
    if transposeradar != "0":
        radar=transposeradar
    if not os.path.exists(pollfolder+'/'+radar):
        os.mkdir(pollfolder+'/'+radar)
    string+='\nSite: '+radar
outfile=open(pollfolder+'/grlevel2.cfg','w')
outfile.write(string)
outfile.close()

#now add second dimension of 2d array
maxindex=0
for radarfile in radarfiles:
    radar=radarfile[0:4]
    radarfiles2d[radararray.index(radar)].append(radarfile)
    if len(radarfiles2d[radararray.index(radar)]) > maxindex:
        maxindex=len(radarfiles2d[radararray.index(radar)])

#loop through all files now
#loop through this way so we download one of each radar at a time
#rather than downloading all of one radar, then moving to the next
index=0
numfile=0
totnumfiles=len(radarfiles)
earliesttimestamp=startdate
string=str(earliesttimestamp) + ' ' + str(numfile) + ' ' + str(totnumfiles)
writetofile(string)
while (index<maxindex):
    earliesttimestamp=1e99
    #time.sleep(0.1)
    # NEED TO DELETE
    # ONLY IN HERE FO SHO PURPOSES
    #time.sleep(1)
    for radar in radararray:
        radarindex=radararray.index(radar)
        if index < len(radarfiles2d[radarindex]):


            #DOWNLOAD RADAR FILE
            radarfile=radarfiles2d[radarindex][index]
            site=radarfile[:4]
            year=radarfile[4:8]
            month=radarfile[8:10]
            day=radarfile[10:12]
            url='https://noaa-nexrad-level2.s3.amazonaws.com/'+year+'/'+month+'/'+day+'/'+site+'/'+radarfile
            source_file=downloadfolder+'/'+radarfile
            urlretrieve(url,source_file)
            #open(source_file,'a')

            newradarfile=site + '_20170101_000000_' + radarfile[4:19]
            #add extension to newradarfile
            try:
                extension=radarfile.split(".")[1]
                newradarfile=newradarfile + '.' + extension
            except IndexError:
                pass

            if transposeradar  != "0":
                print("Transposing",newradarfile,"to",transposeradar)
                fake(source_file, transposeradar, downloadfolder)
                print("Done Transposing")

            numfile=numfile+1
            dest_file=readyfolder+'/'+newradarfile
            #os.rename(source_file,dest_file)
            copyfile(source_file,dest_file)
            timestamp=int(radarfile[4:12] + radarfile[13:19])
            if timestamp < earliesttimestamp:
                earliesttimestamp=timestamp


    #clear contents of file and write the last time stamp
    string=str(earliesttimestamp) + ' ' + str(numfile) + ' ' + str(totnumfiles)
    writetofile(string)
    index=index+1



string=str(enddate) + ' ' + str(numfile) + ' ' + str(totnumfiles)
writetofile(string)

os.chdir(pythonfolder)
monitorscript=pythonfolder+'/monitor.py'
p = subprocess.Popen([monitorscript,folder_org,transposeradar])
