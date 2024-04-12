"""_summary_

    Returns:
    Main page for radar-server
        _type_: _description_
"""

import os

import subprocess
from datetime import datetime, timedelta
import calendar
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import pytz
from pathlib import Path

import dash
# State allows the user to enter input before proceeding
from dash import html, dcc, Input, Output, State, callback
from dash.exceptions import PreventUpdate
# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc

# ----------------------------------------
#        Attempt to set up environment
# ----------------------------------------
TOKEN = 'pk.eyJ1IjoidGp0dXJuYWdlIiwiYSI6ImNsaXoydWQ1OTAyZmYzZmxsM21waWU2N3kifQ.MDNAdaS61MNNmHimdrV7Kg'

    # pyany

SFC_OBS_SCRIPTS_PATH = Path.cwd() / 'obs_placefile.py'
CSV_PATH = Path.cwd() / 'radars.csv'

# ----------------------------------------
#        Set up class then instantiate
# ----------------------------------------

now = datetime.now(pytz.utc)

df = pd.read_csv(CSV_PATH, dtype={'lat': float, 'lon': float})
df['radar_id'] = df['radar']
df.set_index('radar_id', inplace=True)


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
        self.sim_datetime = datetime(self.start_year,self.start_month,self.start_day,self.start_hour,self.start_minute,second=0)
        self.sim_clock = None
        self.radar = None
        self.lat = None
        self.lon = None

    
# ----------------------------------------
#        Initiate Dash app
# ----------------------------------------

sa = RadarSimulator()

app = dash.Dash(__name__,external_stylesheets=[dbc.themes.CYBORG])
app.title = "Radar Simulator"
# Add this line where you define your app's layout

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

step_radar = [dbc.CardBody([html.H5("Use map below to select radar(s)", className="card-text")])]

list_radars = [dbc.CardBody([html.H5("Selected Radar(s)", className="card-text")])]

step_year = [dbc.CardBody([html.P("Year",className="card-text")])]

step_month = [dbc.CardBody([html.P("Month", className="card-text")])]

step_day = [dbc.CardBody([html.P("Day", className="card-text")])]

step_hour = [dbc.CardBody([html.P("Hour", className="card-text")])]

step_minute = [dbc.CardBody([html.P("Minute", className="card-text")])]

step_duration = [dbc.CardBody([html.P("Duration", className="card-text")])]

step_sim_clock = [dbc.CardBody([html.H5("Simulation Clock", className="card-text")])]

view_output = [
            dbc.CardBody([html.P("Output", className="card-title", style=bold),
                html.P("Results",className="card-text")])
            ]


################################################################################
#      Build Webpage Layout
################################################################################


app.layout = dbc.Container([
    dcc.Store(id='sim_store'),
    html.Div([ ], style={'height': '5px'}),
    html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col(html.Div(dbc.Card(top_content, color="secondary", inverse=True)), width=9),
                dbc.Col(html.Div(html.Img(src="/assets/radar-web.svg",
                                      style={'display': 'block', 'margin-left': 'auto',
                                             'margin-right': 'auto', 'margin-top': '10px',
                                            'verticalAlign': 'middle', 'width':'70%'})), width=3),
            ],id='test',style={"padding":"1em",'border':'3px gray solid'})],style={"padding":"1.7em", "text-align":"center"}),
    ]),
    html.Div([
        dbc.Row([                  
                dbc.Col(
                    
                    html.Div([
                    html.Div(id='sim_year'),
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
                        ) 
                        ])
                    ),
                dbc.Col(
                    html.Div([
                        html.Div(id='sim_hour'),
                        dbc.Card(step_hour, color="secondary", inverse=True),         
                        dcc.Dropdown(np.arange(0,24),18,id='start_hour'),
                        ])
                    ),
                dbc.Col(
                    html.Div([
                        html.Div(id='sim_minute'),
                        dbc.Card(step_minute, color="secondary", inverse=True),
                        dcc.Dropdown([0,15,30,45],30,id='start_minute'),
                        ])
                    ),
                dbc.Col(
                    html.Div([ 
                        html.Div(id='sim_duration'),  
                        dbc.Card(step_duration, color="secondary", inverse=True),
                        dcc.Dropdown(np.arange(0,240,30),120,id='duration'),
                        ])
                    )
        ])
    ],style={'padding':'1em'}),
    
    html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                dbc.Button("Click to check values", size="lg", id='check_values', n_clicks=0, style={'padding':'1em','width':'100%'}),
                html.Div(id="show_values",style=feedback)
                ])
            )
        ])
    ]),
        html.Div([
       dbc.Row([
            dbc.Col(html.Div(id='show_radar',style=feedback)),
        ]),
    ]),    
    html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                            dbc.Button('Toggle map on/off', size="lg", id='map_btn', n_clicks=0),
                        ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
        ])
        ], style={'padding':'1em', 'vertical-align':'middle'}),
    
    html.Div([
        html.Div([
                dbc.Card(step_radar, color="secondary", inverse=True)],
                style={'text-align':'center'},),
        html.Div([dcc.Graph(
                id='graph',
                config={'displayModeBar': False,'scrollZoom': True},
                style={'padding-bottom': '2px', 'padding-left': '2px','height': '73vh', 'width': '100%'},
                figure=fig
                )
                ]),
    ], id='graph-container', style={'display': 'none'}),
    html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Run Obs Placefile', size="lg", id='run_scripts', n_clicks=0),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
                    html.Div(id='show_script_progress',style=feedback)
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'}),

    html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Store settings and begin data processing', size="lg", id='sim_data_store_btn', n_clicks=0),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
                    html.Div(id='sim_data_store_status',style=feedback)
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'}),
    html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Toggle Simulation Clock', size="lg", id='start_sim', n_clicks=0),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}
                ),
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'}),
    
    html.Div([
        html.Div([
        html.Div([
                dbc.Card(step_sim_clock, color="secondary", inverse=True)],
                style={'text-align':'center'},),
            dcc.Interval(
                id='interval-component',
                interval=15*1000, # in milliseconds
                n_intervals=0
                ),
        html.Div(id='clock-output', style=feedback)
        ], id='clock-container', style={'display': 'none'}), 
    ]),

    html.Div([ ], style={'height': '500px'}),
])  # end of app.layout

# ---------------------------------------- Run Scripts ---------------------
################################################################################

def run_obs_script(args):
    subprocess.run(["python", SFC_OBS_SCRIPTS_PATH] + args)
    return


@app.callback(
    Output('sim_data_store_status', 'children'),
    Input('sim_data_store_btn', 'n_clicks'),
    #State('sim_store', 'data'))
)
def store_sim_properties(n_clicks):
    if n_clicks is None:
        raise PreventUpdate
    # Store data in a dictionary
    data = {
        'sim_datetime': sa.sim_datetime,
        'timestring': sa.timestring,
        'duration': sa.duration,
        'radar': sa.radar,
    }
    return str(data)

@app.callback(
    Output('show_script_progress', 'children'),
    [Input('run_scripts', 'n_clicks')],
    prevent_initial_call=True)
def launch_obs_script(n_clicks):
    if n_clicks > 0:
        run_obs_script([sa.radar,str(sa.lat),str(sa.lon),sa.timestring,str(sa.duration)])
        return "Script has been run"
    else:
        return ""

# @callback(Output('{}-clicks'.format(store), 'children'),
#                 # Since we use the data prop in an output,
#                 # we cannot get the initial data on load with the data prop.
#                 # To counter this, you can use the modified_timestamp
#                 # as Input and the data as State.
#                 # This limitation is due to the initial None callbacks
#                 # https://github.com/plotly/dash-renderer/pull/81
#                 Input(store, 'modified_timestamp'),
#                 State(store, 'data'))
# def on_data(ts, data):
#     if ts is None:
#         raise PreventUpdate

#     data = data or {}

#     return data.get('clicks', 0)



# ---------------------------------------- Clock Callbacks ---------------------
################################################################################

@app.callback(
    Output('clock-output', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_time(n):
    sa.sim_datetime = sa.sim_datetime + timedelta(seconds=15)
    # create datetime object from timestamp
    return sa.sim_datetime.strftime("%Y-%m-%d %H:%M:%S UTC")

# ---------------------------------------- Graph Callbacks ----------------------------------------

@app.callback(
    Output('clock-container', 'style'),
    Input('start_sim', 'n_clicks'))
def toggle_simulation_clock(n):
    if n % 2 == 0:
        return {'display': 'none'}
    else:
        return {'padding-bottom': '2px', 'padding-left': '2px','height': '80vh', 'width': '100%'}

@app.callback(
    Output('graph-container', 'style'),
    Input('map_btn', 'n_clicks'))
def toggle_map_display(n):
    if n % 2 == 1:
        return {'display': 'none'}
    else:
        return {'padding-bottom': '2px', 'padding-left': '2px','height': '80vh', 'width': '100%'}


@app.callback(
    Output('show_radar', 'children'),
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
            sa.lat = df[df['radar'] == sa.radar]['lat'].values[0]
            sa.lon = df[df['radar'] == sa.radar]['lon'].values[0]
            return f'Selected Radar -- {the_link.upper()}'



################################################################################
# ---------------------------------------- Time Callbacks ----------------------
################################################################################

@app.callback(
Output('show_values', 'children'),
Input('check_values', 'n_clicks'))
def get_sim(n_clicks):
    sa.sim_datetime = datetime(sa.start_year,sa.start_month,sa.start_day,sa.start_hour,sa.start_minute,second=0)
    #sa.sim_timestamp = sa.sim_datetime.strftime('%Y-%m-%d %H:%M:%S').timestamp()
    sa.timestring = datetime.strftime(sa.sim_datetime,"%Y-%m-%d %H:%M UTC")
    if sa.radar is None:
        sa.radar = 'RADAR SELECTION REQUIRED!'
    line1 = f'Sim Start: {sa.timestring} ____ Duration: {sa.duration} minutes ____ Radar: {sa.radar.upper()}'
    return line1

@app.callback(Output('sim_year', 'children'),Input('start_year', 'value'), suppress_callback_exceptions=True)
def get_year(start_year):
    sa.start_year = start_year
    return

@app.callback(
    Output('start_day', 'options'),
    [Input('start_year', 'value'), Input('start_month', 'value')])
def update_day_dropdown(selected_year, selected_month):
    _, num_days = calendar.monthrange(selected_year, selected_month)
    day_options = [{'label': str(day), 'value': day} for day in range(1, num_days+1)]
    return day_options


@app.callback(Output('sim_month', 'children'),Input('start_month', 'value'))
def get_month(start_month):
    sa.start_month = start_month
    return

@app.callback(Output('sim_day', 'children'),Input('start_day', 'value'))
def get_day(start_day):
    sa.start_day = start_day
    return


@app.callback(Output('sim_hour', 'children'),Input('start_hour', 'value'))
def get_hour(start_hour):
    sa.start_hour = start_hour
    return

@app.callback(Output('sim_minute', 'children'),Input('start_minute', 'value'), suppress_callback_exceptions=True)
def get_minute(start_minute):
    sa.start_minute = start_minute
    return

@app.callback(Output('sim_duration', 'children'),Input('duration', 'value'), suppress_callback_exceptions=True)
def get_duration(duration):
    sa.duration = duration
    return




if __name__ == '__main__':
    app.run_server(debug=True, port=8050, threaded=True)