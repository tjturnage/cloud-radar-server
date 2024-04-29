from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import html, dcc

now = datetime.now(pytz.utc)

df = pd.read_csv('radars.csv', dtype={'lat': float, 'lon': float})
df['radar_id'] = df['radar']
df.set_index('radar_id', inplace=True)
#df['upper'] = [u.upper() for u in list(df.index)]

bold = {'font-weight': 'bold'}

feedback = {'border': '2px gray solid', 'padding':'0.1em', 'font-weight': 'bold',
            'font-size':'1.5em', 'text-align':'center', 'height':'5vh'}

url_rename = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

weekdaynames= ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
monthnames = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December" ]

top_section = html.Div([ ], style={'height': '5px'})

top_content = [
            dbc.CardBody([html.H2("Cloud Radar Simulation Server", className="card-title",
                                  style={'font-weight': 'bold', 'font-style': 'italic'}),
                html.H5(
                    "Providing radar simulations for NOAA/NWS training ...",
                    className="card-text", style={'color':'rgb(52,152,219)', 'font-weight': 'bold', 'font-style': 'italic'}
                ),
                html.H5(
                    "Project funded by FY2024 NOAA Cloud Compute Grant",
                    className="card-text"
                ),
                html.Div([
                dbc.CardLink("GitHub", href="https://github.com/tjturnage/cloud-radar-server")]),
                ])
            ]

step_one_card = [dbc.CardBody([
    html.H5("Step 1: Select Simulation Start Date, Time, and Duration (in Minutes)",className="card-text")])]

step_one_section = html.Div([
                dbc.Card(step_one_card, color="secondary", inverse=True)],
                style={'text-align':'center'},)

step_two_card = [dbc.CardBody([
    html.H5("Step 2: Select radar from Map below",className="card-text")])]

step_two_section = html.Div([
                dbc.Card(step_two_card, color="secondary", inverse=True)],
                style={'text-align':'center'},)


list_radars = [dbc.CardBody([html.H5("Selected Radar(s)", className="card-text")])]



view_output = [
            dbc.CardBody([html.P("Output", className="card-title", style=bold),
                html.P("Results",className="card-text")])
            ]


top_banner = html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col(html.Div(dbc.Card(top_content, color="secondary", inverse=True)), width=9),
                dbc.Col(html.Div(html.Img(src="/assets/radar-web.svg",
                                      style={'display': 'block', 'margin-left': 'auto',
                                             'margin-right': 'auto', 'margin-top': '10px',
                                            'verticalAlign': 'middle', 'width':'70%'})), width=3),
        ],id='test',style={"padding":"1em",'border':'3px gray solid'})],
                      style={"padding":"1.7em", "text-align":"center"}),
    ])


check_values = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([html.Div(id="show_values",style=feedback)])
            )
        ])
    ])

#---------------------------------------------------------------
# Time/duration components
#---------------------------------------------------------------

step_year = [dbc.CardBody([html.P("Year",className="card-text")],style={'height':'5vh'})]
step_month = [dbc.CardBody([html.P("Month", className="card-text")],style={'height':'5vh'})]
step_day = [dbc.CardBody([html.P("Day", className="card-text")],style={'height':'5vh'})]
step_hour = [dbc.CardBody([html.P("Hour", className="card-text")],style={'height':'5vh'})]
step_minute = [dbc.CardBody([html.P("Minute", className="card-text")],style={'height':'5vh'})]
step_duration = [dbc.CardBody([html.P("Duration", className="card-text")],style={'height':'5vh'})]


sim_year_section = dbc.Col(
                    html.Div([
                    dbc.Card(step_year, color="secondary", inverse=True),
                    html.Div(id='year-picker'),
                    dcc.Dropdown(np.arange(1992,now.year + 1),now.year-1,
                                 id='start_year',clearable=False),
                    ]))

sim_month_section = dbc.Col(
                    html.Div([
                        dbc.Card(step_month, color="secondary", inverse=True),      
                        dcc.Dropdown(np.arange(1,13),6,id='start_month',clearable=False),
                        ]))


sim_hour_section = dbc.Col(
                    html.Div([
                        dbc.Card(step_hour, color="secondary", inverse=True),         
                        dcc.Dropdown(np.arange(0,24),18,id='start_hour',clearable=False),
                        ]))

sim_minute_section =  dbc.Col(
                    html.Div([
                        dbc.Card(step_minute, color="secondary", inverse=True),
                        dcc.Dropdown([0,15,30,45],30,id='start_minute',clearable=False),
                        ]))

sim_duration_section = dbc.Col(
                    html.Div([ 
                        dbc.Card(step_duration, color="secondary", inverse=True),
                        dcc.Dropdown(np.arange(0,240,30),60,id='duration',clearable=False),
                        ]))


time_settings_readout = html.Div([
        dbc.Row([
            dbc.Col(
                    html.Div(id='show_time_data',style=feedback)
            )
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'})

store_time_settings_section = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Store time settings and open map to select radar',
                               size="lg", id='store_time_data_btn', n_clicks=0, disabled=False),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'})
radar_id = html.Div(id='radar',style={'display': 'none'})

#---------------------------------------------------------------
# Radar display components
#---------------------------------------------------------------

step_radar = [dbc.CardBody([html.H5("Use map below to select radar(s)", className="card-text")])]

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
    mapbox = {#'accesstoken': TOKEN,
                'style': "carto-darkmatter",
                'center': {'lon': -93.945155, 'lat': 38.80105},
                'zoom': 3.5})


fig.update_layout(uirevision= 'foo', clickmode= 'event+select',
                hovermode='closest', hoverdistance=2,
                margin = {'r':0,'t':0,'l':0,'b':0},)

graph_section = html.Div([
        # html.Div([
        #         dbc.Card(step_radar, color="secondary", inverse=True)],
        #         style={'text-align':'center'},),
        html.Div([dcc.Graph(
                id='graph',
                config={'displayModeBar': False,'scrollZoom': True},
                style={'padding-bottom': '2px', 'padding-left': '2px',
                       'height': '73vh', 'width': '100%'},
                figure=fig)]),
    ], id='graph-container', style={'display': 'none'})


show_radar_section = html.Div([dbc.Row([dbc.Col(html.Div(id='show_radar',style=feedback)),
        ]),])

map_toggle = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                        dbc.Button('Toggle map on/off', size="lg", id='map_btn', n_clicks=0),
                        ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
        ])
        ], style={'padding':'1em', 'vertical-align':'middle'})

#---------------------------------------------------------------
# Transpose component
#---------------------------------------------------------------

transpose_list = sorted(list(df.index))
transpose_list.insert(0, 'None')
transpose_card = [dbc.CardBody([html.H5("Transpose Radar", className="card-text")])]
transpose_radar = dbc.Col(  
                    html.Div([
                    dbc.Card(transpose_card, color="secondary", inverse=True),
                    html.Div(id='transpose-r'),
                    dcc.Dropdown(transpose_list,'None',id='tradar',clearable=False),
                    ]))

#---------------------------------------------------------------
# Run script button
#---------------------------------------------------------------

scripts_button = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Run Scripts',
                               size="lg", id='run_scripts', n_clicks=0),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'})


#---------------------------------------------------------------
# Script status components
#---------------------------------------------------------------
obs_placefile_status_card = [dbc.CardBody([html.P("Placefile status",className="card-text")]
                                      ,style={'height':'5vh'})]
obs_placefile_status = dbc.Col(html.Div([
                    dbc.Card(obs_placefile_status_card, color="secondary", inverse=True),
                    dbc.Progress(id='obs_placefile_status',striped=True, value=0),
                    ]))

radar_status_card = [dbc.CardBody([html.P("Radar data status",className="card-text")],
                                  style={'height':'5vh'})]
radar_status = dbc.Col(html.Div([
                    dbc.Card(radar_status_card, color="secondary", inverse=True),
                    dbc.Progress(id='radar_status',striped=True, value=0),
                    ]))

hodograph_status_card = [dbc.CardBody([html.P("Hodograph status",className="card-text")],
                                      style={'height':'5vh'})]
hodograph_status = dbc.Col(html.Div([
                    dbc.Card(hodograph_status_card, color="secondary", inverse=True),
                    dbc.Progress(id='hodo_status',striped=True, value=0),
                    ]))

nse_status_card = [dbc.CardBody([html.P("NSE placefiles status",className="card-text")],
                                style={'height':'5vh'})]
nse_status = dbc.Col(html.Div([
                    dbc.Card(nse_status_card, color="secondary", inverse=True),
                    dbc.Progress(id='nse_status',striped=True, value=0),
                    ]))

transpose_status_card = [dbc.CardBody([html.P("Transpose status",className="card-text")],
                                style={'height':'5vh'})]
transpose_status = dbc.Col(html.Div([
                    dbc.Card(transpose_status_card, color="secondary", inverse=True),
                    dbc.Progress(id='transpose_status',striped=True, value=0),
                    ]))

status_section = html.Div([dbc.Row([obs_placefile_status, radar_status, hodograph_status, nse_status, transpose_status])])
#---------------------------------------------------------------
# Clock components
#---------------------------------------------------------------

step_sim_clock = [dbc.CardBody([html.H5("Simulation Clock", className="card-text")])]

simulation_clock_slider = dcc.Slider(id='sim_clock', min=0, max=1440, step=1, value=0,
                                     marks={0:'00:00', 240:'04:00'})


toggle_simulation_clock = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                        dbc.Button('Enable Simulation Clock', size="lg", id='enable_sim_clock', n_clicks=0),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}
                ),
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'})


bottom_section = html.Div([ ], style={'height': '500px'})
