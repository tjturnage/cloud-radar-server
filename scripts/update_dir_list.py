"""_summary_

    Returns:
        _type_: _description_
"""

from __future__ import print_function
import sys
from pathlib import Path
from datetime import datetime
import pytz

from config import POLLING_DIR

#BASE_DIR = Path('/data/cloud-radar-server')
#if sys.platform.startswith('darwin') or sys.platform.startswith('win'):
#    parts = Path.cwd().parts
#    idx = parts.index('cloud-radar-server')
#    BASE_DIR =  Path(*parts[0:idx+1])

#POLLING_DIR = BASE_DIR / 'assets' / 'polling'

class UpdateDirList():
    """
    updates the dir.list file in the polling directory so GR2Analyst can play this back

    radar: string
         the radar that needs updating, must correspond to a real nexrad location (like KGRR)
         If None, will use radar location associated with archive files 
         
    current_playback_time: str
        uses l2munger to:
        - change valid times starting at 2 hours prior to current real time
        - remap data to new_rda if provided (see below).

    initialize: bool
        True: creates a new dir.list file with only the first three files in the polling directory
        False: updates dir.list with files in polling directory older than the current playback time

    """



    def __init__(self, radar: str, current_playback_timestr: str, initialize: bool = False):
        self.radar = radar.upper()
        self.current_playback_timestr = current_playback_timestr
        self.this_radar_polling_directory = POLLING_DIR / self.radar
        print(self.this_radar_polling_directory)
        self.dirlist_file = self.this_radar_polling_directory / 'dir.list'
        self.current_playback_time = None
        self.initialize = initialize
        self.filelist = sorted(list(self.this_radar_polling_directory.glob('*gz')))
        if initialize:
            self.dirlist_initialize()
        else:
            try:
                self.current_playback_time = datetime.strptime(self.current_playback_timestr, \
                    "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC).timestamp()
                print(f'Update dirlist time: {self.current_playback_timestr}')
                self.update_dirlist()
            except ValueError as ve:
                print(f'Could not update radar dirlist: {ve}')
                self.current_playback_time = 'None'


    def datetime_object_from_timestring(self, filename: str) -> float:
        """
        - input: filename
            filename containing datetime info (example: KGRR20240601_125151.gz)
        - returns: file_time --> float
            timestamp in UTC associated with datetime string in filename
        """
        file_time = datetime.strptime(filename[4:19], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
        return file_time

    def dirlist_initialize(self) -> None:
        """
        - Used just at simulation beginning to give some radar files to poll while other scripts run
        """
        output = ''
        for file in self.filelist[0:3]:
            line = f'{file.stat().st_size} {file.parts[-1]}\n'
            #print(line)
            output = output + line
        with open(self.dirlist_file, mode='w', encoding='utf-8') as f:
            f.write(output)

    def update_dirlist(self) -> None:
        """
        - returns: none
        - updates dir.list file in polling directory so GR2Analyst see only files prior to current
        sim playback time
        """
        output = ''
        for file in self.filelist:
            #print(file.parts[-1])
            file_timestamp = self.datetime_object_from_timestring(file.parts[-1])
            if file_timestamp < self.current_playback_time:
                print(f'file: {file_timestamp} is older than {self.current_playback_time}')
                line = f'{file.stat().st_size} {file.parts[-1]}'
                print(f'adding: {line}')
                output = output + line+"\n"
        with open(self.dirlist_file, mode='w', encoding='utf-8') as f:
            f.write(output)

#-------------------------------
if __name__ == "__main__":
    #this_radar = 'KGRR'
    #this_playback_time = '2024-06-01 23:15'
    UpdateDirList(sys.argv[1],sys.argv[2],sys.argv[3])
