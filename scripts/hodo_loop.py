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

def create_hodographs_page():
    # List all image files in the directory
    image_files = [f for f in Path(HODOGRAPHS_DIR).iterdir() if f.is_file() and f.suffix in ['.png', '.jpg', '.jpeg', '.gif']]
    
    # Base URL for accessing the images
    link_base = "http://localhost:8050/assets/hodographs"
    
    # HTML content with JavaScript to loop through images using a slider
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<title>Hodographs</title>
<style>
  body {{ font-family: Arial, sans-serif; }}
  img {{ max-width: 100%; height: auto; }}
  .slider-container {{
    width: 100%;
    text-align: center;
  }}
  .slider {{
    width: 80%;
  }}
</style>
</head>
<body>
<h1>Hodographs</h1>
<div id="image-container">
  <img id="hodograph-image" src="{link_base}/{image_files[0].name}" alt="Hodograph">
</div>
<div class="slider-container">
  <input type="range" min="0" max="{len(image_files) - 1}" value="0" class="slider" id="image-slider">
</div>
<script>
  var images = { [f'"{link_base}/{img.name}"' for img in image_files] };
  var slider = document.getElementById('image-slider');
  slider.oninput = function() {{
    document.getElementById('hodograph-image').src = images[this.value];
  }};
</script>
</body>
</html>"""
    
    # Write the HTML content to a file
    with open(HODOGRAPHS_PAGE, 'w') as file:
        file.write(html_content)

# Call the function to create the page
create_hodographs_page()