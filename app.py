"""
This is the main script for the Radar Simulator application. It is a Dash application that
allows users to simulate radar operations, including the generation of radar data, placefiles, and
hodographs. The application is designed to mimic the behavior of a radar system over a
specified period, starting from a predefined date and time. It allows for the simulation of
radar data generation, including the handling of time shifts and geographical coordinates.

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
import mimetypes
import psutil, signal
import pytz
#import pandas as pd

# from time import sleep
from dash import Dash, html, Input, Output, dcc, ctx, State #, callback
from dash.exceptions import PreventUpdate
# from dash import diskcache, DiskcacheManager, CeleryManager
# from uuid import uuid4
# import diskcache
import numpy as np
from botocore.client import Config
# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc
import config 
from config import app

import layout_components as lc
from scripts.obs_placefile import Mesowest
from scripts.Nexrad import NexradDownloader
from scripts.munger import Munger
from scripts.update_dir_list import UpdateDirList
from scripts.update_hodo_page import UpdateHodoHTML
from scripts.nse import Nse

import utils
mimetypes.add_type("text/plain", ".cfg", True)
mimetypes.add_type("text/plain", ".list", True)

# Earth radius (km)
R = 6_378_137

# Regular expressions. First one finds lat/lon pairs, second finds the timestamps.
LAT_LON_REGEX = "[0-9]{1,2}.[0-9]{1,100},[ ]{0,1}[|\\s-][0-9]{1,3}.[0-9]{1,100}"
TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
#TOKEN = 'INSERT YOUR MAPBOX TOKEN HERE'

# Configure logging
"""
Idea is to move all of these functions to some other utility script within the main dir
"""
def create_logfile(LOG_DIR):
    """
    Generate the main logfile for the download and processing scripts. 
    """
    logging.basicConfig(
        filename=f'{LOG_DIR}/scripts.txt',  # Log file location
        level=logging.INFO,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(levelname)s %(asctime)s :: %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def copy_grlevel2_cfg_file(cfg) -> None:
    """
    Ensures a grlevel2.cfg file is copied into the polling directory.
    This file is required for GR2Analyst to poll for radar data.
    """
    source = f"{cfg['BASE_DIR']}/grlevel2.cfg"
    destination = f"{cfg['POLLING_DIR']}/grlevel2.cfg"
    try:
        shutil.copyfile(source, destination)
    except Exception as e:
        print(f"Error copying {source} to {destination}: {e}")

def remove_files_and_dirs(cfg) -> None:
    """
    Cleans up files and directories from the previous simulation so these datasets
    are not included in the current simulation.
    """
    dirs = [cfg['RADAR_DIR'], cfg['POLLING_DIR'], cfg['HODOGRAPHS_DIR'], cfg['MODEL_DIR'],
            cfg['PLACEFILES_DIR']]
    for directory in dirs:
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                if name != 'grlevel2.cfg':
                    os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

def date_time_string(dt) -> str:
    """
    Converts a datetime object to a string.
    """
    return datetime.strftime(dt, "%Y-%m-%d %H:%M")

def make_simulation_times(sa) -> dict:
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

    sa['playback_start'] = datetime.now(pytz.utc) - timedelta(hours=2)
    sa['playback_start'] = sa['playback_start'].replace(second=0, microsecond=0)
    if sa['playback_start'].minute < 30:
        sa['playback_start'] = sa['playback_start'].replace(minute=0)
    else:
        sa['playback_start'] = sa['playback_start'].replace(minute=30)

    sa['playback_start_str'] = date_time_string(sa['playback_start'])

    sa['playback_end'] = sa['playback_start'] + timedelta(minutes=int(sa['event_duration']))
    sa['playback_end_str'] = date_time_string(sa['playback_end'])

    sa['playback_clock'] = sa['playback_start'] + timedelta(seconds=600)
    sa['playback_clock_str'] = date_time_string(sa['playback_clock'])

    sa['event_start_time'] = datetime(sa['event_start_year'], sa['event_start_month'],
                                      sa['event_start_day'], sa['event_start_hour'],
                                      sa['event_start_minute'], second=0,
                                      tzinfo=timezone.utc)
    # a timedelta object is not JSON serializable, so cannot be included in the output 
    # dictionary stored in the dcc.Store object. All references to simulation_time_shift
    # will need to use the simulation_seconds_shift reference instead.
    simulation_time_shift = sa['playback_start'] - sa['event_start_time']
    sa['simulation_seconds_shift'] = round(simulation_time_shift.total_seconds())
    sa['event_start_str'] = date_time_string(sa['event_start_time'])
    increment_list = []
    for t in range(0, int(sa['event_duration']/5) + 1 , 1):
        new_time = sa['playback_start'] + timedelta(seconds=t*300)
        new_time_str = date_time_string(new_time)
        increment_list.append(new_time_str)

    sa['playback_dropdown_dict'] = [{'label': increment, 'value': increment} for increment in increment_list]
    return sa

def create_radar_dict(sa) -> dict:
    """
    Creates dictionary of radar sites and their metadata to be used in the simulation.
    """
    for _i, radar in enumerate(sa['radar_list']):
        sa['lat'] = lc.df[lc.df['radar'] == radar]['lat'].values[0]
        sa['lon'] = lc.df[lc.df['radar'] == radar]['lon'].values[0]
        asos_one = lc.df[lc.df['radar'] == radar]['asos_one'].values[0]
        asos_two = lc.df[lc.df['radar'] == radar]['asos_two'].values[0]
        sa['radar_dict'][radar.upper()] = {'lat': sa['lat'], 'lon': sa['lon'],
                                            'asos_one': asos_one, 'asos_two': asos_two,
                                            'radar': radar.upper(), 'file_list': []}

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
        self.playback_dropdown_dict = {}
        self.radar_dict = {}
        self.radar_files_dict = {}
        self.radar = None
        self.lat = None
        self.lon = None
        self.new_radar = 'None'
        self.new_lat = None
        self.new_lon = None
        self.scripts_progress = 'Scripts not started'
        self.base_dir = Path.cwd()
        self.playback_initiated = False
        self.playback_speed = 1.0
        self.playback_start = 'Not Ready'
        self.playback_end = 'Not Ready'
        self.playback_start_str = 'Not Ready'
        self.playback_end_str = 'Not Ready'
        self.playback_current_time = 'Not Ready'
        self.playback_clock = None
        self.playback_clock_str = None
        self.simulation_running = False
        self.playback_paused = False
        #self.make_simulation_times()
        # This will generate a logfile. Something we'll want to turn on in the future.
        self.log = self.create_logfile()
        #UpdateHodoHTML('None', '', '')  # set up the hodo page with no images
        
    def create_logfile(self):
        """
        Creates an initial logfile. Stored in the data dir for now. Call is 
        sa.log.info or sa.log.error or sa.log.warning or sa.log.exception
        """
        os.makedirs(config.LOG_DIR, exist_ok=True)
        logging.basicConfig(filename=f"{config.LOG_DIR}/logfile.txt",
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

    def copy_grlevel2_cfg_file(self, cfg) -> None:
        """
        Ensures a grlevel2.cfg file is copied into the polling directory.
        This file is required for GR2Analyst to poll for radar data.
        """
        source = f"{cfg['BASE_DIR']}/grlevel2.cfg"
        destination = f"{cfg['POLLING_DIR']}/grlevel2.cfg"
        try:
            shutil.copyfile(source, destination)
        except Exception as e:
            print(f"Error copying {source} to {destination}: {e}")

    def date_time_string(self,dt) -> str:
        """
        Converts a datetime object to a string.
        """
        return datetime.strftime(dt, "%Y-%m-%d %H:%M")

    def date_time_object(self,dt_str) -> datetime:
        """
        Converts a string to a timezone aware datetime object.
        """
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        dt.replace(tzinfo=pytz.UTC)
        return dt

    def timestamp_from_string(self,dt_str) -> float:
        """
        Converts a string to a timestamp.
        """
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").timestamp()

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

        self.playback_start_str = self.date_time_string(self.playback_start)

        self.playback_end = self.playback_start + \
            timedelta(minutes=int(self.event_duration))
        self.playback_end_str = self.date_time_string(self.playback_end)

        self.playback_clock = self.playback_start + timedelta(seconds=600)
        self.playback_clock_str = self.date_time_string(self.playback_clock)

        self.event_start_time = datetime(self.event_start_year, self.event_start_month,
                                         self.event_start_day, self.event_start_hour,
                                         self.event_start_minute, second=0,
                                         tzinfo=timezone.utc)
        self.simulation_time_shift = self.playback_start - self.event_start_time
        self.simulation_seconds_shift = round(
            self.simulation_time_shift.total_seconds())
        self.event_start_str = self.date_time_string(self.event_start_time)
        increment_list = []
        for t in range(0, int(self.event_duration/5) + 1 , 1):
            new_time = self.playback_start + timedelta(seconds=t*300)
            new_time_str = self.date_time_string(new_time)
            increment_list.append(new_time_str)

        self.playback_dropdown_dict = [{'label': increment, 'value': increment} for increment in increment_list]

    def change_playback_time(self,dseconds) -> str:
        """
        This function is called by the playback_clock interval component. It updates the playback
        time and checks if the simulation is complete. If so, it will stop the interval component.
        """
        self.playback_clock += timedelta(seconds=dseconds * self.playback_speed)
        if self.playback_start < self.playback_clock < self.playback_end:
            self.playback_clock_str = self.date_time_string(self.playback_clock)
        elif self.playback_clock >= self.playback_end:
            self.playback_clock_str = self.playback_end_str
        else:
            self.playback_clock_str = self.playback_start_str
        return self.playback_clock_str


    #def get_days_in_month(self) -> None:
    #    """
    #    Helper function to determine number of days to display in the dropdown
    #    """
    #    self.days_in_month = calendar.monthrange(
    #        self.event_start_year, self.event_start_month)[1]

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

    def shift_placefiles(self, PLACEFILES_DIR) -> None:
        """
        # While the _shifted placefiles should be purged for each run, just ensure we're
        # only querying the "original" placefiles to shift (exclude any with _shifted.txt)        
        """
        filenames = glob(f"{PLACEFILES_DIR}/*.txt")
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


    def datetime_object_from_timestring(self, dt_str: str) -> datetime:
        """
        - extracts datetime info from the radar filename
        - converts it to a timezone aware datetime object in UTC
        """
        file_time = datetime.strptime(dt_str, '%Y%m%d_%H%M%S')
        utc_file_time = file_time.replace(tzinfo=pytz.UTC)
        return utc_file_time

    def remove_files_and_dirs(self, cfg) -> None:
        """
        Cleans up files and directories from the previous simulation so these datasets
        are not included in the current simulation.
        """
        dirs = [cfg['RADAR_DIR'], cfg['POLLING_DIR'], cfg['HODOGRAPHS_DIR'], cfg['MODEL_DIR'],
                cfg['PLACEFILES_DIR']]
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

################################################################################################
# ----------------------------- Build the layout  ---------------------------------------------
################################################################################################
################################################################################################
################################################################################################
################################################################################################
################################################################################################
playback_time_options = dbc.Col(html.Div([
    dcc.Dropdown(options={'label': 'Sim not started', 'value': ''}, id='change_time', 
                 disabled=True, clearable=False)]))

playback_time_options_col = dbc.Col(html.Div([lc.change_playback_time_label, lc.spacer_mini,
                                              playback_time_options]))

playback_controls = dbc.Container(
    html.Div([dbc.Row([lc.playback_speed_col,lc.playback_status_box,
                       playback_time_options_col])]))

simulation_playback_section = dbc.Container(
    dbc.Container(
    html.Div([lc.playback_banner, lc.spacer, lc.playback_buttons_container,lc.spacer,
              lc.playback_timer_readout_container,lc.spacer,
              playback_controls, lc.spacer_mini,
              ]),style=lc.section_box_pad))

@app.callback( 
    Output('dynamic_container', 'children'),
    Output('layout_has_initialized', 'data'),
    Output('sim_settings', 'data'),
    Input('directory_monitor', 'n_intervals'),
    State('layout_has_initialized', 'data'),
    State('dynamic_container', 'children'),
    State('sim_settings', 'data'),
    State('configs', 'data')
)
def generate_layout(n_intervals, layout_has_initialized, children, sim_settings, configs):
    """
    Dynamically generate the layout, which was started in the config file to set up 
    the unique session id. This callback should only be executed once at page load in. 
    Thereafter, layout_has_initialized will be set to True
    """
    if not layout_has_initialized['added']:

        # Initialize variables
        sim_settings['event_start_year'] = 2024
        sim_settings['event_start_month'] = 7
        sim_settings['event_start_day'] = 16
        sim_settings['event_start_hour'] = 0
        sim_settings['event_start_minute'] = 30
        sim_settings['event_duration'] = 60
        sim_settings['days_in_month'] = 30
        sim_settings['timestring'] = None
        sim_settings['number_of_radars'] = 1
        sim_settings['radar_list'] = []
        sim_settings['playback_dropdown_dict'] = {}
        sim_settings['radar_dict'] = {}
        sim_settings['radar_files_dict'] = {}
        #sim_settings['radar'] = None
        sim_settings['lat'] = None
        sim_settings['lon'] = None
        sim_settings['new_radar'] = 'None'
        sim_settings['new_lat'] = None
        sim_settings['new_lon'] = None
        sim_settings['scripts_progress'] = 'Scripts not started'
        #self.base_dir = Path.cwd()
        sim_settings['playback_initiated'] = False
        sim_settings['playback_speed'] = 1.0
        sim_settings['playback_start'] = 'Not Ready'
        sim_settings['playback_end'] = 'Not Ready'
        sim_settings['playback_start_str'] = 'Not Ready'
        sim_settings['playback_end_str'] = 'Not Ready'
        sim_settings['playback_current_time'] = 'Not Ready'
        sim_settings['playback_clock'] = None
        sim_settings['playback_clock_str'] = None
        sim_settings['simulation_running'] = False
        sim_settings['playback_paused'] = False

        # Settings for date dropdowns moved here to avoid specifying different values in
        # the layout 
        now = datetime.now(pytz.utc)
        sim_year_section = dbc.Col(html.Div([lc.step_year, dcc.Dropdown(np.arange(1992, now.year + 1), sim_settings['event_start_year'], id='start_year', clearable=False),]))
        sim_month_section = dbc.Col(html.Div([lc.step_month, dcc.Dropdown(np.arange(1, 13), sim_settings['event_start_month'], id='start_month', clearable=False),]))
        sim_day_selection = dbc.Col(html.Div([lc.step_day, dcc.Dropdown(np.arange(1, 31), sim_settings['event_start_day'], id='start_day', clearable=False)]))
        sim_hour_section = dbc.Col(html.Div([lc.step_hour, dcc.Dropdown(np.arange(0, 24), sim_settings['event_start_hour'], id='start_hour', clearable=False),]))
        sim_minute_section = dbc.Col(html.Div([lc.step_minute, dcc.Dropdown([0, 15, 30, 45], sim_settings['event_start_minute'], id='start_minute', clearable=False),]))
        sim_duration_section = dbc.Col(html.Div([lc.step_duration, dcc.Dropdown(np.arange(0, 240, 15), sim_settings['event_duration'], id='duration', clearable=False),]))

        if children is None:
            children = []

        new_items = dbc.Container([
            dcc.Interval(id='playback_timer', disabled=True, interval=15*1000),
            dcc.Store(id='tradar'),
            dcc.Store(id='dummy'),
            dcc.Store(id='playback_running_store', data=False),
            dcc.Store(id='playback_start_store'),
            dcc.Store(id='playback_end_store'),
            dcc.Store(id='playback_clock_store'),
            lc.top_section, lc.top_banner,
            dbc.Container([
                dbc.Container([
                    html.Div([html.Div([lc.step_select_time_section, lc.spacer,
                                    dbc.Row([
                                        sim_year_section, sim_month_section, sim_day_selection,
                                        sim_hour_section, sim_minute_section, sim_duration_section,
                                        lc.spacer, lc.step_time_confirm])], style={'padding': '1em'}),
                            ], style=lc.section_box)])
            ]), lc.spacer,
            lc.full_radar_select_section, lc.spacer_mini,
            lc.map_section,
            lc.full_transpose_section,
            lc.scripts_button,
            lc.status_section,
            lc.spacer,lc.toggle_placefiles_btn,lc.spacer_mini,
            lc.full_links_section, lc.spacer,
            simulation_playback_section,
            html.Div(id='playback_speed_dummy', style={'display': 'none'}),
            lc.radar_id, lc.bottom_section
        ])

        # Append the new component to the current list of children
        children = list(children)  
        children.append(new_items)

        layout_has_initialized['added'] = True

        return children, layout_has_initialized, sim_settings

    create_logfile(configs['LOG_DIR'])
    return children, layout_has_initialized, sim_settings

################################################################################################
################################################################################################
################################################################################################
################################################################################################
################################################################################################
################################################################################################
# ----------------------------- Radar map section  ---------------------------------------------
################################################################################################

@app.callback(
    Output('show_radar_selection_feedback', 'children'),
    Output('confirm_radars_btn', 'children'),
    Output('confirm_radars_btn', 'disabled'),
    Output('sim_settings', 'data', allow_duplicate=True),
    Input('radar_quantity', 'value'),
    Input('graph', 'clickData'),
    State('sim_settings', 'data'),
    prevent_initial_call=True
    )
def display_click_data(quant_str: str, click_data: dict, sim_settings: dict):
    """
    Any time a radar site is clicked, 
    this function will trigger and update the radar list.

    The allow_duplicate=True addition seems to cause this callback to fire repeatedly
    event when no user input has triggered. Necessitated some workarounds.
    """
    # initially have to make radar selections and can't finalize
    select_action = 'Make'
    btn_deactivated = True

    #triggered_id = ctx.triggered_id
    sim_settings['number_of_radars'] = int(quant_str[0:1])

    # This block was getting triggered repeatedly when adding allow_duplicate=True. 
    #if triggered_id == 'radar_quantity' and len(sim_settings['radar_list']) != 0:
    #    sa.number_of_radars = int(quant_str[0:1])
    #    sa.radar_list = []
    #    sa.radar_dict = {}

    #    sim_settings['number_of_radars'] = int(quant_str[0:1])
    #    sim_settings['radar_list'] = []
    #    sim_settings['radar_dict'] = {} 

    #    return f'Use map to select {quant_str}', f'{select_action} selections', True, sim_settings
    add_to_list = False
    try:
        radar = click_data['points'][0]['customdata']
        if len(sim_settings['radar_list']) > 0:
            if radar != sim_settings['radar_list'][-1] and radar not in sim_settings['radar_list']:
                add_to_list = True
        else:
            add_to_list = True
    except (KeyError, IndexError, TypeError):
        return 'No radar selected ...', f'{select_action} selections', True, sim_settings

    #if triggered_id != 'radar_quantity':
    if add_to_list:
        sim_settings['radar_list'].append(radar)
    if len(sim_settings['radar_list']) > sim_settings['number_of_radars']:
        sim_settings['radar_list'] = sim_settings['radar_list'][-sim_settings['number_of_radars']:]
    if len(sim_settings['radar_list']) == sim_settings['number_of_radars']:
        select_action = 'Finalize'
        btn_deactivated = False

    #print(f"Radar list: {sim_settings['radar_list']}")
    listed_radars = ', '.join(sim_settings['radar_list'])
    return listed_radars, f'{select_action} selections', btn_deactivated, sim_settings


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

def query_radar_files(cfg, sim_settings):
    """
    Get the radar files from the AWS bucket. This is a preliminary step to build the progess bar.
    """
    # Need to reset the expected files dictionary with each call. Otherwise, if a user
    # cancels a request, the previously-requested files will still be in the dictionary.
    #sa.radar_files_dict = {}
    sim_settings['radar_files_dict'] = {}
    for _r, radar in enumerate(sim_settings['radar_list']):
        radar = radar.upper()
        args = [radar, str(sim_settings['event_start_str']), str(sim_settings['event_duration']), 
                str(False), cfg['RADAR_DIR']]
        logging.info(f"{cfg['SESSION_ID']} :: Passing {args} to Nexrad.py")
        results = utils.exec_script(Path(cfg['NEXRAD_SCRIPT_PATH']), args, cfg['SESSION_ID'])
        if results['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            logging.warning(f"{cfg['SESSION_ID']} :: User cancelled query_radar_files()")
            break

        json_data = results['stdout'].decode('utf-8')
        logging.info(f"{cfg['SESSION_ID']} :: Nexrad.py returned with {json_data}")
        #sa.radar_files_dict.update(json.loads(json_data))
        sim_settings['radar_files_dict'].update(json.loads(json_data))

    # Write radar metadata for this simulation to a text file. More complicated updating the
    # dcc.Store object with this information since this function isn't a callback. 
    with open(f'{cfg['RADAR_DIR']}/radarinfo.json', 'w') as jsonfile:
        json.dump(sim_settings['radar_files_dict'], jsonfile)  
    
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
    subprocess.run(["python", config.HODO_SCRIPT_PATH] + args, check=True)


def call_function(func, *args, **kwargs):
    # For the main script calls
    if len(args) > 2: 
        logging.info(f"Sending {args[1]} to {args[0]}")

    result = func(*args, **kwargs)

    if len(result['stderr']) > 0: 
        logging.error(result['stderr'].decode('utf-8'))
    if 'exception' in result:
        logging.error(f"Exception {result['exception']} occurred in {func.__name__}")
    return result


def run_with_cancel_button(cfg, sim_settings):
    """
    This version of the script-launcher trying to work in cancel button
    """
    UpdateHodoHTML('None', cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])

    #sa.scripts_progress = 'Setting up files and times'
    sim_settings['scripts_progress'] = 'Setting up files and times'
    # determine actual event time, playback time, diff of these two
    #sa.make_simulation_times()
    sim_settings = make_simulation_times(sim_settings)
    # clean out old files and directories
    try:
        remove_files_and_dirs(cfg)
        #sa.remove_files_and_dirs(cfg)
    except Exception as e:
        logging.exception("Error removing files and directories: ", exc_info=True)

    # based on list of selected radars, create a dictionary of radar metadata
    try:
        sa.create_radar_dict()
        create_radar_dict(sim_settings)

        sa.copy_grlevel2_cfg_file(cfg)
        copy_grlevel2_cfg_file(cfg)
    except Exception as e:
        logging.exception("Error creating radar dict or config file: ", exc_info=True)

    # Create initial dictionary of expected radar files
    if len(sim_settings['radar_list']) > 0:
        res = call_function(query_radar_files, cfg, sim_settings)
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            return

        for _r, radar in enumerate(sim_settings['radar_list']):
            radar = radar.upper()
            try:
                if sim_settings['new_radar'] == 'None':
                    new_radar = radar
                else:
                    new_radar = sim_settings['new_radar'].upper()
            except Exception as e:
                logging.exception("Error defining new radar: ", exc_info=True)

            # Radar download
            args = [radar, str(sim_settings['event_start_str']), 
                    str(sim_settings['event_duration']), str(True), cfg['RADAR_DIR']]
            res = call_function(utils.exec_script, Path(cfg['NEXRAD_SCRIPT_PATH']), 
                                args, cfg['SESSION_ID'])
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
                return

            # Munger
            args = [radar, str(sim_settings['playback_start_str']), 
                    str(sim_settings['event_duration']), 
                    str(sim_settings['simulation_seconds_shift']), cfg['RADAR_DIR'], 
                    cfg['POLLING_DIR'],cfg['L2MUNGER_FILEPATH'], cfg['DEBZ_FILEPATH'], 
                    new_radar]
            res = call_function(utils.exec_script, Path(cfg['MUNGER_SCRIPT_FILEPATH']), 
                                args, cfg['SESSION_ID'])
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
                return
            
    '''
            # this gives the user some radar data to poll while other scripts are running
            try:
                UpdateDirList(new_radar, 'None', cfg['POLLING_DIR'], initialize=True)
            except Exception as e:
                print(f"Error with UpdateDirList ", e)
                sa.log.exception(f"Error with UpdateDirList ", exc_info=True)
    
    # Surface observations
    args = [str(sa.lat), str(sa.lon), sa.event_start_str, cfg['PLACEFILES_DIR'], 
            str(sa.event_duration)]
    res = call_function(utils.exec_script, Path(cfg['OBS_SCRIPT_PATH']), args, 
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # NSE placefiles
    args = [str(sa.event_start_time), str(sa.event_duration), cfg['SCRIPTS_DIR'],
            cfg['DATA_DIR'], cfg['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, Path(cfg['NSE_SCRIPT_PATH']), args, 
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # Since there will always be a timeshift associated with a simulation, this
    # script needs to execute every time, even if a user doesn't select a radar
    # to transpose to.
    sa.log.info(f"Entering function run_transpose_script")
    run_transpose_script(cfg['PLACEFILES_DIR'])

    # Hodographs 
    for radar, data in sa.radar_dict.items():
        try:
            asos_one = data['asos_one']
            asos_two = data['asos_two']
        except KeyError as e:
            sa.log.exception("Error getting radar metadata: ", exc_info=True)

        # Execute hodograph script
        args = [radar, sa.new_radar, asos_one, asos_two, str(sa.simulation_seconds_shift),
                cfg['RADAR_DIR'], cfg['HODOGRAPHS_DIR']]
        res = call_function(utils.exec_script, Path(cfg['HODO_SCRIPT_PATH']), args, 
                            cfg['SESSION_ID'])
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            return

        try:
            UpdateHodoHTML('None', cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
        except Exception as e:
            print("Error updating hodo html: ", e)
            sa.log.exception("Error updating hodo html: ", exc_info=True)
    '''
@app.callback(
    Output('show_script_progress', 'children', allow_duplicate=True),
    [Input('run_scripts_btn', 'n_clicks'),
     State('configs', 'data'),
     State('sim_settings', 'data')],
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
        (Output('playback_clock_store', 'disabled'), True, False),
        (Output('confirm_radars_btn', 'disabled'), True, False), # added radar confirm btn
        (Output('playback_btn', 'disabled'), True, False), # add start sim btn
        #(Output('pause_resume_playback_btn', 'disabled'), True, False), # add pause/resume btn
        (Output('change_time', 'disabled'), True, False), # wait to enable change time dropdown
        (Output('cancel_scripts', 'disabled'), False, True),
    ])
def launch_simulation(n_clicks, configs, sim_settings) -> None:
    """
    This function is called when the "Run Scripts" button is clicked. It will execute the
    necessary scripts to simulate radar operations, create hodographs, and transpose placefiles.
    """
    if n_clicks == 0:
        raise PreventUpdate
    else:
        if config.PLATFORM == 'WINDOWS':
            sa.make_simulation_times()
        else:
            run_with_cancel_button(configs, sim_settings)

################################################################################################
# ----------------------------- Monitoring and reporting script status  ------------------------
################################################################################################

@app.callback(
    Output('dummy', 'data'),
    [Input('cancel_scripts', 'n_clicks'),
     State('session_id', 'data')],
    prevent_initial_call=True)
def cancel_scripts(n_clicks, SESSION_ID) -> None:
    """
    This function is called when the "Cancel Scripts" button is clicked. It will cancel all
    Args:
        n_clicks (int): incremented whenever the "Cancel Scripts" button is clicked
    """
    if n_clicks > 0:
        utils.cancel_all(sa, SESSION_ID)


@app.callback(
    Output('radar_status', 'value'),
    Output('hodo_status', 'value'),
    Output('transpose_status', 'value'),
    Output('obs_placefile_status', 'children'),
    Output('model_table', 'data'),
    Output('model_status_warning', 'children'),
    Output('show_script_progress', 'children', allow_duplicate=True),
    [Input('directory_monitor', 'n_intervals'),
     State('configs', 'data'),
     State('sim_settings', 'data')],
    prevent_initial_call=True
)
def monitor(_n, cfg, sim_settings):
    """
    This function is called every second by the directory_monitor interval. It (1) checks 
    the status of the various scripts and reports them to the front-end application and 
    (2) monitors the completion status of the scripts. 
    """
    processes = utils.get_app_processes()
    screen_output = ""
    seen_scripts = []
    for p in processes:
        process_session_id = p['session_id']
        if process_session_id == cfg['SESSION_ID']:
            # Returns get_data or process (the two scripts launched by nse.py)
            name = p['cmdline'][1].rsplit('/')[-1].rsplit('.')[0]

            # Scripts executed as python modules will be like [python, -m, script.name]
            if p['cmdline'][1] == '-m':
                # Should return Nexrad, munger, nse, etc.
                name = p['cmdline'][2].rsplit('/')[-1].rsplit('.')[-1]
                if p['name'] == 'wgrib2':
                    name = 'wgrib2'

            if name in config.scripts_list and name not in seen_scripts:
                runtime = time.time() - p['create_time']
                screen_output += f"{name}: running for {round(runtime,1)} s. "
                seen_scripts.append(name)

    # Radar file download status
    radar_dl_completion, radar_files = utils.radar_monitor(cfg)

    # Radar mungering/transposing status
    munger_completion = utils.munger_monitor(sa, cfg)

    # Surface placefile status
    placefile_stats = utils.surface_placefile_monitor(sa, cfg)
    placefile_status_string = f"{placefile_stats[0]}/{placefile_stats[1]} files found"

    # Hodographs. Currently hard-coded to expect 2 files for every radar and radar file.
    num_hodograph_images = len(glob(f"{cfg['HODOGRAPHS_DIR']}/*.png"))
    hodograph_completion = 0
    if len(radar_files) > 0:
        hodograph_completion = 100 * \
            (num_hodograph_images / (2*len(radar_files)))

    # NSE placefiles
    model_list, model_warning = utils.nse_status_checker(sa, cfg)
    return (radar_dl_completion, hodograph_completion, munger_completion, 
            placefile_status_string, model_list, model_warning, screen_output)

################################################################################################
# ----------------------------- Transpose placefiles in time and space  ------------------------
################################################################################################
# A time shift will always be applied in the case of a simulation. Determination of
# whether to also perform a spatial shift occurrs within self.shift_placefiles where
# a check for sa.new_radar != None takes place.

def run_transpose_script(PLACEFILES_DIR) -> None:
    """
    Wrapper function to the shift_placefiles script
    """
    sa.shift_placefiles(PLACEFILES_DIR)

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
    return lc.section_box_pad, f'Hide {btn_text}'

################################################################################################
# ----------------------------- Clock Callbacks  -----------------------------------------------
################################################################################################

@app.callback(
    Output('playback_btn', 'children'),
    Output('playback_btn', 'disabled'),
    Output('pause_resume_playback_btn', 'disabled'),
    Output('playback_running_store', 'data'),
    Output('start_readout', 'children'),
    Output('start_readout', 'style'),    
    Output('end_readout', 'children'),
    Output('end_readout', 'style'),
    Output('change_time', 'options'),
    Input('playback_btn', 'n_clicks'),
    State('configs', 'data'),
    prevent_initial_call=True)
def initiate_playback(_nclick, cfg):
    """     
    Enables/disables interval component that elapses the playback time

    """
    btn_text = 'Simulation Launched'
    btn_disabled = True
    playback_running = True
    start = sa.playback_start_str
    end = sa.playback_end_str
    style = lc.playback_times_style
    options = sa.playback_dropdown_dict
    if config.PLATFORM != 'WINDOWS':
        UpdateHodoHTML(sa.playback_clock_str, cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
        if sa.new_radar != 'None':
            UpdateDirList(sa.new_radar, sa.playback_clock_str, cfg['POLLING_DIR'])
        else:
            for _r, radar in enumerate(sa.radar_list):
                UpdateDirList(radar, sa.playback_clock_str, cfg['POLLING_DIR'])

    return btn_text, btn_disabled, False, playback_running, start, style, end, style, options

@app.callback(
    Output('playback_timer', 'disabled'),
    Output('playback_status', 'children'),
    Output('playback_status', 'style'),
    Output('pause_resume_playback_btn', 'children'),
    Output('current_readout', 'children'),
    Output('current_readout', 'style'),
    [Input('pause_resume_playback_btn', 'n_clicks'),
    Input('playback_timer', 'n_intervals'),
    Input('change_time', 'value'),
    Input('playback_running_store', 'data'),
    State('configs', 'data')
    ], prevent_initial_call=True)
def manage_clock_(nclicks, _n_intervals, new_time, _playback_running, cfg):
    """     
    Test
    """
    interval_disabled = False
    status = 'Running'
    sa.playback_paused = False
    playback_btn_text = 'Pause Playback'
    if sa.playback_clock.tzinfo is None:
        sa.playback_clock = sa.playback_clock.replace(tzinfo=timezone.utc)
    readout_time = datetime.strftime(sa.playback_clock, '%Y-%m-%d   %H:%M:%S')
    style = lc.feedback_green
    triggered_id = ctx.triggered_id

    if triggered_id == 'playback_timer':
        if sa.playback_clock.tzinfo is None:
            sa.playback_clock = sa.playback_clock.replace(tzinfo=timezone.utc)
        sa.playback_clock += timedelta(seconds=15 * sa.playback_speed)
        if sa.playback_clock < sa.playback_end:
            sa.playback_clock_str = sa.date_time_string(sa.playback_clock)
            readout_time = datetime.strftime(sa.playback_clock, '%Y-%m-%d   %H:%M:%S')
            if config.PLATFORM != 'WINDOWS':
                UpdateHodoHTML(sa.playback_clock_str, cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
                if sa.new_radar != 'None':
                    UpdateDirList(sa.new_radar, sa.playback_clock_str, cfg['POLLING_DIR'])
                else:
                    for _r, radar in enumerate(sa.radar_list):
                        UpdateDirList(radar, sa.playback_clock_str, cfg['POLLING_DIR'])
            else:
                pass

        if sa.playback_clock >= sa.playback_end:
            interval_disabled = True
            sa.playback_paused = True
            sa.playback_clock = sa.playback_end
            sa.playback_clock_str = sa.date_time_string(sa.playback_clock)
            status = 'Simulation Complete'
            playback_btn_text = 'Restart Simulation'
            style = lc.feedback_yellow

    if triggered_id == 'pause_resume_playback_btn':
        interval_disabled = False
        status = 'Running'
        sa.playback_paused = False
        playback_btn_text = 'Pause Playback'
        style = lc.feedback_green

        if nclicks % 2 == 1:
            interval_disabled = True
            status = 'Paused'
            sa.playback_paused = True
            playback_btn_text = 'Resume Playback'
            style = lc.feedback_yellow
           
    if triggered_id == 'change_time':
        sa.playback_clock = datetime.strptime(new_time, '%Y-%m-%d %H:%M')
        if sa.playback_clock.tzinfo is None:
            sa.playback_clock = sa.playback_clock.replace(tzinfo=timezone.utc)
            sa.playback_clock_str = new_time
            readout_time = datetime.strftime(sa.playback_clock, '%Y-%m-%d %H:%M:%S')
        if config.PLATFORM != 'WINDOWS':
            UpdateHodoHTML(sa.playback_clock_str, cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
            if sa.new_radar != 'None':
                UpdateDirList(sa.new_radar, sa.playback_clock_str, cfg['POLLING_DIR'])
            else:
                for _r, radar in enumerate(sa.radar_list):
                    UpdateDirList(radar, sa.playback_clock_str, cfg['POLLING_DIR'])

    if triggered_id == 'playback_running_store':
        pass
        # if not playback_running:
        #     interval_disabled = True
        #     status = 'Paused'
        #     playback_btn_text = 'Resume Simulation'

    return interval_disabled, status, style, playback_btn_text, readout_time, style

################################################################################################
# ----------------------------- Playback Speed Callbacks  --------------------------------------
################################################################################################
@app.callback(
    Output('playback_speed_dummy', 'children'),
    Input('speed_dropdown', 'value'))
def update_playback_speed(selected_speed):
    """
    Updates the playback speed in the sa object
    """
    sa.playback_speed = selected_speed
    try:
        sa.playback_speed = float(selected_speed)
    except ValueError:
        print(f"Error converting {selected_speed} to float")
        sa.playback_speed = 1.0
    return selected_speed


################################################################################################
# ----------------------------- Time Selection Summary and Callbacks  --------------------------
################################################################################################
@app.callback(
    Output('show_time_data', 'children'),
    Output('sim_settings', 'data', allow_duplicate=True),
    Input('start_year', 'value'),
    Input('start_month', 'value'),
    Input('start_day', 'value'),
    Input('start_hour', 'value'),
    Input('start_minute', 'value'),
    Input('duration', 'value'),
    State('sim_settings', 'data'),
    prevent_initial_call='initial_duplicate'
)
def get_sim(_yr, _mo, _dy, _hr, _mn, _dur, sim_settings) -> str:
    """
    Changes to any of the Inputs above will trigger this callback function to update
    the time summary displayed on the page. Variables already have been stored in sa
    object for use in scripts so don't need to be explicitly returned here.
    """
    sim_settings = make_simulation_times(sim_settings)
    line1 = f'{sim_settings['event_start_str']}Z ____ {sim_settings['event_duration']} minutes'
    return line1, sim_settings


@app.callback(
    Output('sim_settings', 'data', allow_duplicate=True), 
    Input('start_year', 'value'),
    State('sim_settings', 'data'),
    prevent_initial_call='initial_duplicate'
)
def get_year(start_year, sim_settings) -> int:
    """
    Updates the start year variable
    """
    sim_settings['event_start_year'] = start_year
    return sim_settings


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


@app.callback(
    Output('sim_settings', 'data', allow_duplicate=True), 
    Input('start_month', 'value'),
    State('sim_settings', 'data'),
    prevent_initial_call='initial_duplicate'
)
def get_month(start_month, sim_settings) -> int:
    """
    Updates the start month variable
    """
    sim_settings['event_start_month'] = start_month
    return sim_settings


@app.callback(
    Output('sim_settings', 'data', allow_duplicate=True), 
    Input('start_day', 'value'),
    State('sim_settings', 'data'),
    prevent_initial_call='initial_duplicate'
)
def get_day(start_day, sim_settings) -> int:
    """
    Updates the start day variable
    """
    sim_settings['event_start_day'] = start_day
    return sim_settings


@app.callback(
    Output('sim_settings', 'data', allow_duplicate=True), 
    Input('start_hour', 'value'),
    State('sim_settings', 'data'),
    prevent_initial_call='initial_duplicate'
)
def get_hour(start_hour, sim_settings) -> int:
    """
    Updates the start hour variable
    """
    sim_settings['event_start_hour'] = start_hour
    return sim_settings


@app.callback(
    Output('sim_settings', 'data', allow_duplicate=True), 
    Input('start_minute', 'value'),
    State('sim_settings', 'data'),
    prevent_initial_call='initial_duplicate'
)
def get_minute(start_minute, sim_settings) -> int:
    """
    Updates the start minute variable
    """
    sim_settings['event_start_minute'] = start_minute
    return sim_settings


@app.callback(
    Output('sim_settings', 'data', allow_duplicate=True), 
    Input('duration', 'value'),
    State('sim_settings', 'data'),
    prevent_initial_call='initial_duplicate'
)
def get_duration(duration, sim_settings) -> int:
    """
    Updates the event duration (in minutes)
    """
    sim_settings['event_duration'] = duration
    return sim_settings

################################################################################################
# ----------------------------- Start app  -----------------------------------------------------
################################################################################################

if __name__ == '__main__':
    if config.CLOUD:
        app.run_server(host="0.0.0.0", port=8050, threaded=True, debug=True, use_reloader=False,
                       dev_tools_hot_reload=False)
    else:
        if config.PLATFORM == 'DARWIN':
            app.run(host="0.0.0.0", port=8051, threaded=True, debug=True, use_reloader=False,
                dev_tools_hot_reload=False)
        else:
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
