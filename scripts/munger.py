"""_summary_

    Returns:
        _type_: _description_
"""

from __future__ import print_function
import os
import sys
from datetime import datetime, timedelta, timezone
import pytz
from pathlib import Path
from time import sleep
import bz2
import gzip
import struct


class Munger():
    """
    Copies Nexrad Archive 2 files from a raw directory so Displaced Real-Time (DRT) simulations can be performed
    using GR2Analyst.

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
    SCRIPTS_DIR = '/data/cloud-radar-server/scripts'
    L2MUNGER_FILEPATH = f'{SCRIPTS_DIR}/l2munger'
    DEBZ_FILEPATH = f'{SCRIPTS_DIR}/debz.py'
    MUNGER_SCRIPT_BASE = '/data/cloud-radar-server/data/radar' #/KGRR/downloads'
    POLLING_DIR = '/data/cloud-radar-server/assets/polling'
    def __init__(self, original_rda, playback_start, duration, timeshift, new_rda, start_simulation=True, playback_speed=1.5):

        self.new_rda = new_rda
        self.original_rda = original_rda
        self.playback_start = datetime.strptime(playback_start,"%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=pytz.UTC)
        self.duration = duration
        self.seconds_shift = timeshift
        self.source_directory = Path(f'{self.MUNGER_SCRIPT_BASE}/{self.original_rda}/downloads')
        self.start_simulation = start_simulation
        self.playback_speed = playback_speed
        #self.clean_files()
        self.copy_l2munger_executable()
        self.uncompress_files()

        # determine amount of time shift needed for munge based on first file's timestamp
        self.uncompressed_files = list(self.source_directory.glob('*uncompressed'))
        self.full_polling_dir = os.path.join(self.POLLING_DIR, self.new_rda)
        os.makedirs(self.full_polling_dir, exist_ok=True)

        # commence munging
        self.munge_files()

        if self.start_simulation:
            #print(' Starting simulation!! \n Set polling to https://turnageweather.us/public/radar')
            self.simulation_files_directory = Path(self.full_polling_dir)
            self.simulation_files = sorted(list(self.simulation_files_directory.glob('*gz')))
            self.update_dirlist()
    
    def clean_files(self):
        """
        Purges all radar files associated with previous simulation
        """
        rm_munge_files = f'rm {self.source_directory}/K*'
        os.system(rm_munge_files)
        os.chdir(self.source_directory)
        os.chdir(self.full_polling_dir)
        try:
            [os.remove(f) for f in os.listdir()]
        except Exception as e:
            print(f'Error: {e}')
        
        return    

    def copy_l2munger_executable(self):
        """
        The compiled l2munger executable needs to be in the source
        radar files directory to work properly
        """
        cp_cmd = f'cp {self.L2MUNGER_FILEPATH} {self.source_directory}'
        os.system(cp_cmd)
        
        return
    
    def uncompress_files(self):
        """
        example command line: python debz.py KBRO20170825_195747_V06 KBRO20170825_195747_V06.uncompressed
        """

        os.chdir(self.source_directory)
        self.source_files = list(self.source_directory.glob('*V06'))
        for original_file in self.source_files:
            command_string = f'python {self.DEBZ_FILEPATH} {str(original_file)} {str(original_file)}.uncompressed'
            os.system(command_string)
        print("uncompress complete!")
        return

    def datetime_object_from_timestring(self, file):
        """
        - extracts datetime info from the radar filename
        - converts it to a timezone aware datetime object in UTC
        """
        file_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S')
        utc_file_time = file_time.replace(tzinfo=pytz.UTC)
        return utc_file_time

    def datetime_from_timestring_argument(self, string):
        """
        - extracts datetime info from the radar filename
        - converts it to a timezone aware datetime object in UTC
        """
        dt = datetime.strptime(string,"%Y-%m-%d %H:%M:%S UTC")
        utc_time_object = dt.replace(tzinfo=pytz.UTC)
        return utc_time_object


    def fake(self,filename, new_dt):
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
        orig_dt = datetime.utcfromtimestamp((date - 1) * 86400. +
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

    
    def munge_files(self):
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
            #print(command_line)
            #print(f'     source file = {fn}')
            os.system(command_line)
            new_filename = f'{self.new_rda}{new_filename_date_string}'
            #print(new_filename)
            gzip_filename = f'{new_filename}.gz'
            if gzip_filename not in os.listdir(self.source_directory):
                gzip_command = f'gzip {new_filename}'
                os.system(gzip_command)
            else:
                print(f'{gzip_filename} already exists!')

        
        move_command = f'mv {self.source_directory}/{self.new_rda}*gz {self.full_polling_dir}'
        #print(move_command)
        os.system(move_command)
        return
        
    def update_dirlist(self):
        """
        The dir.list file is needed for GR2Analyst to poll in DRT
        """
        #simulation_counter = self.datetime_from_timestring_argument(self.playback_start) + timedelta(seconds=60)
        #playback_end = self.datetime_from_timestring_argument(self.playback_start) + timedelta(minutes=self.duration)
        simulation_counter = self.playback_start + timedelta(seconds=60)
        playback_end = self.playback_start + timedelta(minutes=self.duration)
        #print(simulation_counter,last_file_timestamp-simulation_counter)
        while simulation_counter < playback_end:
            simulation_counter = simulation_counter + timedelta(seconds=60)
            self.output = ''     
            for file in self.simulation_files:
                file_timestamp = self.datetime_object_from_timestring(file.parts[-1])
                if file_timestamp < simulation_counter:
                    line = f'{file.stat().st_size} {file.parts[-1]}\n'
                    self.output = self.output + line
                    with open(f'{self.POLLING_DIR}/dir.list', mode='w', encoding='utf-8') as f:
                        f.write(self.output)
                else:
                    pass

            sleep(int(60/self.playback_speed))

        print("simulation complete!")

        return

#-------------------------------
if __name__ == "__main__":
    orig_rda = 'KGRR'
    target_rda = 'KGRR'
    playback_start_time = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    event_start_time = datetime(2024, 5, 7, 22, 0, 0, tzinfo=timezone.utc)
    sim_duration = 60   # minutes

    simulation_time_shift = playback_start_time - event_start_time
    seconds_shift = int(simulation_time_shift.total_seconds())

    playback_start_str = datetime.strftime(playback_start_time,"%Y-%m-%d %H:%M:%S UTC")
    #playback_end_time = playback_start_time + timedelta(minutes=int(event_duration))

    Munger(orig_rda, playback_start_str, sim_duration, seconds_shift, target_rda, start_simulation=True, playback_speed=1.5)