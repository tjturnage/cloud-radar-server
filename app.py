"""_summary_

    Returns:
    Main page for radar-server
        _type_: _description_
"""

import os
import re
from glob import glob
from datetime import datetime, timedelta
import calendar
from pathlib import Path
import math
import subprocess
from dash import Dash, html, Input, Output, dcc, ctx, callback
from dash.exceptions import PreventUpdate
#from dash import diskcache, DiskcacheManager, CeleryManager
#from uuid import uuid4
#import diskcache



import numpy as np
import boto3
import botocore
from botocore.client import Config

# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc
from obs_placefile import Mesowest
from get_nexrad import NexradDownloader
import layout_components as lc

 # Earth radius (km)
R = 6_378_137

# Regular expressions. First one finds lat/lon pairs, second finds the timestamps.
LAT_LON_REGEX = "[0-9]{1,2}.[0-9]{1,100},[ ]{0,1}[|\\s-][0-9]{1,3}.[0-9]{1,100}"
TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

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
        start_year (int): The year when the simulation starts.
        start_month (int): The month when the simulation starts.
        days_in_month (int): The number of days in the starting month.
        start_day (int): The day of the month when the simulation starts.
        start_hour (int): The hour of the day when the simulation starts (24-hour format).
        start_minute (int): The minute of the hour when the simulation starts.
        duration (int): The total duration of the simulation in minutes.
        timeshift (Optional[int]): The time shift in minutes to apply to the simulation clock. Default is None.
        timestring (Optional[str]): A string representation of the current simulation time. Default is None.
        sim_clock (Optional[datetime]): The current simulation time as a datetime object. Default is None.
        radar (Optional[object]): An instance of a radar object used in the simulation. Default is None.
        lat (Optional[float]): The latitude coordinate for the radar. Default is None.
        lon (Optional[float]): The longitude coordinate for the radar. Default is None.
        t_radar (str): A temporary variable for radar type. Default is 'None'.
        tlat (Optional[float]): Temporary storage for latitude coordinate. Default is None.
        tlon (Optional[float]): Temporary storage for longitude coordinate. Default is None.
        simulation_running (bool): Flag to indicate if the simulation is currently running. Default is False.
    """

    def __init__(self):
        super().__init__()
        self.start_year = 2023
        self.start_month = 6
        self.days_in_month = 30
        self.start_day = 15
        self.start_hour = 18
        self.start_minute = 30
        self.duration = 60
        self.timeshift = None
        self.timestring = None
        self.sim_clock = None
        self.radar = None
        self.lat = None
        self.lon = None
        self.t_radar = 'None'
        self.tlat = None
        self.tlon = None
        self.simulation_running = False
        self.current_dir = Path.cwd()
        self.make_directories()
        self.make_radar_download_folders()
        self.make_times()
        self.make_prefix()
        self.bucket = boto3.resource('s3',
                                    config=Config(signature_version=botocore.UNSIGNED,
                                    user_agent_extra='Resource')).Bucket('noaa-nexrad-level2')

    def make_directories(self):
        self.csv_file = self.current_dir / 'radars.csv'
        self.data_dir = self.current_dir / 'data'
        os.makedirs(self.data_dir, exist_ok=True)
        self.scripts_path = self.current_dir / 'scripts'
        self.obs_script_path = self.current_dir / 'obs_placefile.py'
        self.hodo_script_path = self.scripts_path / 'hodo_plot.py'
        self.nexrad_script_path = self.scripts_path / 'get_nexrad.py'
        self.assets_dir = self.current_dir / 'assets'
        self.hodo_images = self.assets_dir / 'hodographs'
        os.makedirs(self.hodo_images, exist_ok=True)
        self.placefiles_dir = self.assets_dir / 'placefiles'
        os.makedirs(self.placefiles_dir, exist_ok=True)
        return

    def make_times(self):
        self.sim_start = datetime(self.start_year,self.start_month,self.start_day,
                                  self.start_hour,self.start_minute,second=0)
        self.sim_clock = self.sim_start
        self.sim_start_str = datetime.strftime(self.sim_start,"%Y-%m-%d %H:%M:%S UTC")
        self.sim_end = self.sim_start + timedelta(minutes=int(self.duration))
        return
   
    def get_days_in_month(self):
        self.days_in_month = calendar.monthrange(self.start_year, self.start_month)[1]
        return

    def make_radar_download_folders(self):
        if self.radar is not None:
            self.radar_site_dir = self.data_dir / 'radar' / self.radar
            os.makedirs(self.radar_site_dir, exist_ok=True)
            self.radar_site_download_dir = self.radar_site_dir / 'downloads'
            os.makedirs(self.radar_site_download_dir, exist_ok=True)
            self.cf_dir = self.radar_site_download_dir / 'cf_radial'
            os.makedirs(self.cf_dir, exist_ok=True)
            return
        return

    def make_prefix(self):
        first_folder = self.sim_start.strftime('%Y/%m/%d/')
        second_folder = self.sim_end.strftime('%Y/%m/%d/')
        self.prefix_day_one = f'{first_folder}{self.radar}'  
        if first_folder != second_folder:
            self.prefix_day_two = f'{second_folder}{self.radar}'
        else:
            self.prefix_day_two = None
        
        return

    def download_files(self):
        for obj in self.bucket.objects.filter(Prefix=self.prefix_day_one):
            file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
            if file_dt >= self.sim_start and file_dt <= self.sim_end:
                if obj.key.endswith('V06') or obj.key.endswith('V08'):
                    print(obj.key)
                    file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
                    self.bucket.download_file(obj.key, str(self.radar_site_download_dir / Path(obj.key).name))


        if self.prefix_day_two is not None:
            for obj in self.bucket.objects.filter(Prefix=self.prefix_day_two):
                file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
                if file_dt >= self.sim_start and file_dt <= self.sim_end:
                    if obj.key.endswith('V06') or obj.key.endswith('V08'):
                        print(obj.key)
                        self.bucket.download_file(obj.key, str(self.radar_site_download_dir / Path(obj.key).name))

        return

    def move_point(self,plat,plon):
        """
        Shift placefiles to a different radar site. Maintains the original azimuth and range
        from a specified RDA and applies it to a new radar location. 

        Parameters:
        -----------
        lat: float 
            Original placefile latitude
        lon: float 
            Original palcefile longitude
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
        phi_new, lambda_new = math.radians(self.tlat), math.radians(self.tlon)
        phi_out = math.asin((math.sin(phi_new) * math.cos(d/R)) + (math.cos(phi_new) * \
                            math.sin(d/R) * math.cos(math.radians(bearing))))
        lambda_out = lambda_new + math.atan2(math.sin(math.radians(bearing)) *    \
                    math.sin(d/R) * math.cos(phi_new), math.cos(d/R) - math.sin(phi_new) * \
                    math.sin(phi_out))
        return math.degrees(phi_out), math.degrees(lambda_out)


    def shift_placefiles(self, filepath):
        filenames = glob(f"{filepath}/*.txt")
        for file_ in filenames:
            print(f"Shifting placefile: {file_}")
            with open(file_, 'r', encoding='utf-8') as f: data = f.readlines()
            outfile = open(outfilename, 'w', encoding='utf-8')
            outfilename = f"{file_[0:file_.index('.txt')]}.shifted"
            for line in data:
                new_line = line

                if self.timeshift is not None and any(x in line for x in ['Valid', 'TimeRange']):
                    new_line = self.shift_time(line)

                # Shift this line in space
                # This regex search finds lines with valid latitude/longitude pairs
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
            new_validstring = datetime.strftime(dt + timedelta(minutes=self.timeshift),
                                                '%H:%MZ %a %b %d %Y')
            new_line = line.replace(valid_timestring, new_validstring)

        if 'TimeRange' in line:
            regex = re.findall(TIME_REGEX, line)
            dt = datetime.strptime(regex[0], '%Y-%m-%dT%H:%M:%SZ')
            new_datestring_1 = datetime.strftime(dt + timedelta(minutes=self.timeshift),
                                                '%Y-%m-%dT%H:%M:%SZ')
            dt = datetime.strptime(regex[1], '%Y-%m-%dT%H:%M:%SZ')
            new_datestring_2 = datetime.strftime(dt + timedelta(minutes=self.timeshift),
                                                '%Y-%m-%dT%H:%M:%SZ')
            new_line = line.replace(f"{regex[0]} {regex[1]}",
                                    f"{new_datestring_1} {new_datestring_2}") 
        return new_line 



################################################################################################
#      Initialize the app
################################################################################################

sa = RadarSimulator()
app = Dash(__name__,external_stylesheets=[dbc.themes.CYBORG],
                prevent_initial_callbacks=False, suppress_callback_exceptions=True)
app.title = "Radar Simulator"

################################################################################################
#     Build the layout
################################################################################################

sim_day_selection =  dbc.Col(html.Div([
                    dbc.Card(lc.step_day, color="secondary", inverse=True),           
                    dcc.Dropdown(np.arange(1,sa.days_in_month+1),15,id='start_day',clearable=False
                    ) ]))

simulation_clock_slider = dcc.Slider(id='sim_clock', min=0, max=1440, step=1, value=0,
                                     marks={0:'00:00', 240:'04:00'})


simulation_clock = html.Div([
        html.Div([
        html.Div([
                dbc.Card(lc.step_sim_clock, color="secondary", inverse=True)],
                style={'text-align':'center'},),
                simulation_clock_slider,
            dcc.Interval(
                id='interval-component',
                interval=999*1000, # in milliseconds
                n_intervals=0
                ),
        html.Div(id='clock-output', style=lc.feedback),

        ], id='clock-container', style={'display': 'none'}), 
    ])


app.layout = dbc.Container([
    dcc.Store(id='sim_store'),
    lc.top_section, lc.top_banner, lc.step_one_section,
    lc.time_settings_readout,
    html.Div([
        dbc.Row([
                lc.sim_year_section,lc.sim_month_section, sim_day_selection,
                lc.sim_hour_section, lc.sim_minute_section, lc.sim_duration_section
        ])],style={'padding':'1em'}),
    lc.step_two_section, lc.map_toggle, 
    lc.graph_section, lc.transpose_radar, lc.scripts_button,
    lc.status_section,
    lc.toggle_simulation_clock,simulation_clock, lc.radar_id, lc.bottom_section
    ])  # end of app.layout

################################################################################################
#     Run the scripts
################################################################################################


@app.callback(
    Output('tradar', 'value'),
    Input('tradar', 'value'), prevent_initial_call=True)
def transpose_radar(tradar):
    if tradar != 'None':
        sa.t_radar = tradar
        sa.tlat = lc.df[lc.df['radar'] == sa.t_radar]['lat'].values[0]
        sa.tlon = lc.df[lc.df['radar'] == sa.t_radar]['lon'].values[0]
        #print(sa.radar,sa.lat,sa.lon,sa.t_radar,sa.tlat,sa.tlon)
        return f'{sa.t_radar}'

    return 'None'


# -------------------------------------
# ---  Run Scripts button ---
# -------------------------------------
@app.callback(
    Output('run_obs_script', 'n_clicks'),
    [Input('run_scripts', 'n_clicks')],
    prevent_initial_call=True)
def launch_obs_script(n_clicks):
    if n_clicks > 0:
        return n_clicks
    return 0

# -------------------------------------
# ---  Mesowest Placefile script ---
# -------------------------------------
@app.callback(
    [Output('obs_placefile_status', 'value'),
    Output('run_nexrad_script', 'n_clicks')],
    Input('run_obs_script', 'n_clicks'))
def run_obs_script(n_clicks):
    if n_clicks > 0:
        Mesowest(sa.radar,str(sa.lat),str(sa.lon),sa.sim_start_str,str(sa.duration))
        return 100, n_clicks
    return PreventUpdate, PreventUpdate

# -------------------------------------
# --- Get Nexrad data ---
# -------------------------------------
@app.callback(
    [Output('run_hodo_script', 'n_clicks'),Output('radar_status', 'value')],
    Input('run_nexrad_script', 'n_clicks'))
def run_nexrad_script(n_clicks):
    if n_clicks > 0:
        NexradDownloader(sa.radar, sa.sim_start_str, sa.duration)
        return n_clicks, 100
    return PreventUpdate, PreventUpdate


# -------------------------------------
# --- Hodo plots ---
# -------------------------------------
@app.callback(
    [Output('run_nse', 'n_clicks'), Output('hodo_status', 'value')],
    Input('run_hodo_script', 'n_clicks'))
def run_hodo_script(args):
    subprocess.run(["python", sa.hodo_script_path] + args, check=True)
    return

# -------------------------------------
# --- NSE placefiles
# -------------------------------------
@app.callback(
    [Output('run_transpose_script', 'n_clicks'), Output('nse_status', 'value')],
    Input('run_nse', 'n_clicks'))
def run_nse_script(n_clicks):
    if n_clicks > 0:
        sa.shift_placefiles(sa.placefiles_dir)
        return n_clicks, 100
    return PreventUpdate, PreventUpdate

# -------------------------------------
# --- Transpose if transpose radar selected
# -------------------------------------
@app.callback(
    Output('transpose_status', 'value'),
    Input('run_transpose_script', 'n_clicks'))
def run_transpose_script(n_clicks):
    if sa.t_radar == 'None':
        return 100
    if n_clicks > 0:
        sa.shift_placefiles(sa.placefiles_dir)
        return 100
    return 0

################################################################################################
# ---------------------------------------- Radar Graph Callbacks -------------------------------------
################################################################################################

@app.callback(
    Output('graph-container', 'style'),
    Input('map_btn', 'n_clicks'))
def toggle_map_display(n):
    if n%2 == 0:
        return {'display': 'none'}
    else:
        return {'padding-bottom': '2px', 'padding-left': '2px','height': '80vh', 'width': '100%'}


@app.callback(
    Output('radar', 'children'),
    [Input('graph', 'clickData')])
def display_click_data(clickData):
    if clickData is None:
        return 'No radars selected ...'
    else:
        print (clickData)
        the_link=clickData['points'][0]['customdata']
        if the_link is None:
            return 'No Website Available'
        else:
            sa.radar = the_link
            sa.lat = lc.df[lc.df['radar'] == sa.radar]['lat'].values[0]
            sa.lon = lc.df[lc.df['radar'] == sa.radar]['lon'].values[0]
            return f'{the_link.upper()}'

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
    sa.make_times()
    line1 = f'Sim Start: {sa.sim_start_str[:-7]}Z ____ Duration: {sa.duration} minutes'
    return line1

@app.callback(Output('start_year', 'value'),Input('start_year', 'value'))
def get_year(start_year):
    sa.start_year = start_year
    return sa.start_year

@app.callback(
    Output('start_day', 'options'),
    [Input('start_year', 'value'), Input('start_month', 'value')])
def update_day_dropdown(selected_year, selected_month):
    _, num_days = calendar.monthrange(selected_year, selected_month)
    day_options = [{'label': str(day), 'value': day} for day in range(1, num_days+1)]
    return day_options


@app.callback(Output('start_month', 'value'),Input('start_month', 'value'))
def get_month(start_month):
    sa.start_month = start_month
    return sa.start_month

@app.callback(Output('start_day', 'value'),Input('start_day', 'value'))
def get_day(start_day):
    sa.start_day = start_day
    return sa.start_day

@app.callback(Output('start_hour', 'value'),Input('start_hour', 'value'))
def get_hour(start_hour):
    sa.start_hour = start_hour
    return sa.start_hour

@app.callback(Output('start_minute', 'value'),Input('start_minute', 'value'))
def get_minute(start_minute):
    sa.start_minute = start_minute
    return sa.start_minute

@app.callback(Output('duration', 'value'),Input('duration', 'value'))
def get_duration(duration):
    sa.duration = duration
    return sa.duration

################################################################################################
# ---------------------------------------- Clock Callbacks ----------------
################################################################################################

@app.callback(
    Output('clock-container', 'style'),
    Input('enable_sim_clock', 'n_clicks'))
def enable_simulation_clock(n):
    if n % 2 == 0:
        return {'display': 'none'}
    else:
        return {'padding-bottom': '2px', 'padding-left': '2px','height': '80vh', 'width': '100%'}


@app.callback(
    Output('clock-output', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_time(_n):
    sa.sim_clock = sa.sim_clock + timedelta(seconds=15)
    return sa.sim_clock.strftime("%Y-%m-%d %H:%M:%S UTC")

################################################################################################
# ---------------------------------------- Call app ----------------
################################################################################################

if __name__ == '__main__':
    #app.run_server(debug=True, host="0.0.0.0", port=8050, threaded=True)
    app.run(debug=True, port=8050, threaded=True)
    
# pathname_params = dict()
# if my_settings.hosting_path is not None:
#     pathname_params["routes_pathname_prefix"] = "/"                                                                                                                                                                                                                              
#     pathname_params["requests_pathname_prefix"] = "/{}/".format(my_settings.hosting_path)   