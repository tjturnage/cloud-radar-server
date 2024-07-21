"""
UpdateHoooHTML Class
updated: 2021-06-02
"""
from pathlib import Path
import os
import sys
from datetime import datetime
import pytz

HODOGRAPHS_DIR = '/data/cloud-radar-server/assets/hodographs'
HODOGRAPHS_HTML_PAGE = '/data/cloud-radar-server/assets/hodographs.html'
dir_parts = Path.cwd().parts
if 'C:\\' in dir_parts:
    HODOGRAPHS_DIR = 'C:/data/scripts/cloud-radar-server/assets/hodographs'
    HODOGRAPHS_HTML_PAGE = 'C:/data/scripts/cloud-radar-server/assets/hodographs.html'
    #link_base = "http://localhost:8050/assets"
    #cloud = False


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
<title>Hodographs</title>
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
    def __init__(self, playback_time: str, initialize: bool = False):
        self.playback_time = playback_time
        self.initialize = initialize
        if initialize:
            self.initialize_hodo_page()
        else:
            self.update_hodo_page()

    def initialize_hodo_page(self) -> None:
        """
        Initializes the hodographs.html page with a message that graphics are not available
        """
        with open(HODOGRAPHS_HTML_PAGE, 'w', encoding='utf-8') as fout:
            fout.write(HEAD_NOLIST)
            fout.write('<h1>Graphics not available, check back later!</h1>\n')
            fout.write(TAIL_NOLIST)
    
    def update_hodo_page(self) -> None:
        """
        Updates the hodographs.html page with available hodographs based on the current playback time
        Playback time is in the format 'YYYY-MM-DD HH:MM UTC', but will be ignored if it is not in this format
        """
        try:
            current_playback_time = datetime.strptime(self.playback_time,"%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC).timestamp()
            print(current_playback_time)
        except ValueError as ve:
            print(f'Could not decode current playback time: {ve}')
            current_playback_time = 'None'
       
        with open(HODOGRAPHS_HTML_PAGE, 'w', encoding='utf-8') as fout:
            fout.write(HEAD)
            image_files = [f for f in os.listdir(HODOGRAPHS_DIR) if f.endswith('.png') or f.endswith('.jpg')]
            for filename in image_files:
                file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
                if file_time < current_playback_time:
                    print(filename)
                    line = f'<li><a href="hodographs/{filename}">{filename}</a></li>\n'
                    fout.write(line)
            fout.write(TAIL)

if __name__ == "__main__":
    #this_playback_time = '2024-06-01 23:15 UTC'
    UpdateHodoHTML(sys.argv[1], sys.argv[2])
