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

head = """<!DOCTYPE html>
<html>
<head>
<title>Hodographs</title>
</head>
<body>
<ul>"""

tail = """</ul>
</body>
</html>"""

class UpdateHodoHTML():
    """_summary_
    Looks at the current playback time and updates the hodographs.html page if associated times are prior to the 
    current playback time 
    """
    def __init__(self, playback_time: str):
        self.playback_time = playback_time

    def update_hodo_page(self) -> None:
        """_summary_

        Args:
            playback_time (_type_): _description_
        """
        current_playback_time = datetime.strptime(self.playback_time,"%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=pytz.UTC).timestamp()
        with open(HODOGRAPHS_HTML_PAGE, 'w', encoding='utf-8') as fout:
            fout.write(head)
            image_files = [f for f in os.listdir(HODOGRAPHS_DIR) if f.endswith('.png') or f.endswith('.jpg')]
            for filename in image_files:
                file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
                if file_time < current_playback_time:
                    print(filename)      
                    line = f'<li><a href="hodographs/{filename}">{filename}</a></li>\n'
                    fout.write(line)
            fout.write(tail)
        return

if __name__ == "__main__":
    #this_playback_time = '2024-06-01 23:15:20 UTC'
    UpdateHodoHTML(sys.argv[1])
