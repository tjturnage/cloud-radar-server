"""_summary_

    Returns:
    Main page for radar-server
        _type_: _description_
"""

import os

import subprocess
from datetime import datetime
import calendar
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import pytz

import dash
# State allows the user to enter input before proceeding
from dash import Input, Output, State, dcc, html
# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc

# ----------------------------------------
#        Attempt to set up environment
# ----------------------------------------
TOKEN = 'pk.eyJ1IjoidGp0dXJuYWdlIiwiYSI6ImNsaXoydWQ1OTAyZmYzZmxsM21waWU2N3kifQ.MDNAdaS61MNNmHimdrV7Kg'

SFC_OBS_SCRIPTS_PATH = './scripts/surface_'    # pyany

RADAR_DIR = '.'      # pyany

try:
    os.chdir(RADAR_DIR)
except Exception:
    print("Cant import!")

# ----------------------------------------
#        Set up class then instantiate
# ----------------------------------------

now = datetime.now(pytz.utc)
df = pd.read_csv('radars.gis', sep='|', header=None, names=['radar','wfo','lat','lon', 'elevation','code','state', 'full_name'], dtype={'lat': float, 'lon': float})
df['color'] = np.where(df['code']== 1, 'blue', 'green')
df['caps'] = [r.upper() for r in df['radar']]

fig = go.Figure(go.Scattermapbox(
    mode='markers',
    lon = df['lon'],
    lat = df['lat'],
    marker={'size': 26, 'color' : 'rgb(50,130,245)', 'opacity': 0.6},
    unselected={'marker' : {'opacity':0.4}},
    selected={'marker' : {'opacity':0.6, 'size':30, 'color': 'rgb(255,255,0)'}},
    hoverinfo='text',
    hovertext=df['radar'],
    customdata=df['radar'],
    text=df['radar']))

fig.update_layout(
    mapbox = {'accesstoken': TOKEN,
                'style': "dark",
                'center': {'lon': -93.945155, 'lat': 38.80105},
                'zoom': 3.5})


fig.update_layout(uirevision= 'foo', clickmode= 'event+select', hovermode='closest', 
                hoverdistance=2,
                margin = {'r':0,'t':0,'l':0,'b':0},
                
                )

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
        self.days_in_month = 30
        self.leap_year = False
        self.timestring = None
        self.sim_datetime = None
        self.radar = None
        self.lat = None
        self.lon = None

    
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
            dbc.CardBody([html.H2("Cloud Radar Simulation Server", className="card-title",
                                  style={'font-weight': 'bold', 'font-style': 'italic'}),
                html.H5(
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
            dbc.CardBody([html.H5("Select Simulation Start Date and Time ... Duration is in Minutes", 
            className="card-text"),])]

step_radar = [dbc.CardBody([html.H5("Select Radar", className="card-text")])]

step_year = [dbc.CardBody([html.P("Year",className="card-text")])]

step_month = [dbc.CardBody([html.P("Month", className="card-text")])]

step_day = [dbc.CardBody([html.P("Day", className="card-text")])]

step_hour = [dbc.CardBody([html.P("Hour", className="card-text")])]

step_minute = [dbc.CardBody([html.P("Minute", className="card-text")])]

step_duration = [dbc.CardBody([html.P("Duration", className="card-text")])]

view_output = [
            dbc.CardBody([html.P("Output", className="card-title", style=bold),
                html.P("Results",className="card-text")])
            ]


################################################################################
#      Build Webpage Layout
################################################################################


def run_script(args):
    subprocess.run(["python", "./scripts/surface-obs-placefiles/surface_obs_placefile.py"] + args)
    return

app.layout = dbc.Container(
    html.Div([dbc.Container([
            dbc.Row([
                dbc.Col(html.Div(dbc.Card(top_content, color="secondary", inverse=True)), width=9),
                dbc.Col(html.Div(html.Img(src="/assets/radar-web.svg",
                                      style={'display': 'block', 'margin-left': 'auto',
                                             'margin-right': 'auto', 'margin-top': '10px',
                                            'verticalAlign': 'middle', 'width':'70%'})), width=3),
            ],id='test',style={'border':'3px gray solid'})]),
            dbc.Row([
                dbc.Col(
                    html.Div([
                    dbc.Card(step_instructions, color="secondary", inverse=True)
                    ],style={"padding":"0.4em", "text-align":"center"})
                    )
                ]),
            dbc.Row([
                dbc.Col(
                    html.Div([
                    html.Div(id="sim_year"),
                    dbc.Card(step_year, color="secondary", inverse=True),
                    html.Div(id='year-picker'),
                    dcc.Dropdown(np.arange(1992,now.year + 1),now.year-1,id='start_year')
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
                    dcc.Dropdown(np.arange(1,sa.days_in_month+1),15,id='start_day'
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
                )
        ]),
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button("Click Here to Check Selections",id='check_sim_vars', n_clicks=0, style={'padding':'1em','width':'100%'}),
                    html.Div(id="show_sim_vars",style=feedback)
                        ], style={'padding':'0.4em'}
                        )
                    )
            ]),
    html.Div([
        dbc.Card(step_radar, color="secondary", inverse=True)],style={"text-align":"center"}),
    html.Div([
        dcc.Graph(
            id='graph',
            config={'displayModeBar': False,'scrollZoom': True},
            style={'padding-bottom': '2px', 'padding-left': '2px','height': '80vh', 'width': '100%'},
            figure=fig
            )
        ]),
           
       dbc.Row([
            dbc.Col(
                html.Div(id='show_radar',style=feedback)
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
    Output('show_radar', 'children'),
    [Input('graph', 'clickData')])
def display_click_data(clickData):
    if clickData is None:
        return 'Click on any bubble'
    else:
        print (clickData)
        the_link=clickData['points'][0]['customdata']
        if the_link is None:
            return 'No Website Available'
        else:
            sa.radar = the_link
            sa.lat = df[df['radar'] == sa.radar]['lat'].values[0]
            sa.lon = df[df['radar'] == sa.radar]['lon'].values[0]
            return the_link.upper()
@app.callback(
    Output('show_script_progress', 'children'),
    [Input('run_scripts', 'n_clicks')],
    prevent_initial_call=True
)
def execute_script(n_clicks):
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
    [Output('start_day', 'options'), Output('start_day', 'value')],
    [Input('start_year', 'value'), Input('start_month', 'value')]
)
def update_day_dropdown(selected_year, selected_month):
    _, num_days = calendar.monthrange(selected_year, selected_month)
    day_options = [{'label': str(day), 'value': day} for day in range(1, num_days+1)]
    return day_options, 15


@app.callback(
Output('sim_day', 'children'),
Input('start_day', 'value'))
def get_day(start_day):
    sa.start_day = start_day
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