import dash
from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State

now = datetime.now(pytz.utc)

df = pd.read_csv('radars.csv', dtype={'lat': float, 'lon': float})
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
    mapbox = {#'accesstoken': TOKEN,
                'style': "carto-darkmatter",
                'center': {'lon': -93.945155, 'lat': 38.80105},
                'zoom': 3.5})


fig.update_layout(uirevision= 'foo', clickmode= 'event+select', hovermode='closest', 
                hoverdistance=2,
                margin = {'r':0,'t':0,'l':0,'b':0},
                
                )


bold = {'font-weight': 'bold'}

feedback = {'border': '2px gray solid', 'padding':'0.5em', 'font-weight': 'bold',
            'font-size':'1.5em', 'text-align':'center'}

url_rename = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

weekdaynames= ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
monthnames = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December" ]

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


first_content = html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col(html.Div(dbc.Card(top_content, color="secondary", inverse=True)), width=9),
                dbc.Col(html.Div(html.Img(src="/assets/radar-web.svg",
                                      style={'display': 'block', 'margin-left': 'auto',
                                             'margin-right': 'auto', 'margin-top': '10px',
                                            'verticalAlign': 'middle', 'width':'70%'})), width=3),
            ],id='test',style={"padding":"1em",'border':'3px gray solid'})],style={"padding":"1.7em", "text-align":"center"}),
    ])

graph_section =  html.Div([
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
    ], id='graph-container', style={'display': 'none'})

scripts_button = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Make Obs Placefile ... Download radar data ... Make hodo plots', size="lg", id='run_scripts', n_clicks=0),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
                    html.Div(id='show_script_progress',style=feedback)
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'})

check_values = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                #dbc.Button("Click to check values", size="lg", id='check_values', n_clicks=0, style={'padding':'1em','width':'100%'}),
                html.Div(id="show_values",style=feedback)
                ])
            )
        ])
    ])

show_radar_section = html.Div([dbc.Row([dbc.Col(html.Div(id='show_radar',style=feedback)),
        ]),])
#show_radar_section = html.Div([dbc.Row([dbc.Col(html.Div(id='show_radar',style={'display': 'none'})),
#        ]),])


map_toggle = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                            dbc.Button('Toggle map on/off', size="lg", id='map_btn', n_clicks=0),
                        ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
        ])
        ], style={'padding':'1em', 'vertical-align':'middle'})

graph_section = html.Div([
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
    ], id='graph-container', style={'display': 'none'})

toggle_simulation_clock = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Toggle Simulation Clock', size="lg", id='start_sim', n_clicks=0),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}
                ),
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'})

simulation_clock_slider = dcc.Slider(id='sim_clock', min=0, max=1440, step=1, value=0, marks={0:'00:00', 240:'04:00', 480:'08:00', 720:'12:00', 960:'16:00', 1200:'20:00', 1440:'00:00'})


simulation_clock = html.Div([
        html.Div([
        html.Div([
                dbc.Card(step_sim_clock, color="secondary", inverse=True)],
                style={'text-align':'center'},),
                simulation_clock_slider,
            dcc.Interval(
                id='interval-component',
                interval=15*1000, # in milliseconds
                n_intervals=0
                ),
        html.Div(id='clock-output', style=feedback),

        ], id='clock-container', style={'display': 'none'}), 
    ])



sim_duration_section = dbc.Col(
                    html.Div([ 
                        dbc.Card(step_duration, color="secondary", inverse=True),
                        dcc.Dropdown(np.arange(0,240,30),120,id='duration',clearable=False),
                        ])
                    )

sim_year_section = dbc.Col(
                    
                    html.Div([
                    dbc.Card(step_year, color="secondary", inverse=True),
                    html.Div(id='year-picker'),
                    dcc.Dropdown(np.arange(1992,now.year + 1),now.year-1,id='start_year',clearable=False),
                    ])
                )

sim_month_section = dbc.Col(
                    html.Div([
                        dbc.Card(step_month, color="secondary", inverse=True),      
                        dcc.Dropdown(np.arange(1,13),6,id='start_month',clearable=False),
                        ])
                    )


sim_hour_section = dbc.Col(
                    html.Div([
                        dbc.Card(step_hour, color="secondary", inverse=True),         
                        dcc.Dropdown(np.arange(0,24),18,id='start_hour',clearable=False),
                        ])
                    )

sim_minute_section =  dbc.Col(
                    html.Div([
                        dbc.Card(step_minute, color="secondary", inverse=True),
                        dcc.Dropdown([0,15,30,45],30,id='start_minute',clearable=False),
                        ])
                    )

store_settings_section = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    dbc.Button('Store settings and begin data processing', size="lg", id='sim_data_store_btn', n_clicks=0, disabled=True),
                    ], className="d-grid gap-2"), style={'vertical-align':'middle'}),
                    html.Div(id='sim_data_store_status',style=feedback)
        ])
            ], style={'padding':'1em', 'vertical-align':'middle'})
radar_id = html.Div(id='radar',style={'display': 'none'})
top_section = html.Div([ ], style={'height': '5px'})
bottom_section = html.Div([ ], style={'height': '500px'})