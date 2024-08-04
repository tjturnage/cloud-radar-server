"""
This is the main script for the Radar Simulator application. It is a Dash application that
allows users to simulate radar operations, including the generation of radar data, placefiles, and
hodographs. The application is designed to mimic the behavior of a radar system over a
specified period, starting from a predefined date and time. It allows for the simulation of
radar data generation, including the handling of time shifts and geographical coordinates.

09 June 2024
-- More docstrings and type hints added
-- Pylinting checks and corrections

11 Jun 2024
- Trying to show Transpose radar section only if radar_quantity is 1 and radar is selected
- need to account for the possibility of a user selecting fewer radars, including 3 --> 1
"""
# from flask import Flask, render_template
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
import json
import logging
import psutil, signal
import pytz
#import pandas as pd

# from time import sleep
from dash import Dash, html, Input, Output, dcc , ctx #, callback
from dash.exceptions import PreventUpdate
# from dash import diskcache, DiskcacheManager, CeleryManager
# from uuid import uuid4
# import diskcache
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

import utils 

import mimetypes
mimetypes.add_type("text/plain", ".cfg", True)
mimetypes.add_type("text/plain", ".list", True)

# Earth radius (km)
R = 6_378_137

# Regular expressions. First one finds lat/lon pairs, second finds the timestamps.
LAT_LON_REGEX = "[0-9]{1,2}.[0-9]{1,100},[ ]{0,1}[|\\s-][0-9]{1,3}.[0-9]{1,100}"
TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

################################################################################################
# ----------------------------- Attempt to set up environment  ---------------------------------
################################################################################################
TOKEN = 'INSERT YOUR MAPBOX TOKEN HERE'

BASE_DIR = Path.cwd()
ASSETS_DIR = BASE_DIR / 'assets'
HODO_HTML_PAGE = ASSETS_DIR / 'hodographs.html'
POLLING_DIR = ASSETS_DIR / 'polling'
PLACEFILES_DIR = ASSETS_DIR / 'placefiles'
HODOGRAPHS_DIR = ASSETS_DIR / 'hodographs'
DATA_DIR = BASE_DIR / 'data'
MODEL_DIR = DATA_DIR / 'model_data'
RADAR_DIR = DATA_DIR / 'radar'
CSV_PATH = BASE_DIR / 'radars.csv'
SCRIPTS_DIR = BASE_DIR / 'scripts'
OBS_SCRIPT_PATH = SCRIPTS_DIR / 'obs_placefile.py'
HODO_SCRIPT_PATH = SCRIPTS_DIR / 'hodo_plot.py'
NEXRAD_SCRIPT_PATH = SCRIPTS_DIR / 'Nexrad.py'
L2MUNGER_FILEPATH = SCRIPTS_DIR / 'l2munger'

################################################################################################
# ----------------------------- Define class RadarSimulator  -----------------------------------
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
        self.number_of_radars = 1
        self.radar_list = []
        self.radar_dict = {}
        self.radar_files_dict = {}
        self.radar = None
        self.lat = None
        self.lon = None
        self.new_radar = 'None'
        self.new_lat = None
        self.new_lon = None
        self.scripts_progress = 'Scripts not started'
        self.current_dir = Path.cwd()
        self.define_scripts_and_assets_directories()
        self.playback_clock = None
        self.playback_clock_str = None
        self.simulation_running = False
        self.make_simulation_times()

        # This will generate a logfile. Something we'll want to turn on in the future.
        self.log = self.create_logfile()

        # self.get_radar_coordinates()

    def create_logfile(self):
        """
        Creates an initial logfile. Stored in the data dir for now. Call is 
        sa.log.info or sa.log.error or sa.log.warning or sa.log.exception
        """
        logging.basicConfig(filename=f"{self.log_dir}/logfile.txt",
                            format='%(levelname)s %(asctime)s :: %(message)s',
                            datefmt="%Y-%m-%d %H:%M:%S")
        log = logging.getLogger()
        log.setLevel(logging.DEBUG)
        return log

    def create_radar_dict(self) -> None:
        """
        Creates dictionary of radar sites and their metadata to be used in the simulation.
        """
        for _i, radar in enumerate(self.radar_list):
            self.lat = lc.df[lc.df['radar'] == radar]['lat'].values[0]
            self.lon = lc.df[lc.df['radar'] == radar]['lon'].values[0]
            asos_one = lc.df[lc.df['radar'] == radar]['asos_one'].values[0]
            asos_two = lc.df[lc.df['radar'] == radar]['asos_two'].values[0]
            self.radar_dict[radar.upper()] = {'lat': self.lat, 'lon': self.lon,
                                              'asos_one': asos_one, 'asos_two': asos_two,
                                              'radar': radar.upper(), 'file_list': []}

    def copy_grlevel2_cfg_file(self) -> None:
        """
        Ensures a grlevel2.cfg file is copied into the polling directory.
        This file is required for GR2Analyst to poll for radar data.
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
        self.log_dir = self.data_dir / 'logs'
        os.makedirs(self.log_dir, exist_ok=True)
        self.scripts_path = self.current_dir / 'scripts'
        self.obs_script_path = self.scripts_path / 'obs_placefile.py'
        self.hodo_script_path = self.scripts_path / 'hodo_plot.py'
        self.nexrad_script_path = self.scripts_path / 'Nexrad.py'
        self.l2munger_script_path = self.scripts_path / 'munger.py'
        self.nse_script_path = self.scripts_path / 'nse.py'
        self.munge_dir = self.scripts_path / 'munge'
        self.assets_dir = self.current_dir / 'assets'
        self.hodo_images = self.assets_dir / 'hodographs'
        os.makedirs(self.hodo_images, exist_ok=True)
        self.polling_dir = self.assets_dir / 'polling'
        self.placefiles_dir = self.assets_dir / 'placefiles'
        os.makedirs(self.placefiles_dir, exist_ok=True)


    def make_simulation_times(self) -> None:
        """
        playback_start_time: datetime object
            - the time the simulation starts.
            - set to (current UTC time rounded to nearest 30 minutes then minus 2hrs)
            - This is "recent enough" for GR2Analyst to poll data
        playback_timer: datetime object
            - the "current" displaced realtime during the playback
        event_start_time: datetime object
            - the historical time the actual event started.
            - based on user inputs of the event start time
        simulation_time_shift: timedelta object
            the difference between the playback start time and the event start time
        simulation_seconds_shift: int
            the difference between the playback start time and the event start time in seconds

        Variables ending with "_str" are the string representations of the datetime objects
        """
        self.playback_start = datetime.now(pytz.utc) - timedelta(hours=2)
        self.playback_start = self.playback_start.replace(second=0, microsecond=0)
        if self.playback_start.minute < 30:
            self.playback_start = self.playback_start.replace(minute=0)
        else:
            self.playback_start = self.playback_start.replace(minute=30)

        self.playback_start_str = datetime.strftime(
            self.playback_start, "%Y-%m-%d %H:%M")
        self.playback_end_time = self.playback_start + \
            timedelta(minutes=int(self.event_duration))

        self.playback_clock = self.playback_start + timedelta(seconds=600)
        self.playback_clock_str = datetime.strftime(
            self.playback_clock, "%Y-%m-%d %H:%M")

        self.event_start_time = datetime(self.event_start_year, self.event_start_month,
                                         self.event_start_day, self.event_start_hour,
                                         self.event_start_minute, second=0,
                                         tzinfo=timezone.utc)
        self.simulation_time_shift = self.playback_start - self.event_start_time
        self.simulation_seconds_shift = round(
            self.simulation_time_shift.total_seconds())
        self.event_start_str = datetime.strftime(
            self.event_start_time, "%Y-%m-%d %H:%M")

    def get_days_in_month(self) -> None:
        """
        Helper function to determine number of days to display in the dropdown
        """
        self.days_in_month = calendar.monthrange(
            self.event_start_year, self.event_start_month)[1]

    def get_timestamp(self, file: str) -> float:
        """
        - extracts datetime info from the radar filename
        - returns a datetime timestamp (epoch seconds) object
        """
        file_epoch_time = datetime.strptime(
            file[4:19], '%Y%m%d_%H%M%S').timestamp()
        return file_epoch_time

    def move_point(self, plat, plon):
        # radar1_lat, radar1_lon, radar2_lat, radar2_lon, lat, lon
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

        a = math.sin(d_phi/2)**2 + (math.cos(phi1) *
                                    math.cos(phi2) * math.sin(d_lambda/2)**2)
        a = _clamp(a, 0, a)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = R * c

        # Compute the bearing
        y = math.sin(d_lambda) * math.cos(phi2)
        x = (math.cos(phi1) * math.sin(phi2)) - (math.sin(phi1) * math.cos(phi2) *
                                                 math.cos(d_lambda))
        theta = math.atan2(y, x)
        bearing = (math.degrees(theta) + 360) % 360

        # Apply this distance and bearing to the new radar location
        phi_new, lambda_new = math.radians(
            self.new_lat), math.radians(self.new_lon)
        phi_out = math.asin((math.sin(phi_new) * math.cos(d/R)) + (math.cos(phi_new) *
                            math.sin(d/R) * math.cos(math.radians(bearing))))
        lambda_out = lambda_new + math.atan2(math.sin(math.radians(bearing)) *
                                             math.sin(d/R) * math.cos(phi_new),
                                             math.cos(d/R) - math.sin(phi_new) * math.sin(phi_out))
        return math.degrees(phi_out), math.degrees(lambda_out)

    def shift_placefiles(self) -> None:
        """
        # While the _shifted placefiles should be purged for each run, just ensure we're
        # only querying the "original" placefiles to shift (exclude any with _shifted.txt)        
        """
        filenames = glob(f"{self.placefiles_dir}/*.txt")
        filenames = [x for x in filenames if "shifted" not in x]
        for file_ in filenames:
            with open(file_, 'r', encoding='utf-8') as f:
                data = f.readlines()
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
                        lat, lon = float(regex[0][0:idx]), float(
                            regex[0][idx+1:])
                        lat_out, lon_out = self.move_point(lat, lon)
                        new_line = line.replace(
                            regex[0], f"{lat_out}, {lon_out}")

                outfile.write(new_line)
            outfile.close()

    def shift_time(self, line: str) -> str:
        """
        Shifts the time-associated lines in a placefile.
        These look for 'Valid' and 'TimeRange'.
        """
        new_line = line
        if 'Valid:' in line:
            idx = line.find('Valid:')
            # Leave off \n character
            valid_timestring = line[idx+len('Valid:')+1:-1]
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


    def datetime_object_from_timestring(self, file: str) -> datetime:
        """
        - extracts datetime info from the radar filename
        - converts it to a timezone aware datetime object in UTC
        """
        file_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S')
        utc_file_time = file_time.replace(tzinfo=pytz.UTC)
        return utc_file_time

    def remove_files_and_dirs(self) -> None:
        """
        Cleans up files and directories from the previous simulation so these datasets
        are not included in the current simulation.
        """
        dirs = [RADAR_DIR, POLLING_DIR, HODOGRAPHS_DIR, MODEL_DIR]
        for directory in dirs:
            for root, dirs, files in os.walk(directory, topdown=False):
                for name in files:
                    if name != 'grlevel2.cfg':
                        os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))

################################################################################################
# ----------------------------- Initialize the app  --------------------------------------------
################################################################################################


sa = RadarSimulator()
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG],
           suppress_callback_exceptions=True)
app.title = "Radar Simulator"

################################################################################################
# ----------------------------- Build the layout  ---------------------------------------------
################################################################################################

sim_day_selection = dbc.Col(html.Div([
    lc.step_day,
    dcc.Dropdown(np.arange(1, sa.days_in_month+1), 7, id='start_day', clearable=False)]))

app.layout = dbc.Container([
    # testing directory size monitoring
    dcc.Interval(id='directory_monitor', disabled=False, interval=2*1000),
    dcc.Interval(id='playback_clock', disabled=True, interval=60*1000),
    # dcc.Store(id='model_dir_size'),
    # dcc.Store(id='radar_dir_size'),
    dcc.Store(id='tradar'),
    dcc.Store(id='dummy'),
    dcc.Store(id='sim_store'),
    lc.top_section, lc.top_banner,
    dbc.Container([
        dbc.Container([
            html.Div([html.Div([lc.step_select_time_section, lc.spacer,
                            dbc.Row([
                                lc.sim_year_section, lc.sim_month_section, sim_day_selection,
                                lc.sim_hour_section, lc.sim_minute_section, lc.sim_duration_section,
                                lc.spacer, lc.step_time_confirm])], style={'padding': '1em'}),
                      ], style=lc.section_box)])
    ]), lc.spacer,
    lc.full_radar_select_section, lc.spacer_mini,
    lc.map_section,
    lc.full_transpose_section,
    lc.scripts_button,
    lc.status_section,
    lc.spacer,lc.toggle_placefiles_btn,
    lc.full_links_section, lc.spacer,
    lc.simulation_playback_section,
    lc.radar_id, lc.bottom_section
])  # end of app.layout

################################################################################################
# ----------------------------- Radar map section  ---------------------------------------------
################################################################################################

@app.callback(
    [Output('show_radar_selection_feedback', 'children'),
    Output('confirm_radars_btn', 'children'),
    Output('confirm_radars_btn', 'disabled')],
    Input('radar_quantity', 'value'),
    Input('graph', 'clickData'),
    prevent_initial_call=True
    )
def display_click_data(quant_str: str, click_data: dict):
    """
    Any time a radar site is clicked, 
    this function will trigger and update the radar list.
    """
    # initially have to make radar selections and can't finalize
    select_action = 'Make'
    btn_deactivated = True

    triggered_id = ctx.triggered_id
    if triggered_id == 'radar_quantity':
        sa.number_of_radars = int(quant_str[0:1])
        sa.radar_list = []
        sa.radar_dict = {}
        return f'Use map to select {quant_str}', f'{select_action} selections', True
    try:
        sa.radar = click_data['points'][0]['customdata']
        print(f"Selected radar: {sa.radar}")
    except (KeyError, IndexError, TypeError):
        return 'No radar selected ...', f'{select_action} selections', True

    sa.radar_list.append(sa.radar)
    if len(sa.radar_list) > sa.number_of_radars:
        sa.radar_list = sa.radar_list[-sa.number_of_radars:]
    if len(sa.radar_list) == sa.number_of_radars:
        select_action = 'Finalize'
        btn_deactivated = False

    print(f"Radar list: {sa.radar_list}")
    listed_radars = ', '.join(sa.radar_list)
    return listed_radars, f'{select_action} selections', btn_deactivated


@app.callback(
    [Output('graph-container', 'style'),
     Output('map_btn', 'children')],
    Input('map_btn', 'n_clicks'),
    Input('confirm_radars_btn', 'n_clicks'))
def toggle_map_display(map_n, confirm_n) -> dict:
    """
    based on button click, show or hide the map by returning a css style dictionary
    to modify the associated html element
    """
    total_clicks = map_n + confirm_n
    if total_clicks % 2 == 0:
        return {'display': 'none'}, 'Show Radar Map'
    return lc.map_section_style, 'Hide Radar Map'

@app.callback(
    [Output('full_transpose_section_id', 'style'),
    Output('skip_transpose_id', 'style'),
    Output('allow_transpose_id', 'style'),
    Output('run_scripts_btn', 'disabled')
    ], Input('confirm_radars_btn', 'n_clicks'),
    Input('radar_quantity', 'value'),
    prevent_initial_call=True)
def finalize_radar_selections(clicks: int, _quant_str: str) -> dict:
    """
    This will display the transpose section on the page if the user has selected a single radar.
    """
    disp_none = {'display': 'none'}
    #script_style = {'padding': '1em', 'vertical-align': 'middle'}
    triggered_id = ctx.triggered_id
    if triggered_id == 'radar_quantity':
        return disp_none, disp_none, disp_none, True
    if clicks > 0:
        if sa.number_of_radars == 1 and len(sa.radar_list) == 1:
            return lc.section_box_pad, disp_none, {'display': 'block'}, False
    return lc.section_box_pad, {'display': 'block'}, disp_none, False

################################################################################################
# ----------------------------- Transpose radar section  ---------------------------------------
################################################################################################

@app.callback(
    Output('tradar', 'data'),
    Input('new_radar_selection', 'value'))
def transpose_radar(value):
    """
    If a user switches from a selection BACK to "None", without this, the application 
    will not update sa.new_radar to None. Instead, it'll be the previous selection.
    Since we always evaluate "value" after every user selection, always set new_radar 
    initially to None.
    
    Added tradar as a dcc.Store as this callback didn't seem to execute otherwise. The
    tradar store value is not used (currently), as everything is stored in sa.whatever.
    """
    sa.new_radar = 'None'

    if value != 'None':
        sa.new_radar = value
        sa.new_lat = lc.df[lc.df['radar'] == sa.new_radar]['lat'].values[0]
        sa.new_lon = lc.df[lc.df['radar'] == sa.new_radar]['lon'].values[0]
        return f'{sa.new_radar}'
    return 'None'

################################################################################################
# ----------------------------- Run Scripts button  --------------------------------------------
################################################################################################

def query_radar_files():
    """
    Get the radar files from the AWS bucket. This is a preliminary step to build the progess bar.
    """
    # Need to reset the expected files dictionary with each call. Otherwise, if a user
    # cancels a request, the previously-requested files will still be in the dictionary.
    sa.radar_files_dict = {}
    for _r, radar in enumerate(sa.radar_list):
        radar = radar.upper()
        args = [radar, f'{sa.event_start_str}', str(sa.event_duration), str(False)]
        sa.log.info(f"Passing {args} to Nexrad.py")
        results = utils.exec_script(sa.nexrad_script_path, args)
        if results['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            sa.log.warning(f"User cancelled query_radar_files()")
            break

        json_data = results['stdout'].decode('utf-8')
        sa.log.info(f"Nexrad.py returned with {json_data}")
        sa.radar_files_dict.update(json.loads(json_data))

    return results


def run_hodo_script(args) -> None:
    """
    Runs the hodo script with the necessary arguments. 
    radar: str - the original radar, tells script where to find raw radar data
    sa.new_radar: str - Either 'None' or the new radar to transpose to
    asos_one: str - the first ASOS station to use for hodographs
    asos_two: str - the second ASOS station to use for hodographs as a backup
    sa.simulation_seconds_shift: str - time shift (seconds) between the event
    start and playback start
    """
    print(args)
    subprocess.run(["python", HODO_SCRIPT_PATH] + args, check=True)


def call_function(func, *args, **kwargs):
    if len(args) > 0: 
        sa.log.info(f"Sending {args[1]} to {args[0]}")

    result = func(*args, **kwargs)

    if len(result['stderr']) > 0: 
        sa.log.error(result['stderr'].decode('utf-8'))
    if 'exception' in result:
        sa.log.error(f"Exception {result['exception']} occurred in {func.__name__}")
    return result


def run_with_cancel_button():
    """
    This version of the script-launcher trying to work in cancel button
    """
    sa.scripts_progress = 'Setting up files and times'
    # determine actual event time, playback time, diff of these two
    sa.make_simulation_times()

    # clean out old files and directories
    try:
        sa.remove_files_and_dirs()
    except Exception as e:
        sa.log.exception("Error removing files and directories: ", exc_info=True)

    # based on list of selected radars, create a dictionary of radar metadata
    try:
        sa.create_radar_dict()
        sa.copy_grlevel2_cfg_file()
    except Exception as e:
        sa.log.exception("Error creating radar dict or config file: ", exc_info=True)

    # Create initial dictionary of expected radar files
    if len(sa.radar_list) > 0:
        res = call_function(query_radar_files)
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            return

        for _r, radar in enumerate(sa.radar_list):
            radar = radar.upper()
            try:
                if sa.new_radar == 'None':
                    new_radar = radar
                else:
                    new_radar = sa.new_radar.upper()
            except Exception as e:
                sa.log.exception("Error defining new radar: ", exc_info=True)
   
            # Radar download
            args = [radar, str(sa.event_start_str), str(sa.event_duration), str(True)]
            res = call_function(utils.exec_script, sa.nexrad_script_path, args)
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
                return

            # Munger
            args = [radar, str(sa.playback_start_str), str(sa.event_duration), 
                    str(sa.simulation_seconds_shift), new_radar]
            res = call_function(utils.exec_script, sa.l2munger_script_path, args)
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]: 
                return
      
            # this gives the user some radar data to poll while other scripts are running
            try:
                UpdateDirList(new_radar, 'None', initialize=True)
            except Exception as e:
                print(f"Error with UpdateDirList ", e)
                sa.log.exception(f"Error with UpdateDirList ", exc_info=True)

    # Surface observations
    args = [str(sa.lat), str(sa.lon), sa.event_start_str, str(sa.event_duration)]
    res = call_function(utils.exec_script, sa.obs_script_path, args)
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # NSE placefiles
    args = [str(sa.event_start_time), str(sa.event_duration), str(sa.scripts_path), 
            str(sa.data_dir), str(sa.placefiles_dir)]
    res = call_function(utils.exec_script, sa.nse_script_path, args)
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # Since there will always be a timeshift associated with a simulation, this
    # script needs to execute every time, even if a user doesn't select a radar
    # to transpose to.
    sa.log.info(f"Entering function run_transpose_script")
    run_transpose_script()

    # Hodographs 
    for radar, data in sa.radar_dict.items():
        try:
            asos_one = data['asos_one']
            asos_two = data['asos_two']
        except KeyError as e:
            sa.log.exception("Error getting radar metadata: ", exc_info=True)
    
        # Execute hodograph script
        args = [radar, sa.new_radar, asos_one, asos_two, str(sa.simulation_seconds_shift)]
        res = call_function(utils.exec_script, sa.hodo_script_path, args)
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            return

        try:
            UpdateHodoHTML('None')
        except Exception as e:
            print("Error updating hodo html: ", e)
            sa.log.exception("Error updating hodo html: ", exc_info=True)

@app.callback(
    Output('show_script_progress', 'children', allow_duplicate=True),
    [Input('run_scripts_btn', 'n_clicks')],
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
        (Output('run_scripts_btn', 'disabled'), True, False),
        (Output('playback_clock', 'disabled'), True, False),
        (Output('confirm_radars_btn', 'disabled'), True, False), # added radar confirm btn
        (Output('start_simulation_btn', 'disabled'), True, False), # add start sim btn
        (Output('cancel_scripts', 'disabled'), False, True),
    ])
def launch_simulation(n_clicks) -> None:
    """
    This function is called when the "Run Scripts" button is clicked. It will execute the
    necessary scripts to simulate radar operations, create hodographs, and transpose placefiles.
    """
    if n_clicks == 0:
        raise PreventUpdate
    else:
        run_with_cancel_button()
 
################################################################################################
# ----------------------------- Monitoring and reporting script status  ------------------------
################################################################################################

@app.callback(
    Output('dummy', 'data'),
    [Input('cancel_scripts', 'n_clicks')],
    prevent_initial_call=True)
def cancel_scripts(n_clicks) -> None:
    """
    This function is called when the "Cancel Scripts" button is clicked. It will cancel all
    Args:
        n_clicks (int): incremented whenever the "Cancel Scripts" button is clicked
    """
    if n_clicks > 0:
        utils.cancel_all(sa)


@app.callback(
    Output('radar_status', 'value'),
    Output('hodo_status', 'value'),
    Output('transpose_status', 'value'),
    Output('obs_placefile_status', 'children'),
    Output('model_table', 'data'),
    Output('model_status_warning', 'children'),
    Output('show_script_progress', 'children', allow_duplicate=True),
    [Input('directory_monitor', 'n_intervals')],
    prevent_initial_call=True
)
def monitor(_n):
    """
    This function is called every second by the directory_monitor interval. It checks the
    status of the radar and hodograph scripts and reports the status to the user.
    """

    # Need to put this list and utils.cancel_all scripts_list into __init__ or somewhere
    # similar. Finds running processes, determines if they're associated with this app, 
    # and outputs text at the bottom. 
    scripts_list = ["Nexrad.py", "nse.py", "get_data.py", "process.py", 
                    "hodo_plot.py", "munger.py", "wgrib2", "obs_placefile.py"]
    processes = utils.get_app_processes()
    screen_output = ""
    seen_scripts = []
    for p in processes:
        name = p['cmdline'][1].rsplit('/', 1)
        if len(name) > 1: name = name[1]
        if p['name'] == 'wgrib2':
            name = 'wgrib2'
      
        if name in scripts_list and name not in seen_scripts:
            runtime = time.time() - p['create_time']
            #screen_output += f"{name}: {p['status']} for {round(runtime,1)} s. "
            screen_output += f"{name}: running for {round(runtime,1)} s. "
        seen_scripts.append(name)

    # Radar file download status
    radar_dl_completion, radar_files = utils.radar_monitor(sa)

    # Radar mungering/transposing status
    munger_completion = utils.munger_monitor(sa)

    # Surface placefile status
    placefile_completion = utils.surface_placefile_monitor(sa)
    placefile_status_string = ''
    if placefile_completion > 99:
        placefile_status_string = 'Surface placefiles done!'

    # Hodographs. Currently hard-coded to expect 2 files for every radar and radar file.
    num_hodograph_images = len(glob(f"{sa.hodo_images}/*.png"))
    hodograph_completion = 0
    if len(radar_files) > 0:
        hodograph_completion = 100 * \
            (num_hodograph_images / (2*len(radar_files)))

    # NSE placefiles
    model_list, model_warning = utils.nse_status_checker(sa)
    return (radar_dl_completion, hodograph_completion, munger_completion, 
            placefile_status_string, model_list, model_warning, screen_output)

################################################################################################
# ----------------------------- Transpose placefiles in time and space  ------------------------
################################################################################################
# A time shift will always be applied in the case of a simulation. Determination of
# whether to also perform a spatial shift occurrs within self.shift_placefiles where
# a check for sa.new_radar != None takes place.

def run_transpose_script() -> None:
    """
    Wrapper function to the shift_placefiles script
    """
    sa.shift_placefiles()

################################################################################################
# ----------------------------- Toggle Placefiles Section --------------------------------------
################################################################################################

@app.callback(
    [Output('placefiles_section', 'style'),
     Output('toggle_placefiles_section_btn', 'children')],
    Input('toggle_placefiles_section_btn', 'n_clicks'),
    prevent_initial_call=True)
def toggle_placefiles_section(n) -> dict:
    """
    based on button click, show or hide the map by returning a css style dictionary
    to modify the associated html element
    """
    btn_text = 'Links Section'
    if n % 2 == 1:
        return {'display': 'none'}, f'Show {btn_text}'
    return {'display': 'block'}, f'Hide {btn_text}'

################################################################################################
# ----------------------------- Clock Callbacks  -----------------------------------------------
################################################################################################


@app.callback(
    Output('start_simulation_btn', 'children'),
    Output('playback_clock', 'disabled'),
    Output('clock_readout', 'children'),
    Input('start_simulation_btn', 'n_clicks'),
    Input('playback_clock', 'n_intervals'),
    prevent_initial_call=True
    )
def manage_clock_(nclick, _n_intervals) -> tuple:
    """     
    Enables/disables interval component that elapses the playback time

    If scripts are still running, provides a text status update.
    After scripts are done:
       - counter updates the playback time, and this used to update:
       - assets/hodographs.html page
       - assets/polling/KXXX/dir.list files
    """
    btn_text = 'Simulation Playback'
    start_btn = f'Start {btn_text}'
    pause_btn = f'Pause {btn_text}'
    paused_text = f'{btn_text} Paused at {sa.playback_clock_str}'
    running_text = f'{btn_text} Running at {sa.playback_clock_str}'
    completed_text = 'Simulation Complete!'
    triggered_id = ctx.triggered_id
    
    if triggered_id == 'start_simulation_btn':
        if nclick == 0:
            return start_btn, True, 'Simulation not started'
        if nclick % 2 == 1:
            return pause_btn, False, running_text
        return start_btn, True, paused_text

    sa.playback_clock += timedelta(seconds=60)
    if sa.playback_clock < sa.playback_end_time:
        sa.playback_clock_str = sa.playback_clock.strftime("%Y-%m-%d %H:%M")
        UpdateHodoHTML(sa.playback_clock_str)
        if sa.new_radar != 'None':
            UpdateDirList(sa.new_radar, sa.playback_clock_str)
        else:
            for _r, radar in enumerate(sa.radar_list):
                UpdateDirList(radar,sa.playback_clock_str)
        return pause_btn, False, running_text
    return completed_text, True, completed_text
            

################################################################################################
# ----------------------------- Time Selection Summary and Callbacks  --------------------------
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
def get_sim(_yr, _mo, _dy, _hr, _mn, _dur) -> str:
    """
    Changes to any of the Inputs above will trigger this callback function to update
    the time summary displayed on the page. Variables already have been stored in sa
    object for use in scripts so don't need to be explicitly returned here.
    """
    sa.make_simulation_times()
    line1 = f'Start: {sa.event_start_str}Z ____ {sa.event_duration} minutes'
    return line1


@app.callback(Output('start_year', 'value'), Input('start_year', 'value'))
def get_year(start_year) -> int:
    """
    Updates the start year variable in the sa object
    """
    sa.event_start_year = start_year
    return sa.event_start_year


@app.callback(
    Output('start_day', 'options'),
    [Input('start_year', 'value'), Input('start_month', 'value')])
def update_day_dropdown(selected_year, selected_month):
    """
    Updates the day dropdown based on the selected year and month
    """
    _, num_days = calendar.monthrange(selected_year, selected_month)
    day_options = [{'label': str(day), 'value': day}
                   for day in range(1, num_days+1)]
    return day_options


@app.callback(Output('start_month', 'value'), Input('start_month', 'value'))
def get_month(start_month) -> int:
    """
    Updates the start month variable in the sa object
    """
    sa.event_start_month = start_month
    return sa.event_start_month


@app.callback(Output('start_day', 'value'), Input('start_day', 'value'))
def get_day(start_day) -> int:
    """
    Updates the start day variable in the sa object
    """
    sa.event_start_day = start_day
    return sa.event_start_day


@app.callback(Output('start_hour', 'value'), Input('start_hour', 'value'))
def get_hour(start_hour) -> int:
    """
    Updates the start hour variable in the sa object
    """
    sa.event_start_hour = start_hour
    return sa.event_start_hour


@app.callback(Output('start_minute', 'value'), Input('start_minute', 'value'))
def get_minute(start_minute) -> int:
    """
    Updates the start minute variable in the sa object
    """
    sa.event_start_minute = start_minute
    return sa.event_start_minute


@app.callback(Output('duration', 'value'), Input('duration', 'value'))
def get_duration(duration) -> int:
    """
    Updates the event duration (in minutes) in the sa object
    """
    sa.event_duration = duration
    return sa.event_duration

################################################################################################
# ----------------------------- Start app  -----------------------------------------------------
################################################################################################

if __name__ == '__main__':
    if lc.cloud:
        app.run_server(host="0.0.0.0", port=8050, threaded=True, debug=True, use_reloader=False,
                       dev_tools_hot_reload=False)
    else:
        # Add hot reload to False. As files update during a run, page updates, and
        # simulation dates change back to defaults causing issues with time shifting.
        app.run(debug=True, port=8050, threaded=True,
                dev_tools_hot_reload=False)

'''

@app.callback(
    Output('start_simulation_btn', 'children'),
    Output('playback_clock', 'disabled'),
    Output('clock_output', 'children'),
    Input('start_simulation_btn', 'n_clicks'),
    prevent_initial_call=True)
def enable_simulation_clock(n: int) -> tuple:
    """
    Toggles the simulation clock display on/off by returning a css style dictionary to modify
    Disabled this for now
    """
    btn_text = 'Simulation Playback'
    if n > 0:
        if n % 2 == 1:
            return f'Pause {btn_text}', False,  f'{btn_text} Running at {sa.playback_clock_str}'
        return f'Start {btn_text}', True, f'{btn_text} Paused at {sa.playback_clock_str}'
    return f'Start {btn_text}', True, 'Simulation Not Started'


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