#!/usr/bin/python3.6

import sys,os
from datetime import datetime, timedelta
#this will turn off the pyc files
#doesn't seem necessary to do so
#sys.dont_write_bytecode = True
from folders import *
sys.path.insert(0,userfolder)
from timectl import *
transposeradar=sys.argv[2]

currentdate_p=datetime(int(str(currentdate)[0:4]),int(str(currentdate)[4:6]),int(str(currentdate)[6:8]),int(str(currentdate)[8:10]),int(str(currentdate)[10:12]),int(str(currentdate)[12:14]))

#move files from ready to polling
for file in os.listdir(readyfolder):
    filedate_p=datetime(int(str(file)[21:25]),int(str(file)[25:27]),int(str(file)[27:29]),int(str(file)[30:32]),int(str(file)[32:34]),int(str(file)[34:36]))
    if filedate_p < currentdate_p:
        radarfolder=pollfolder+'/'+file[:4]
        if transposeradar != "0":
            radarfolder=pollfolder+'/'+transposeradar
        os.rename(readyfolder+'/'+file,radarfolder+'/'+file)
        print ("moving",file,"to poll folder")



#move files from polling to ready
for folder in os.listdir(pollfolder):
    if folder != 'grlevel2.cfg':
        radarfolder=pollfolder+'/'+folder
        if transposeradar != "0":
            radarfolder=pollfolder+'/'+transposeradar
        for file in os.listdir(radarfolder):
            if file != 'dir.list':
                filedate_p=datetime(int(str(file)[21:25]),int(str(file)[25:27]),int(str(file)[27:29]),int(str(file)[30:32]),int(str(file)[32:34]),int(str(file)[34:36]))
                if filedate_p > currentdate_p:
                    os.rename(radarfolder+'/'+file,readyfolder+'/'+file)
                    print ("moving",file,"to ready folder")
                    print (filedate_p,"is greater than",currentdate_p)


#need to rename file for polling
for folder in os.listdir(pollfolder):
    if folder != 'grlevel2.cfg':
        print ('folder is',folder)
        radarfolder=pollfolder+'/'+folder
        if transposeradar != "0":
            radarfolder=pollfolder+'/'+transposeradar
        outfile=open(radarfolder+'/dir.list','w')
        length=len(os.listdir(radarfolder))
        time=datetime.utcnow()-timedelta(seconds=length)
        #time=datetime.utcnow()+timedelta(minutes=length)
        #do this so the files always have the same dummy time.
        #time=datetime.utcnow().replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
        count=0
        for file in sorted(os.listdir(radarfolder),key=lambda x: x[21:]):
            if file != 'dir.list':
                site=file[:4]
                orgtime=file[21:36]
                #putting the file number here (count) so only that file gets chached
                newfile=site + time.strftime('_%Y%m%d_%H%M%S_') + orgtime;
                try:
                    extension=file.split(".")[1]
                    newfile=newfile + '.' + extension;
                except IndexError:
                    pass

                #get file size
                size=os.stat(radarfolder+'/'+file).st_size
                os.rename(radarfolder+'/'+file,radarfolder+'/'+newfile)
                string=str(size) + ' ' + str(newfile) + '\n'
                outfile.write(str(string))
                time=time+timedelta(seconds=1)
                count=count+1
        outfile.close()
