"""
This script is used to munge Nexrad Archive 2 files so they can be used in Displaced Real-Time
(DRT) simulations using GR2Analyst.

09 June 2024
-- older archived files are compressed with gzip, so we need to uncompress them first
-- unclear if uncompressed gzip files then need bzip2 uncompression
-- writes munged files directly to polling dir with python gzip library instead of os.system commands

"""

from __future__ import print_function
import os
import sys
import shutil
from pathlib import Path
import bz2
import gzip
import struct
from datetime import datetime, timedelta, timezone
import time
import pytz

class Munger():
    """
    Copies Nexrad Archive 2 files from a raw directory so Displaced Real-Time (DRT) simulations
    can be performed using GR2Analyst.

    munge_data: Boolean
        uses l2munger to:
        - change valid times starting at 2 hours prior to current real time
        - remap data to new_rda if provided (see below).

    new_rda: string or None
         If string is provided, it must correspond to a real nexrad location (like KGRR)
         If None, will use radar location associated with archive files 
     
    start_simulation: Boolean
        To poll in displaced real time
        a dir.list file will be created and updated in the polling directory so GR2Analyst can play this back
    - playback_speed: float
        speed of simulation compared to real time ... example: 2.0 means event proceeds twice as fast
    """
    BASE_DIR = Path('/data/cloud-radar-server')
    # In order to get this work on my dev and work laptop
    if sys.platform.startswith('darwin') or sys.platform.startswith('win'):
        parts = Path.cwd().parts
        idx = parts.index('cloud-radar-server')
        BASE_DIR =  Path(*parts[0:idx+1])

    SCRIPTS_DIR = BASE_DIR / 'scripts'
    L2MUNGER_FILEPATH = SCRIPTS_DIR / 'l2munger'
    DEBZ_FILEPATH = SCRIPTS_DIR / 'debz.py'

    RADAR_DATA_BASE_DIR = BASE_DIR / 'data' / 'radar' #/KGRR/downloads'
    POLLING_DIR = BASE_DIR / 'assets' / 'polling'

    #SCRIPTS_DIR = Path('/data/cloud-radar-server/scripts')
    #L2MUNGER_FILEPATH = SCRIPTS_DIR / 'l2munger'	    
    #DEBZ_FILEPATH = SCRIPTS_DIR / 'debz.py'	    
    #RADAR_DATA_BASE_DIR = Path('/data/cloud-radar-server/data/radar') #/KGRR/downloads'	
    #POLLING_DIR = Path('/data/cloud-radar-server/assets/polling')

    def __init__(self, original_rda, playback_start, duration, timeshift, new_rda, playback_speed=1.5):
        self.original_rda = original_rda.upper()
        self.source_directory = self.RADAR_DATA_BASE_DIR / self.original_rda / 'downloads'
        os.makedirs(self.source_directory, exist_ok=True)
        self.playback_start = datetime.strptime(playback_start,"%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=pytz.UTC)
        self.duration = duration
        self.seconds_shift = int(timeshift)    # Needed for data passed in via command line. 
        self.new_rda = new_rda
        self.this_radar_polling_dir = self.POLLING_DIR / self.original_rda
        if self.new_rda != 'None':
            self.this_radar_polling_dir = self.POLLING_DIR / self.new_rda.upper()

        os.makedirs(self.this_radar_polling_dir, exist_ok=True)

        self.playback_speed = playback_speed
        self.copy_l2munger_executable()
        self.uncompress_files()
        self.uncompressed_files = list(self.source_directory.glob('*uncompressed'))
        # commence munging
        self.munge_files()

    def copy_l2munger_executable(self) -> None:
        """
        The compiled l2munger executable needs to be in the source
        radar files directory to work properly
        """
        chmod_cmd = f'chmod 775 {self.L2MUNGER_FILEPATH}'
        os.system(chmod_cmd)
        cp_cmd = f'cp {self.L2MUNGER_FILEPATH} {self.source_directory}'
        os.system(cp_cmd)


    def uncompress_files(self) -> None:
        """
        recent archived files are compressed with bzip2
        earlier files are compressed with gzip
        example command line: python debz.py KBRO20170825_195747_V06 KBRO20170825_195747_V06.uncompressed
        """

        os.chdir(self.source_directory)
        self.source_files = list(self.source_directory.glob('*'))

        for original_file in self.source_files:
            filename_str = str(original_file)
            print(f'Uncompressing {filename_str}')
            if original_file.suffix == '.gz':
                command_string = f'gunzip {filename_str}'
                os.system(command_string)
                # unsure if ungzip'ed file needs to be passed to debz.py
                filename_str = filename_str[:-3]
                new_filename = f'{filename_str}.uncompressed'
                os.rename(filename_str, new_filename)
                time.sleep(1)
                
            if 'V0' in filename_str:
                # Keep existing logic for .V06 and .V08 files
                command_string = f'python {self.DEBZ_FILEPATH} {filename_str} {filename_str}.uncompressed'
                os.system(command_string)
            else:
                print(f'File type not recognized: {filename_str}')
                continue
        print("uncompress complete!")



    def datetime_object_from_timestring(self, file: str) -> datetime:
        """
        - extracts datetime info from the radar filename
        - converts it to a timezone aware datetime object in UTC
        """
        file_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S')
        utc_file_time = file_time.replace(tzinfo=pytz.UTC)
        return utc_file_time


    def fake(self,filename, new_dt) -> None:
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
        _stid = struct.unpack('4s', fobj.read(4))[0]
        _orig_dt = datetime.utcfromtimestamp((date - 1) * 86400. +
                                                    time_ms * 0.001)

        seconds = (new_dt - datetime(1970, 1, 1)).total_seconds()
        new_date = int(seconds / 86400) + 1
        new_time_ms = int(seconds % 86400) * 1000
        newfn = "%s%s" % (self.new_rda, new_dt.strftime("%Y%m%d_%H%M%S"))
        if os.path.isfile(newfn):
            print("Abort: Refusing to overwrite existing file: '%s'" % (newfn, ))
            return
        #print(new_date)
        #print(date)
        output = open(newfn, 'wb')
        output.write(struct.pack('9s', version.encode('utf-8')))
        output.write(struct.pack('3s', vol_num.encode('utf-8')))
        output.write(struct.pack('>L', new_date))
        output.write(struct.pack('>L', new_time_ms))
        output.write(struct.pack('4s', self.new_rda.encode('utf-8')))
        output.write(fobj.read())
        output.close()
        return

    
    def munge_files(self) -> None:
        """
        Sets reference time to two hours before current time
        munges radar files to start at the reference time
        also changes RDA location
        """
        os.chdir(self.source_directory)
        self.source_files = list(self.source_directory.glob('*uncompressed'))
        for uncompressed_file in self.uncompressed_files:
            file_datetime_str = str(uncompressed_file.parts[-1])
            file_datetime_obj = datetime.strptime(file_datetime_str[4:19], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC)
            new_time_obj = file_datetime_obj + timedelta(seconds=self.seconds_shift)
            new_time_str = datetime.strftime(new_time_obj, '%Y/%m/%d %H:%M:%S')
            new_filename_date_string = datetime.strftime(new_time_obj, '%Y%m%d_%H%M%S')
            command_line = f'./l2munger {self.new_rda} {new_time_str} 1 {file_datetime_str}'
            print(command_line)
            #print(f'     source file = {fn}')
            os.system(command_line)
            new_filename = f'{self.new_rda}{new_filename_date_string}'
            #print(new_filename)
            with open(new_filename, 'rb') as f_in:
                with gzip.open(f'{self.this_radar_polling_dir}/{new_filename}.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            #gzip_filename = f'{new_filename}.gz'
            #if gzip_filename not in os.listdir(self.this_radar_polling_dir):
            #    gzip_command = f"gzip -c {new_filename} > {self.this_radar_polling_dir}/{new_filename}.gz"
                
            #    os.system(gzip_command)
            #else:
            #    print(f'{gzip_filename} already exists!')

        #move_command = f'mv {self.source_directory}/{self.new_rda}*gz {self.this_radar_polling_dir}'
        #print(move_command)
        #os.system(move_command)


#-------------------------------
if __name__ == "__main__":
    MANUAL_RUN = False
    if MANUAL_RUN:
        ORIG_RDA = 'KGRR'
        NEW_RDA = 'KGRR'
        playback_start_time = datetime.now(tz=timezone.utc) - timedelta(hours=2)
        event_start_time = datetime(2013, 5, 7, 21, 45, 0, tzinfo=timezone.utc)
        DURATION = 30
        simulation_time_shift = playback_start_time - event_start_time
        seconds_shift = int(simulation_time_shift.total_seconds())
        playback_start_str = datetime.strftime(playback_start_time,"%Y-%m-%d %H:%M:%S UTC")
        playback_end_time = playback_start_time + timedelta(minutes=int(DURATION))
        Munger(ORIG_RDA, playback_start_str, DURATION, seconds_shift, NEW_RDA, playback_speed=1.5)
    else:
        Munger(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], playback_speed=1.5)
        #original_rda, playback_start, duration, timeshift, new_rda, playback_speed=1.5