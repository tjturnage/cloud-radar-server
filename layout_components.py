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
bold = {'font-weight': 'bold'}

feedback = {'border': '1px gray solid', 'padding':'0.4em', 'font-weight': 'bold',
            'font-size':'1.4em', 'text-align':'center', 'vertical-align': 'center','height':'6vh'}

steps = {'padding':'0.4em', 'border': '0.3em', 'border-radius': '15px','font-weight': 'bold',
         'color':'yellow','background':'#555555', 'font-size':'1.4em', 'text-align':'left', 'height':'vh5'}

steps_right = {'padding':'0.4em', 'border': '0.3em', 'border-radius': '15px','font-weight': 'bold',
               'color':'#06DB42','background':'#555555', 'font-size':'1.4em', 'text-align':'right', 'height':'vh5'}

steps_center = {'padding':'0.4em', 'border': '0.3em', 'border-radius': '15px',
                'font-weight': 'bold', 'color':'#06DB42','background':'#555555', 'font-size':'1.4em',
                'text-align':'center', 'height':'vh5'}


url_rename = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

weekdaynames= ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
monthnames = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December" ]

top_section = html.Div([ ], style={'height': '5px'})
spacer = html.Div([ ], style={'height': '20px'})

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


#---------------------------------------------------------------
# Time/duration components
#---------------------------------------------------------------

STEP_SELECT_TIME = "Select Simulation Start Date, Time, and Duration (in Minutes)"

step_select_time_section = dbc.Container(
    dbc.Col(html.Div(children=STEP_SELECT_TIME,style=steps_center)))

time_headers = {'padding':'0.05em', 'border': '1em', 'border-radius': '12px','background':'#555555',
            'font-size':'1.4em', 'color': 'white','text-align':'center', 'vertical-align': 'top', 'height':'4vh'}

step_year = html.Div(children="Year",style=time_headers)
step_month = html.Div(children="Month",style=time_headers)
step_day = html.Div(children="Day",style=time_headers)
step_hour = html.Div(children="Hour",style=time_headers)
step_minute = html.Div(children="Minute",style=time_headers)
step_duration = html.Div(children="Duration",style=time_headers)

sim_year_section = dbc.Col(html.Div([step_year,
                    dcc.Dropdown(np.arange(1992,now.year + 1),now.year-1,
                    id='start_year',clearable=False),]))

sim_month_section = dbc.Col(html.Div([
                    step_month, dcc.Dropdown(np.arange(1,13),6,id='start_month',clearable=False),]))

sim_hour_section = dbc.Col(html.Div([
                    step_hour, dcc.Dropdown(np.arange(0,24),18,id='start_hour',clearable=False),]))

sim_minute_section =  dbc.Col(html.Div([
                    step_minute, dcc.Dropdown([0,15,30,45],30,id='start_minute',clearable=False),]))

sim_duration_section = dbc.Col(html.Div([
                    step_duration,dcc.Dropdown(np.arange(0,240,30),60,id='duration',clearable=False),]))

CONFIRM_TIMES_TEXT = "Confirm simulation date/time/duration, then proceed below"
confirm_times_section = dbc.Col(html.Div(children=CONFIRM_TIMES_TEXT,style=steps_right))
time_settings_readout = dbc.Col(html.Div(id='show_time_data',style=feedback))
step_time_confirm = dbc.Container(html.Div([dbc.Row([confirm_times_section, time_settings_readout
        ])]))

radar_id = html.Div(id='radar',style={'display': 'none'})

#---------------------------------------------------------------
# Radar map components
#---------------------------------------------------------------

STEP_CHOOSE_FROM_MAP = "Use button at right to display map of radars"

#step_radar_section = dbc.Col(html.Div(children=STEP_CHOOSE_FROM_MAP,style=steps_right))
map_toggle_button = dbc.Col(html.Div([dbc.Button('ClICK HERE TO TOGGLE RADAR MAP DISPLAY', size="lg", id='map_btn', n_clicks=0)],
                                  className="d-grid gap-2 col-12 mx-auto"))


radar_selections_readout = dbc.Col(html.Div(id='show_radar_selections',style=feedback))
radar_select_section = dbc.Container(html.Div([dbc.Row([map_toggle_button,radar_selections_readout])]))

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

radar_map_instruction = dbc.Col(html.Div(children="Click circles to select up to three radars",style=steps_center))

map_section = html.Div([
    radar_map_instruction,
        html.Div([dcc.Graph(
                id='graph',
                config={'displayModeBar': False,'scrollZoom': True},
                style={'padding-bottom': '2px', 'padding-left': '2px',
                       'height': '73vh', 'width': '100%'},
                figure=fig)]),
    ], id='graph-container', style={'display': 'none'})




#---------------------------------------------------------------
# Transpose component
#---------------------------------------------------------------

transpose_list = sorted(list(df.index))
transpose_list.insert(0, 'None')


STEP_TRANSPOSE_TEXT = "Select radar to transpose to (if desired)"
step_transpose_radar = dbc.Col(html.Div(children=STEP_TRANSPOSE_TEXT,style=steps_right))

transpose_radar_dropdown = dbc.Col(html.Div([dcc.Dropdown(transpose_list,'None',id='tradar',
                                                clearable=False)],className="d-grid gap-2 col-10 mx-auto",style={'vertical-align':'bottom'}))
transpose_section = dbc.Container(html.Div([dbc.Row([step_transpose_radar, transpose_radar_dropdown],style={'vertical-align':'bottom'})]))

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
status_headers = {'padding':'0.05em', 'border': '1em', 'border-radius': '12px','background':'#555555',
            'font-size':'1.3em', 'color': 'white','text-align':'center', 'vertical-align': 'top', 'height':'4vh'}

obs_placefile_status_header = html.Div(children="Placefile status",style=status_headers)

obs_placefile_status = dbc.Col(html.Div([obs_placefile_status_header,
                    dbc.Progress(id='obs_placefile_status',striped=True, value=0),]))

radar_status_header = html.Div(children="Radar data status",style=status_headers)
radar_status = dbc.Col(html.Div([radar_status_header,
                    dbc.Progress(id='radar_status',striped=True, value=0),]))

hodo_status_header = html.Div(children="Hodograph status",style=status_headers)
hodograph_status = dbc.Col(html.Div([hodo_status_header,
                    dbc.Progress(id='hodo_status',striped=True, value=0),]))

nse_status_header = html.Div(children="NSE placefile status",style=status_headers)
nse_status = dbc.Col(html.Div([nse_status_header,
                    dbc.Progress(id='nse_status',striped=True, value=0),]))

transpose_status_header = html.Div(children="Transpose status",style=status_headers)
transpose_status = dbc.Col(html.Div([transpose_status_header,
                    dbc.Progress(id='transpose_status',striped=True, value=0),]))

status_section = dbc.Container(dbc.Container(
    html.Div([dbc.Row([obs_placefile_status, radar_status, hodograph_status, nse_status, transpose_status])] )
    ))
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
