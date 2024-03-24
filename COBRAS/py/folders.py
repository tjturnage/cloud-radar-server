import sys, os
folder=sys.argv[1]

cwd=os.getcwd()
basefolder=os.path.dirname(cwd)+'/data'
pythonfolder=os.path.dirname(cwd)+'/py'
#user unique folder
userfolder=basefolder+'/'+folder
#folder for actively downloading files
downloadfolder=userfolder+'/download'
#folder for files that have completed downloading
readyfolder=userfolder+'/ready'
#folder users uses to poll data
pollfolder=userfolder+'/polling'

