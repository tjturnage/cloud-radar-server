import glob
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep

scripts_dir = '/home/wwwgrr/scripts'

munge_dir = f'{scripts_dir}/munger'
#py3_path = '/home/tjt/anaconda3/bin/python'
py3_path = '/usr/bin/python3'

#base_destination_directory = '/home/tjt/public_html/public/radar/'
base_destination_directory = '/data/www/html/soo/munger/'

raw_dir = f'{scripts_dir}/arc2dat/'

class Munger():
    """
    Copies Nexrad Archive 2 files from a raw directory so Displaced Real-Time (DRT) simulations can be performed
    using GR2Analyst.

    munge_data: Boolean
        uses l2munger to:
        - change valid times starting at 2 hours from current real time
        - remap data to new_rda if provided (see below).

    new_rda: string or None
         If string is provided, it must correspond to a real nexrad location (like KGRR)
         If None, will use radar location associated with archive files 
     
    start_simulation: Boolean
        To poll in displac
        a dir.list file will be created and updated in the polling directory so GR2Analyst can play this back
    - playback_speed: float
        speed of simulation compared to real time ... example: 2.0 means event proceeds twice as fast
    """
    
    def __init__(self, munge_data=True, new_rda='KGRR', start_simulation=True, playback_speed=1.5):

        self.new_rda = new_rda
        self.munge_data = munge_data
        self.source_directory = Path(munge_dir)
        self.start_simulation = start_simulation
        self.playback_speed = playback_speed
        self.radar_dir = f'{base_destination_directory}{self.new_rda}'
        self.clean_files()
        self.copy_files()
        self.uncompress_files()

        # determine amount of time shift needed for munge based on first file's timestamp
        self.uncompressed_files = list(self.source_directory.glob('*uncompressed'))
        self.first_file = self.uncompressed_files[0].parts[-1]
        self.first_file_epoch_time = self.get_timestamp(self.first_file)

        if self.munge_data:
        # Determine RDA associated with archive files if necessary
            if self.new_rda == 'None':
                self.first_file_rda = self.first_file[:4]
                self.new_rda = self.first_file_rda
            # commence munging
            self.munge_files()

        if self.start_simulation:
            #print(' Starting simulation!! \n Set polling to https://turnageweather.us/public/radar')
            print(' Starting simulation!! \n Set polling to http://intra-grr.cr.nws.noaa/grr/soo/munger/')
            self.simulation_files_directory = Path(self.radar_dir)
            self.simulation_files = sorted(list(self.simulation_files_directory.glob('*gz')))
            self.update_dirlist()

        if not self.munge_data and not self.start_simulation:
            print('nothing to do!')
    
    def clean_files(self):
        """
        Purges all radar files associated with previous simulation
        """
        rm_munge_files = f'rm {munge_dir}/K*'
        os.system(rm_munge_files)
        os.chdir(munge_dir)
        os.chdir(self.radar_dir)
        try:
            [os.remove(f) for f in os.listdir()]
        except:
            print('cannot delete radar web files!')
        
        return            

    def copy_files(self):
        """
        stages raw files into munge directory where munger script lives
        """
        cp_cmd = f'cp {raw_dir}/* {munge_dir}'
        os.system(cp_cmd)
        
        return 
    
    def uncompress_files(self):
        """
        example command line: python debz.py KBRO20170825_195747_V06 KBRO20170825_195747_V06.uncompressed
        """

        os.chdir(munge_dir)
        self.source_files = list(self.source_directory.glob('*V06'))
        for original_file in self.source_files:
            command_string = f'{py3_path} debz.py {str(original_file)} {str(original_file)}.uncompressed'
            os.system(command_string)
        print("uncompress complete!")
        return

    def get_timestamp(self,file):
        """
        - extracts datetime info from the radar filename
        - converts it to a datetime timestamp (epoch seconds) object
        """
        file_epoch_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S').timestamp()
        return file_epoch_time        
    
    def munge_files(self):
        """
        Sets reference time to two hours before current time
        munges radar files to start at the reference time
        also changes RDA location
        """
        os.chdir(munge_dir)
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
            move_command = f'mv {munge_dir}/{new_filename} {self.radar_dir}/{new_filename}'
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
                    f = open(f'{self.radar_dir}/dir.list',mode='w')
                    f.write(self.output)
                    f.close()
                else:
                    pass

            sleep(int(60/self.playback_speed))

        print("simulation complete!")

        return

#-------------------------------

test = Munger(new_rda='KGRR',munge_data=True,start_simulation=True)

