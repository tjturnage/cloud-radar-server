"""
UpdateHoooHTML Class
updated: 2021-06-02
"""
import os
import sys
from datetime import datetime
import pytz

HODOGRAPHS_DIR = '/data/cloud-radar-server/assets/hodographs'
HODOGRAPHS_HTML_PAGE = '/data/cloud-radar-server/assets/hodographs.html'

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
        Current playback time in the format 'YYYY-MM-DD HH:MM:SS UTC'
    initialize: bool
        If True, the page will be initialized with a message that graphics are not available
        If False, the page will be updated with "available" hodographs based on the current playback time
    """
    def __init__(self, playback_time: str, initialize: bool = False):
        self.playback_time = playback_time
        self.initialize = initialize

    def update_hodo_page(self) -> None:
        """
        Updates the hodographs.html page with available hodographs based on the current playback time
        Playback time is in the format 'YYYY-MM-DD HH:MM:SS UTC', but will be ignored if it is not in this format
        """
        try:
            current_playback_time = datetime.strptime(self.playback_time,"%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=pytz.UTC).timestamp()
        except ValueError:
            current_playback_time = 'None'
        
        if self.initialize:
            with open(HODOGRAPHS_HTML_PAGE, 'w', encoding='utf-8') as fout:
                fout.write(HEAD_NOLIST)
                fout.write('<h1>Graphics not available, check back later!</h1>\n')
                fout.write(TAIL_NOLIST)
            return
        
        with open(HODOGRAPHS_HTML_PAGE, 'w', encoding='utf-8') as fout:
            fout.write(HEAD)
            image_files = [f for f in os.listdir(HODOGRAPHS_DIR) if f.endswith('.png') or f.endswith('.jpg')]
            for filename in image_files:
                file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
                #if file_time < current_playback_time:
                if file_time < 999999999999999:
                    print(filename)      
                    line = f'<li><a href="hodographs/{filename}">{filename}</a></li>\n'
                    fout.write(line)
            fout.write(TAIL)
        return

if __name__ == "__main__":
    #this_playback_time = '2024-06-01 23:15:20 UTC'
    UpdateHodoHTML(sys.argv[1])
