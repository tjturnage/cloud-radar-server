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
    
    def __init__(self, munge_dir, polling_dir, sim_timedelta, new_rda, playback_speed=1.5):

        self.new_rda = new_rda
        self.munge_dir = munge_dir
        self.polling_dir = polling_dir
        self.sim_timedelta = sim_timedelta
        self.source_directory = Path(self.munge_dir)
        #self.start_simulation = start_simulation
        self.playback_speed = playback_speed
        self.radar_dir = f'{self.polling_dir}{self.new_rda}'
        self.clean_files()
        self.copy_files()
        self.uncompress_files()

        # determine amount of time shift needed for munge based on first file's timestamp
        self.uncompressed_files = list(self.source_directory.glob('*uncompressed'))
        self.first_file = self.uncompressed_files[0].parts[-1]
        self.first_file_epoch_time = self.get_timestamp(self.first_file)

        # # Determine RDA associated with archive files if necessary
        # if self.new_rda == 'None':
        #     self.first_file_rda = self.first_file[:4]
        #     self.new_rda = self.first_file_rda
        # # commence munging
        # self.munge_files()

        # if self.start_simulation:
        #     #print(' Starting simulation!! \n Set polling to https://turnageweather.us/public/radar')
        #     print(' Starting simulation!! \n Set polling to http://intra-grr.cr.nws.noaa/grr/soo/munger/')
        #     self.simulation_files_directory = Path(self.radar_dir)
        #     self.simulation_files = sorted(list(self.simulation_files_directory.glob('*gz')))
        #     self.update_dirlist()

    
    def clean_files(self):
        """
        Purges all radar files associated with previous simulation
        """
        rm_munge_files = f'rm {self.munge_dir}/K*'
        os.system(rm_munge_files)
        os.chdir(self.munge_dir)
        os.chdir(self.radar_dir)
        try:
            [os.remove(f) for f in os.listdir()]
        except Exception as e:
            print(f'Error: {e}')
        
        return    

    def copy_files(self):
        """
        stages raw files into munge directory where munger script lives
        """
        cp_cmd = f'cp {self.source_directory}/* self.{self.munge_dir}'
        os.system(cp_cmd)
        
        return
    
    def uncompress_files(self):
        """
        example command line: python debz.py KBRO20170825_195747_V06 KBRO20170825_195747_V06.uncompressed
        """

        os.chdir(self.munge_dir)
        self.source_files = list(self.source_directory.glob('*V06'))
        for original_file in self.source_files:
            command_string = f'python debz.py {str(original_file)} {str(original_file)}.uncompressed'
            os.system(command_string)
        print("uncompress complete!")
        return

    def get_timestamp(self, file):
        """
        - extracts datetime info from the radar filename
        - converts it to a timezone aware datetime object in UTC
        """
        file_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S')
        utc_file_time = file_time.replace(tzinfo=pytz.UTC)
        return utc_file_time


    def fake(self,filename):#,filename, new_stid, new_dt):
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
        print(new_date)
        print(date)
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
        os.chdir(self.munge_dir)
        simulation_start_time = datetime.now(timezone.utc) - timedelta(seconds=(60*60*2))
        simulation_start_time_epoch = simulation_start_time.timestamp()
        for uncompressed_file in self.uncompressed_files:
            fn = str(uncompressed_file.parts[-1])
            fn_epoch_time = self.get_timestamp(fn)
            fn_time_shift = int(fn_epoch_time - self.first_file_epoch_time)
            new_time_obj = simulation_start_time + timedelta(seconds=fn_time_shift)
            new_time_str = datetime.strftime(new_time_obj, '%Y/%m/%d %H:%M:%S')
            new_filename_date_string = datetime.strftime(new_time_obj, '%Y%m%d_%H%M%S')
            command_line = f'./l2munger {self.new_rda} {new_time_str} 1 {fn}'
            print(command_line)
            #print(f'     source file = {fn}')
            os.system(command_line)
            new_filename = f'{self.new_rda}{new_filename_date_string}'
            move_command = f'mv {self.munge_dir}/{new_filename} {self.radar_dir}/{new_filename}'
            print(move_command)
            os.system(move_command)
        
        simulation_directory = Path(self.radar_dir)
        simulation_files = list(simulation_directory.glob('*'))
        os.chdir(self.radar_dir)
        for file in simulation_files:
            print(f'compressing munged file ... {file.parts[-1]}')
            gzip_command = f'gzip {file.parts[-1]}'
            os.system(gzip_command)

        return
        
    def update_dirlist(self):
        """
        The dir.list file is needed for GR2Analyst to poll in DRT
        """
        simulation_counter = self.get_timestamp(self.simulation_files[0].parts[-1]) + 360
        last_file_timestamp = self.get_timestamp(self.simulation_files[-1].parts[-1])
        print(simulation_counter,last_file_timestamp-simulation_counter)
        while simulation_counter < last_file_timestamp:
            simulation_counter += 60
            self.output = ''     
            for file in self.simulation_files:
                file_timestamp = self.get_timestamp(file.parts[-1])
                if file_timestamp < simulation_counter:
                    line = f'{file.stat().st_size} {file.parts[-1]}\n'
                    self.output = self.output + line
                    with open(f'{self.radar_dir}/dir.list', mode='w', encoding='utf-8') as f:
                        f.write(self.output)
                else:
                    pass

            sleep(int(60/self.playback_speed))

        print("simulation complete!")

        return

#-------------------------------
if __name__ == "__main__":

    #NexradDownloader('kgrr', '2023-08-24 23:45:00 UTC', 30)
    Munger(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    #Munger(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])