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
import bz2
import gzip
import struct
from datetime import datetime, timedelta, timezone
import time
import pytz
from pathlib import Path

#from config import RADAR_DIR, POLLING_DIR, L2MUNGER_FILEPATH, DEBZ_FILEPATH

class Munger():
    """
    Processes Nexrad Archive 2 files by changing their valid times to something very recent
    so that GR2Analyst can poll the data. If a new radar location is provided, the RDA location
    is shifted to that location.

    Parameters
    ----------
    original_rda: string
        The original radar location
    playback_start: string
        The start time of the playback in the format 'YYYY-MM-DD HH:MM'
    duration: int
        The duration of the playback in minutes (appears to be unused)
    timeshift: str
        The time shift in seconds between the playback start time and the event start time
        Needs to be converted to an integer
    new_rda: string or None
         If string is provided, it must correspond to a real nexrad location (like KGRR)
         If None, will use original radar location 
    """

    def __init__(self, original_rda, playback_start, duration, timeshift, RADAR_DIR, POLLING_DIR,
                 USER_DOWNLOADS_DIR,L2MUNGER_FILEPATH, DEBZ_FILEPATH, new_rda='None'):
        self.original_rda = original_rda.upper()
        print(self.original_rda)
        self.source_directory = Path(f"{RADAR_DIR}/{self.original_rda}/downloads")
        os.makedirs(self.source_directory, exist_ok=True)
        self.playback_start = datetime.strptime(playback_start,"%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC)
        self.duration = duration
        self.seconds_shift = int(timeshift)    # Needed for data passed in via command line.
        self.new_rda = new_rda
        self.polling_dir = Path(POLLING_DIR)
        self.user_downloads_dir = Path(USER_DOWNLOADS_DIR)
        self.assets_dir = self.polling_dir.parent
        self.this_radar_polling_dir = Path(f"{POLLING_DIR}/{self.original_rda}")
        if self.new_rda != 'None':
            self.this_radar_polling_dir = Path(f"{POLLING_DIR}/{self.new_rda.upper()}")

        self.l2munger_filepath = Path(L2MUNGER_FILEPATH)
        self.debz_filepath = Path(DEBZ_FILEPATH)
        os.makedirs(self.this_radar_polling_dir, exist_ok=True)

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
        chmod_cmd = f'chmod 775 {self.l2munger_filepath}'
        os.system(chmod_cmd)
        cp_cmd = f'cp {self.l2munger_filepath} {self.source_directory}'
        os.system(cp_cmd)


    def uncompress_files(self) -> None:
        """
        recent archived files are compressed with bzip2
        earlier files are compressed with gzip
        example command line:
            python debz.py KBRO20170825_195747_V06 KBRO20170825_195747_V06.uncompressed
        """

        os.chdir(self.source_directory)
        self.source_files = list(self.source_directory.glob('*'))

        for original_file in self.source_files:
            filename_str = str(original_file)
            print(f'Uncompressing {filename_str}')
            if original_file.suffix == '.gz':
                # unsure if ungzip'ed file needs to be passed to debz.py
                # Edit 6/28: keep original compressed file used for radar status tracking.
                filename_str = filename_str[:-3]
                cp_command_str = f'cp {filename_str} {self.user_downloads_dir}/{filename_str}'
                print(cp_command_str)
                os.system(cp_command_str)
                new_filename = f'{filename_str}.uncompressed'
                command_string = f'gunzip -c {filename_str} > {new_filename}'
                os.system(command_string)
                #os.rename(filename_str, new_filename)
                time.sleep(1)

            if 'V0' in filename_str:
                # Keep existing logic for .V06 and .V08 files
                uncompressed_filestr = f'{filename_str}.uncompressed'
                command_str = f'python {self.debz_filepath} {filename_str} {uncompressed_filestr}'
                os.system(command_str)
                #zip_command_str = f'gzip {uncompressed_filestr} -c > {self.user_downloads_dir}/{filename_str}.gz'
                #os.system(zip_command_str)
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
        fout = open(f'{self.assets_dir}/file_times.txt', 'w', encoding='utf-8')
        os.chdir(self.source_directory)
        self.source_files = list(self.source_directory.glob('*uncompressed'))
        for uncompressed_file in self.uncompressed_files:
            file_datetime_str = str(uncompressed_file.parts[-1])
            orig_file_timestr = file_datetime_str[4:19]
            file_datetime_obj = datetime.strptime(orig_file_timestr, '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC)
            new_time_obj = file_datetime_obj + timedelta(seconds=self.seconds_shift)
            new_time_str = datetime.strftime(new_time_obj, '%Y/%m/%d %H:%M:%S')
            new_filename_date_string = datetime.strftime(new_time_obj, '%Y%m%d_%H%M%S')
            fout.write(f'{file_datetime_str[:19]} -- {new_time_str}\n')
            command_line = f'./l2munger {self.new_rda} {new_time_str} 1 {file_datetime_str}'
            print(command_line)
            os.system(command_line)
            new_filename = f'{self.new_rda}{new_filename_date_string}'
            with open(new_filename, 'rb') as f_in:
                with gzip.open(f'{self.this_radar_polling_dir}/{new_filename}.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        fout.close()

    # def make_radar_files_downloadable(self) -> None:
    #     """
    #     Moves radar files to the user downloads directory so they can be downloaded
    #     """
    #     for file in self.source_files:
    #         if '_' in str(file):
    #             shutil.move(file, self.user_downloads_dir)
            

#-------------------------------
if __name__ == "__main__":
    MANUAL_RUN = False
    if MANUAL_RUN:
        ORIG_RDA = 'KGRR'
        playback_start_time = datetime.now(tz=timezone.utc) - timedelta(hours=2)
        playback_start_str = datetime.strftime(playback_start_time,"%Y-%m-%d %H:%M")
        event_start_time = datetime(2013, 5, 7, 21, 45, 0, tzinfo=timezone.utc)
        DURATION = 30
        simulation_time_shift = playback_start_time - event_start_time
        seconds_shift = int(simulation_time_shift.total_seconds())
        radar_dir = None
        polling_dir = None
        user_downloads_dir = None
        l2munger_filepath = None
        debz_filepath = None
        NEW_RDA = 'KGRR'

    else:
        Munger(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
               sys.argv[6], sys.argv[7], sys.argv[8], sys.argv[9], sys.argv[10])
