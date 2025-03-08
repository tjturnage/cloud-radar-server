"""
UpdateHodoHTML Class

"""
from pathlib import Path
import os
import sys
from datetime import datetime
import pytz

dir_parts = Path.cwd().parts
if 'C:\\' in dir_parts:
    PLATFORM = 'windows'
#    HODOGRAPHS_DIR = 'C:/data/scripts/cloud-radar-server/assets/hodographs'
#    HODOGRAPHS_PAGE = 'C:/data/scripts/cloud-radar-server/assets/hodographs.html'
#    #link_base = "http://localhost:8050/assets"
#    #cloud = False
else:
    PLATFORM = 'not_windows'


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
<link rel="icon" type="image/x-icon" href="./favicon.ico">
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootswatch/4.5.2/cyborg/bootstrap.min.css">
</head>
<body>"""

TAIL = """</ul>
</body>
</html>"""

interval_code = "setInterval(function() {location.reload();}, 120000);"

TAIL_NOLIST = """<script>
{interval_code}
</script>
</body>
</html>"""

class UpdateHodoHTML():
    """
    playback_time: str
        Current playback time in the format 'YYYY-MM-DD HH:MM'
    initialize: bool
        If True, the page will be initialized with a message that graphics are not available
        If False, the page will be updated with "available" hodographs based on the current playback time
    """
    def __init__(self, clock_str: str, hodographs_dir: str, hodographs_page: str):
        self.clock_str = clock_str
        self.hodographs_dir = hodographs_dir
        self.hodographs_page = hodographs_page
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
        self.image_files = [f for f in os.listdir(self.hodographs_dir) if f.endswith('.png') or f.endswith('.jpg')]
        self.image_files.sort()
        try:
            self.first_image_path = self.image_files[0]
            #print(self.image_files)
            for filename in self.image_files:
                file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
                if file_time < self.clock_time:
                    valid_hodo_list.append(filename)
            valid_hodo_list.sort()
            return valid_hodo_list
        except IndexError as ie:
            print(f'Could not find any hodographs in UpdateHodoHTML: {ie}')
            self.initialize_hodo_page()
            return []

    def initialize_hodo_page(self) -> None:
        """
        Initializes the hodographs.html page with a message that graphics are not available
        """
        with open(self.hodographs_page, 'w', encoding='utf-8') as fout:
            fout.write(HEAD_NOLIST)
            fout.write('<br><br>\n')
            fout.write('<h3>Graphics not available, check back later!</h3>\n')
            fout.write(TAIL_NOLIST)
    
    def update_hodo_page(self) -> None:
        """
        Updates the hodographs.html page with available hodographs based on the current playback time
        Playback time is in the format 'YYYY-MM-DD HH:MM UTC', but will be ignored if it is not in this format
        """
        if len(self.valid_hodo_list) == 0:
            self.initialize_hodo_page()
        else:
            with open(self.hodographs_page, 'w', encoding='utf-8') as fout:
                fout.write(HEAD)
                for filename in self.valid_hodo_list:
                    file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
                    if file_time < self.clock_time:
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
            link_list = []
            station_codes = set(img[-24:-20] for img in self.image_files)
            for filename in self.valid_hodo_list:
                file_time = datetime.strptime(filename[-19:-4], '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC).timestamp()
                if file_time < self.clock_time:
                    #print(filename)
                    link = f'hodographs/{filename}'
                    link_list.append(link)
            #print(link_list)
         
        # HTML content with JavaScript to loop through images using a slider
            html_content = f"""<!DOCTYPE html>
            <html>
            <head>
            <title>Hodographs</title>
            <link rel="icon" href="https://rssic.nws.noaa.gov/assets/favicon.ico" type="image/x-icon">
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootswatch/4.5.2/cyborg/bootstrap.min.css">
            <style>
            img {{ max-width: 90%; height: auto; }} /* Display images at 90% size */
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
                width: 90%;
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
            </head>
            <body class="container">
            <br>
            <br>
            <div class="slider-text-container">Playback time: {self.clock_str}</div>
            <div id="controls" class="mb-4">
            <label for="station-dropdown">Select Station:</label>
            <select id="station-dropdown" class="form-control">
                {"".join(f'<option value="{code}">{code}</option>' for code in station_codes)}
            </select>
            </div>
            <div id="image-container" class="mb-4">
            <img id="hodograph-image" src="hodographs/{self.image_files[0]}" alt="Hodograph">
            <div id="station-container"></div>
            </div>
            <div class="slider-text-container">Ground Relative&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp | &nbsp&nbsp&nbsp&nbsp&nbsp&nbspStorm Relative</div>
            <div class="slider-container mb-4">
            <input type="range" min="0" max="{len(self.image_files) - 1}" value="0" class="slider" id="image-slider">
            </div>
            <div class="slider-text-container">Choose which half of the slider to use based on desired hodo type</div>

            <hr>
            <br>
            <h2>Storm-Relative Hodograph Interpretation</h2>
            <br>
            <h3 style="color:#800080;">Purple: 0-1km</h3></div>
            <ul>
            <li>Governs the strength of a supercell’s low-level mesocyclone</li>
            <li>Especially large curved or sickle-shaped segments are favorable for tornadoes</li>
            <li>Surface storm-relative inflow > 40kt becomes more favorable for longer-tracked tornadoes</li>
            </ul>
            <br>
            <h3 style="color:#FF0000;">Red: 1-3km</h3>
            <ul>
            <li>Governs the strength of a supercell’s mid-level mesocyclone</li>
            <li>Especially long segments here are favorable for robust supercell formation</li>
            <li>Straighter segments are more favorable for storm splitting</li>
            </ul>
            <br>
            <h3 style="color:#008000;">Green: 3-6km</h3>
            <ul>
            <li>May govern precipitation ventilation especially within the foward flank “vault” region</li>
            <li>Especially segments lying outside the 15kt range ring may be more favorable for clean “vault” regions</li>
            <li>Curved segments at constant storm-relative wind becomes more favorable for deep “mothership” structures</li>
            </ul>
            <br>
            <h3 style="color:#FFD700;">Yellow: 6-8km</h3>
            <ul>
            <li>May govern precipitation ventilation especially within the rear-flank downdraft region</li>
            <li>Segments lying outside the 40kt range ring may be more favorable for “low-precipitation” mode</li>
            <li>Segments lying inside the 20kt range ring may be more favorable for “high-precipitation” mode</li>
            <li>Longer, straighter segments oriented radial to storm motion means storms are more favored to be “tilted”, back-sheared, and without anvils</li>
            </ul>

            <script>
            var allImages = {link_list};
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

            // Refresh the page every 2 minutes (120,000 milliseconds)
            {interval_code}
            </script>
            </body>
            </html>"""
            with open(self.hodographs_page, 'w', encoding='utf-8') as fout:
                fout.write(html_content)


if __name__ == "__main__":
    if PLATFORM == 'windows':
        UpdateHodoHTML('2024-09-01 23:15', sys.argv[2], sys.argv[3])
    else:
        UpdateHodoHTML(sys.argv[1], sys.argv[2], sys.argv[3])
