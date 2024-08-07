"""
Defines the directories for scripts, data files, and web assets used in the simulation.
"""
from pathlib import Path
import os
import sys

#BASE_DIR = Path.cwd()
BASE_DIR = Path('/data/cloud-radar-server')
LINK_BASE = "https://rssic.nws.noaa.gov/assets"
CLOUD = True
# In order to get this work on my dev and work laptop
if sys.platform.startswith('darwin') or sys.platform.startswith('win'):
    parts = Path.cwd().parts
    idx = parts.index('cloud-radar-server')
    BASE_DIR =  Path(*parts[0:idx+1])
    LINK_BASE = "http://localhost:8050/assets"
    CLOUD = False


ASSETS_DIR = BASE_DIR / 'assets'
PLACEFILES_DIR = ASSETS_DIR / 'placefiles'

PLACEFILES_LINKS = f'{LINK_BASE}/placefiles'

HODOGRAPHS_DIR = ASSETS_DIR / 'hodographs'
HODOGRAPHS_PAGE = ASSETS_DIR / 'hodographs.html'
HODO_HTML_PAGE = HODOGRAPHS_PAGE

HODO_HTML_LINK = f'{LINK_BASE}/hodographs.html'
HODO_IMAGES = ASSETS_DIR / 'hodographs'
POLLING_DIR = ASSETS_DIR / 'polling'


DATA_DIR = BASE_DIR / 'data'
MODEL_DIR = DATA_DIR / 'model_data'
RADAR_DIR = DATA_DIR / 'radar'
LOG_DIR = DATA_DIR / 'logs'
CSV_PATH = BASE_DIR / 'radars.csv'
SCRIPTS_DIR = BASE_DIR / 'scripts'
OBS_SCRIPT_PATH = SCRIPTS_DIR / 'obs_placefile.py'
HODO_SCRIPT_PATH = SCRIPTS_DIR / 'hodo_plot.py'
NEXRAD_SCRIPT_PATH = SCRIPTS_DIR / 'Nexrad.py'
L2MUNGER_FILEPATH = SCRIPTS_DIR / 'l2munger'
MUNGER_SCRIPT_FILEPATH = SCRIPTS_DIR / 'munger.py'
MUNGE_DIR = SCRIPTS_DIR / 'munge'
nse_script_path = SCRIPTS_DIR / 'nse.py'
NSE_SCRIPT_PATH = SCRIPTS_DIR / 'nse.py'
DEBZ_FILEPATH = SCRIPTS_DIR / 'debz.py'
LOG_DIR = DATA_DIR / 'logs'

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HODO_IMAGES, exist_ok=True)
os.makedirs(PLACEFILES_DIR, exist_ok=True)
