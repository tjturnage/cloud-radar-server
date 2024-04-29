import glob
import os
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

#munge_dir = '/data/scripts/l2munger-main'
munge_dir = '/home/wwwgrr/scripts/munger'
#munge_dir = 'data/scripts/l2munger-main'
#py3_path = '/home/tjt/anaconda3/bin/python'
py3_path = '/usr/bin/python3'
#dest_dir = '/home/tjt/public_html/public/radar/'
dest_dir = '/data/www/html/soo/munger/'

class Munger():
    """

    """
    
    def __init__(self,new_rda='KGRR'):
        self.new_rda = new_rda
        self.radar_dir = f'{dest_dir}{self.new_rda}' 
        self.original_dir = munge_dir
        self.orig_dir = Path(self.original_dir)
        self.orig_files = list(self.orig_dir.glob('*V06'))
        self.first_file = self.orig_files[0].parts[-1]
        first_file_rda = self.first_file[:4]
        self.first_file_epoch_time = datetime.strptime(self.first_file[4:-4], '%Y%m%d_%H%M%S').timestamp()
        
        
        self.clean_directories();
        self.uncompress_files();
        self.uncompressed_files = list(self.orig_dir.glob('*uncompressed'))
        self.munge_files()
    
    def clean_directories(self):
        """
        filetype example - f'{self.new_rda}*'
        """
        os.chdir(munge_dir)
        [os.remove(f) for f in os.listdir() if f.startswith(self.new_rda)]
        #os.chdir(self.radar_dir)
        #[os.remove(f) for f in os.listdir()]
        return
    
    def uncompress_files(self):
        #python debz.py KBRO20170825_195747_V06 KBRO20170825_195747_V06.uncompressed
        for original_file in self.orig_files:
            command_string = f'{py3_path} debz.py {str(original_file)} {str(original_file)}.uncompressed'
            os.system(command_string)
        print("uncompress complete!")
        return

    #def reference_time_shift(self):
    #    first_file_time_epoch = datetime.strptime(self.first_file[4:19], '%Y%m%d_%H%M%S').timestamp()
    #    reference_time_epoch = datetime.strptime(self.reference_time, '%Y%m%d_%H%M%S').timestamp()
    #    self.time_shift = first_file_time_epoch - reference_time_epoch
    #    return
    
    def munge_files(self):
        """
        Sets times of files to reference time
        """
        os.chdir(munge_dir)
        simulation_start_time = datetime.utcnow() - timedelta(seconds=(60*60*2))
        simulation_start_time_epoch = simulation_start_time.timestamp()
        #simulation_time_delta = int(simulation_start_time_epoch - first_file_time_epoch)
        for uncompressed_file in self.uncompressed_files:
            fn = str(uncompressed_file.parts[-1])
            fn_epoch_time = datetime.strptime(fn[4:19], '%Y%m%d_%H%M%S').timestamp()
            fn_time_shift = int(fn_epoch_time - self.first_file_epoch_time)
            new_time_obj = simulation_start_time + timedelta(seconds=fn_time_shift)
            new_time_str = datetime.strftime(new_time_obj, '%Y/%m/%d %H:%M:%S')
            command_line = f'./munger {self.new_rda} {new_time_str} 1 {fn}'
            print(f'     source file = {fn}')
            os.system(command_line)
        q = Path(self.original_dir)
        munged_files = list(q.glob(f'{self.new_rda}*'))
        for m in munged_files:
            print(f'compressing munged file ... {m.parts[-1]}')
            gzip_command = f'gzip {m.parts[-1]}'
            os.system(gzip_command)

        os.chdir(munge_dir)
        print('copying files to base directory')
        os.system(f'cp *gz {dest_dir}')
        return
    

#-------------------------------

test = Munger(new_rda='KGRR')

