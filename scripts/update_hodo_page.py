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
<meta http-equiv="refresh" content="60">
<link rel="icon" type="image/x-icon" href="./favicon.ico">
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
                #self.update_hodo_page()
                self.update_hodographs_loop_page()
            except ValueError as ve:
                print(f'Could not decode current playback time in UpdateHodoHTML: {ve}')
                self.clock_time = 'None'


    def make_valid_hodo_list(self) -> list:
        """
        Returns a list of valid hodographs based on the current playback time
        """
        valid_hodo_list = []
        self.image_files = [f for f in os.listdir(HODOGRAPHS_DIR) if f.endswith('.png') or f.endswith('.jpg')]
        self.first_image_path = f'hodographs/{self.image_files[0]}'
        print(self.image_files)
        for filename in self.image_files:
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

    def update_hodographs_loop_page(self) -> None:
        """
        Creates slider loop in hodographs.html page based on the current playback time
        """

        if len(self.valid_hodo_list) == 0:
            self.initialize_hodo_page()

        else:
            station_codes = set(img[-24:-20] for img in self.image_files)
        # HTML content with JavaScript to loop through images using a slider
            html_content = f"""<!DOCTYPE html>
            <html>
            <head>
            <title>Hodographs</title>
            <meta http-equiv="refresh" content="60">
            <style>
            body {{ font-family: Arial, sans-serif; }}
            img {{ max-width: 60%; height: auto; }}
            .slider-container {{
                width: 100%;
                text-align: center;
            }}
            .slider-text-container {{
                font-size: 2em;
                font-style: strong;
                width: 100%;
                text-align: center;
            }}
            .slider {{
                width: 80%;
            }}
            #image-container {{
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            #station-container {{
                display: none;
                margin-left: 20px;
                font-size: 1.5em;
                font-weight: bold;
            }}
            </style>
            <link rel="icon" type="image/x-icon" href="./favicon.ico">
            </head>
            <body>
            <h1>Hodographs</h1>
            <div class="slider-text-container">Playback time: {self.clock_str}</div>
            <div id="controls">
            <label for="station-dropdown">Select Station:</label>
            <select id="station-dropdown">
                <option value="all">All</option>
                {"".join(f'<option value="{code}">{code}</option>' for code in station_codes)}
            </select>
            </div>
            <div id="image-container">
            <img id="hodograph-image" src="hodographs/{self.image_files[0]}" alt="Hodograph">
            <div id="station-container"></div>
            </div>
            <br><br>
            <div class="slider-text-container">Choose which half of the slider range to use based on preferred hodo type</div>
            <div class="slider-container">
            <input type="range" min="0" max="{len(self.image_files) - 1}" value="0" class="slider" id="image-slider">
            </div>
            <div class="slider-text-container">Ground Relative&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp | &nbsp&nbsp&nbsp&nbsp&nbsp&nbspStorm Relative</div>

            <script>
            var allImages = { [f'hodographs/{img}' for img in self.image_files] };
            var images = allImages;
            var slider = document.getElementById('image-slider');
            var dropdown = document.getElementById('station-dropdown');

            function updateSlider() {{
                var selectedStation = dropdown.value;
                if (selectedStation === 'all') {{
                images = allImages;
                }} else {{
                images = allImages.filter(img => img.includes(selectedStation));
                }}
                slider.max = images.length - 1;
                slider.value = 0;
                document.getElementById('hodograph-image').src = images[0];
                updateStationCode(images[0]);
            }}

            function updateStationCode(imagePath) {{
                var stationCode = imagePath.slice(-24, -20);
                document.getElementById('station-container').innerText = stationCode;
            }}

            slider.oninput = function() {{
                var selectedImage = images[this.value];
                document.getElementById('hodograph-image').src = selectedImage;
                updateStationCode(selectedImage);
            }};

            dropdown.onchange = function() {{
                updateSlider();
            }};

            updateSlider(); // Initialize the slider with the default selection
        
            </script>
            </body>
            </html>"""
            with open(HODOGRAPHS_PAGE, 'w', encoding='utf-8') as fout:
                fout.write(html_content)


if __name__ == "__main__":
    #UpdateHodoHTML('2024-09-01 23:15')
    UpdateHodoHTML(sys.argv[1])
