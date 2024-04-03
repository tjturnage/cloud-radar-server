"""_summary_

    Returns:
    Main page for radar-server
        _type_: _description_
"""

import os
#import re
#import sys
#import time
from datetime import date
from datetime import datetime
import pytz
import json
import numpy as np

import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash_extensions.javascript import assign
import dash
# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc
# dcc = dash core components
from dash import Dash, html, dcc, Input, Output, State
# State allows the user to enter input before proceeding
import subprocess

# ----------------------------------------
#        Attempt to set up environment
# ----------------------------------------


RADAR_DIR = '.'      # pyany

try:
    os.chdir(RADAR_DIR)
except Exception:
    print("Cant import!")

# ----------------------------------------
#        Set up class then instantiate
# ----------------------------------------

now = datetime.now(pytz.utc)

radar_list = []
rdas = []
with open('radars.gis','r', encoding='utf-8') as fin:
    for line in fin.readlines():
        if line[0][0] == 'k':
            elements = line.split("|")
            radar_list.append(dict(radar=elements[0][-3:].upper(),lat=float(elements[2]),lon=float(elements[3])))
            rdas.append(elements[0][-3:].upper())

class RadarSimulator:
    """
    A class representing a radar simulator.

    Attributes:
        start_time (datetime): The start time of the simulation.
        duration (int): The duration of the simulation in seconds.
        radars (list): A list of radar objects.
        product_directory_list (list): A list of directories in the data directory.

    """

    def __init__(self):
        self.start_year = 2024
        self.start_month = 6
        self.start_day = 15
        self.start_hour = 18
        self.start_minute = 30
        self.duration = 180
        #self.geojson = self.populate_map()
        self.timestring = None
        self.sim_datetime = None
        self.radar = None
        self.lat = None
        self.lon = None


    def populate_map(self):
        """
        generates all the radar sites
        """
        radar_list = []
        rdas = []
        with open('radars.gis','r', encoding='utf-8') as fin:
            for line in fin.readlines():
                if line[0][0] == 'k':
                    elements = line.split("|")
                    radar_list.append(dict(radar=elements[0][-3:].upper(),lat=float(elements[2]),lon=float(elements[3])))
                    rdas.append(elements[0][-3:].upper())
        geojson = dlx.dicts_to_geojson([{**r, **dict(tooltip=r['radar'])} for r in radar_list])
        #with open('radars.json','w') as fout:
        #    fout.write(json.dumps(geojson))
            
        #return geojson
    
# ----------------------------------------
#        Initiate Dash app
# ----------------------------------------

sa = RadarSimulator()

app = dash.Dash(__name__,external_stylesheets=[dbc.themes.CYBORG])
app.title = "Radar Simulator"

# ----------------------------------------
#        Define some webpage layout variables
# ----------------------------------------

bold = {'font-weight': 'bold'}

feedback = {'border': '2px gray solid', 'padding':'0.5em', 'font-weight': 'bold',
            'font-size':'1.5em', 'text-align':'center'}

weekdaynames= ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
monthnames = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December" ]

top_content = [
            dbc.CardBody([html.H1("Cloud Radar Simulation Server", className="card-title",
                                  style={'font-weight': 'bold', 'font-style': 'italic'}),
                html.H4(
                    "Providing radar simulations for National Weather Service training ...",
                    className="card-text", style={'color':'rgb(52,152,219)', 'font-weight': 'bold', 'font-style': 'italic'}
                ),
                html.H5(
                    "Developed by many folks ...",
                    className="card-text",
                ),
                html.Div([
                dbc.CardLink("GitHub", href="https://github.com/tjturnage/cloud-radar-server")]),
                ])
            ]

step_instructions = [
            dbc.CardBody([html.H4("Select Simulation Start Date and Time ... Duration is in Minutes", 
            className="card-text"),])]

step_radar = [
            dbc.CardBody([html.H5("Select Radar", 
            className="card-text"),])]

step_year = [
            dbc.CardBody([html.H5("Year",
            className="card-text"),])]

step_month = [
            dbc.CardBody([html.H5("Month",
            className="card-text"),])]

step_day = [
            dbc.CardBody([html.H5("Day", className="card-text"),])]

step_hour = [
            dbc.CardBody([html.H5("Hour", className="card-text"),])]

step_minute = [
            dbc.CardBody([html.H5("Minute", className="card-text"),])]

step_duration = [
            dbc.CardBody([html.H5("Duration",
                                  className="card-text"),])]

view_output = [
            dbc.CardBody([html.H5("Output", className="card-title", style=bold),
                html.P(
                    "Results",
                    className="card-text",
                ),])]


################################################################################
#      Build Webpage Layout
################################################################################

with open("assets/radars.json") as f:
    data = json.load(f)

markers = [dl.CircleMarker(center=[feature["geometry"]["coordinates"][1], feature["geometry"]["coordinates"][0]], radius=10) for feature in data["features"]]

style_handle = assign("""function(feature, context){
    const {selected} = context.hideout;
    if(selected.includes(feature.properties.name)){
        return {fillColor: 'red', color: 'grey'}
    }
    return {fillColor: 'grey', color: 'grey'}
}""")

def run_script(args):
    subprocess.run(["python", "surface_obs_placefile.py"] + args)
    return

app.layout = dbc.Container(
    html.Div([
        dbc.Row(dbc.Card(top_content, color="secondary", inverse=True)),
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Card(step_instructions, color="secondary", inverse=True)
                    ],style={"padding":"1.2em", "text-align":"center"})
            )
        ]),
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.Div(id="sim_year"),
                    dbc.Card(step_year, color="secondary", inverse=True),
                    html.Div(id='year-picker'),
                    dcc.Dropdown(np.arange(1992,now.year + 1),now.year,id='start_year')
                    ])
                ),
            dbc.Col(
                html.Div([
                    html.Div(id='sim_month'),
                    dbc.Card(step_month, color="secondary", inverse=True),                    
                    dcc.Dropdown(np.arange(1,13),6,id='start_month')
                    ])
                ),
            dbc.Col(
                html.Div([
                    html.Div(id='sim_day'),
                    dbc.Card(step_day, color="secondary", inverse=True),                    
                    dcc.Dropdown(np.arange(1,32),15,id='start_day'
                    ), 
                    ])
                ),
            dbc.Col(
                html.Div([
                    html.Div(id='sim_hour'),
                    dbc.Card(step_hour, color="secondary", inverse=True),                    
                    dcc.Dropdown(np.arange(0,24),18,id='start_hour'
                    ),
                    ])
                ),
            dbc.Col(
                html.Div([
                    html.Div(id='sim_minute'),
                    dbc.Card(step_minute, color="secondary", inverse=True),                    
                    dcc.Dropdown([0,15,30,45],30,id='start_minute'
                    ),
                    ])
                ),
            dbc.Col(
                html.Div([
                    html.Div(id='sim_duration'),                    
                    dbc.Card(step_duration, color="secondary", inverse=True), 
                    dcc.Dropdown(np.arange(0,240,30),120,id='duration'
                    ),
                    ])
                ),
        dbc.Row([
            dbc.Col(
                html.Div([
                dbc.Button("Click Here to Check Selections",id='check_sim_vars', n_clicks=0, style={'padding':'1em','width':'100%'}),
                html.Div(id="show_sim_vars",style=feedback)
                ],
                style={'padding':'1em'},

                )
            ),]),
            ]),
        dbc.Row([
            dbc.Col(
                html.Div([
                    dl.Map(id='radar_map', style={'height': '7vh'},
                    center = [40, -95],zoom=4.6,scrollWheelZoom=False,
                    children=[dl.TileLayer(),
                              dl.GeoJSON(url="/assets/radars.json", zoomToBounds=True, id="geojson",
               hideout=dict(selected=[]), style=style_handle)]),
                            ],
                    ),
        )]),

        dbc.Row([
                    dbc.Col(
                html.Div([
                    dbc.Card(step_radar, color="secondary", inverse=True),
                    dcc.Dropdown(rdas,rdas[0],id='sim_radar'),
                    html.Div(id='show_radar')                    
                    ])
                ),
        ]),
        dbc.Row([
            dbc.Col(
                html.Div([
                dbc.Button("Click to run scripts",id='run_scripts', n_clicks=0, style={'padding':'1em','width':'100%'}),
                html.Div(id="show_script_progress",style=feedback)
                ])
            )
        ])
    ])
)


@app.callback(
    Output("geojson", "hideout"),
    Input("geojson", "n_clicks"),
    State("geojson", "clickData"),
    State("geojson", "hideout"),
    prevent_initial_call=True)
def toggle_select(_, feature, hideout):
    selected = hideout["selected"]
    name = feature["properties"]["radar"]
    if name in selected:
        selected.remove(name)
    else:
        selected.append(name)
    return hideout

@app.callback(
    Output('show_script_progress', 'children'),
    [Input('run_scripts', 'n_clicks')]
)
def update_output(n_clicks):
    if n_clicks > 0:
        run_script([sa.radar,str(sa.lat),str(sa.lon),sa.timestring,str(sa.duration)])
        return "Script has been run"
    else:
        return ""

@app.callback(
Output('sim_year', 'children'),
Input('start_year', 'value'))
def get_year(start_year):
    sa.start_year = start_year
    return

@app.callback(
Output('sim_month', 'children'),
Input('start_month', 'value'))
def get_month(start_month):
    sa.start_month = start_month
    return

@app.callback(
Output('sim_day', 'children'),
Input('start_day', 'value'))
def get_day(start_day):
    sa.start_day = start_day
    return

@app.callback(
Output('show_radar', 'children'),
Input('sim_radar', 'value'))
def get_radar(sim_radar):
    sa.radar = sim_radar
    sa.lat = [item['lat'] for item in radar_list if item['radar'] == sim_radar][0]
    sa.lon = [item['lon'] for item in radar_list if item['radar'] == sim_radar][0]
    return

@app.callback(
Output('show_sim_vars', 'children'),
Input('check_sim_vars', 'n_clicks'))
def get_sim(n_clicks):
    sa.sim_datetime = datetime(sa.start_year,sa.start_month,sa.start_day,sa.start_hour,sa.start_minute,second=0)
    sa.timestring = datetime.strftime(sa.sim_datetime,"%Y-%m-%d %H:%M UTC")
    
    return f'Sim Start _____ {sa.timestring} _____ Duration: {sa.duration} minutes'


@app.callback(
Output('sim_minute', 'children'),
Input('start_minute', 'value'))
def get_minute(start_minute):
    sa.start_minute = start_minute
    return

@app.callback(
Output('sim_duration', 'children'),
Input('duration', 'value'))
def get_duration(duration):
    sa.duration = duration
    return

if __name__ == '__main__':
    app.run_server(debug=True)