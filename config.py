"""
Defines the directories for scripts, data files, and web assets used in the simulation.
"""
from pathlib import Path
import os
import sys
import time 
import uuid

import flask
from dash import Dash, dcc, html, State, Input, Output
import dash_bootstrap_components as dbc

########################################################################################
# Define the initial base directory 
########################################################################################
BASE_DIR = Path('/data/cloud-radar-server')
LINK_BASE = "https://rssic.nws.noaa.gov/assets"
CLOUD = True
PLATFORM = 'AWS'
# In order to get this work on my dev and work laptop
if sys.platform.startswith('darwin') or os.getlogin() == 'lee.carlaw':
    parts = Path.cwd().parts
    idx = parts.index('cloud-radar-server')
    BASE_DIR =  Path(*parts[0:idx+1])
    LINK_BASE = "http://localhost:8050/assets"
    CLOUD = False
    PLATFORM = 'DARWIN'
if sys.platform.startswith('win'):
    parts = Path.cwd().parts
    idx = parts.index('cloud-radar-server')
    BASE_DIR =  Path(*parts[0:idx+1])
    LINK_BASE = "http://localhost:8050/assets"
    CLOUD = False
    PLATFORM = 'WINDOWS'

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# This and LINK_BASE will need to be moved into the dcc.Store object. All references to 
# these locations in layout_components will also need to be moved into app.py after 
# directory paths are read in from 
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
PLACEFILES_LINKS = f'{LINK_BASE}/placefiles'

########################################################################################
# Initialize the application layout. A unique session ID will be generated on each page
# load. 
########################################################################################
server = flask.Flask(__name__)
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG],
           suppress_callback_exceptions=True, update_title=None, server=server)
app.title = "Radar Simulator"

def init_layout():
    """
    Initialize the layout with a unique session id.  The 'dynamic container' is used 
    within the app to build out the rest of the application layout on page load
    """
    session_id = f'{time.time_ns()//1000}_{uuid.uuid4()}'
    return dbc.Container([
        # Elements used to store and track the session id 
        dcc.Store(id='session_id', data=session_id, storage_type='session'),
        dcc.Interval(id='broadcast_session_id', interval=1, n_intervals=0, max_intervals=1),
        dcc.Store(id='configs', data={}),
        dcc.Store(id='sim_settings', data={}),

        # Elements needed to set up the layout on page load by app.py
        dcc.Interval(id='directory_monitor', interval=1000),
        dcc.Store(id='layout_has_initialized', data={'added': False}),
        html.Div(id='dynamic_container')
    ])

app.layout = init_layout

@app.callback(
    Output('configs', 'data'),
    Input('broadcast_session_id', 'n_intervals'),
    State('session_id', 'data')
)
def broadcast_session_id(n_intervals, session_id):
    """
    Callback executed once on page load to query the session id in dcc.Store component.
    Creates a dictionary of directory paths and stores in a separate dcc.Store component.  

    We cannot pass pathlib.Path objects in this dictionary since they're not 
    JSON-serializable.
    """
    if n_intervals > 0:
        dirs = {
            'BASE_DIR': f'{BASE_DIR}',
            'ASSETS_DIR': f'{BASE_DIR}/assets/{session_id}',
            'DATA_DIR': f'{BASE_DIR}/data/{session_id}'
        }

        dirs['SESSION_ID'] = session_id
        dirs['PLACEFILES_DIR'] = f"{dirs['ASSETS_DIR']}/placefiles"
        dirs['HODOGRAPHS_DIR'] = f"{dirs['ASSETS_DIR']}/hodographs"
        dirs['HODOGRAPHS_PAGE'] = f"{dirs['ASSETS_DIR']}/hodographs.html"
        dirs['HODO_HTML_PAGE'] = dirs['HODOGRAPHS_PAGE']
        dirs['POLLING_DIR'] = f"{dirs['ASSETS_DIR']}/polling"
        dirs['MODEL_DIR'] = f"{dirs['DATA_DIR']}/model_data"
        dirs['RADAR_DIR'] = f"{dirs['DATA_DIR']}/radar"
        dirs['LOG_DIR'] = f"{dirs['DATA_DIR']}/logs"

        # Need to be updated
        dirs['LINK_BASE'] = f"https://rssic.nws.noaa.gov/assets/{session_id}"
        dirs['PLACEFILES_LINKS'] = f"{dirs['LINK_BASE']}/placefiles"
        dirs['HODO_HTML_LINK'] = f"{dirs['LINK_BASE']}/hodographs.html"

        # Static directories (not dependent on session id)
        dirs['SCRIPTS_DIR'] = f'{BASE_DIR}/scripts'
        dirs['OBS_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/obs_placefile.py'
        dirs['HODO_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/hodo_plot.py'
        dirs['NEXRAD_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/Nexrad.py'
        dirs['L2MUNGER_FILEPATH'] = f'{dirs['SCRIPTS_DIR']}/l2munger'
        dirs['MUNGER_SCRIPT_FILEPATH'] = f'{dirs['SCRIPTS_DIR']}/munger.py'
        dirs['MUNGE_DIR'] = f'{dirs['SCRIPTS_DIR']}/munge'
        dirs['NSE_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/nse.py'
        dirs['DEBZ_FILEPATH'] = f'{dirs['SCRIPTS_DIR']}/debz.py'
        dirs['CSV_PATH'] = f'{BASE_DIR}/radars.csv'

        os.makedirs(dirs['MODEL_DIR'], exist_ok=True)
        os.makedirs(dirs['RADAR_DIR'], exist_ok=True)
        os.makedirs(dirs['HODOGRAPHS_DIR'], exist_ok=True)
        os.makedirs(dirs['PLACEFILES_DIR'], exist_ok=True)
        os.makedirs(dirs['POLLING_DIR'], exist_ok=True)
        os.makedirs(dirs['LOG_DIR'], exist_ok=True)

        return dirs

'''
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
'''
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = DATA_DIR / 'logs'
# Names (without extensions) of various pre-processing scripts. Needed for script 
# monitoring and/or cancelling. 
scripts_list = ["Nexrad", "munger", "obs_placefile", "nse", "wgrib2", 
                "get_data", "process", "hodo_plot"]
