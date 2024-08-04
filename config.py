"""
Defines the directories for scripts, data files, and web assets used in the simulation.
"""
from pathlib import Path
import os

# Set the base directory for the app
dir_parts = Path.cwd().parts
link_base = "http://localhost:8050/assets"
if 'C:\\' in dir_parts:
    APP_HOME_DIR = Path('C:/data/scripts/cloud-radar-server')
    cloud = False
elif 'carlaw' in dir_parts:
    APP_HOME_DIR = Path('C:/data/scripts/cloud-radar-server')
else:
    link_base = "https://rssic.nws.noaa.gov/assets"
    cloud = True



place_base = f"{link_base}/placefiles"


csv_file = APP_HOME_DIR / 'radars.csv'
data_dir = APP_HOME_DIR / 'data'
assets_dir = APP_HOME_DIR / 'assets'
os.makedirs(data_dir, exist_ok=True)
log_dir = data_dir / 'logs'
os.makedirs(log_dir, exist_ok=True)
scripts_path = APP_HOME_DIR / 'scripts'
obs_script_path = scripts_path / 'obs_placefile.py'
hodo_script_path = scripts_path / 'hodo_plot.py'
nexrad_script_path = scripts_path / 'Nexrad.py'
l2munger_script_path = scripts_path / 'munger.py'
nse_script_path = scripts_path / 'nse.py'
munge_dir = scripts_path / 'munge'
hodo_images = assets_dir / 'hodographs'
os.makedirs(hodo_images, exist_ok=True)
polling_dir = assets_dir / 'polling'
placefiles_dir = assets_dir / 'placefiles'
os.makedirs(placefiles_dir, exist_ok=True)
