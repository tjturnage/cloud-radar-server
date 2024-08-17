"""
UpdateHodoHTML Class
updated: 2021-06-02
"""
from pathlib import Path
import os
import sys
from datetime import datetime
import pytz

from config import HODOGRAPHS_DIR, HODOGRAPHS_PAGE

#HODO_DIR = '/data/cloud-radar-server/assets/hodographs'
#HODOGRAPHS_PAGE = '/data/cloud-radar-server/assets/hodographs.html'
dir_parts = Path.cwd().parts
if 'C:\\' in dir_parts:
    HODOGRAPHS_DIR = 'C:/data/scripts/cloud-radar-server/assets/hodographs'
    HODOGRAPHS_PAGE = 'C:/data/scripts/cloud-radar-server/assets/hodographs.html'
    link_base = "http://localhost:8050/assets"
    cloud = False


HEAD = """<!DOCTYPE html>
<html>
<head>
<title>Hodographs</title>
</head>
<body>
<ul>"""

HEAD_NOLIST = """<!DOCTYPE html>
<html>
<head>
<title>Sim Hodos/title>
</head>
<body>"""

TAIL = """</ul>
</body>
</html>"""

TAIL_NOLIST = """</body>
</html>"""


class UpdateHodoHTML():
    """
    playback_time: str
        Current playback time in the format 'YYYY-MM-DD HH:MM'
    initialize: bool
        If True, the page will be initialized with a message that graphics are not available
        If False, the page will be updated with "available" hodographs based on the current playback time
    """
    def __init__(self, clock_str: str):
        self.clock_str = clock_str
        if self.clock_str == 'None':
            self.initialize_hodo_page()
        else:
            try:
                self.clock_time = datetime.strptime(self.clock_str,"%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC).timestamp()
                self.valid_hodo_list = self.make_valid_hodo_list()
                self.update_hodo_page()
            except ValueError as ve:
                print(f'Could not decode current playback time in UpdateHodoHTML: {ve}')
                self.clock_time = 'None'


    def make_valid_hodo_list(self) -> list:
        """
        Returns a list of valid hodographs based on the current playback time
        """
        valid_hodo_list = []
        image_files = [f for f in os.listdir(HODOGRAPHS_DIR) if f.endswith('.png') or f.endswith('.jpg')]
        
        for filename in image_files:
            file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
            if file_time < self.clock_time:
                valid_hodo_list.append(filename)
        return valid_hodo_list

    def initialize_hodo_page(self) -> None:
        """
        Initializes the hodographs.html page with a message that graphics are not available
        """
        with open(HODOGRAPHS_PAGE, 'w', encoding='utf-8') as fout:
            fout.write(HEAD_NOLIST)
            fout.write('<h1>Graphics not available, check back later!</h1>\n')
            fout.write(TAIL_NOLIST)
    
    def update_hodo_page(self) -> None:
        """
        Updates the hodographs.html page with available hodographs based on the current playback time
        Playback time is in the format 'YYYY-MM-DD HH:MM UTC', but will be ignored if it is not in this format
        """
        if len(self.valid_hodo_list) == 0:
            self.initialize_hodo_page()
        else:
            with open(HODOGRAPHS_PAGE, 'w', encoding='utf-8') as fout:
                fout.write(HEAD)
                for filename in self.valid_hodo_list:
                    file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
                    if file_time < self.clock_time:
                        print(filename)
                        line = f'<li><a href="hodographs/{filename}">{filename}</a></li>\n'
                        fout.write(line)
                fout.write(TAIL)

if __name__ == "__main__":
    #this_playback_time = '2024-06-01 23:15 UTC'
    UpdateHodoHTML(sys.argv[1])
