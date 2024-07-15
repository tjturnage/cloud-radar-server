import time
from uuid import uuid4
import diskcache
from dash import Dash, html, DiskcacheManager, CeleryManager, Input, Output, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta 
import subprocess
import boto3
import botocore
from botocore.client import Config
from pathlib import Path
import os 
import calendar

import layout_components as lc

class RadarSimulator(Config):
    """
    A class representing a radar simulator.

    Attributes:
        start_time (datetime): The start time of the simulation.
        duration (int): The duration of the simulation in seconds.
        radars (list): A list of radar objects.
        product_directory_list (list): A list of directories in the data directory.

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


launch_uid = uuid4()
cache = diskcache.Cache("./cache")

background_callback_manager = DiskcacheManager(
    cache, cache_by=[lambda: launch_uid], expire=60
)

sa = RadarSimulator()
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
           background_callback_manager=background_callback_manager)

app.layout = dbc.Container([
    dcc.Store(id='dummy1'), 
    dcc.Store(id='dummy2'), 
    dcc.Store(id='dummy3'), 
    dcc.Store(id='dummy4'),
    lc.scripts_button,
    lc.status_section,
    html.Button(id='cancel_button_id', children='Cancel all requests'),
    ])  # end of app.layout

def calculate_percent_progress(iteration, total):
    percent = int((iteration / total) * 100)
    f_percent = f"{int(percent)} %"
    return percent, f_percent


def slow_process_1(set_progress):
    """
    """
    total = 10
    for i in range(total):
        time.sleep(0.5)
        percent, f_percent = calculate_percent_progress(iteration=i+1, total=total)
        set_progress([int(percent), f"{int(percent)} %"])

def slow_process_2(set_progress):
    """
    """
    total = 20
    for i in range(total):
        time.sleep(0.5)
        percent, f_percent = calculate_percent_progress(iteration=i+1, total=total)
        set_progress([int(percent), f"{int(percent)} %"])

def slow_process_3(set_progress):
    """
    """
    total = 30
    for i in range(total):
        time.sleep(0.5)
        percent, f_percent = calculate_percent_progress(iteration=i+1, total=total)
        set_progress([int(percent), f"{int(percent)} %"])
    print("end of slow_process_3")

def slow_process_4(set_progress):
    """
    """
    total = 50
    for i in range(total):
        time.sleep(0.5)
        percent, f_percent = calculate_percent_progress(iteration=i+1, total=total)
        set_progress([int(percent), f"{int(percent)} %"])

# Long callback 1 for mesowest placefiles
@app.callback(
    Output("dummy1", "data"),
    Input("run_scripts_btn", "n_clicks"),
    running=[
        (Output("run_scripts_btn", "disabled"), True, False),
        (Output("cancel_button_id", "disabled"), False, True),
    ],
    cancel=[Input("cancel_button_id", "n_clicks")],
    progress=[
        Output("placefile_status", "value"),
        Output("placefile_status", "label"),
    ],
    interval=1000,
    background=True,
    prevent_initial_call=True
)
def launch_mesowest(set_progress, n_clicks):
    if n_clicks > 0:
        #Mesowest(sa.radar,str(sa.lat),str(sa.lon),sa.sim_start_str,str(sa.duration))
        slow_process_1(set_progress) 
    return

# Long callback 2 for radar downloads
@app.callback(
    Output("dummy2", "data"),
    Input("run_scripts_btn", "n_clicks"),
    running=[
        (Output("run_scripts_btn", "disabled"), True, False),
        (Output("cancel_button_id", "disabled"), False, True),
    ],
    cancel=[Input("cancel_button_id", "n_clicks")],
    progress=[
        Output("radar_status", "value"),
        Output("radar_status", "label"),
    ],
    interval=1000,
    background=True,
    prevent_initial_call=True
)
def get_nexrad(set_progress, n_clicks):
    if n_clicks > 0:
        #NexradDownloader(sa.radar, sa.sim_start_str, sa.duration)
        slow_process_2(set_progress) 
    return

# Long callback 3 for hodographs
@app.callback(
    Output("dummy3", "data"),
    Input("run_scripts_btn", "n_clicks"),
    running=[
        (Output("run_scripts_btn", "disabled"), True, False),
        (Output("cancel_button_id", "disabled"), False, True),
    ],
    cancel=[Input("cancel_button_id", "n_clicks")],
    progress=[
        Output("hodo_status", "value"),
        Output("hodo_status", "label"),
    ],
    interval=1000,
    background=True,
    prevent_initial_call=True
)
def create_hodographs(set_progress, n_clicks):
    if n_clicks > 0:
        #run_hodo_script([sa.radar.upper()])
        slow_process_3(set_progress) 
    return

# Long callback 4 for NSE placefiles
@app.callback(
    Output("dummy4", "data"),
    Input("run_scripts_btn", "n_clicks"),
    running=[
        (Output("run_scripts_btn", "disabled"), True, False),
        (Output("cancel_button_id", "disabled"), False, True),
    ],
    cancel=[Input("cancel_button_id", "n_clicks")],
    progress=[
        Output("nse_status", "value"),
        Output("nse_status", "label"),
    ],
    interval=1000,
    background=True,
    prevent_initial_call=True
)
def create_placefiles(set_progress, n_clicks):
    if n_clicks > 0:
        #start_string = datetime.strftime(sa.sim_start,"%Y-%m-%d/%H")
        #end_string = datetime.strftime(sa.sim_end,"%Y-%m-%d/%H")
        start_string = "2024-04-21/00"
        end_string = "2024-04-21/02"
        args = f"-s {start_string} -e {end_string} -statuspath {sa.data_dir}".split()
        #get_data_status = subprocess.run(
        #    ["python", f"./scripts/meso/get_data.py"] + args
        #)
        slow_process_4(set_progress) 
    return

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1")