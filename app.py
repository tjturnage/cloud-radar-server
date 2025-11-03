"""
This is the main script for the Radar Simulator application. It is a Dash application that
allows users to simulate radar operations, including the generation of radar data, placefiles, and
hodographs. The application is designed to mimic the behavior of a radar system over a
specified period, starting from a predefined date and time. It allows for the simulation of
radar data generation, including the handling of time shifts and geographical coordinates.
"""

import os
from pathlib import Path
from glob import glob
import time
from datetime import datetime, timedelta, timezone
import calendar
import logging
import mimetypes
#import smtplib
#from email.mime.text import MIMEText
#from email.mime.multipart import MIMEMultipart
import pytz
import pandas as pd

from dash import Dash, html, Input, Output, dcc, ctx, State, no_update  
from dash.exceptions import PreventUpdate

import numpy as np
from botocore.client import Config
# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc
import config
from config import app

import layout_components as lc
from scripts.update_dir_list import UpdateDirList
from scripts.update_hodo_page import UpdateHodoHTML
from scripts.update_placefiles import UpdatePlacefiles
import utils
import processing
import placefiles
import times

mimetypes.add_type("text/plain", ".cfg", True)
mimetypes.add_type("text/plain", ".list", True)

# Stops flask from writing "POST /_dash-update-component HTTP/1.1" 200 to logs
log = logging.getLogger('werkzeug')  # 'werkzeug' is the logger used by Flask
log.setLevel(logging.WARNING)  # You can set it to ERROR or CRITICAL as well
logging.Formatter.converter = time.gmtime  # Global change to UTC

def create_logfile(LOG_DIR):
    """
    Generate the main logfile for the download and processing scripts. 
    """
    logging.basicConfig(
        filename=f'{LOG_DIR}/app.log',  # Log file location
        # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        level=logging.INFO,
        format='%(levelname)s %(asctime)s :: %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    )


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

        # Initialize the script status tracking file and purge completion file if 
        # it exists 
        utils.write_status_file('startup', f"{configs['DATA_DIR']}/script_status.txt")
        completed_file = Path(f"{configs['DATA_DIR']}/completed.txt")
        if completed_file.is_file():
            completed_file.unlink()

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
                                href=f"{configs['LINK_BASE']}/downloads/original_radar_files.zip",
                                disabled=True, id="download_radar_link"),
                                style={'color':lc.graphics_c},width=4),
                     dbc.Col(dbc.ListGroupItem("Download Original Unshifted Placefiles",
                                href=f"{configs['LINK_BASE']}/downloads/original_placefiles.zip",
                                disabled=True, id="download_placefile_link"),
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

        MODAL_TEXT = """
            A change to one of the inputs has been detected after previously running the
            processing scripts. You will need to click the Run Scripts button again to 
            regenerate data for your simulation. All sim clock buttons will be disabled.
        """
        new_items = dbc.Container([
            dbc.Modal(
                [dbc.ModalHeader(dbc.ModalTitle("Alert!")), dbc.ModalBody(MODAL_TEXT)],
                id='input_change_modal', size='lg', is_open=False, style={'font-size':'20px'},
            ),
            dcc.Store(id='modal_count', data=0),
            dcc.Store(id='disable_sim_flag', data=False),
            dcc.Interval(id='playback_timer', disabled=True, interval=15*1000),
            dcc.Store(id='dummy'),
            dcc.Store(id='playback_running_store', data=False),

            dcc.Store(id='radar_info', data=radar_info),
            dcc.Store(id='sim_times'),
            dcc.Store(id='playback_speed_store', data=playback_speed),
            dcc.Store(id='playback_specs'),

            # For app/script monitoring
            dcc.Interval(id='script_status_interval', interval=1000),
            dcc.Interval(id='directory_monitor', interval=2000, disabled=True),
            dcc.Store(id='monitor_store', data=monitor_store),

            lc.top_section, lc.top_banner,
            dbc.Container([
                dbc.Container([
                    html.Div([html.Div([lc.step_select_event_time_section, lc.spacer,
                                        dbc.Row([
                                            sim_year_section, sim_month_section, sim_day_selection,
                                            sim_hour_section, sim_minute_section,
                                            sim_duration_section, lc.output_selections, lc.spacer,
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
    Output('new_radar_selection', 'value', allow_duplicate=True),
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
        radar_info['new_radar'] = 'None'
        radar_info['new_lat'] = None 
        radar_info['new_lon'] = None
        return f'Use map to select {quant_str}', f'{select_action} selections', True, radar_info, 'None'

    try:
        radar = click_data['points'][0]['customdata']
    except (KeyError, IndexError, TypeError):
        return 'No radar selected ...', f'{select_action} selections', True, radar_info, no_update

    if radar not in radar_info['radar_list']:
        radar_info['radar_list'].append(radar)
    if len(radar_info['radar_list']) > radar_info['number_of_radars']:
        radar_info['radar_list'] = radar_info['radar_list'][-radar_info['number_of_radars']:]
    if len(radar_info['radar_list']) == radar_info['number_of_radars']:
        select_action = 'Finalize'
        btn_deactivated = False
    radar_info['radar'] = radar

    listed_radars = ', '.join(radar_info['radar_list'])
    return listed_radars, f'{select_action} selections', btn_deactivated, radar_info, no_update


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

################################################################################################
# ----------------------------- Transpose radar section  ---------------------------------------
################################################################################################

@app.callback(
    [Output('full_transpose_section_id', 'style'),
     Output('skip_transpose_id', 'style'),
     Output('allow_transpose_id', 'style'),
     Output('run_scripts_btn', 'disabled')
     ], Input('confirm_radars_btn', 'n_clicks'),
    Input('radar_quantity', 'value'),
    State('radar_info', 'data'),
    Input('output_selections', 'value'),
    prevent_initial_call=True)
def finalize_radar_selections(clicks: int, _quant_str: str, radar_info: dict,
                              output_selections: list) -> dict:
    """
    This will display the transpose section on the page if the user has selected a single radar.
    Also handles changes to the output selections--if original radar only is selected or not.
    """
    disp_none = {'display': 'none'}
    # script_style = {'padding': '1em', 'vertical-align': 'middle'}
    triggered_id = ctx.triggered_id
    if triggered_id == 'radar_quantity':
        return disp_none, disp_none, disp_none, True
    if clicks > 0:
        if radar_info['number_of_radars'] == 1 and len(radar_info['radar_list']) == 1 and \
            'original_radar_only' not in output_selections:
            return lc.section_box_pad, disp_none, {'display': 'block'}, False
        else: 
            return lc.section_box_pad, {'display': 'block'}, disp_none, False
    
    # This needs to be last, otherwise run scripts button won't activate if this option
    # is selected prior to making radar selections. Additional checking so that clicking 
    # original radar doesn't result in Run scripts briefly becoming clickable each time.
    if triggered_id == 'output_selections':
        if 'original_radar_only' in output_selections:
            return no_update, no_update, no_update, no_update
        else:
            return disp_none, {'display': 'block'}, disp_none, True
    return disp_none, {'display': 'block'}, disp_none, False


@app.callback(
    Output('radar_info', 'data', allow_duplicate=True),
    #Output('new_radar_selection', 'value', allow_duplicate=True),
    [Input('new_radar_selection', 'value'),
     Input('radar_quantity', 'value'),
     State('radar_info', 'data'),
     Input('output_selections', 'value')],
    prevent_initial_call=True
)
def transpose_radar(value, radar_quantity, radar_info, output_selections):
    """
    If a user switches from a selection BACK to "None", without this, the application 
    will not update new_radar to None. Instead, it'll be the previous selection.
    Since we always evaluate "value" after every user selection, always set new_radar 
    initially to None.
    """
    #new_radar = 'None'
    radar_info['new_radar'] = 'None'
    radar_info['new_lat'] = None
    radar_info['new_lon'] = None
    radar_info['number_of_radars'] = int(radar_quantity[0:1])
    if value != 'None' and radar_info['number_of_radars'] == 1 and \
        'original_radar_only' not in output_selections:
        new_radar = value
        radar_info['new_radar'] = new_radar
        radar_info['new_lat'] = lc.df[lc.df['radar']
                                      == new_radar]['lat'].values[0]
        radar_info['new_lon'] = lc.df[lc.df['radar']
                                      == new_radar]['lon'].values[0]
    return radar_info

################################################################################################
# ----------------------------- Processing Scripts  --------------------------------------------
################################################################################################

def run_scripts(scripts_to_run, sim_times, configs, radar_info, lsr_delay):
    """
    This function handles the execution of all processing scripts 
    """
    status = 'running'
    create_radar_dict(radar_info)
    if scripts_to_run['query_and_download_radar']:
        logging.info(f"Radar download status: {status}")
        status = processing.query_and_download_radars(radar_info, configs, sim_times)

    if scripts_to_run['munger_radar'] and status == 'running':
        logging.info(f"Radar mungering status: {status}")
        status = processing.munger_radar(radar_info, configs, sim_times)

    if scripts_to_run['placefiles'] and status == 'running':
        logging.info(f"Surface placefile status: {status}")
        status = processing.generate_fast_placefiles(radar_info, configs, sim_times, 
                                                     lsr_delay)

    # The events files are always updated
    if status == 'running':
        logging.info(f"Event files status: {status}")
        status = processing.generate_events_files(configs, sim_times)

    if scripts_to_run['nse_placefiles'] and status == 'running':
        logging.info(f"NSE placefile status: {status}")
        status = processing.generate_nse_placefiles(configs, sim_times)

    # There always is a timeshift with a simulation, so this script needs to
    # execute every time, even if a user doesn't select a radar to transpose to.
    if status == 'running':
        logging.info("Entering function run_transpose_script")
        run_transpose_script(configs['PLACEFILES_DIR'], sim_times, radar_info)

        # Zip placefiles up, even if user bypassed the nse placefile generation step.
        try:
            placefiles.zip_original_placefiles(configs)
        except Exception as e:
            logging.exception("Error zipping original placefiles ", exc_info=True)

    if scripts_to_run['hodographs'] and status == 'running':
        logging.info(f"Hodograph status: {status}")
        status = processing.generate_hodographs(radar_info, configs, sim_times)
        
    return status

@app.callback(
    Output('output_selections', 'options'),
    Output('output_selections', 'value'),
    State('output_selections', 'options'),
    Input('output_selections', 'value')
)
def enable_disable_outputs(output_options, output_selections):
    """
    If user selects "Original radar only" from the output checklist, disable hodograph
    generation and lsr delay. Placefile generation is still ok and is left unchanged. 

    LSR delay is also disabled if surface placefiles are turned off.
    """
    updated_output_options = []
    for element in output_options:
        # Disable hodographs if original radar only selected for now. We can turn these
        # on once we add them as a downloadable zip file. Otherwise, user has no way of 
        # accessing since sims are disabled for this case. 
        if element['value'] == 'hodographs':
            if 'original_radar_only' in output_selections: 
                element['disabled'] = True 
                if 'hodographs' in output_selections: 
                    output_selections.remove('hodographs')
            else:
                element['disabled'] = False 

        if element['value'] == 'lsr_delay':
            if 'placefiles' not in output_selections or \
                'original_radar_only' in output_selections:
                element['disabled'] = True
                if 'lsr_delay' in output_selections: 
                    output_selections.remove('lsr_delay')
            else:
                element['disabled'] = False 

        updated_output_options.append(element)
    return updated_output_options, output_selections

@app.callback(
    Output('show_script_progress', 'children', allow_duplicate=True),
    Input('sim_times', 'data'),
    State('configs', 'data'),
    State('radar_info', 'data'),
    State('output_selections', 'value'),
    prevent_initial_call=True,
)
def coordinate_processing_scripts(sim_times, configs, radar_info, output_selections):
    """
    This function is called after the sim_times dcc.Store object is updated, which in
    turn happens after either the run scripts or refresh polling buttons are clicked.  

    Function handles the processing of necessary scripts to simulate radar operations, 
    create hodographs, and transpose placefiles, and importantly, coordinates which 
    processing scripts are run based on the button clicked.
    """
    if not sim_times:
        raise PreventUpdate
    
    button_source = sim_times.get('source')
    scripts_to_run = {
        'query_and_download_radar': True,
        'munger_radar': False,
        'placefiles': False,
        'nse_placefiles': False,
        'hodographs': False
    }

    for selection in output_selections:
        if selection: scripts_to_run[selection] = True
    
    if 'original_radar_only' not in output_selections: 
        scripts_to_run['munger_radar'] = True 
    # Special case if user only wants the original radar data. This allows hodograph
    # generation with the original date/time.
    else:
        sim_times['simulation_seconds_shift'] = 0

    lsr_delay = True
    if 'lsr_delay' not in output_selections:
        lsr_delay = False

    create_radar_dict(radar_info)
    # Run the regular pre-processing scripts
    if button_source == 'run_scripts_btn':
        #if config.PLATFORM != 'WINDOWS':
            # try:
            #     send_email(
            #         subject="RSSiC simulation launched",
            #         body="RSSiC simulation launched",
            #         to_email="thomas.turnage@noaa.gov"
            #     )
            # except (smtplib.SMTPException, ConnectionError) as e:
            #     print(f"Failed to send email: {e}")
        processing.remove_files_and_dirs(configs)

        # If scripts were previously completed, remove the status file
        completed_file = Path(f"{configs['DATA_DIR']}/completed.txt")
        if completed_file.is_file(): 
            completed_file.unlink()

    # Run the refresh polling scripts
    elif button_source == 'refresh_polling_btn':
        # The following scripts are never run for a polling refresh
        scripts_to_run['query_and_download_radar'] = False
        scripts_to_run['placefiles'] = False
        scripts_to_run['nse_placefiles'] = False

        # Add any user overrides from the UI
        prep_refresh_polling(configs)
    
    else:
        logging.warning(f"Unrecognized button source: {sim_times.get('source')}")
        raise PreventUpdate
    
    utils.write_status_file('running', f"{configs['DATA_DIR']}/script_status.txt")
    log_string = (
        f"\n"
        f"=========================Simulation Settings========================\n"
        f"Session ID: {configs['SESSION_ID']}\n"
        f"Simulation settings: {sim_times}\n\n"
        f"Radar info: {radar_info}\n\n"
        f"Scripts settings: {scripts_to_run}\n"
        f"====================================================================\n"
    )
    logging.info(log_string)

    # Run the processing scripts
    status = run_scripts(scripts_to_run, sim_times, configs, radar_info, lsr_delay)
    log_string = (
        f"\n"
        f"*************************Scripts completed**************************\n"
        f"Session ID: {configs['SESSION_ID']}\n"
        f"********************************************************************\n"
    )
    if status == 'running':
        # Small delay so that monitor interval fires prior to being disabled by the 
        # button_control function when script_status changes from 'running'. 
        time.sleep(2) 
        # If we're here, scripts ran to completion (were not cancelled)
        utils.write_status_file('completed', f"{configs['DATA_DIR']}/script_status.txt")
        utils.write_status_file('', f"{configs['DATA_DIR']}/completed.txt")
        logging.info(log_string)

    return no_update


def prep_refresh_polling(configs):
    """
    Handle initial file removal prior to re-running of pertinent processing script
    """
    # Remove the original file_times.txt file. This will get re-created by munger.py
    try:
        os.remove(f"{configs['ASSETS_DIR']}/file_times.txt")
    except FileNotFoundError:
        pass

    # Delete the uncompressed/munged radar files from the data directory. Needed if a user
    # canceled a previous refresh before mungering finishes, leaving orphaned .uncompressed
    # files in the radar data directory.
    try:
        processing.remove_munged_radar_files(configs)
    except KeyError as e:
        logging.exception("Error removing munged radar files ", exc_info=True)

    # Remove old mungered files 
    for root, _, files in os.walk(configs['POLLING_DIR']):
        for name in files:
            if name not in ['grlevel2.cfg']:
                logging.info(f"Deleting {name}")
                os.remove(os.path.join(root, name))

    # Remove original hodograph images
    hodo_images = glob(f"{configs['HODOGRAPHS_DIR']}/*.png")
    for image in hodo_images:
        try:
            os.remove(image)
        except:
            logging.exception(f"Error removing: {image}")


@app.callback(
    Output('sim_times', 'data'),
    Output('disable_sim_flag', 'data', allow_duplicate=True),
    Output('directory_monitor', 'disabled', allow_duplicate=True),
    Output('modal_count', 'data', allow_duplicate=True),
     [Input('run_scripts_btn', 'n_clicks'),
      Input('refresh_polling_btn', 'n_clicks'),
     State('start_year', 'value'),
     State('start_month', 'value'),
     State('start_day', 'value'),
     State('start_hour', 'value'),
     State('start_minute', 'value'),
     State('duration', 'value'),
     State('sim_times', 'data')],  # Get the current sim_times (needed for refresh_polling)
    prevent_initial_call=True,
)
def update_sim_times(n_clicks_run_scripts, n_clicks_refresh_polling, yr, mo, dy, hr, mn,
                     dur, current_sim_times):
    """
    Update the sim_times dictionary and send to dcc.Store object when either the
    Run Scripts button or the Refresh Polling button is clicked. This logic
    ensures sim_times is updated immediately after either button is clicked.
     
    This is a **CRITICAL** component of the application workflow, ensuring the sim 
    time specifications are always updated and available to all callbacks that need them,
    even if a user leaves the application idle. 
    """
    triggered = ctx.triggered_id
    if triggered == 'run_scripts_btn':
        dt = datetime(yr, mo, dy, hr, mn, second=0, tzinfo=timezone.utc)
        sim_times = times.make_simulation_times(dt, dur)
    elif triggered == 'refresh_polling_btn' and current_sim_times:
        dt = datetime.strptime(current_sim_times['event_start_str'], "%Y-%m-%d %H:%M")
        dt = dt.replace(tzinfo=timezone.utc)
        sim_times = times.make_simulation_times(dt, current_sim_times['event_duration'])
    else:
        raise PreventUpdate

    sim_times['source'] = triggered 
    log_string = (
        f"\n"
        f"==========================Simulation Times==========================\n"
        f"{triggered} Clicked\n"
        f"Sim times: {sim_times['playback_start_str']} "
        f"{sim_times['playback_end_str']}"
        f"\n"
        f"====================================================================\n"
    )
    logging.info(log_string)

    # Always reset this flag, which could be True due to user changing input(s) after 
    # processing scripts completed. See raise_modal_alert. 
    disable_sim_flag = False

    # Start the directory monitoring interval 
    monitor_disabled = False 
    return sim_times, disable_sim_flag, monitor_disabled, 0

################################################################################################
# -----------------------------Internal button logic  ------------------------------------------
################################################################################################
@app.callback(
    Output('run_scripts_btn', 'disabled', allow_duplicate=True), 
    Output('playback_btn', 'disabled', allow_duplicate=True), 
    Output('refresh_polling_btn', 'disabled', allow_duplicate=True), 
    Output('pause_resume_playback_btn', 'disabled', allow_duplicate=True),  
    Output('cancel_scripts', 'disabled', allow_duplicate=True), 
    Output('playback_btn', 'children', allow_duplicate=True),
    Output('change_time', 'disabled', allow_duplicate=True),
    Output('speed_dropdown', 'disabled', allow_duplicate=True),
    Output('upload-data', 'disabled', allow_duplicate=True),
    Output('download_radar_link', 'disabled'),
    Output('download_placefile_link', 'disabled'),
    # Time and output selections
    Output('start_year', 'disabled'),
    Output('start_month', 'disabled'),
    Output('start_day', 'disabled'),
    Output('start_hour', 'disabled'),
    Output('start_minute', 'disabled'),
    Output('duration', 'disabled'),
    Output('output_selections_div', 'style'),
    # Radar section
    Output('radar_quantity', 'disabled'),
    Output('map_btn', 'disabled'),
    Output('confirm_radars_btn', 'disabled', allow_duplicate=True),
    Output('new_radar_selection', 'disabled', allow_duplicate=True),
    # Interval components
    Output('directory_monitor', 'disabled', allow_duplicate=True),  
    Output('show_script_progress', 'children', allow_duplicate=True),
    Input('script_status_interval', 'n_intervals'),
    State('configs', 'data'),
    State('radar_info', 'data'),
    State('output_selections', 'value'),
    State('playback_status', 'children'),
    State('disable_sim_flag', 'data'),
    prevent_initial_call=True
)
def button_control(_n, configs, radar_info, output_selections, playback_status,
                   disable_sim_flag):
    """
    Coordinates activation and deactivation of clock and script-related buttons on the 
    UI. This removes button control from the script processing callback due to issues 
    with handling button release during long-running callbacks.

    Note: disable_sim_flag is set by raise_modal_alert. It's reset to False when
    either run scripts or refresh polling are clicked. This is mean to inhibit a user 
    from trying to run a sim with changed inputs, which could cause issues on the backend
    that aren't broadcast to the user.
    """
    monitor_disabled = False 
    screen_output = no_update

    # Get script status from file. Will be: startup, running, cancelled, or sim launched
    status_file = f"{configs['DATA_DIR']}/script_status.txt"
    script_status = utils.read_status_file(status_file)

    (
    run_scripts_btn_disabled,
    playback_btn_disabled,
    refresh_polling_btn_disabled,
    pause_resume_playback_btn_disabled,
    cancel_scripts_disabled,
    playback_btn_children,
    change_time_disabled,
    change_speed_disabled,
    upload_data_disabled,
    ) = _update_button_states(script_status, disable_sim_flag)

    # If scripts previously completed, allow polling refresh.
    completed_file = Path(f"{configs['DATA_DIR']}/completed.txt")
    if completed_file.is_file() and script_status not in ['running', 'sim launched'] \
        and not disable_sim_flag:
        refresh_polling_btn_disabled = False

    if script_status != 'running':
        monitor_disabled = True
        screen_output = "" # So the last script status is purged from the display
    
    #if script_status not in ['running', 'sim launched']:
    #    script_interval_disabled = True

    # If user changes the # of radars, run scripts needs to be disabled until they
    # finalize their new selection(s)
    if 'radar_list' in radar_info:
        if len(radar_info['radar_list']) != radar_info['number_of_radars']:
            run_scripts_btn_disabled = True

    # If user selected 'Original radar only', disable simulation running. 
    #dir_list_sizes = utils.check_dirlist_sizes(configs['POLLING_DIR']) 
    #if 'original_radar_only' in output_selections or sum(dir_list_sizes.values()) < 1:
    if 'original_radar_only' in output_selections:
        playback_btn_disabled = True 
        pause_resume_playback_btn_disabled = True 
        refresh_polling_btn_disabled = True 
        change_time_disabled = True

    # If .zip files are available, change link color and activate ListGroupItem
    dl_radar_link_disabled, dl_placefile_link_disabled = _update_link_status(configs)

    # Disables user interaction w/ time and radar/map inputs while sim or scripts running
    (year_disabled, month_disabled, day_disabled, hour_disabled, minute_disabled, 
    duration_disabled, radar_quantity_disabled, map_btn_disabled, 
    confirm_radars_btn_disabled, new_radar_selection_disabled, output_selection_display
    ) = _update_ui_status(playback_status, script_status)
    
    return (run_scripts_btn_disabled, playback_btn_disabled, refresh_polling_btn_disabled, 
            pause_resume_playback_btn_disabled, cancel_scripts_disabled, playback_btn_children, 
            change_time_disabled, change_speed_disabled, upload_data_disabled, 
            dl_radar_link_disabled, dl_placefile_link_disabled, year_disabled, 
            month_disabled, day_disabled, hour_disabled, minute_disabled, 
            duration_disabled, output_selection_display, radar_quantity_disabled, 
            map_btn_disabled, confirm_radars_btn_disabled, new_radar_selection_disabled,
            monitor_disabled, screen_output)

def _update_ui_status(playback_status, script_status):
    """
    Helper function to button_control. If simulation or processing scripts are running, 
    disables ability for user to make changes to any inputs. 
    """
    # Initial default state (all enabled, output visible)
    states = {
        'year': False,
        'month': False,
        'day': False,
        'hour': False,
        'minute': False,
        'duration': False,
        'radar_quantity': False,
        'map_btn': False,
        'confirm_radars_btn': False,
        'new_radar_selection': False
    }
    output_selection_display = {'display': 'block'}

    if playback_status == 'Running' or script_status == 'running':
        # Set all to True (disabled) and hide the output
        for key in states:
            states[key] = True
        output_selection_display = {'display': 'none'}

    return (
        states['year'], states['month'], states['day'], states['hour'],states['minute'],
        states['duration'], states['radar_quantity'], states['map_btn'], 
        states['confirm_radars_btn'], states['new_radar_selection'], 
        output_selection_display)

def _update_link_status(configs):
    """
    Helper function to button_control. If downloadable .zip file(s) exist(s), acivate
    associated ListGroupItem. Empty zip files seem to be about 22 bytes, so this checks
    for file sizes over 30 bytes. 
    
    This could be extended in the future to update text styling to better highlight 
    availability, and handle all links--including polling location (which should be 
    disabled for original radar-only download).
    """
    file_path = Path(f"{configs['USER_DOWNLOADS_DIR']}/original_radar_files.zip")
    download_radar_link_disabled = True
    #download_radar_link_style = {'color':lc.graphics_c}
    if file_path.is_file() and file_path.stat().st_size > 30:
        download_radar_link_disabled = False
        #download_radar_link_style = {'color':'#06DB42'}

    file_path = Path(f"{configs['USER_DOWNLOADS_DIR']}/original_placefiles.zip")
    download_placefile_link_disabled = True
    #download_placefile_link_style = {'color':lc.graphics_c}
    if file_path.is_file() and file_path.stat().st_size > 30:
        download_placefile_link_disabled = False
        #download_placefile_link_style = {'color':'#06DB42'}
    
    return download_radar_link_disabled, download_placefile_link_disabled

def _update_button_states(script_status, disable_sim_flag):
    """
    Helper function to button_control to map button states to script status.
    """
    # Default values
    state = {
        'run_scripts_btn_disabled': no_update,
        'playback_btn_disabled': no_update,
        'refresh_polling_btn_disabled': no_update,
        'pause_resume_playback_btn_disabled': no_update,
        'cancel_scripts_disabled': no_update,
        'playback_btn_children': no_update,
        'change_time_disabled': no_update,
        'change_speed_disabled': no_update,
        'upload_data_disabled': no_update,
    }

    # Mapping of script_status to specific updates
    status_updates = {
        'running': {
            'run_scripts_btn_disabled': True,
            'playback_btn_disabled': True,
            'refresh_polling_btn_disabled': True,
            'pause_resume_playback_btn_disabled': True,
            'cancel_scripts_disabled': False,
            'playback_btn_children': 'Launch Simulation',
            'upload_data_disabled': True,
        },
        'completed': {
            'run_scripts_btn_disabled': False,
            'playback_btn_disabled': False,
            'refresh_polling_btn_disabled': False,
            'pause_resume_playback_btn_disabled': True,
            'cancel_scripts_disabled': True,
            'playback_btn_children': 'Launch Simulation',
            'upload_data_disabled': False,
        },
        'cancelled': {
            'run_scripts_btn_disabled': False,
            'playback_btn_disabled': True,
            'refresh_polling_btn_disabled': True,
            'pause_resume_playback_btn_disabled': True,
            'cancel_scripts_disabled': True,
            'playback_btn_children': 'Launch Simulation',
            'upload_data_disabled': False,
        },
        'sim launched': {
            'change_time_disabled': False,
            'upload_data_disabled': True,
        }
    }

    # Apply updates for the given status
    if script_status in status_updates:
        state.update(status_updates[script_status])

    # If user changed an input after script completion, raise_modal_alert will set 
    # disable_sim_flag to True, signaling the sim buttons should be disabled.
    if disable_sim_flag:
        state['playback_btn_disabled'] = True
        state['pause_resume_playback_btn_disabled'] = True
        state['refresh_polling_btn_disabled'] = True
        state['change_time_disabled'] = True
        state['change_speed_disabled'] = True
    
    return (
        state['run_scripts_btn_disabled'],
        state['playback_btn_disabled'],
        state['refresh_polling_btn_disabled'],
        state['pause_resume_playback_btn_disabled'],
        state['cancel_scripts_disabled'],
        state['playback_btn_children'],
        state['change_time_disabled'],
        state['change_speed_disabled'],
        state['upload_data_disabled'],
    )
################################################################################################
# ----------------------------- Monitoring and reporting script status  ------------------------
################################################################################################
@app.callback(
    Output('input_change_modal', 'is_open'),
    Output('modal_count', 'data'),
    Output('disable_sim_flag', 'data', allow_duplicate=True),
    Input('start_year', 'value'),
    Input('start_month', 'value'),
    Input('start_day', 'value'),
    Input('start_hour', 'value'),
    Input('start_minute', 'value'),
    Input('duration', 'value'),
    Input('output_selections', 'value'),
    Input('radar_quantity', 'value'),
    Input('graph', 'clickData'),
    Input('new_radar_selection', 'value'),
    State('configs', 'data'),
    State('modal_count', 'data'),
    prevent_initial_call=True
)
def raise_modal_alert(yr, mo, dy, hr, mn, dur, outputs, num_radars, graph_click, 
                      new_radar, configs, modal_count):
    """
    If the user makes a change to any of the inputs following completion of processing 
    scripts, serve an alert modal indicating that all simulation clock buttons will be
    disabled until processing scripts are run again. Function sets disable_sim_flag to 
    True, which is then picked up by the button monitoring interval to make the changes
    to the clock/sim playback buttons.

    Exceptions:
    -----------
    This only happens if original_radar_only is NOT selected and if the simulation hasn't
    already been launched. In this latter case: (1) all of the simulation-dependent items 
    seem to be stored in the local playback_specs store object, and (2) we don't want to
    force a user to re-run the pre-processing scripts in the middle of a sim due to an 
    inadvertent input change. 

    This modal will appear once between each run scripts/refresh polling click. 
    """
    completed_file = Path(f"{configs['DATA_DIR']}/completed.txt")
    script_status = utils.read_status_file(f"{configs['DATA_DIR']}/script_status.txt")
    if completed_file.is_file() and 'original_radar_only' not in outputs \
        and script_status != 'sim launched':
        modal_count += 1
        if modal_count == 1:
            return True, modal_count, True
        else:
            return no_update, modal_count, True
    return no_update, modal_count, no_update


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
                (num_hodograph_images / (2*len(radar_files[::2])))

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
    placefiles.shift_placefiles(PLACEFILES_DIR, sim_times, radar_info)


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
    Output('speed_dropdown', 'disabled', allow_duplicate=True),
    Output('playback_specs', 'data', allow_duplicate=True),
    Output('refresh_polling_btn', 'disabled', allow_duplicate=True),
    Output('run_scripts_btn', 'disabled', allow_duplicate=True),
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

    refresh_polling_btn_disabled = False
    run_scripts_btn_disabled = False
    if playback_running:
        refresh_polling_btn_disabled = True
        run_scripts_btn_disabled = True

    # Report out the size of the dir.list files in the polling directory. This is done
    # following UpdateDirList call. 
    dir_list_sizes = utils.check_dirlist_sizes(cfg['POLLING_DIR'])
    log_string = (
        f"\n"
        f"*************************Playback Launched**************************\n"
        f"Session ID: {cfg['SESSION_ID']}\n"
        f"dir.list sizes (in bytes): {dir_list_sizes}\n"
        f"Start: {sim_times['playback_start_str']}, End: {sim_times['playback_end_str']}\n"
        f"Start dt: {sim_times['playback_start']}, End dt: {sim_times['playback_end']}\n"
        f"Launch Simulation Button Disabled?: {btn_disabled}\n"
        f"Pause Playback Button Disabled?: {False}\n"
        f"Refresh Polling Button Disabled?: {refresh_polling_btn_disabled}\n"
        f"********************************************************************\n"
    )
    logging.info(log_string)
    utils.write_status_file('sim launched', f"{cfg['DATA_DIR']}/script_status.txt")
    return (btn_text, btn_disabled, False, playback_running, start, style, end, style, options,
            False, playback_specs, refresh_polling_btn_disabled, run_scripts_btn_disabled)


@app.callback(
    Output('playback_timer', 'disabled'),
    Output('playback_status', 'children'),
    Output('playback_status', 'style'),
    Output('pause_resume_playback_btn', 'children'),
    Output('current_readout', 'children'),
    Output('current_readout', 'style'),
    Output('playback_specs', 'data', allow_duplicate=True),
    Output('refresh_polling_btn', 'disabled', allow_duplicate=True),
    Output('run_scripts_btn', 'disabled', allow_duplicate=True),
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
            specs['playback_clock_str'] = times.date_time_string(specs['playback_clock'])
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

    refresh_polling_btn_disabled = True
    run_scripts_btn_disabled = True
    if playback_paused:
        refresh_polling_btn_disabled = False
        run_scripts_btn_disabled = False
    return (specs['interval_disabled'], specs['status'], specs['style'],
            specs['playback_btn_text'], readout_time, style, specs,
            refresh_polling_btn_disabled, run_scripts_btn_disabled)

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
    #Output('sim_times', 'data'),
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
    return line


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
            _df, error = placefiles.make_events_placefile(contents, filename, configs)
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
            app.run_server(host="0.0.0.0", port=8051, threaded=True, debug=True, 
                           use_reloader=False, dev_tools_hot_reload=False)
        elif config.PLATFORM == 'CLOUD_DEV':
            app.run_server(host="0.0.0.0", port=8051, threaded=True, debug=False, 
                           use_reloader=False, dev_tools_hot_reload=False)
        else:
            app.run(debug=True, port=8050, threaded=True, dev_tools_hot_reload=False)
