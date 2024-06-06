"""_summary_

    Returns:
    Main page for radar-server
        _type_: _description_
"""
#from flask import Flask, render_template
import os
import shutil
import re
import subprocess
from pathlib import Path
from glob import glob
import time
from datetime import datetime, timedelta, timezone
import calendar
import math
#import pandas as pd
import pytz
#from time import sleep
from dash import Dash, html, Input, Output, dcc #, ctx, callback
from dash.exceptions import PreventUpdate
#from dash import diskcache, DiskcacheManager, CeleryManager
#from uuid import uuid4
#import diskcache
import numpy as np
from botocore.client import Config

# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc
import layout_components as lc
from scripts.obs_placefile import Mesowest
from scripts.Nexrad import NexradDownloader
from scripts.munger import Munger
from scripts.update_dir_list import UpdateDirList
from scripts.update_hodo_page import UpdateHodoHTML
from scripts.nse import Nse

 # Earth radius (km)
R = 6_378_137

# Regular expressions. First one finds lat/lon pairs, second finds the timestamps.
LAT_LON_REGEX = "[0-9]{1,2}.[0-9]{1,100},[ ]{0,1}[|\\s-][0-9]{1,3}.[0-9]{1,100}"
TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

# ----------------------------------------
#        Attempt to set up environment
# ----------------------------------------
TOKEN = 'INSERT YOUR MAPBOX TOKEN HERE'

BASE_DIR = Path.cwd()
ASSETS_DIR = BASE_DIR / 'assets'
HODO_HTML_PAGE = ASSETS_DIR / 'hodographs.html'
POLLING_DIR = ASSETS_DIR / 'polling'
PLACEFILES_DIR = ASSETS_DIR / 'placefiles'
HODOGRAPHS_DIR = ASSETS_DIR / 'hodographs'
DATA_DIR = BASE_DIR / 'data'
RADAR_DIR = DATA_DIR / 'radar'
CSV_PATH = BASE_DIR / 'radars.csv'
SCRIPTS_DIR = BASE_DIR / 'scripts'
OBS_SCRIPT_PATH = SCRIPTS_DIR / 'obs_placefile.py'
HODO_SCRIPT_PATH = SCRIPTS_DIR / 'hodo_plot.py'
NEXRAD_SCRIPT_PATH = SCRIPTS_DIR / 'Nexrad.py'
L2MUNGER_FILEPATH = SCRIPTS_DIR / 'l2munger'

################################################################################################
#       Define class RadarSimulator
################################################################################################

class RadarSimulator(Config):
    """
    A class to simulate radar operations, inheriting configurations from a base Config class.

    This simulator is designed to mimic the behavior of a radar system over a specified period,
    starting from a predefined date and time. It allows for the simulation of radar data generation,
    including the handling of time shifts and geographical coordinates.

    Attributes:
    """

    def __init__(self):
        super().__init__()
        self.event_start_year = 2023
        self.event_start_month = 6
        self.days_in_month = 30
        self.event_start_day = 7
        self.event_start_hour = 21
        self.event_start_minute = 45
        self.event_duration = 30
        self.timestring = None
        self.number_of_radars = 0
        self.radar_list = []
        self.radar_dict = {}
        self.radar = None
        self.lat = None
        self.lon = None
        self.new_radar = 'None'
        self.new_lat = None
        self.new_lon = None
        self.simulation_clock = None
        self.simulation_running = False
        self.scripts_progress = 'Scripts not started'
        self.current_dir = Path.cwd()
        self.define_scripts_and_assets_directories()
        self.make_simulation_times()
        # self.get_radar_coordinates()

    def create_radar_dict(self) -> None:
        """
        Creates a dictionary of radar sites and their associated metadata that will be used in the simulation.
        """
        for _i,radar in enumerate(self.radar_list):
            self.lat = lc.df[lc.df['radar'] == radar]['lat'].values[0]
            self.lon = lc.df[lc.df['radar'] == radar]['lon'].values[0]
            asos_one = lc.df[lc.df['radar'] == radar]['asos_one'].values[0]
            asos_two = lc.df[lc.df['radar'] == radar]['asos_two'].values[0]
            self.radar_dict[radar.upper()] = {'lat':self.lat,'lon':self.lon, 'asos_one':asos_one, 'asos_two':asos_two, 'radar':radar.upper(), 'file_list':[]}

    def create_grlevel2_cfg_file(self) -> None:
        """
        Ensures a grlevel2.cfg file is created in the polling directory. It's required for GR2Analyst to poll for radar data.
        Only the radar sites used in the simulation are listed in this file instead of all available radars
        """
        f = open(POLLING_DIR / 'grlevel2.cfg', 'w', encoding='utf-8')
        f.write('ListFile: dir.list\n')
        if sa.new_radar != 'None':
            f.write(f'Site: {sa.new_radar.upper()}\n')
        else:
            for _i,radar in enumerate(self.radar_list):
                f.write(f'Site: {radar.upper()}\n')
        f.close()

    def copy_grlevel2_cfg_file(self) -> None:
        """
        Ensures a grlevel2.cfg file is copied into the polling directory. It's required for GR2Analyst to poll for radar data.
        Only the radar sites used in the simulation are listed in this file instead of all available radars
        """       
        source = BASE_DIR / 'grlevel2.cfg'
        destination = POLLING_DIR / 'grlevel2.cfg'
        try:
            shutil.copyfile(source, destination)
        except Exception as e:
            print(f"Error copying {source} to {destination}: {e}")

    
    def define_scripts_and_assets_directories(self) -> None:
        """
        Defines the directories for scripts, data files, and web assets used in the simulation.
        """
        self.csv_file = self.current_dir / 'radars.csv'
        self.data_dir = self.current_dir / 'data'
        os.makedirs(self.data_dir, exist_ok=True)
        self.scripts_path = self.current_dir / 'scripts'
        self.obs_script_path = self.current_dir / 'obs_placefile.py'
        self.hodo_script_path = self.scripts_path / 'hodo_plot.py'
        self.nexrad_script_path = self.scripts_path / 'get_nexrad.py'
        self.munge_dir = self.scripts_path / 'munge'
        self.assets_dir = self.current_dir / 'assets'
        self.hodo_images = self.assets_dir / 'hodographs'
        os.makedirs(self.hodo_images, exist_ok=True)
        self.placefiles_dir = self.assets_dir / 'placefiles'
        os.makedirs(self.placefiles_dir, exist_ok=True)
        UpdateHodoHTML('None', initialize=True)

    def make_simulation_times(self) -> None:
        """
        playback_start_time: datetime object
            the time the simulation starts. It's arbitrarily set to 2 hours prior to current real time so GR2Analyst can poll for data
        playback_timer: datetime object
            the "current" displaced realtime during the playback
        event_start_time: datetime object
            the historical time the actual event started. This is based on user inputs of the event start time
        simulation_time_shift: timedelta object
            the difference between the playback start time and the event start time
        simulation_seconds_shift: int
            the difference between the playback start time and the event start time in seconds

        Variables ending with "_str" are the string representations of the datetime objects
        """
        self.playback_start_time = datetime.now(tz=timezone.utc) - timedelta(hours=2)
        self.playback_timer = self.playback_start_time + timedelta(seconds=360)
        self.event_start_time = datetime(self.event_start_year,self.event_start_month,self.event_start_day,
                                  self.event_start_hour,self.event_start_minute,second=0,
                                  tzinfo=timezone.utc)
        self.simulation_time_shift = self.playback_start_time - self.event_start_time
        self.simulation_seconds_shift = round(self.simulation_time_shift.total_seconds())
        self.sim_clock = self.playback_start_time
        self.event_start_str = datetime.strftime(self.event_start_time,"%Y-%m-%d %H:%M:%S UTC")
        self.playback_start_str = datetime.strftime(self.playback_start_time,"%Y-%m-%d %H:%M:%S UTC")
        self.playback_end_time = self.playback_start_time + timedelta(minutes=int(self.event_duration))

    def get_days_in_month(self) -> None:
        """
        This is a helper function for knowing how many days to list in the dropdown for the day selection
        """
        self.days_in_month = calendar.monthrange(self.event_start_year, self.event_start_month)[1]

    def get_timestamp(self,file: str) -> float:
        """
        - extracts datetime info from the radar filename
        - returns a datetime timestamp (epoch seconds) object
        """
        file_epoch_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S').timestamp()
        return file_epoch_time

    def move_point(self,plat,plon):
        #radar1_lat, radar1_lon, radar2_lat, radar2_lon, lat, lon
        """
        Shift placefiles to a different radar site. Maintains the original azimuth and range
        from a specified RDA and applies it to a new radar location. 

        Parameters:
        -----------
        plat: float 
            Original placefile latitude
        plon: float 
            Original palcefile longitude

        self.lat and self.lon is the lat/lon pair for the original radar 
        self.new_lat and self.new_lon is for the transposed radar. These values are set in 
        the transpose_radar function after a user makes a selection in the new_radar_selection
        dropdown. 

        """
        def _clamp(n, minimum, maximum):
            """
            Helper function to make sure we're not taking the square root of a negative 
            number during the calculation of `c` below. Same as numpy.clip(). 
            """
            return max(min(maximum, n), minimum)

        # Compute the initial distance from the original radar location
        phi1, phi2 = math.radians(self.lat), math.radians(plat)
        d_phi = math.radians(plat - self.lat)
        d_lambda = math.radians(plon - self.lon)

        a = math.sin(d_phi/2)**2 + (math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda/2)**2)
        a = _clamp(a, 0, a)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = R * c

        # Compute the bearing
        y = math.sin(d_lambda) * math.cos(phi2)
        x = (math.cos(phi1) * math.sin(phi2)) - (math.sin(phi1) * math.cos(phi2) * \
                                                math.cos(d_lambda))
        theta = math.atan2(y, x)
        bearing = (math.degrees(theta) + 360) % 360

        # Apply this distance and bearing to the new radar location
        phi_new, lambda_new = math.radians(self.new_lat), math.radians(self.new_lon)
        phi_out = math.asin((math.sin(phi_new) * math.cos(d/R)) + (math.cos(phi_new) * \
                            math.sin(d/R) * math.cos(math.radians(bearing))))
        lambda_out = lambda_new + math.atan2(math.sin(math.radians(bearing)) *    \
                    math.sin(d/R) * math.cos(phi_new), math.cos(d/R) - math.sin(phi_new) * \
                    math.sin(phi_out))
        return math.degrees(phi_out), math.degrees(lambda_out)

    def shift_placefiles(self):
        filenames = glob(f"{self.placefiles_dir}/*[0-9].txt")
        for file_ in filenames:
            with open(file_, 'r', encoding='utf-8') as f: data = f.readlines()
            outfilename = f"{file_[0:file_.index('.txt')]}_shifted.txt"
            outfile = open(outfilename, 'w', encoding='utf-8')
            
            for line in data:
                new_line = line

                if self.simulation_time_shift is not None and any(x in line for x in ['Valid', 'TimeRange']):
                    new_line = self.shift_time(line)

                # Shift this line in space. Only perform if both an original and 
                # transposing radar have been specified. 
                if self.new_radar != 'None' and self.radar is not None:
                    regex = re.findall(LAT_LON_REGEX, line)
                    if len(regex) > 0:
                        idx = regex[0].index(',')
                        lat, lon = float(regex[0][0:idx]), float(regex[0][idx+1:])
                        lat_out, lon_out = self.move_point(lat, lon)
                        new_line = line.replace(regex[0], f"{lat_out}, {lon_out}")

                outfile.write(new_line)
            outfile.close()
        return

    def shift_time(self, line):
        new_line = line
        if 'Valid:' in line:
            idx = line.find('Valid:')
            valid_timestring = line[idx+len('Valid:')+1:-1] # Leave off \n character
            dt = datetime.strptime(valid_timestring, '%H:%MZ %a %b %d %Y')
            new_validstring = datetime.strftime(dt + self.simulation_time_shift,
                                                '%H:%MZ %a %b %d %Y')
            new_line = line.replace(valid_timestring, new_validstring)

        if 'TimeRange' in line:
            regex = re.findall(TIME_REGEX, line)
            dt = datetime.strptime(regex[0], '%Y-%m-%dT%H:%M:%SZ')
            new_datestring_1 = datetime.strftime(dt + self.simulation_time_shift,
                                                '%Y-%m-%dT%H:%M:%SZ')
            dt = datetime.strptime(regex[1], '%Y-%m-%dT%H:%M:%SZ')
            new_datestring_2 = datetime.strftime(dt + self.simulation_time_shift,
                                                '%Y-%m-%dT%H:%M:%SZ')
            new_line = line.replace(f"{regex[0]} {regex[1]}",
                                    f"{new_datestring_1} {new_datestring_2}")
        return new_line


    def rename_shifted_nse_placefiles(self) -> None:
        """
        making a standard name for NSE placefiles by removing the datetime info
        Example -- mlcape_2024050721-2024050722_shifted.txt -> mlcape_shifted.txt
        """
        placefiles = list(PLACEFILES_DIR.glob('*_shifted.txt'))
        for file in placefiles:
            if '-' in file.name:
                print(f'filename: {file.name}')
                parts = file.name.split('_')
                new_parts = [p for p in parts if '-' not in p]
                new_filename = '_'.join(new_parts)
                if file.name != new_filename:
                    new_filepath = PLACEFILES_DIR / new_filename
                    shutil.copy(file, new_filepath)
        
        for ob_file in ('wind','dwpt','temp','road','latest_surface_observations','latest_surface_observations_lg','latest_surface_observations_xlg'):
            original_filename = PLACEFILES_DIR / f'{ob_file}.txt'
            new_filename =  PLACEFILES_DIR / f'{ob_file}_shifted.txt'
            try:
                shutil.copy(original_filename, new_filename)
            except Exception as e:
                print(f"Error copying {original_filename} to {new_filename}: {e}")
                
                


    def datetime_object_from_timestring(self, file: str) -> datetime:
        """
        - extracts datetime info from the radar filename
        - converts it to a timezone aware datetime object in UTC
        """
        file_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S')
        utc_file_time = file_time.replace(tzinfo=pytz.UTC)
        return utc_file_time

    def remove_files_and_dirs(self):
        """
        Cleans up files and directories from the previous simulation so these datasets
        are not included in the current simulation.
        """
        dirs = [RADAR_DIR, POLLING_DIR, HODOGRAPHS_DIR]
        for directory in dirs:
            for root, dirs, files in os.walk(directory, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        return
################################################################################################
#      Initialize the app
################################################################################################

sa = RadarSimulator()
app = Dash(__name__,external_stylesheets=[dbc.themes.CYBORG],
                suppress_callback_exceptions=True)
app.title = "Radar Simulator"

################################################################################################
#     Build the layout
################################################################################################

sim_day_selection =  dbc.Col(html.Div([
                    lc.step_day,
                    dcc.Dropdown(np.arange(1,sa.days_in_month+1),7,id='start_day',clearable=False
                    ) ]))

app.layout = dbc.Container([
    # testing directory size monitoring
    dcc.Interval(id='directory_monitor', disabled=True, interval=60*60*1000),
    dcc.Interval(id='playback-clock', disabled=True, interval=60*1000, n_intervals=0),
    dcc.Store(id='model_dir_size'),
    dcc.Store(id='radar_dir_size'),
    dcc.Store(id='tradar'),
    dcc.Store(id='sim_store'),
    lc.top_section, lc.top_banner,
    dbc.Container([
    dbc.Container([
    html.Div([html.Div([ lc.step_select_time_section,lc.spacer,
        dbc.Row([
                lc.sim_year_section,lc.sim_month_section, sim_day_selection,
                lc.sim_hour_section, lc.sim_minute_section, lc.sim_duration_section,
                lc.spacer,lc.step_time_confirm])],style={'padding':'1em'}),
    ],style=lc.section_box)])
    ]),lc.spacer,lc.spacer,
        dbc.Container([
        dbc.Container([html.Div([lc.radar_select_section],style={'background-color': '#333333', 'border': '2.5px gray solid','padding':'1em'})]),
]),
        lc.spacer,
        lc.map_section, lc.transpose_section, lc.spacer_mini,
        lc.scripts_button,
    lc.status_section,
    lc.links_section,
    lc.simulation_clock, lc.radar_id, lc.bottom_section
    ])  # end of app.layout


# -------------------------------------
# ---  Radar Map section  ---
# -------------------------------------

@app.callback(
    Output('show_radar_selections', 'children'),
    [Input('graph', 'clickData')])
def display_click_data(clickData: dict) -> str:
   
    """_summary_

    Args:
        clickData (_type_): _description_

    Returns:
        _type_: _description_
    """
    if clickData is None:
        return 'No radars selected ...'
    else:
        print (clickData)
        the_link=clickData['points'][0]['customdata']
        if the_link is None:
            return 'No Website Available'
        else:
            sa.radar = the_link
            if sa.radar_list in sa.radar_list:
                return f'{sa.radar} already selected'
            if len(sa.radar_list) < sa.number_of_radars:
                sa.radar_list.append(sa.radar)
                print(sa.radar_list)
                sa.create_radar_dict()
                radar_list = ', '.join(sa.radar_list)
                return f'{radar_list}'
            if len(sa.radar_list) == sa.number_of_radars:
                sa.radar_list = sa.radar_list[1:]
                sa.radar_list.append(sa.radar)
                print(sa.radar_list)
                sa.create_radar_dict()
                radar_list = ', '.join(sa.radar_list)
                return radar_list

@app.callback(
    Output('graph-container', 'style'),
    Input('map_btn', 'n_clicks'))
def toggle_map_display(n) -> dict:
    """
    based on button click, show or hide the map by returning a css style dictionary
    to modify the associated html element
    """
    if n%2 == 0:
        return {'display': 'none'}
    return {'padding-bottom': '2px', 'padding-left': '2px','height': '80vh', 'width': '100%'}

# -------------------------------------
# ---  Transpose radar section  ---
# -------------------------------------
# Added tradar as a dcc.Store as this callback didn't seem to execute otherwise. The 
# tradar store value is not used (currently), as everything is stored in sa.whatever.
@app.callback(
    Output('tradar', 'data'),
    Input('new_radar_selection', 'value'))
def transpose_radar(value):
    """
    If a user switches from a selection BACK to "None", without this, the application 
    will not update sa.new_radar to None. Instead, it'll be the previous selection.
    Since we always evaluate "value" after every user selection, always set new_radar 
    initially to None.
    """
    sa.new_radar = 'None'

    if value != 'None':
        sa.new_radar = value
        sa.new_lat = lc.df[lc.df['radar'] == sa.new_radar]['lat'].values[0]
        sa.new_lon = lc.df[lc.df['radar'] == sa.new_radar]['lon'].values[0]
        return f'{sa.new_radar}'
    return 'None'

@app.callback(
    Output('transpose_section', 'style'),
    Input('radar_quantity', 'value'))
def toggle_transpose_display(value):
    """
    Transposing is an option only if the number of selected radars = 1
    This function will hide the transpose section if the number of radars is > 1
    """
    sa.number_of_radars = value
    while len(sa.radar_list) > sa.number_of_radars:
        sa.radar_list = sa.radar_list[1:]
    if sa.number_of_radars == 1:
        return lc.section_box
    return {'display': 'none'}

# -------------------------------------
# ---  Run Scripts button ---
# -------------------------------------

def run_hodo_script(args):
    subprocess.run(["python", HODO_SCRIPT_PATH] + args, check=True)
    return

@app.callback(
    Output('show_script_progress', 'children'),
    [Input('run_scripts', 'n_clicks')],
    prevent_initial_call=True,
    running=[
        (Output('start_year', 'disabled'), True, False),
        (Output('start_month', 'disabled'), True, False),
        (Output('start_day', 'disabled'), True, False),
        (Output('start_hour', 'disabled'), True, False),
        (Output('start_minute', 'disabled'), True, False),
        (Output('duration', 'disabled'), True, False),
        (Output('radar_quantity', 'disabled'), True, False),
        (Output('map_btn', 'disabled'), True, False),
        (Output('new_radar_selection', 'disabled'), True, False),
        (Output('run_scripts', 'disabled'), True, False),
        (Output('playback-clock', 'disabled'), True, False),
        ])
def launch_simulation(n_clicks):
    """
    This function is called when the "Run Scripts" button is clicked. It will execute the
    necessary scripts to simulate radar operations, create hodographs, and transpose placefiles.
    """
    if n_clicks == 0:
        raise PreventUpdate
    else:
        sa.scripts_progress = 'Setting up files and times'
        sa.make_simulation_times()  # determine actual event time, playback time, diff of these two

        # clean out old files and directories
        try:
            sa.remove_files_and_dirs()
        except Exception as e:
            print("Error removing files and directories: ", e)

        # based on list of selected radars, create a dictionary of radar metadata
        try:
            sa.create_radar_dict()
            #sa.create_grlevel2_cfg_file()
            sa.copy_grlevel2_cfg_file()
        except Exception as e:
            print("Error creating radar dict or config file: ", e)

        # acquire radar data for the event
        sa.scripts_progress = 'Downloading radar data ...'
        try:
            for _r, radar in enumerate(sa.radar_list):
                radar = radar.upper()
                try:
                    if sa.new_radar == 'None':
                        new_radar = radar
                    else:
                        new_radar = sa.new_radar.upper()
                except Exception as e:
                    print("Error defining new radar: ", e)
                try:
                    print(f"Nexrad Downloader - {radar}, {sa.event_start_str}, {str(sa.event_duration)}")
                    _file_list = NexradDownloader(radar, sa.event_start_str, str(sa.event_duration))
                    #sa.radar_dict[radar]['file_list'] = file_list
                    time.sleep(10)
                except Exception as e:
                    print("Error running nexrad script: ", e)
                try:
                    print(f"Munge from {radar} to {new_radar}...")
                    Munger(radar,sa.playback_start_str,sa.event_duration, sa.simulation_seconds_shift,
                           new_radar, playback_speed=1.5)
                    print(f"Munge for {new_radar} completed ...")
                    # this gives the user some radar data to poll while other scripts are running
                    UpdateDirList(new_radar, current_playback_time='None', initialize=True)

                except Exception as e:
                    print("Error running Munge from {radar} to {new_radar}: ", e)
        except Exception as e:
            print("Error running nexrad or munge scripts: ", e)
            
        sa.scripts_progress = 'Creating obs placefiles ...'
        try:
            print("Running obs script...")
            Mesowest(str(sa.lat),str(sa.lon),sa.event_start_str,str(sa.event_duration))
            print("Obs script completed")
        except Exception as e:
            print("Error running obs script: ", e)

        sa.scripts_progress = 'Creating NSE placefiles ...'
        # NSE placefiles
        try:
            print("Running NSE scripts...")
            Nse(sa.event_start_time, sa.event_duration, sa.scripts_path, sa.data_dir,
                sa.placefiles_dir)
        except Exception as e:
            print("Error running NSE scripts: ", e)

        # Since there will always be a timeshift associated with a simulation, this 
        # script needs to execute every time, even if a user doesn't select a radar
        # to transpose to. 
        run_transpose_script()
        sa.rename_shifted_nse_placefiles()
          
        sa.scripts_progress = 'Creating hodo plots ...'
        for radar, data in sa.radar_dict.items():
            try:
                asos_one = data['asos_one']
                asos_two = data['asos_two']
                print(asos_one, asos_two, radar)
            except KeyError as e:
                print("Error getting radar metadata: ", e)

            try:
                print(f'hodo script:  {radar}, {sa.new_radar}, {asos_one}, {asos_two}, {sa.simulation_seconds_shift}')
                run_hodo_script([radar, sa.new_radar, asos_one, asos_two, str(sa.simulation_seconds_shift)])
                print("Hodograph script completed ...")
            except Exception as e:
                print("Error running hodo script: ", e)
                
        sa.scripts_progress = 'Scripts completed!'

    return


# -------------------------------------
# --- Transpose placefiles in time and space
# -------------------------------------
# A time shift will always be applied in the case of a simulation. Determination of 
# whether to also perform a spatial shift occurrs within self.shift_placefiles where
# a check for sa.new_radar != None takes place. 
def run_transpose_script():
    sa.shift_placefiles()
    return

#@app.callback(
#    Output('transpose_status', 'value'),
#    Input('run_transpose_script', 'n_clicks'))
#def run_transpose_script(n_clicks):
#    if sa.new_radar == None:
#        return 100
#    if n_clicks > 0:
#        sa.shift_placefiles()
#        return 100
#    return 0

################################################################################################
# ---------------------------------------- Time Selection Summary and Callbacks ----------------
################################################################################################

@app.callback(
Output('show_time_data', 'children'),
Input('start_year', 'value'),
Input('start_month', 'value'),
Input('start_day', 'value'),
Input('start_hour', 'value'),
Input('start_minute', 'value'),
Input('duration', 'value'),
)
def get_sim(_yr, _mo, _dy, _hr, _mn, _dur):
    sa.make_simulation_times()
    line1 = f'Start: {sa.event_start_str[:-7]}Z ____ {sa.event_duration} minutes'
    return line1

@app.callback(Output('start_year', 'value'),Input('start_year', 'value'))
def get_year(start_year):
    sa.event_start_year = start_year
    return sa.event_start_year

@app.callback(
    Output('start_day', 'options'),
    [Input('start_year', 'value'), Input('start_month', 'value')])
def update_day_dropdown(selected_year, selected_month):
    _, num_days = calendar.monthrange(selected_year, selected_month)
    day_options = [{'label': str(day), 'value': day} for day in range(1, num_days+1)]
    return day_options


@app.callback(Output('start_month', 'value'),Input('start_month', 'value'))
def get_month(start_month):
    sa.event_start_month = start_month
    return sa.event_start_month

@app.callback(Output('start_day', 'value'),Input('start_day', 'value'))
def get_day(start_day):
    sa.event_start_day = start_day
    return sa.event_start_day

@app.callback(Output('start_hour', 'value'),Input('start_hour', 'value'))
def get_hour(start_hour):
    sa.event_start_hour = start_hour
    return sa.event_start_hour

@app.callback(Output('start_minute', 'value'),Input('start_minute', 'value'))
def get_minute(start_minute):
    sa.event_start_minute = start_minute
    return sa.event_start_minute

@app.callback(Output('duration', 'value'),Input('duration', 'value'))
def get_duration(duration):
    sa.event_duration = duration
    return sa.event_duration

################################################################################################
# ---------------------------------------- Clock Callbacks ----------------
################################################################################################

@app.callback(
    Output('clock-container', 'style'),
    Input('enable_sim_clock', 'n_clicks'))
def enable_simulation_clock(n: int) -> dict:
    """
    Toggles the simulation clock display on/off by returning a css style dictionary to modify
    Disabled this for now
    """
    if n < 0:
        return {'display': 'none'}
    return {'padding-bottom': '2px', 'padding-left': '2px','height': '80vh', 'width': '100%'}


@app.callback(
    Output('clock-output', 'children'),
    Input('playback-clock', 'n_intervals')
)
def update_time(_n) -> str:
    """
    If scripts are still running, provides a text status update.
    After scripts are done:
       - counter updates the playback time, and this used to update:
       - assets/hodographs.html page
       - assets/polling/KXXX/dir.list files
    """
    if sa.scripts_progress != 'Scripts completed!':
        return sa.scripts_progress
    
    #sa.playback_timer += timedelta(seconds=90)
    while sa.playback_timer < sa.playback_end_time:
        sa.playback_timer += timedelta(seconds=45)
        playback_time_str = sa.playback_timer.strftime("%Y-%m-%d %H:%M:%S UTC")
        UpdateHodoHTML(playback_time_str, initialize=False)
        if sa.new_radar != 'None':
            UpdateDirList(sa.new_radar, playback_time_str, initialize=False)
        else:
            for _r, radar in enumerate(sa.radar_list):
                UpdateDirList(radar, playback_time_str, initialize=False)
        return playback_time_str

################################################################################################
# ---------------------------------------- Call app ----------------
################################################################################################

if __name__ == '__main__':
    if lc.cloud:
        app.run_server(host="0.0.0.0", port=8050, threaded=True, debug=True, use_reloader=False)
    else:
        # Add hot reload to False. As files update during a run, page updates, and 
        # simulation dates change back to defaults causing issues with time shifting. 
        app.run(debug=True, port=8050, threaded=True, dev_tools_hot_reload=False)
 
'''
# pathname_params = dict()
# if my_settings.hosting_path is not None:
#     pathname_params["routes_pathname_prefix"] = "/"
#     pathname_params["requests_pathname_prefix"] = "/{}/".format(my_settings.hosting_path)


# Monitoring size of data and output directories for progress bar output
def directory_stats(folder):
    """Return the size of a directory. If path hasn't been created yet, returns 0."""
    num_files = 0
    total_size = 0
    if os.path.isdir(folder):
        total_size = sum(
            sum(
                os.path.getsize(os.path.join(walk_result[0], element))
                for element in walk_result[2]
            )
            for walk_result in os.walk(folder)
        )

        for _, _, files in os.walk(folder):
            num_files += len(files)

    return total_size/1024000, num_files
'''
'''
@app.callback(
    #Output('tradar', 'value'),
    Output('model_dir_size', 'data'),
    Output('radar_dir_size', 'data'),
    #Output('model_table_df', 'data'),
    [Input('directory_monitor', 'n_intervals')],
    prevent_initial_call=True)
def monitor(n):
    model_dir = directory_stats(f"{sa.data_dir}/model_data")
    radar_dir = directory_stats(f"{sa.data_dir}/radar")
    print("sa.new_radar", sa.new_radar)
    #print(model_dir)

    # Read modeldata.txt file 
    #filename = f"{sa.data_dir}/model_data/model_list.txt"
    #model_table = []
    #if os.path.exists(filename):
    #    model_listing = []
    #    with open(filename, 'r') as f: model_list = f.readlines()
    #    for line in model_list:
    #        model_listing.append(line.rsplit('/', 1)[1][:-1])
    # 
    #     df = pd.DataFrame({'Model Data': model_listing})
    #     output = df.to_dict('records')

    return model_dir[0], radar_dir[0]
'''
