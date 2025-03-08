"""
Defines the directories for scripts, data files, and web assets used in the simulation.
"""
from pathlib import Path
import os
import sys
import time
# import uuid

# import flask
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
    BASE_DIR = Path(*parts[0:idx+1])
    LINK_BASE = "http://localhost:8050/assets"
    CLOUD = False
    PLATFORM = 'DARWIN'
if sys.platform.startswith('win'):
    parts = Path.cwd().parts
    idx = parts.index('cloud-radar-server')
    BASE_DIR = Path(*parts[0:idx+1])
    LINK_BASE = "http://localhost:8050/assets"
    CLOUD = False
    PLATFORM = 'WINDOWS'

########################################################################################
# Initialize the application layout. A unique session ID will be generated on each page
# load.
########################################################################################
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG],
           suppress_callback_exceptions=True, update_title=None)
# server = flask.Flask(__name__)
# app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG],
#           suppress_callback_exceptions=True, update_title=None, server=server)
app.title = "RSSiC"


def init_layout():
    """
    Initialize the layout with a unique session id.  The 'dynamic container' is used 
    within the app to build out the rest of the application layout on page load
    """
    # session_id = f'{time.time_ns()//1000}_{uuid.uuid4().hex}'
    session_id = f'{time.time_ns()//1000000}'
    return dbc.Container([
        # Elements used to store and track the session id and initialize the layout
        dcc.Store(id='session_id', data=session_id, storage_type='session'),
        dcc.Interval(id='setup', interval=1, n_intervals=0, max_intervals=1),

        dcc.Store(id='configs', data={}),
        # dcc.Store(id='sim_settings', data={}),

        # Elements needed to set up the layout on page load by app.py
        dcc.Store(id='layout_has_initialized', data={'added': False}),
        # dcc.Interval(id='container_init', interval=100, n_intervals=0, max_intervals=1),
        html.Div(id='dynamic_container')
    ])


app.layout = init_layout


@app.callback(
    Output('configs', 'data'),
    Input('setup', 'n_intervals'),
    State('session_id', 'data')
)
def setup_paths_and_dirs(n_intervals, session_id):
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
        dirs['USER_DOWNLOADS_DIR'] = f"{dirs['ASSETS_DIR']}/downloads"
        dirs['HODOGRAPHS_PAGE'] = f"{dirs['ASSETS_DIR']}/hodographs.html"
        dirs['LINKS_HTML_PAGE'] = f"{dirs['ASSETS_DIR']}/links.html"
        dirs['HODO_HTML_PAGE'] = dirs['HODOGRAPHS_PAGE']
        dirs['EVENTS_HTML_PAGE'] = f"{dirs['ASSETS_DIR']}/events.html"
        dirs['EVENTS_TEXT_FILE'] = f"{dirs['ASSETS_DIR']}/events.txt"
        dirs['POLLING_DIR'] = f"{dirs['ASSETS_DIR']}/polling"
        dirs['MODEL_DIR'] = f"{dirs['DATA_DIR']}/model_data"
        dirs['RADAR_DIR'] = f"{dirs['DATA_DIR']}/radar"
        dirs['PROBSEVERE_DIR'] = f"{dirs['DATA_DIR']}/probsevere"
        dirs['LOG_DIR'] = f"{dirs['BASE_DIR']}/data/logs"

        # Need to be updated
        dirs['LINK_BASE'] = f"{LINK_BASE}/{session_id}"
        dirs['PLACEFILES_LINKS'] = f"{dirs['LINK_BASE']}/placefiles"
        dirs['HODO_HTML_LINK'] = f"{dirs['LINK_BASE']}/hodographs.html"

        # Static directories (not dependent on session id)
        dirs['SCRIPTS_DIR'] = f'{BASE_DIR}/scripts'
        dirs['OBS_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/obs_placefile.py'
        dirs['LSR_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/lsrs.py'
        dirs['EVENT_TIMES_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/write_event_times.py'
        dirs['LINKS_PAGE_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/write_links_page.py'
        dirs['HODO_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/hodo_plot.py'
        dirs['NEXRAD_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/Nexrad.py'
        dirs['SOUNDINGS_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/gr2a_soundings.py'
        dirs['PROBSEVERE_DOWNLOAD_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/ProbSevere.py'
        dirs['PROBSEVERE_PLACEFILE_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/probsevere_placefile.py'
        dirs['L2MUNGER_FILEPATH'] = f'{dirs['SCRIPTS_DIR']}/l2munger'
        dirs['MUNGER_SCRIPT_FILEPATH'] = f'{dirs['SCRIPTS_DIR']}/munger.py'
        dirs['MUNGE_DIR'] = f'{dirs['SCRIPTS_DIR']}/munge'
        dirs['NSE_SCRIPT_PATH'] = f'{dirs['SCRIPTS_DIR']}/nse.py'
        dirs['DEBZ_FILEPATH'] = f'{dirs['SCRIPTS_DIR']}/debz.py'
        dirs['CSV_PATH'] = f'{BASE_DIR}/radars.csv'

        os.makedirs(dirs['MODEL_DIR'], exist_ok=True)
        os.makedirs(dirs['RADAR_DIR'], exist_ok=True)
        os.makedirs(dirs['PROBSEVERE_DIR'], exist_ok=True)
        os.makedirs(dirs['HODOGRAPHS_DIR'], exist_ok=True)
        os.makedirs(dirs['USER_DOWNLOADS_DIR'], exist_ok=True)
        os.makedirs(dirs['PLACEFILES_DIR'], exist_ok=True)
        os.makedirs(dirs['POLLING_DIR'], exist_ok=True)
        os.makedirs(dirs['LOG_DIR'], exist_ok=True)

        return dirs


# Names (without extensions) of various pre-processing scripts. Needed for script
# monitoring and/or cancelling.
scripts_list = ["Nexrad", "munger", "obs_placefile", "nse", "wgrib2",
                "get_data", "process", "hodo_plot"]

# Names of surface placefiles for monitoring script
surface_placefiles = [
    'wind.txt', 'temp.txt', 'latest_surface_observations.txt',
    'latest_surface_observations_lg.txt', 'latest_surface_observations_xlg.txt',
    'ProbSevere.txt', 'LSRs.txt'
]
