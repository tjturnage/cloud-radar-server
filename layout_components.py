from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from pathlib import Path


dir_parts = Path.cwd().parts
if 'C:\\' in dir_parts:
    link_base = "http://localhost:8050/assets"
    cloud = False

else:
    link_base = "https://rssic.nws.noaa.gov/assets"
    cloud = True

place_base = f"{link_base}/placefiles"

now = datetime.now(pytz.utc)

spacer = html.Div([ ], style={'height': '30px'})
spacer_mini = html.Div([ ], style={'height': '10px'})

df = pd.read_csv('radars.csv', dtype={'lat': float, 'lon': float})
#df = pd.read_csv('radars_no_tdwr.csv', dtype={'lat': float, 'lon': float})
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


column_label = {'font-weight': 'bold','text-align':'right'}

section_box = {'background-color': '#333333', 'border': '2.5px gray solid'}

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
                    dcc.Dropdown(np.arange(1992,now.year + 1),now.year,
                    id='start_year',clearable=False),]))

sim_month_section = dbc.Col(html.Div([
                    step_month, dcc.Dropdown(np.arange(1,13),5,id='start_month',clearable=False),]))

sim_hour_section = dbc.Col(html.Div([
                    step_hour, dcc.Dropdown(np.arange(0,24),21,id='start_hour',clearable=False),]))

sim_minute_section =  dbc.Col(html.Div([
                    step_minute, dcc.Dropdown([0,15,30,45],45,id='start_minute',clearable=False),]))

sim_duration_section = dbc.Col(html.Div([
                    step_duration,dcc.Dropdown(np.arange(0,240,15),30,id='duration',clearable=False),]))

CONFIRM_TIMES_TEXT = "Confirm start time and duration -->"
confirm_times_section = dbc.Col(html.Div(children=CONFIRM_TIMES_TEXT,style=steps_right))
time_settings_readout = dbc.Col(html.Div(id='show_time_data',style=feedback))
step_time_confirm = dbc.Container(html.Div([dbc.Row([confirm_times_section, time_settings_readout
        ])]))

radar_id = html.Div(id='radar',style={'display': 'none'})

#---------------------------------------------------------------
# Radar map components
#---------------------------------------------------------------

radar_quantity = html.Div(children="Number of radars",style=time_headers)
radar_quantity_section = dbc.Col(html.Div([radar_quantity,spacer_mini,
                    dcc.Slider(1,3,1,value=1,id='radar_quantity'),]))


STEP_CHOOSE_FROM_MAP = "Use button at right to display map of radars"

#step_radar_section = dbc.Col(html.Div(children=STEP_CHOOSE_FROM_MAP,style=steps_right))
map_toggle_button = dbc.Col(html.Div([dbc.Button('Click to toggle radar map on/off', size="lg", id='map_btn', n_clicks=0)],
                                  className="d-grid gap-2 col-12 mx-auto"))

# map_reset_radars = dbc.Col(html.Div([dbc.Button('Reset', size="lg", id='radar_reset_btn', n_clicks=0)],
#                                   className="d-grid gap-2 col-12 mx-auto"))
map_instructions = "Select up to 3 radars for simulation. Most recent selections will be used."
map_instructions_component = dbc.Row(dbc.Col(html.Div(children=map_instructions,style=steps_center)))
radar_selections_readout = dbc.Col(html.Div(id='show_radar_selections',style=feedback))
radar_select_section = dbc.Container(html.Div([map_instructions_component, spacer, dbc.Row([radar_quantity_section,
                                                        map_toggle_button,radar_selections_readout])]))

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
                hovermode='closest', hoverdistance=10,
                margin = {'r':0,'t':0,'l':0,'b':0},)


map_section = html.Div([

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


STEP_TRANSPOSE_TEXT = "Optional: selected radar site to transpose to -->"
step_transpose_radar = dbc.Col(html.Div(children=STEP_TRANSPOSE_TEXT,style=steps_right))

transpose_radar_dropdown = dbc.Col(html.Div([spacer_mini,dcc.Dropdown(transpose_list,'None',id='new_radar_selection',
                                                clearable=False)],className="d-grid gap-2 col-10 mx-auto",style={'vertical-align':'top'}))
transpose_section = dbc.Container(dbc.Container(
    dbc.Container(html.Div([dbc.Row([step_transpose_radar, transpose_radar_dropdown],id='transpose_section')]))))

#---------------------------------------------------------------
# Run script button
#---------------------------------------------------------------

scripts_button = dbc.Container(html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Download and process radar data ... Make Obs/NSE Placefiles ... Make hodo plots', size="lg", id='run_scripts', n_clicks=0),
                    dbc.Button('Cancel all scripts', size="lg", id='cancel_scripts', n_clicks=0, disabled=True, 
                                style={'background-color': '#e25050', 'border-color': '#e25050'}),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
                    html.Div(id='show_script_progress',style=feedback)
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'}))


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
model_status_text = html.P(id='model_status_warning', 
                           style={'color':'red', 
                                  'font-weight':'bold',
                                  'textAlign':'center'})
model_status_table = dash_table.DataTable(id='model_table', 
                                          data=[],
                                          style_cell={'fontSize': 9, 
                                                      'text_align': 'center',
                                                      'color':'black',
                                                      'border': 'none',
                                          },   
                                          style_header={'backgroundColor':'black',
                                                        'color':'white',
                                                        'fontWeight':'bold',
                                          },
                    )
nse_status = dbc.Col(html.Div([nse_status_header, model_status_table, model_status_text]))

transpose_status_header = html.Div(children="Transpose status",style=status_headers)
transpose_status = dbc.Col(html.Div([transpose_status_header,
                    dbc.Progress(id='transpose_status',striped=True, value=0),]))

status_section = dbc.Container(dbc.Container(
    html.Div([dbc.Row([radar_status, transpose_status, obs_placefile_status, nse_status, hodograph_status])] )
    ))

placefiles_banner_text = "Placefile and graphics links"
placefiles_banner = dbc.Row(dbc.Col(html.Div(children=placefiles_banner_text,style=steps_center)))

links_section = dbc.Container(dbc.Container(html.Div(
    [
        spacer_mini,
        spacer_mini,
        placefiles_banner,
        spacer_mini,
        spacer_mini,
        dbc.Row(
            [
                dbc.Col(dbc.ListGroupItem("Copy this polling address into GR2Analyst:"), style={'font-weight': 'bold', 'color':'white', 'border': '1px gray solid','font-size':'1.2em','text-align':'right'}, width=4),
                dbc.Col(dbc.ListGroupItem("https://rssic.nws.noaa.gov/assets/polling"), style={'font-weight': 'bold', 'color':'white', 'border': '1px gray solid','font-size':'1.2em','text-align':'left'}, width=8),
            ],
            style={"display": "flex", "flexWrap": "wrap"},
        ),
        dbc.Row(
            [
                dbc.Col(dbc.ListGroupItem("Graphics"), style={'font-weight': 'bold', 'color':'white', 'border': '1px gray solid','font-size':'1.2em','text-align':'right'}, width=2),
                dbc.Col(dbc.ListGroupItem("Hodographs", href=f"{link_base}/hodographs.html"), width=2),
            ],
            style={"display": "flex", "flexWrap": "wrap"},
        ),
        dbc.Row(
            [
                dbc.Col(dbc.ListGroupItem("Sfc obs"), style={'font-weight': 'bold', 'color':'white', 'border': '1px gray solid', 'font-size':'1.2em','text-align':'right'}, width=2),
                dbc.Col(dbc.ListGroupItem("Regular font", href=f"{place_base}/latest_surface_observations_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("Large font", href=f"{place_base}/latest_surface_observations_lg_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("Small font", href=f"{place_base}/latest_surface_observations_xlg_shifted.txt"), width=2),
            ],
            style={"display": "flex", "flexWrap": "wrap"},
        ),
        dbc.Row(
            [
                dbc.Col(dbc.ListGroupItem("Sfc obs parts"), style={'font-weight': 'bold', 'color':'white','border': '1px gray solid', 'font-size':'1.2em','text-align':'right'}, width=2),
                dbc.Col(dbc.ListGroupItem("Wind", href=f"{place_base}/wind_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
                dbc.Col(dbc.ListGroupItem("Temp", href=f"{place_base}/temp_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("Dwpt", href=f"{place_base}/dwpt_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("Road obs", href=f"{place_base}/road_shifted.txt"), width=2),
            ],
            style={"display": "flex", "flexWrap": "wrap"},
        
        ),
        dbc.Row(
            [
                dbc.Col(dbc.ListGroupItem("NSE Shear"), style={'font-weight': 'bold', 'color':'white','border': '1px gray solid', 'font-size':'1.2em','text-align':'right'}, width=2),
                dbc.Col(dbc.ListGroupItem("Effective", href=f"{place_base}/ebwd_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("0-1 SHR", href=f"{place_base}/shr1_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
                dbc.Col(dbc.ListGroupItem("0-3 SHR", href=f"{place_base}/shr3_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("0-6 SHR", href=f"{place_base}/shr6_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("0-8 SHR", href=f"{place_base}/shr8_shifted.txt"), width=2),

            ],
            style={"display": "flex", "flexWrap": "wrap"},
        
        ),
        dbc.Row(
            [
                dbc.Col(dbc.ListGroupItem("NSE SRH"), style={'font-weight': 'bold', 'color':'white','border': '1px gray solid', 'font-size':'1.2em','text-align':'right'}, width=2),
                dbc.Col(dbc.ListGroupItem("Effective", href=f"{place_base}/esrh_shifted.txt"), width=2),
                dbc.Col(dbc.ListGroupItem("0-500m", href=f"{place_base}/srh500_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
                dbc.Col(dbc.ListGroupItem("Blank"), width=2),
                dbc.Col(dbc.ListGroupItem("Blank"), width=2),

            ],
            style={"display": "flex", "flexWrap": "wrap"},
        
        ),
        dbc.Row(
            [
                dbc.Col(dbc.ListGroupItem("NSE Thermo"), style={'font-weight': 'bold', 'color':'white','border': '1px gray solid', 'font-size':'1.2em','text-align':'right'}, width=2),
                dbc.Col(dbc.ListGroupItem("MLCAPE", href=f"{place_base}/mlcape_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
                dbc.Col(dbc.ListGroupItem("MLCIN", href=f"{place_base}/mlcin_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
                dbc.Col(dbc.ListGroupItem("0-3 MLCP", href=f"{place_base}/cape3km_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
                dbc.Col(dbc.ListGroupItem("0-3 LR", href=f"{place_base}/lr03km_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
                dbc.Col(dbc.ListGroupItem("MUCAPE", href=f"{place_base}/mucape_shifted.txt"), style={'a:hover':{'color':'yellow'}},width=2),
            ],
            style={"display": "flex", "flexWrap": "wrap"},
        
        ), 
        html.P(id="counter"),
    ]
)))
#---------------------------------------------------------------
# Clock components
#---------------------------------------------------------------

step_sim_clock = [dbc.CardBody([html.H5("Simulation Progress", className="card-text")])]

simulation_clock_slider = dcc.Slider(id='sim_clock', min=0, max=1440, step=1, value=0,
                                     marks={0:'00:00', 240:'04:00'})


simulation_clock = html.Div([
        html.Div([
        html.Div([
                dbc.Card(step_sim_clock, color="secondary", inverse=True)],
                style={'text-align':'center'},),
                #simulation_clock_slider,

        html.Div(id='clock-output', style=feedback),

        ], id='clock-container', style={'padding':'1em', 'vertical-align':'middle'}),
    ])


# toggle_simulation_clock = html.Div([
#         dbc.Row([
#             dbc.Col(
#                 html.Div([
#                         dbc.Button('Enable Simulation Clock', size="lg", id='enable_sim_clock', n_clicks=0),
#                     ], className="d-grid gap-2"), style={'vertical-align':'middle'}
#                 ),
#         ])
#             ], style={'padding':'1em', 'vertical-align':'middle'})


bottom_section = html.Div([ ], style={'height': '500px'})
