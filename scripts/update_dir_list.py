"""_summary_

    Returns:
        _type_: _description_
"""

from __future__ import print_function
import sys
from pathlib import Path
from datetime import datetime
import pytz

class UpdateDirList():
    """
    updates the dir.list file in the polling directory so GR2Analyst can play this back

    radar: string
         the radar that needs its dIf string is provided, it must correspond to a real nexrad location (like KGRR)
         If None, will use radar location associated with archive files 
         
    current_playback_time: str
        uses l2munger to:
        - change valid times starting at 2 hours prior to current real time
        - remap data to new_rda if provided (see below).

    initialize: bool
        True: will create a new dir.list file with only the first three files in the polling directory
        False: will update the dir.list file with all files in the polling directory that are older than the current playback time

    """
    SCRIPTS_DIR = Path('/data/cloud-radar-server/scripts')
    POLLING_DIR = Path('/data/cloud-radar-server/assets/polling')

    def __init__(self, radar: str, current_playback_time: str, initialize: bool = False):
        self.radar = radar.upper()
        self.this_radar_polling_directory = self.POLLING_DIR / self.radar
        print(self.this_radar_polling_directory)
        self.dirlist_flle = self.this_radar_polling_directory / 'dir.list'
        try:
            self.current_playback_time = datetime.strptime(current_playback_time,"%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=pytz.UTC).timestamp()
        except ValueError:
            self.current_playback_time = 'None'
        print(self.current_playback_time)
        self.initialize = initialize
        self.filelist = sorted(list(self.this_radar_polling_directory.glob('*gz')))
        if initialize:
            self.dirlist_initialize()
        else:
            self.update_dirlist()

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
        with open(self.dirlist_flle, mode='w', encoding='utf-8') as f:
            f.write(output)
        
        return
    
    def update_dirlist(self) -> None:
        """
        - returns: none
        - updates dir.list file in polling directory so GR2Analyst see only files prior to current
        sim playback time
        """
        output = ''
        for file in self.filelist:
            print(file.parts[-1])
            file_timestamp = self.datetime_object_from_timestring(file.parts[-1])
            if file_timestamp < self.current_playback_time:
                line = f'{file.stat().st_size} {file.parts[-1]}\n'
                #print(line)
                output = output + line
        with open(self.dirlist_flle, mode='w', encoding='utf-8') as f:
            f.write(output)
        
        return

#-------------------------------
if __name__ == "__main__":
    #this_radar = 'KGRR'
    #this_playback_time = '2024-06-01 23:15:20 UTC'
    UpdateDirList(sys.argv[1],sys.argv[2],sys.argv[3])
