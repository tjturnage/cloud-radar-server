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
import zipfile
#import gzip

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
import signal
import io
import base64
#import smtplib
#from email.mime.text import MIMEText
#from email.mime.multipart import MIMEMultipart
import psutil
import pytz
import pandas as pd

# from time import sleep
from dash import Dash, html, Input, Output, dcc, ctx, State  # , callback
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
from scripts.update_placefiles import UpdatePlacefiles
from scripts.nse import Nse

import utils
mimetypes.add_type("text/plain", ".cfg", True)
mimetypes.add_type("text/plain", ".list", True)

# Earth radius (km)
R = 6_378_137

# Regular expressions. First one finds lat/lon pairs, second finds the timestamps.
LAT_LON_REGEX = "[0-9]{1,2}.[0-9]{1,100},[ ]{0,1}[|\\s-][0-9]{1,3}.[0-9]{1,100}"
TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

"""
Idea is to move all of these functions to some other utility file within the main dir
to get them out of the app.
"""


def create_logfile(LOG_DIR):
    """
    Generate the main logfile for the download and processing scripts. 
    """
    logging.basicConfig(
        filename=f'{LOG_DIR}/scripts.txt',  # Log file location
        # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        level=logging.INFO,
        format='%(levelname)s %(asctime)s :: %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def shift_placefiles(PLACEFILES_DIR, sim_times, radar_info) -> None:
    """
    # While the _shifted placefiles should be purged for each run, just ensure we're
    # only querying the "original" placefiles to shift (exclude any with _shifted.txt)        
    """
    filenames = glob(f"{PLACEFILES_DIR}/*.txt")
    filenames = [x for x in filenames if "shifted" not in x]
    for file_ in filenames:
        outfilename = f"{file_[0:file_.index('.txt')]}_shifted.txt"
        outfile = open(outfilename, 'w', encoding='utf-8')
        with open(file_, 'r', encoding='utf-8') as f:
            data = f.readlines()

        try:
            for line in data:
                new_line = line

                if sim_times['simulation_seconds_shift'] is not None and \
                        any(x in line for x in ['Valid', 'TimeRange', 'Time']):
                    new_line = shift_time(
                        line, sim_times['simulation_seconds_shift'])

                # Shift this line in space. Only perform if both an original and
                # transpose radar have been specified.
                if radar_info['new_radar'] != 'None' and radar_info['radar'] is not None:
                    regex = re.findall(LAT_LON_REGEX, line)
                    if len(regex) > 0:
                        idx = regex[0].index(',')
                        plat, plon = float(regex[0][0:idx]), float(regex[0][idx+1:])
                        lat_out, lon_out = move_point(plat, plon, radar_info['lat'],
                                                      radar_info['lon'],
                                                      radar_info['new_lat'],
                                                      radar_info['new_lon'])
                        new_line = line.replace(regex[0], f"{lat_out}, {lon_out}")
                outfile.write(new_line)
        except (IOError, ValueError, KeyError) as e:
            outfile.truncate(0)
            outfile.write(f"Errors shifting this placefile: {e}")
        outfile.close()


def shift_time(line: str, simulation_seconds_shift: int) -> str:
    """
    Shifts the time-associated lines in a placefile.
    These look for 'Valid' and 'TimeRange'.
    """
    simulation_time_shift = timedelta(seconds=simulation_seconds_shift)
    new_line = line
    if 'Valid:' in line:
        idx = line.find('Valid:')
        # Leave off \n character
        valid_timestring = line[idx+len('Valid:')+1:-1]
        dt = datetime.strptime(valid_timestring, '%H:%MZ %a %b %d %Y')
        new_validstring = datetime.strftime(dt + simulation_time_shift,
                                            '%H:%MZ %a %b %d %Y')
        new_line = line.replace(valid_timestring, new_validstring)

    if 'TimeRange' in line:
        regex = re.findall(TIME_REGEX, line)
        dt = datetime.strptime(regex[0], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring_1 = datetime.strftime(dt + simulation_time_shift,
                                             '%Y-%m-%dT%H:%M:%SZ')
        dt = datetime.strptime(regex[1], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring_2 = datetime.strftime(dt + simulation_time_shift,
                                             '%Y-%m-%dT%H:%M:%SZ')
        new_line = line.replace(f"{regex[0]} {regex[1]}",
                                f"{new_datestring_1} {new_datestring_2}")

    # For LSR placefiles
    if 'LSR Time' in line:
        regex = re.findall(TIME_REGEX, line)
        dt = datetime.strptime(regex[0], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring = datetime.strftime(dt + simulation_time_shift,
                                           '%Y-%m-%dT%H:%M:%SZ')
        new_line = line.replace(regex[0], new_datestring)

    return new_line


def move_point(plat, plon, lat, lon, new_radar_lat, new_radar_lon):
    """
    Shift placefiles to a different radar site. Maintains the original azimuth and range
    from a specified RDA and applies it to a new radar location. 

    Parameters:
    -----------
    plat: float 
        Original placefile latitude
    plon: float 
        Original palcefile longitude

    lat and lon is the lat/lon pair for the original radar 
    new_lat and new_lon is for the transposed radar. These values are set in 
    the transpose_radar function after a user makes a selection in the 
    new_radar_selection dropdown. 

    """
    def _clamp(n, minimum, maximum):
        """
        Helper function to make sure we're not taking the square root of a negative 
        number during the calculation of `c` below. 
        """
        return max(min(maximum, n), minimum)

    # Compute the initial distance from the original radar location
    phi1, phi2 = math.radians(lat), math.radians(plat)
    d_phi = math.radians(plat - lat)
    d_lambda = math.radians(plon - lon)

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
        new_radar_lat), math.radians(new_radar_lon)
    phi_out = math.asin((math.sin(phi_new) * math.cos(d/R)) + (math.cos(phi_new) *
                        math.sin(d/R) * math.cos(math.radians(bearing))))
    lambda_out = lambda_new + math.atan2(math.sin(math.radians(bearing)) *
                                         math.sin(d/R) * math.cos(phi_new),
                                         math.cos(d/R) - math.sin(phi_new) * math.sin(phi_out))
    return math.degrees(phi_out), math.degrees(lambda_out)


def copy_grlevel2_cfg_file(cfg) -> None:
    """
    Ensures a grlevel2.cfg file is copied into the polling directory.
    This file is required for GR2Analyst to poll for radar data.
    """
    source = f"{cfg['BASE_DIR']}/grlevel2.cfg"
    destination = f"{cfg['POLLING_DIR']}/grlevel2.cfg"
    try:
        shutil.copyfile(source, destination)
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error copying {source} to {destination}: {e}")


def remove_files_and_dirs(cfg) -> None:
    """
    Cleans up files and directories from the previous simulation so these datasets
    are not included in the current simulation.
    """
    dirs = [cfg['RADAR_DIR'], cfg['POLLING_DIR'], cfg['HODOGRAPHS_DIR'], cfg['MODEL_DIR'],
            cfg['PLACEFILES_DIR'], cfg['USER_DOWNLOADS_DIR']]
    for directory in dirs:
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                if name != 'grlevel2.cfg':
                    os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))


def remove_munged_radar_files(cfg) -> None:
    """
    Removes uncompressed and 'munged' radar files within the /data/xx/radar directory 
    after the pre-processing scripts have completed. These files are no longer needed 
    as the appropriate files have been exported to the /assets/xx/polling directory. 
    
    copies the original files to the user downloads directory so they can be
    downloaded by the user if desired.
    """
    regex_pattern = r'^(.{4})(\d{8})_(\d{6})$'
    raw_pattern = r'^(.{4})(\d{8})_(\d{6})_(V\d{2})$'
    for root, _, files in os.walk(cfg['RADAR_DIR']):
        if Path(root).name == 'downloads':
            for name in files:
                thisfile = os.path.join(root, name)
                matched = re.match(regex_pattern, name)
                raw_matched = re.match(raw_pattern, name)
                if matched or '.uncompressed' in name:
                    os.remove(thisfile)
                if raw_matched:
                    shutil.copy2(thisfile, cfg['USER_DOWNLOADS_DIR'])

def zip_downloadable_radar_files(cfg) -> None:
    """
    After all radar files have been processed and are ready for download, this function
    zips up the radar files already in the user downloads directory.
    """
    shutil.make_archive('radar_files', 'zip', cfg['USER_DOWNLOADS_DIR'])
    shutil.move('radar_files.zip', f"{cfg['USER_DOWNLOADS_DIR']}/original_radar_files.zip")


def zip_original_placefiles(cfg) -> None:
    """
    After the placefiles have been shifted and are ready for download, this function
    zips up the original placefiles.
    """
    zip_filepath = f"{cfg['USER_DOWNLOADS_DIR']}/original_placefiles.zip"
    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        for root, _, files in os.walk(cfg['PLACEFILES_DIR']):
            for file in files:
                if 'txt' in file and 'updated' not in file and 'shifted' not in file:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, file)

def date_time_string(dt) -> str:
    """
    Converts a datetime object to a string.
    """
    return datetime.strftime(dt, "%Y-%m-%d %H:%M")


def make_simulation_times(event_start_time, event_duration) -> dict:
    """
    playback_end_time: datetime object
        - set to current time then rounded down to nearest 15 min.
    playback_start_time: datetime object
        - the time the simulation starts.
        - playback_end_time minus the event duration
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

    now = datetime.now(pytz.utc).replace(second=0, microsecond=0)
    playback_end = now - timedelta(minutes=now.minute % 15)
    playback_end_str = date_time_string(playback_end)

    playback_start = playback_end - timedelta(minutes=event_duration)
    playback_start_str = date_time_string(playback_start)

    # The playback clock is set to 10 minutes after the start of the simulation
    playback_clock = playback_start + timedelta(seconds=600)
    playback_clock_str = date_time_string(playback_clock)

    # a timedelta object is not JSON serializable, so cannot be included in the output
    # dictionary stored in the dcc.Store object. All references to simulation_time_shift
    # will need to use the simulation_seconds_shift reference instead.
    simulation_time_shift = playback_start - event_start_time
    simulation_seconds_shift = round(simulation_time_shift.total_seconds())
    event_start_str = date_time_string(event_start_time)
    increment_list = []
    for t in range(0, int(event_duration/5) + 1, 1):
        new_time = playback_start + timedelta(seconds=t*300)
        new_time_str = date_time_string(new_time)
        increment_list.append(new_time_str)

    playback_dropdown_dict = [
        {'label': increment, 'value': increment} for increment in increment_list]

    sim_times = {
        'event_start_str': event_start_str,
        'simulation_seconds_shift': simulation_seconds_shift,
        'playback_start_str': playback_start_str,
        'playback_start': playback_start,
        'playback_end_str': playback_end_str,
        'playback_end': playback_end,
        'playback_clock_str': playback_clock_str,
        'playback_clock': playback_clock,
        'playback_dropdown_dict': playback_dropdown_dict,
        'event_duration': event_duration
    }

    return sim_times


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
    html.Div([dbc.Row([lc.playback_speed_col, lc.playback_status_box,
                       playback_time_options_col])]))

simulation_playback_section = dbc.Container(
    dbc.Container(
        html.Div([lc.playback_banner, lc.spacer, lc.playback_buttons_container, lc.spacer,
                  lc.playback_timer_readout_container, lc.spacer,
                  playback_controls, lc.spacer_mini,
                  ]), style=lc.section_box_pad))


@app.callback(
    Output('dynamic_container', 'children'),
    Output('layout_has_initialized', 'data'),
    # Input('container_init', 'n_intervals'),
    State('layout_has_initialized', 'data'),
    State('dynamic_container', 'children'),
    Input('configs', 'data')
)
def generate_layout(layout_has_initialized, children, configs):
    """
    Dynamically generate the layout, which was started in the config file to set up 
    the unique session id. This callback should only be executed once at page load in. 
    Thereafter, layout_has_initialized will be set to True
    """
    if not layout_has_initialized['added'] and configs is not None:
        if children is None:
            children = []

        # Initialize configurable variables for load in
        event_start_year = 2024
        event_start_month = 5
        event_start_day = 7
        event_start_hour = 21
        event_start_minute = 30
        event_duration = 60
        playback_speed = 1.0
        number_of_radars = 1
        radar_list = []
        radar_dict = {}
        radar = None
        new_radar = 'None'
        lat = None
        lon = None
        new_lat = None
        new_lon = None
        radar_files_dict = {}
        #################################################

        monitor_store = {}
        monitor_store['radar_dl_completion'] = 0
        monitor_store['hodograph_completion'] = 0
        monitor_store['munger_completion'] = 0
        monitor_store['placefile_status_string'] = ""
        monitor_store['model_list'] = []
        monitor_store['model_warning'] = ""
        monitor_store['scripts_previously_running'] = False

        radar_info = {
            'number_of_radars': number_of_radars,
            'radar_list': radar_list,
            'radar_dict': radar_dict,
            'radar': radar,
            'new_radar': new_radar,
            'lat': lat,
            'lon': lon,
            'new_lat': new_lat,
            'new_lon': new_lon,
            'radar_files_dict': radar_files_dict
        }

        # Settings for date dropdowns moved here to avoid specifying different values in
        # the layout
        now = datetime.now(pytz.utc)
        sim_year_section = dbc.Col(html.Div([lc.step_year, dcc.Dropdown(
                                   np.arange(1992, now.year +
                                             1), event_start_year,
                                   id='start_year', clearable=False),]))
        sim_month_section = dbc.Col(html.Div([lc.step_month, dcc.Dropdown(
                                    np.arange(1, 13), event_start_month,
                                    id='start_month', clearable=False),]))
        sim_day_selection = dbc.Col(html.Div([lc.step_day, dcc.Dropdown(
                                    np.arange(1, 31), event_start_day,
                                    id='start_day', clearable=False)]))
        sim_hour_section = dbc.Col(html.Div([lc.step_hour, dcc.Dropdown(
            np.arange(0, 24), event_start_hour,
            id='start_hour', clearable=False),]))
        sim_minute_section = dbc.Col(html.Div([lc.step_minute, dcc.Dropdown(
            [0, 15, 30, 45], event_start_minute,
            id='start_minute', clearable=False),]))
        sim_duration_section = dbc.Col(html.Div([lc.step_duration, dcc.Dropdown(
            np.arange(0, 180, 15), event_duration,
            id='duration', clearable=False),]))

        polling_section = html.Div(
            [
                dbc.Row([
                    dbc.Col(dbc.ListGroupItem("Polling address for GR2Analyst"),
                        style=lc.polling_address_label, width=4),
                    dbc.Col(dbc.ListGroupItem(f"{configs['LINK_BASE']}/polling",
                        href="", target="_blank", style={'color': '#555555'}, id="polling_link"),
                        style=lc.polling_link, width=8)
                ])
            ])

        links_section = dbc.Container(dbc.Container(dbc.Container(html.Div(
            [lc.placefiles_banner, lc.spacer, polling_section,
             lc.spacer,
                dbc.Row(
                 [
                     dbc.Col("Facilitator Links", style=lc.group_header_style, width=6),
                 ], style={"display": "flex", "flexWrap": "wrap"}),
             lc.spacer_mini,lc.spacer_mini,
                    dbc.Row(
                 [dbc.Col(dbc.ListGroupItem("** SHAREABLE LINKS PAGE **",
                                href=f"{configs['LINK_BASE']}/links.html",
                                target="_blank"),style={'color':lc.graphics_c},width=4),
                     dbc.Col(dbc.ListGroupItem("Facilitator Events Guide (html)",
                                href=f"{configs['LINK_BASE']}/events.html",
                                target="_blank"),style={'color':lc.graphics_c},width=4),
                     dbc.Col(dbc.ListGroupItem("Facilitator Events Guide (txt)",
                                href=f"{configs['LINK_BASE']}/events.txt",
                                target="_blank"), style={'color':lc.graphics_c},width=4),
                 ],
                 style={"display": "flex", "flexWrap": "wrap"}
                ),


                dbc.Row(
                 [dbc.Col(dbc.ListGroupItem("Download Original Radar Files",
                                href=f"{configs['LINK_BASE']}/downloads/original_radar_files.zip"),
                                style={'color':lc.graphics_c},width=4),
                     dbc.Col(dbc.ListGroupItem("Download Original Unshifted Placefiles",
                                href=f"{configs['LINK_BASE']}/downloads/original_placefiles.zip"),
                                style={'color':lc.graphics_c},width=4),
                     dbc.Col(dbc.ListGroupItem("Hodograph Creation Instructions",
                                href="https://docs.google.com/document/d/1pRT0l27Zo3WusVnGS-nvJiQXcW3AkyJ91RH8gISqoDQ/edit", target="_blank"),
                                style={'color':lc.graphics_c},width=4),
                 ],
                 style={"display": "flex", "flexWrap": "wrap"}
                ),
             ]
        ))))

        full_links_section = dbc.Container(
            dbc.Container(
                html.Div([
                    links_section
                ]), id="placefiles_section", style=lc.section_box_pad))

        new_items = dbc.Container([
            dcc.Interval(id='playback_timer', disabled=True, interval=15*1000),
            # dcc.Store(id='tradar'),
            dcc.Store(id='dummy'),
            dcc.Store(id='playback_running_store', data=False),
            dcc.Store(id='playback_start_store'),   # might be unused
            dcc.Store(id='playback_end_store'),     # might be unused
            dcc.Store(id='playback_clock_store'),   # might be unused

            dcc.Store(id='radar_info', data=radar_info),
            dcc.Store(id='sim_times'),
            dcc.Store(id='playback_speed_store', data=playback_speed),
            dcc.Store(id='playback_specs'),

            # For app/script monitoring
            dcc.Interval(id='directory_monitor', interval=2000),
            dcc.Store(id='monitor_store', data=monitor_store),

            lc.top_section, lc.top_banner,
            dbc.Container([
                dbc.Container([
                    html.Div([html.Div([lc.step_select_event_time_section, lc.spacer,
                                        dbc.Row([
                                            sim_year_section, sim_month_section, sim_day_selection,
                                            sim_hour_section, sim_minute_section,
                                            sim_duration_section, lc.spacer,
                                            lc.step_time_confirm])], style={'padding': '1em'}),
                              ], style=lc.section_box_pad)])
            ]), lc.spacer,lc.spacer_mini,
            lc.full_radar_select_section, lc.spacer_mini,
            lc.map_section,
            lc.full_transpose_section,
            lc.spacer,
            lc.full_upload_section, lc.spacer,
            lc.scripts_button,
            lc.status_section,
            lc.spacer, #lc.toggle_placefiles_btn, lc.spacer_mini,
            full_links_section, lc.spacer,lc.spacer_mini,
            simulation_playback_section,
            lc.radar_id, lc.bottom_section
        ])

        # Append the new component to the current list of children
        children = list(children)
        children.append(new_items)

        layout_has_initialized['added'] = True
        create_logfile(configs['LOG_DIR'])
        return children, layout_has_initialized

    return children, layout_has_initialized

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
    Output('radar_info', 'data'),
    [Input('radar_quantity', 'value'),
     Input('graph', 'clickData'),
     State('radar_info', 'data')],
    prevent_initial_call=True
)
def display_click_data(quant_str: str, click_data: dict, radar_info: dict):
    """
    Any time a radar site is clicked, 
    this function will trigger and update the radar list.
    """
    # initially have to make radar selections and can't finalize
    select_action = 'Make'
    btn_deactivated = True

    triggered_id = ctx.triggered_id
    radar_info['number_of_radars'] = int(quant_str[0:1])

    if triggered_id == 'radar_quantity':
        radar_info['number_of_radars'] = int(quant_str[0:1])
        radar_info['radar_list'] = []
        radar_info['radar_dict'] = {}
        return f'Use map to select {quant_str}', f'{select_action} selections', True, radar_info

    try:
        radar = click_data['points'][0]['customdata']
    except (KeyError, IndexError, TypeError):
        return 'No radar selected ...', f'{select_action} selections', True, radar_info

    if radar not in radar_info['radar_list']:
        radar_info['radar_list'].append(radar)
    if len(radar_info['radar_list']) > radar_info['number_of_radars']:
        radar_info['radar_list'] = radar_info['radar_list'][-radar_info['number_of_radars']:]
    if len(radar_info['radar_list']) == radar_info['number_of_radars']:
        select_action = 'Finalize'
        btn_deactivated = False
    radar_info['radar'] = radar

    listed_radars = ', '.join(radar_info['radar_list'])
    return listed_radars, f'{select_action} selections', btn_deactivated, radar_info


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
    State('radar_info', 'data'),
    prevent_initial_call=True)
def finalize_radar_selections(clicks: int, _quant_str: str, radar_info: dict) -> dict:
    """
    This will display the transpose section on the page if the user has selected a single radar.
    """
    disp_none = {'display': 'none'}
    # script_style = {'padding': '1em', 'vertical-align': 'middle'}
    triggered_id = ctx.triggered_id
    if triggered_id == 'radar_quantity':
        return disp_none, disp_none, disp_none, True
    if clicks > 0:
        if radar_info['number_of_radars'] == 1 and len(radar_info['radar_list']) == 1:
            return lc.section_box_pad, disp_none, {'display': 'block'}, False
    return lc.section_box_pad, {'display': 'block'}, disp_none, False

################################################################################################
# ----------------------------- Transpose radar section  ---------------------------------------
################################################################################################


@app.callback(
    Output('radar_info', 'data', allow_duplicate=True),
    [Input('new_radar_selection', 'value'),
     Input('radar_quantity', 'value'),
     State('radar_info', 'data')],
    prevent_initial_call=True
)
def transpose_radar(value, radar_quantity, radar_info):
    """
    If a user switches from a selection BACK to "None", without this, the application 
    will not update new_radar to None. Instead, it'll be the previous selection.
    Since we always evaluate "value" after every user selection, always set new_radar 
    initially to None.
    """
    radar_info['new_radar'] = 'None'
    radar_info['new_lat'] = None
    radar_info['new_lon'] = None
    radar_info['number_of_radars'] = int(radar_quantity[0:1])
    if value != 'None' and radar_info['number_of_radars'] == 1:
        new_radar = value
        radar_info['new_radar'] = new_radar
        radar_info['new_lat'] = lc.df[lc.df['radar']
                                      == new_radar]['lat'].values[0]
        radar_info['new_lon'] = lc.df[lc.df['radar']
                                      == new_radar]['lon'].values[0]
    return radar_info

################################################################################################
# ----------------------------- Run Scripts button  --------------------------------------------
################################################################################################


def query_radar_files(cfg, radar_info, sim_times):
    """
    Get the radar files from the AWS bucket. This is a preliminary step to build the progess bar.
    """
    # Need to reset the expected files dictionary with each call. Otherwise, if a user
    # cancels a request, the previously-requested files will still be in the dictionary.
    # radar_files_dict = {}
    radar_info['radar_files_dict'] = {}
    for _r, radar in enumerate(radar_info['radar_list']):
        radar = radar.upper()
        args = [radar, str(sim_times['event_start_str']), str(sim_times['event_duration']),
                str(False), cfg['RADAR_DIR']]
        # logging.info(f"{cfg['SESSION_ID']} :: Passing {args} to Nexrad.py")
        results = utils.exec_script(
            Path(cfg['NEXRAD_SCRIPT_PATH']), args, cfg['SESSION_ID'])
        if results['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            logging.warning(
                f"{cfg['SESSION_ID']} :: User cancelled query_radar_files()")
            break

        json_data = results['stdout'].decode('utf-8')
        logging.info(
            f"{cfg['SESSION_ID']} :: Nexrad.py returned with {json_data}")
        radar_info['radar_files_dict'].update(json.loads(json_data))

    # Write radar metadata for this simulation to a text file. More complicated updating the
    # dcc.Store object with this information since this function isn't a callback.
    with open(f'{cfg['RADAR_DIR']}/radarinfo.json', 'w', encoding='utf-8') as json_file:
        json.dump(radar_info['radar_files_dict'], json_file)

    return results


def call_function(func, *args, **kwargs):
    # For the main script calls
    if len(args) > 2 and func.__name__ != 'query_radar_files':
        logging.info(f"Sending {args[1]} to {args[0]}")

    result = func(*args, **kwargs)

    if len(result['stderr']) > 0:
        logging.error(result['stderr'].decode('utf-8'))
    if 'exception' in result:
        logging.error(f"Exception {result['exception']} occurred in {
                      func.__name__}"
        )
    return result


def run_with_cancel_button(cfg, sim_times, radar_info):
    """
    This version of the script-launcher trying to work in cancel button
    """
    UpdateHodoHTML('None', cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
    # writes a black event_times.txt file to the assets directory
    args = [str(sim_times['simulation_seconds_shift']), 'None', cfg['RADAR_DIR'],
            cfg['EVENTS_HTML_PAGE'], cfg['EVENTS_TEXT_FILE']]
    res = call_function(utils.exec_script, Path(cfg['EVENT_TIMES_SCRIPT_PATH']), args,
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return


    # based on list of selected radars, create a dictionary of radar metadata
    try:
        create_radar_dict(radar_info)
        copy_grlevel2_cfg_file(cfg)
    except (IOError, ValueError, KeyError) as e:
        logging.exception(
            "Error creating radar dict or config file: %s",e,exc_info=True)
        
    log_string = (
        f"\n"
        f"=========================Simulation Settings========================\n"
        f"Session ID: {cfg['SESSION_ID']}\n"
        f"{sim_times}\n"
        f"{radar_info}\n"
        f"====================================================================\n"
    )
    logging.info(log_string)

    if len(radar_info['radar_list']) > 0:

        # Create initial dictionary of expected radar files.
        # TO DO: report back issues with radar downloads (e.g. 0 files found)
        res = call_function(query_radar_files, cfg, radar_info, sim_times)
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            return

        # Radar downloading and mungering steps
        for _r, radar in enumerate(radar_info['radar_list']):
            radar = radar.upper()
            try:
                if radar_info['new_radar'] == 'None':
                    new_radar = radar
                else:
                    new_radar = radar_info['new_radar'].upper()
            except (IOError, ValueError, KeyError) as e:
                logging.exception("Error defining new radar: %s",e,exc_info=True)

            # --------- Links Page -----------------------------------------------------
            #cfg['LINK_BASE'], cfg['LINKS_HTML_PAGE']
            args = [cfg['LINK_BASE'], cfg['LINKS_HTML_PAGE']]
            res = call_function(utils.exec_script, Path(cfg['LINKS_PAGE_SCRIPT_PATH']),
                                args, cfg['SESSION_ID'])
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
                return

            # Radar download
            args = [radar, str(sim_times['event_start_str']),
                    str(sim_times['event_duration']), str(True), cfg['RADAR_DIR']]
            res = call_function(utils.exec_script, Path(cfg['NEXRAD_SCRIPT_PATH']),
                                args, cfg['SESSION_ID'])
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
                return

            # Munger
            args = [radar, str(sim_times['playback_start_str']),
                    str(sim_times['event_duration']),
                    str(sim_times['simulation_seconds_shift']
                        ), cfg['RADAR_DIR'],
                    cfg['POLLING_DIR'], cfg['USER_DOWNLOADS_DIR'], cfg['L2MUNGER_FILEPATH'], cfg['DEBZ_FILEPATH'],
                    new_radar]
            res = call_function(utils.exec_script, Path(cfg['MUNGER_SCRIPT_FILEPATH']),
                                args, cfg['SESSION_ID'])
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
                return

            # this gives the user some radar data to poll while other scripts are running
            try:
                UpdateDirList(new_radar, 'None',
                              cfg['POLLING_DIR'], initialize=True)
            except (IOError, ValueError, KeyError) as e:
                print(f"Error with UpdateDirList: {e}")
                logging.exception("Error with UpdateDirList: %s",e, exc_info=True)

    # Delete the uncompressed/munged radar files from the data directory
    try:
        remove_munged_radar_files(cfg)
    except KeyError as e:
        logging.exception("Error removing munged radar files ", exc_info=True)


    # --------- LSR Placefiles -----------------------------------------------------
    #  Not monitored currently due to how quick this executes
    # center lat, center lon, event start, duration, LSR csv source dir, placefile output dir
    args = [str(radar_info['lat']), str(radar_info['lon']),
            str(sim_times['event_start_str']), str(sim_times['event_duration']),
            cfg['DATA_DIR'], cfg['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, Path(cfg['LSR_SCRIPT_PATH']), args,
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # --------- event times text file ----------------------------------------------
    # -- seconds_shift, csv_dir, radar_dir, html_file, text_file -------------------
    args = [str(sim_times['simulation_seconds_shift']), cfg['DATA_DIR'], cfg['RADAR_DIR'],
            cfg['EVENTS_HTML_PAGE'], cfg['EVENTS_TEXT_FILE']]
    res = call_function(utils.exec_script, Path(cfg['EVENT_TIMES_SCRIPT_PATH']), args,
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # Now that all radar files are in assets/{}/downloads dir, zip them up
    try:
        zip_downloadable_radar_files(cfg)
    except KeyError as e:
        logging.exception("Error zipping radar files ", exc_info=True)

    # --------- Surface observations placefiles -------------------------------------
    # center lat, center lon, start timestr, duration, placefile output directory
    args = [str(radar_info['lat']), str(radar_info['lon']),
            sim_times['event_start_str'], str(sim_times['event_duration']),
            cfg['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, Path(cfg['OBS_SCRIPT_PATH']), args,
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # --------- ProbSevere download -------------------------------------------------
    args = [str(sim_times['event_start_str']), str(sim_times['event_duration']),
            cfg['PROBSEVERE_DIR']]
    res = call_function(utils.exec_script, Path(cfg['PROBSEVERE_DOWNLOAD_SCRIPT_PATH']), args,
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # --------- ProbSevere placefiles -----------------------------------------------
    # -- center lat, center lon, data source directory, placefile output directory --
    args = [str(radar_info['lat']), str(radar_info['lon']),cfg['PROBSEVERE_DIR'],
            cfg['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, Path(cfg['PROBSEVERE_PLACEFILE_SCRIPT_PATH']), args,
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # --------- NSE placefiles ------------------------------------------------------
    args = [str(sim_times['event_start_str']), str(sim_times['event_duration']),
            cfg['SCRIPTS_DIR'], cfg['DATA_DIR'], cfg['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, Path(cfg['NSE_SCRIPT_PATH']), args,
                        cfg['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        return

    # Now that all original placefiles should be available, zip them up
    try:
        zip_original_placefiles(cfg)
    except KeyError as e:
        logging.exception("Error zipping original placefiles ", exc_info=True)

    # There always is a timeshift with a simulation, so this script needs to
    # execute every time, even if a user doesn't select a radar to transpose to.
    logging.info("Entering function run_transpose_script")
    run_transpose_script(cfg['PLACEFILES_DIR'], sim_times, radar_info)

    # get soundings
    #for radar, data in radar_info['radar_dict'].items():
    #    try:
    #        asos_one = data['asos_one']
    #        asos_two = data['asos_two']
    #    except KeyError as e:
    #        logging.exception("Error getting radar metadata: ", exc_info=True)

    # --------- Hodographs ---------------------------------------------------------
    for radar, data in radar_info['radar_dict'].items():
        try:
            asos_one = data['asos_one']
            asos_two = data['asos_two']
        except KeyError as e:
            logging.exception("Error getting radar metadata: ", exc_info=True)

        # Execute hodograph script
        args = [radar, radar_info['new_radar'], asos_one, asos_two,
                str(sim_times['simulation_seconds_shift']), cfg['RADAR_DIR'],
                cfg['HODOGRAPHS_DIR']]
        res = call_function(utils.exec_script, Path(cfg['HODO_SCRIPT_PATH']), args,
                            cfg['SESSION_ID'])
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            return

        try:
            UpdateHodoHTML(
                'None', cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
        except (IOError, ValueError, KeyError) as e:
            print("Error updating hodo html: ", e)
            logging.exception("Error updating hodo html: %s",e, exc_info=True)


@app.callback(
    Output('show_script_progress', 'children', allow_duplicate=True),
    [Input('run_scripts_btn', 'n_clicks'),
     State('configs', 'data'),
     State('sim_times', 'data'),
     State('radar_info', 'data')],
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
        # (Output('playback_clock_store', 'disabled'), True, False),
        (Output('confirm_radars_btn', 'disabled'),
         True, False),  # added radar confirm btn
        (Output('playback_btn', 'disabled'), True, False),  # add start sim btn
        # (Output('pause_resume_playback_btn', 'disabled'), True, False), # add pause/resume btn
        # wait to enable change time dropdown
        (Output('change_time', 'disabled'), True, False),
        (Output('cancel_scripts', 'disabled'), False, True),
    ])
def launch_simulation(n_clicks, configs, sim_times, radar_info):
    """
    This function is called when the "Run Scripts" button is clicked. It will execute the
    necessary scripts to simulate radar operations, create hodographs, and transpose placefiles.
    """
    if n_clicks == 0:
        raise PreventUpdate
    else:
        if config.PLATFORM != 'WINDOWS':
            # try:
            #     send_email(
            #         subject="RSSiC simulation launched",
            #         body="RSSiC simulation launched",
            #         to_email="thomas.turnage@noaa.gov"
            #     )
            # except (smtplib.SMTPException, ConnectionError) as e:
            #     print(f"Failed to send email: {e}")
            run_with_cancel_button(configs, sim_times, radar_info)

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
        utils.cancel_all(SESSION_ID)


@app.callback(
    Output('radar_status', 'value'),
    Output('hodo_status', 'value'),
    Output('transpose_status', 'value'),
    Output('obs_placefile_status', 'children'),
    Output('model_table', 'data'),
    Output('model_status_warning', 'children'),
    Output('show_script_progress', 'children', allow_duplicate=True),
    Output('monitor_store', 'data'),
    Output('polling_link', 'href'),
    Output('polling_link', 'style'),
    [Input('directory_monitor', 'n_intervals'),
     State('configs', 'data'),
     State('cancel_scripts', 'disabled'),
     State('monitor_store', 'data')],
    prevent_initial_call=True
)
def monitor(_n, cfg, cancel_btn_disabled, monitor_store):
    """
    This function is called every second by the directory_monitor interval. It (1) checks 
    the status of the various scripts and reports them to the front-end application and 
    (2) monitors the completion status of the scripts. 

    In order to reduce background latency, this funcion only fully executes when the 
    downloading and pre-processing scripts are running, defined by the cancel button
    being enabled. Previous status data is stored in monitor_store.
    """
    radar_dl_completion = monitor_store['radar_dl_completion']
    hodograph_completion = monitor_store['hodograph_completion']
    munger_completion = monitor_store['munger_completion']
    placefile_status_string = monitor_store['placefile_status_string']
    model_list = monitor_store['model_list']
    model_warning = monitor_store['model_warning']
    screen_output = ""

    # Polling link disclosure when grlevel2.cfg file has been copied into assets dir
    gr2_cfg_filename = f"{cfg['POLLING_DIR']}/grlevel2.cfg"
    polling_link_href = ""
    polling_link_style =  {'color': lc.steps_background}
    if os.path.exists(gr2_cfg_filename):
        polling_link_href = f"{cfg['LINK_BASE']}/polling"
        polling_link_style = {'color': '#cccccc'}

    # Scripts are running or they just recently ended.
    if not cancel_btn_disabled or monitor_store['scripts_previously_running']:
        processes = utils.get_app_processes()
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
                    screen_output += f"{name}: running for {
                        round(runtime, 1)} s. "
                    seen_scripts.append(name)

        # Radar file download status
        radar_dl_completion, radar_files = utils.radar_monitor(
            cfg['RADAR_DIR'])

        # Radar mungering/transposing status
        munger_completion = utils.munger_monitor(
            cfg['RADAR_DIR'], cfg['POLLING_DIR'])

        # Surface placefile status
        placefile_stats = utils.surface_placefile_monitor(
            cfg['PLACEFILES_DIR'])
        placefile_status_string = f"{
            placefile_stats[0]}/{placefile_stats[1]} files found"

        # Hodographs. Currently hard-coded to expect 2 files for every radar and radar file.
        num_hodograph_images = len(glob(f"{cfg['HODOGRAPHS_DIR']}/*.png"))
        hodograph_completion = 0
        if len(radar_files) > 0:
            hodograph_completion = 100 * \
                (num_hodograph_images / (2*len(radar_files)))

        # NSE placefiles
        model_list, model_warning = utils.nse_status_checker(cfg['MODEL_DIR'])

        # Capture the latest status information
        monitor_store['radar_dl_completion'] = radar_dl_completion
        monitor_store['hodograph_completion'] = hodograph_completion
        monitor_store['munger_completion'] = munger_completion
        monitor_store['placefile_status_string'] = placefile_status_string
        monitor_store['model_list'] = model_list
        monitor_store['model_warning'] = model_warning
        monitor_store['scripts_previously_running'] = True

        return (radar_dl_completion, hodograph_completion, munger_completion,
                placefile_status_string, model_list, model_warning, screen_output,
                monitor_store, polling_link_href, polling_link_style)

    # Scripts have completed/stopped, but were running the previous pass through.
    if cancel_btn_disabled and monitor_store['scripts_previously_running']:
        monitor_store['scripts_previously_running'] = False

    return (radar_dl_completion, hodograph_completion, munger_completion,
            placefile_status_string, model_list, model_warning, screen_output, monitor_store,
            polling_link_href, polling_link_style)

################################################################################################
# ----------------------------- Transpose placefiles in time and space  ------------------------
################################################################################################
# A time shift will always be applied in the case of a simulation. Determination of
# whether to also perform a spatial shift occurrs within shift_placefiles where a check for
# new_radar != None takes place.


def run_transpose_script(PLACEFILES_DIR, sim_times, radar_info) -> None:
    """
    Wrapper function to the shift_placefiles script
    """
    shift_placefiles(PLACEFILES_DIR, sim_times, radar_info)


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
    Output('speed_dropdown', 'disabled'),
    Output('playback_specs', 'data', allow_duplicate=True),
    [Input('playback_btn', 'n_clicks'),
     State('playback_speed_store', 'data'),
     State('configs', 'data'),
     State('sim_times', 'data'),
     State('radar_info', 'data')],
    prevent_initial_call=True)
def initiate_playback(_nclick, playback_speed, cfg, sim_times, radar_info):
    """     
    Enables/disables interval component that elapses the playback time. User can only 
    click this button this once.
    """

    playback_specs = {
        'playback_paused': False,
        'playback_clock': sim_times['playback_clock'],
        'playback_clock_str': sim_times['playback_clock_str'],
        'playback_start': sim_times['playback_start'],
        'playback_start_str': sim_times['playback_start_str'],
        'playback_end': sim_times['playback_end'],
        'playback_end_str': sim_times['playback_end_str'],
        'playback_speed': playback_speed,
        'new_radar': radar_info['new_radar'],
        'radar_list': radar_info['radar_list'],
    }

    btn_text = 'Simulation Launched'
    btn_disabled = True
    playback_running = True
    start = sim_times['playback_start_str']
    end = sim_times['playback_end_str']
    style = lc.playback_times_style
    options = sim_times['playback_dropdown_dict']
    if config.PLATFORM != 'WINDOWS':
        UpdatePlacefiles(sim_times['playback_clock_str'], cfg['PLACEFILES_DIR'])
        UpdateHodoHTML(sim_times['playback_clock_str'], cfg['HODOGRAPHS_DIR'],
                       cfg['HODOGRAPHS_PAGE'])
        if radar_info['new_radar'] != 'None':
            UpdateDirList(radar_info['new_radar'], sim_times['playback_clock_str'],
                          cfg['POLLING_DIR'])
        else:
            for _r, radar in enumerate(radar_info['radar_list']):
                UpdateDirList(
                    radar, sim_times['playback_clock_str'], cfg['POLLING_DIR'])

    return (btn_text, btn_disabled, False, playback_running, start, style, end, style, options,
            False, playback_specs)


@app.callback(
    Output('playback_timer', 'disabled'),
    Output('playback_status', 'children'),
    Output('playback_status', 'style'),
    Output('pause_resume_playback_btn', 'children'),
    Output('current_readout', 'children'),
    Output('current_readout', 'style'),
    Output('playback_specs', 'data', allow_duplicate=True),
    [Input('pause_resume_playback_btn', 'n_clicks'),
     Input('playback_timer', 'n_intervals'),
     Input('change_time', 'value'),
     Input('playback_running_store', 'data'),
     Input('playback_speed_store', 'data'),
     State('configs', 'data'),
     State('playback_specs', 'data'),
     ], prevent_initial_call=True)
def manage_clock_(nclicks, _n_intervals, new_time, _playback_running, playback_speed,
                  cfg, specs):
    """     
    This function manages the playback clock. It is called by the dcc.Interval component
    """
    triggered_id = ctx.triggered_id

    specs['playback_speed'] = playback_speed
    interval_disabled = False
    status = 'Running'
    playback_paused = False
    playback_btn_text = 'Pause Playback'

    # Variables stored dcc.Store object are strings.
    specs['playback_clock'] = datetime.strptime(specs['playback_clock'],
                                                '%Y-%m-%dT%H:%M:%S+00:00')

    # Unsure why these string representations change.
    try:
        specs['playback_end'] = datetime.strptime(specs['playback_end'],
                                                  '%Y-%m-%dT%H:%M:%S+00:00')
    except ValueError:
        specs['playback_end'] = datetime.strptime(specs['playback_end'],
                                                  '%Y-%m-%dT%H:%M:%S')

    if specs['playback_clock'].tzinfo is None:
        specs['playback_clock'] = specs['playback_clock'].replace(
            tzinfo=timezone.utc)
    readout_time = datetime.strftime(
        specs['playback_clock'], '%Y-%m-%d   %H:%M:%S')
    style = lc.feedback_green

    if triggered_id == 'playback_timer':
        if specs['playback_clock'].tzinfo is None:
            specs['playback_clock'] = specs['playback_clock'].replace(
                tzinfo=timezone.utc)
        specs['playback_clock'] += timedelta(
            seconds=round(15*specs['playback_speed']))

        if specs['playback_end'].tzinfo is None:
            specs['playback_end'] = specs['playback_end'].replace(
                tzinfo=timezone.utc)

        if specs['playback_clock'] < specs['playback_end']:
            specs['playback_clock_str'] = date_time_string(
                specs['playback_clock'])
            readout_time = datetime.strftime(
                specs['playback_clock'], '%Y-%m-%d   %H:%M:%S')
            if config.PLATFORM != 'WINDOWS':
                UpdatePlacefiles(specs['playback_clock_str'], cfg['PLACEFILES_DIR'])
                UpdateHodoHTML(specs['playback_clock_str'],
                               cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
                if specs['new_radar'] != 'None':
                    UpdateDirList(
                        specs['new_radar'], specs['playback_clock_str'], cfg['POLLING_DIR'])
                else:
                    for _r, radar in enumerate(specs['radar_list']):
                        UpdateDirList(
                            radar, specs['playback_clock_str'], cfg['POLLING_DIR'])
            else:
                pass

        if specs['playback_clock'] >= specs['playback_end']:
            interval_disabled = True
            playback_paused = True
            dt = datetime.strptime(specs['playback_start_str'], '%Y-%m-%d %H:%M') + \
                 timedelta(seconds=600)
            specs['playback_clock_str'] = dt.strftime('%Y-%m-%d %H:%M')
            specs['playback_clock'] = dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            status = 'Simulation Complete'
            playback_btn_text = 'Restart Simulation'
            style = lc.feedback_yellow

    if triggered_id == 'pause_resume_playback_btn':
        interval_disabled = False
        status = 'Running'
        playback_paused = False
        playback_btn_text = 'Pause Playback'
        style = lc.feedback_green

        if nclicks % 2 == 1:
            interval_disabled = True
            status = 'Paused'
            playback_paused = True
            playback_btn_text = 'Resume Playback'
            style = lc.feedback_yellow

    if triggered_id == 'change_time':
        specs['playback_clock'] = datetime.strptime(new_time, '%Y-%m-%d %H:%M')
        if specs['playback_clock'].tzinfo is None:
            specs['playback_clock'] = specs['playback_clock'].replace(
                tzinfo=timezone.utc)
            specs['playback_clock_str'] = new_time
            readout_time = datetime.strftime(
                specs['playback_clock'], '%Y-%m-%d %H:%M:%S')
        if config.PLATFORM != 'WINDOWS':
            UpdatePlacefiles(specs['playback_clock_str'], cfg['PLACEFILES_DIR'])
            UpdateHodoHTML(specs['playback_clock_str'],
                           cfg['HODOGRAPHS_DIR'], cfg['HODOGRAPHS_PAGE'])
            if specs['new_radar'] != 'None':
                UpdateDirList(
                    specs['new_radar'], specs['playback_clock_str'], cfg['POLLING_DIR'])
            else:
                for _r, radar in enumerate(specs['radar_list']):
                    UpdateDirList(
                        radar, specs['playback_clock_str'], cfg['POLLING_DIR'])

    if triggered_id == 'playback_running_store':
        pass

    # Without this, a change to either the playback speed or playback time will restart
    # a paused simulation
    if triggered_id in ['playback_speed_store', 'change_time']:
        interval_disabled = specs['interval_disabled']
        status = specs['status']
        playback_btn_text = specs['playback_btn_text']
        playback_paused = specs['playback_paused']
        style = specs['style']

    specs['interval_disabled'] = interval_disabled
    specs['status'] = status
    specs['playback_paused'] = playback_paused
    specs['playback_btn_text'] = playback_btn_text
    specs['style'] = style
    return (specs['interval_disabled'], specs['status'], specs['style'],
            specs['playback_btn_text'], readout_time, style, specs)

################################################################################################
# ----------------------------- Playback Speed Callbacks  --------------------------------------
################################################################################################


@app.callback(
    Output('playback_speed_store', 'data'),
    Input('speed_dropdown', 'value'),
    prevent_initial_call=True
)
def update_playback_speed(selected_speed) -> float:
    """
    Updates the playback speed in the sa object
    """
    try:
        selected_speed = float(selected_speed)
    except ValueError:
        print(f"Error converting {selected_speed} to float")
        selected_speed = 1.0
    return selected_speed


################################################################################################
# ----------------------------- Time Selection Summary and Callbacks  --------------------------
################################################################################################
@app.callback(
    Output('show_time_data', 'children'),
    Output('sim_times', 'data'),
    [Input('start_year', 'value'),
     Input('start_month', 'value'),
     Input('start_day', 'value'),
     Input('start_hour', 'value'),
     Input('start_minute', 'value'),
     Input('duration', 'value')]
)
def get_sim(yr, mo, dy, hr, mn, dur) -> str:
    """
    Changes to any of the Inputs above will trigger this callback function to update
    the time summary displayed on the page, as well as recomputing variables for 
    the simulation.
    """
    dt = datetime(yr, mo, dy, hr, mn, second=0, tzinfo=timezone.utc)
    line = f'{dt.strftime("%Y-%m-%d %H:%M")}Z ____ {dur} minutes'
    sim_times = make_simulation_times(dt, dur)
    return line, sim_times


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

################################################################################################
# ----------------------------- Upload callback  -----------------------------------------------
################################################################################################

def make_timerange_line(row) -> str:
    """
    This function creates the datetime string for the placefiles
    """
    date_str = row.get('utc_date',"")
    hour = row.get('utc_hour',"")
    minute = row.get('utc_minute',"")
    delay =  row.get('delay_min',"")
    # Handle missing hour or minute values
    if pd.isna(hour):
        hour = 0
    if pd.isna(minute):
        minute = 0
    if pd.isna(delay):
        delay = 0

    # Combine the date, hour, and minute into a datetime object
    datetime_str = f"{date_str} {int(hour):02d}:{int(minute):02d}"

    orig_dtobj = datetime.strptime(datetime_str, '%m/%d/%Y %H:%M')

    dtobj = orig_dtobj + timedelta(minutes=int(delay))
    dtobj_end = dtobj + timedelta(minutes=10)

    time_range_start = dtobj.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_range_end = dtobj_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    timerange_line = f"TimeRange: {time_range_start} {time_range_end}\n"

    return timerange_line

def create_remark(row) -> str:
    """
    This function creates the pop-up text for the placefiles
    """
    typetext= row.get('TYPETEXT',"")
    qualifier = row.get('QUALIFIER',"")
    mag = row.get('MAG',"")
    mag_line = ""
    #if magnitude == "nan" or magnitude == "No_Magnitude":
    if mag in ("nan", "NO MAG", "NA", "No_Magnitude"):
        mag_line = "No Magnitude given"
    else:
        if typetext == 'TSTM WND GST':
            mag_line = f"Wind Gust: {mag} mph"
        if typetext in ('HAIL'):
            mag_line = f"Size: {mag} inches"
        if typetext in ('RAIN', 'SNOW'):
            mag_line = f"Accum: {mag} inches"
    source = row.get('SOURCE',"")
    #fake_rpt = row.get('fake_rpt',"")
    remark = row.get('REMARK',"")
    if remark in ("nan", "No_Comments", "M","NA", "NO MAG"):
        remark_line = ""
    if typetext == 'QUESTION':
        remark_line = f'{typetext}\\nSource: {source}\\n{remark}\nEnd:\n\n'
    else:
        remark_line = f'{typetext}\\n{qualifier}\\n{mag_line}\\nSource: {source}\\n{remark}\nEnd:\n\n'
    return remark_line


def icon_value(event_type) -> int:
    """
    This function assigns an icon value based on the event type
    """
    #if event_type == 'VERIFIED':
    if event_type in ('VERIFIED', 'MEASURED'):
        return 1
    if event_type in ('UNVERIFIED', 'ESTIMATED'):
        return 2
    if event_type == 'QUESTION':
        return 3
    return 3


def make_events_placefile(contents, filename, cfg):
    """
    This function creates the Event Notification placefile for the radar simulation
    """
    top_section = 'Refresh: 1\
    \nThreshold: 999\
    \nTitle: Event Notifications -- for radar simulation\
    \nColor: 255 200 255\
    \nIconFile: 1, 50, 50, 25, 15, https://raw.githubusercontent.com/tjturnage/cloud-radar-server/main/assets/iconfiles/wessl-three.png\
    \nIconFile: 2, 30, 30, 15, 10, https://raw.githubusercontent.com/tjturnage/cloud-radar-server/main/assets/iconfiles/wessl-three-small.png\
    \nFont: 1, 11, 1, "Arial"\n\n'


    _content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if 'csv' in filename:
            place_fout = open(f'{cfg['PLACEFILES_DIR']}/events.txt', 'w', encoding='utf-8')
            #notifications_csv = open(f'{cfg['DATA_DIR']}/notifications.csv', 'w', encoding='utf-8')
            events_csv = f'{cfg['DATA_DIR']}/events.csv'
            place_fout.write("; RSSiC events file\n")
            place_fout.write(top_section)
            # Assume that the user uploaded a CSV file
            df_orig = pd.read_csv(io.StringIO(decoded.decode('utf-8')), dtype=str)
            df_orig.fillna("NA", inplace=True)
            df = df_orig.loc[df_orig['TYPETEXT'] != 'NO EVENT']

            df.to_csv(events_csv, index=False, encoding='utf-8')

            for _index,row in df.iterrows():
                try:
                    lat = row.get('LAT',"")
                    lon = row.get('LON',"")
                    obj_line = f'Object: {lat},{lon}\n'

                    tr_line = make_timerange_line(row)
                    comments = create_remark(row)
                    icon_code = icon_value(row.get('QUALIFIER',""))
                    icon_line = f"Threshold: 999\nIcon: 0,0,0,2,{icon_code}, {comments}"
                    place_fout.write(tr_line)
                    place_fout.write(obj_line)
                    place_fout.write(icon_line)
                except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
                    return None, f"Error processing file: {e}"
            place_fout.close()
            return df, None
        return None, f"Unsupported file type: {filename}"

    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
        return None, f"Error processing file: {e}"

@app.callback(Output('show_upload_feedback', 'children'),
              [Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('configs', 'data'),
              State('sim_times', 'data')],
              prevent_initial_call=True)
def update_output(contents, filename, configs, _sim_times):
    """
    This function is called when the user uploads a file. It will parse the contents and write
    """
    if contents is not None:
        try:
            _df, error = make_events_placefile(contents, filename, configs)
            if error:
                return html.Div([html.H5(error)])
            return html.Div([
            html.H5(f"File uploaded successfully: {filename}"),])

        except (KeyError,pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
            return html.Div([
                html.H5(f"Error processing file: {e}")
            ])
    return html.Div([
        html.H5("No file uploaded")
    ])


################################################################################################
# ----------------------------- Start app  -----------------------------------------------------
################################################################################################


if __name__ == '__main__':

    if config.CLOUD:
        app.run_server(host="0.0.0.0", port=8050, threaded=True, debug=False, use_reloader=False,
                       dev_tools_hot_reload=False)
    else:
        if config.PLATFORM == 'DARWIN':
            app.run(host="0.0.0.0", port=8051, threaded=True, debug=True, use_reloader=False,
                    dev_tools_hot_reload=False)
        else:
            app.run(debug=True, port=8050, threaded=True,
                    dev_tools_hot_reload=False)
