"""
Layout components for the Cloud Radar Simulation Server application    
"""
import os
import ast
import pandas as pd
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dotenv import load_dotenv


def replace_in_dict(input_dict, search_str, replace_str):
    """
    Replace occurrences of search_str with replace_str in the string values of the input dictionary.

    Args:
        input_dict (dict): The dictionary to perform the search and replace on.
        search_str (str): The string to search for.
        replace_str (str): The string to replace with.

    Returns:
        dict: The updated dictionary with replacements made.
    """
    # Convert the dictionary to a string
    dict_str = str(input_dict)

    # Replace search_str with replace_str
    updated_dict_str = dict_str.replace(search_str, replace_str)

    # Convert the string back to a dictionary
    updated_dict = ast.literal_eval(updated_dict_str)

    return updated_dict

load_dotenv()
MAP_TOKEN = os.getenv("MAPBOX_TOKEN")

df = pd.read_csv('radars.csv', dtype={'lat': float, 'lon': float})
df['radar_id'] = df['radar']
df.set_index('radar_id', inplace=True)

spacer = html.Div([], style={'height': '25px'})
spacer_mini = html.Div([], style={'height': '10px'})

obs_c = '#10c4c4'
nse_c = '#bdaf35'
graphics_c = '#cccccc'
#steps_c = '#065c1e'
steps_c = '#05610d'
pad_background = '#202020'
steps_background = '#303030'
feedback_border_radius = '12px'
#'border-radius': '12px',

bold = {'font-weight': 'bold'}

feedback = {'border': '1px gray solid', 'padding': '0.4em',
            'border-radius': feedback_border_radius, 'font-weight': 'bold',
            'font-size': '1.4em', 'text-align': 'center', 'vertical-align': 'middle',
            'height': '6vh'}

feedback_smaller = replace_in_dict(feedback, '1.4em', '1.2em')

feedback_green = {'border': '1px gray solid', 'padding': '0.4em',
                  'border-radius': feedback_border_radius, 'font-weight': 'bold',
                  'font-size': '1.4em', 'text-align': 'center', 'vertical-align': 'middle',
                  'height': '6vh', 'color': 'black', 'background-color': '#06DB42'}

feedback_yellow = replace_in_dict(feedback_green, '#06DB42', '#bfbf19')

playback_times_style = {'border': '1px gray solid', 'padding': '0.4em', 
                        'border-radius': feedback_border_radius,'font-weight': 'bold',
                        'font-size': '1.4em', 'text-align': 'center', 'vertical-align': 'middle',
                        'height': '6vh', 'color': 'white', 'background-color': '#555555'}

steps = {'padding': '0.4em', 'border': '0.3em', 'border-radius': '15px', 'font-weight': 'bold',
         'color': 'yellow', 'background': steps_background, 'font-size': '1.6em', 'text-align': 'left',
         'height': 'vh5'}

steps_right = {'padding': '0.4em', 'border': '0.3em', 'border-radius': '15px',
               'font-weight': 'bold', 'color': '#06DB42', 'background': steps_background,
               'font-size': '1.6em', 'text-align': 'right', 'height': 'vh5'}

confirm_start_time = {'padding': '0.4em', 'border': '0.3em', 'border-radius': '15px',
                        'color': '#cccccc', 'background': steps_background,
                      'font-size': '1.4em', 'text-align': 'center', 'height': 'vh5'}

steps_right_white = replace_in_dict(steps_right, '#06DB42', 'white')
steps_center = replace_in_dict(steps_right, 'right', 'center')
steps_center_sm = replace_in_dict(steps_center, '1.6em', '1.2em')
steps_center_white = replace_in_dict(steps_center, '#06DB42', 'white')
steps_center_white_normal = replace_in_dict(steps_center_white, " 'font-weight': 'bold',", "")

column_label = {'font-weight': 'bold', 'text-align': 'right'}

section_box = {'background-color': '#333333', 'border': '2.5px gray solid'}
section_box_pad = {'background-color': pad_background,
                   'border': '2.5px solid #333333', 'padding': '1em', 'border-radius': '8px'}
top_section_box_pad = replace_in_dict(section_box_pad, '2.5px', '4px')

url_rename = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

weekdaynames = ["Sunday", "Monday", "Tuesday",
                "Wednesday", "Thursday", "Friday", "Saturday"]
monthnames = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]

top_section = html.Div([], style={'height': '5px'})


top_content = [
    dbc.CardBody([html.H2("Radar Simulation Server in the Cloud", className="card-title",
                          style={'font-weight': 'bold', 'font-style': 'italic'}),
                  html.H5(
        "Providing radar simulations for NOAA/NWS training ...",
        className="card-text", style={'color': 'rgb(52,152,219)', 'font-weight': 'bold',
                                      'font-style': 'italic'}),
                  html.H5(
        "Project funded by FY2024 NOAA Cloud Compute Grant",
        className="card-text"
    ),
        spacer_mini,
        dbc.Row([
            html.Hr(style={"borderWidth": "0.5vh", "width": "90%",
                    "margin": "auto", "color": "#cccccc"}),
        ]),
        spacer_mini,
        html.Div([
            dbc.Row([
                dbc.Col(dbc.CardLink(
                    "User Guide", href="https://docs.google.com/document/d/1uAcsjzjTAl6SA4dKgcj3pIpM__X-yfH0OGVsdam4dQw/edit", target="_blank")),
                dbc.Col(dbc.CardLink(
                    "Feedback Form", href="https://docs.google.com/forms/d/e/1FAIpQLScoQhdYa6uoR1sD1f3PUYmNVMLgOn5UDvSkUJXHu4_gpWZ9pw/viewform", target="_blank")),
                dbc.Col(dbc.CardLink(
                    "GitHub", href="https://github.com/tjturnage/cloud-radar-server", target="_blank"))
            ]),
        ])
    ])
]

top_banner = html.Div([
    dbc.Container([
        dbc.Row([
                dbc.Col(
                    html.Div(dbc.Card(top_content, color="secondary", inverse=True)), width=9),
                dbc.Col(html.Div(html.Img(src="/assets/radar-web.svg",
                                          style={'display': 'block', 'margin-left': 'auto',
                                                 'margin-right': 'auto', 'margin-top': '28px',
                                                 'verticalAlign': 'middle', 'width': '80%'})), width=3),
                ], id='test', style=top_section_box_pad)],
        style={"padding": "1.7em", "text-align": "center"}),
])


################################################################################################
# ----------------------------- Upload components  -------------------------------------------
################################################################################################
STEP_UPLOAD_OPTIONAL = "Optional -- Upload a CSV file to create a placefile"

step_upload_optional = dbc.Container(
    dbc.Col(html.Div(children=STEP_UPLOAD_OPTIONAL, style=steps_center)))

upload_feedback_readout = dbc.Col(html.Div(id='show_upload_feedback',
                                          style=feedback), width=12,
                                 style={'vertical-align': 'top'})

upload_component = dbc.Container(
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select a CSV File')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=False
        ),
        html.Div(id='output-data-upload')
    ]),
    className="mb-3"
)

upload_section = dbc.Container(html.Div([
    dbc.Row(step_upload_optional),
    spacer_mini,
    dbc.Row(upload_component),
    dbc.Row(upload_feedback_readout)]))


full_upload_section = dbc.Container(
    dbc.Container([html.Div([upload_section], style=section_box_pad)])
)

################################################################################################
# ----------------------------- Time/duration components  --------------------------------------
################################################################################################

STEP_SELECT_EVENT_TIME = "Select Event Start Date, Time (in UTC), and Duration (in Minutes)"
STEP_SELECT_TIME = "Select Simulation Start Date, Time (in UTC), and Duration (in Minutes)"

step_select_event_time_section = dbc.Container(
    dbc.Col(html.Div(children=STEP_SELECT_EVENT_TIME, style=steps_center)))

time_headers = {'padding': '0.05em', 'border': '1em', 'border-radius': '12px',
                'background': steps_background, 'font-size': '1.4em', 'color': '#cccccc',
                'text-align': 'center', 'vertical-align': 'top', 'height': '4vh'}

smaller_headers = replace_in_dict(time_headers, '1.4em', '1.2em')

step_year = html.Div(children="Year", style=time_headers)
step_month = html.Div(children="Month", style=time_headers)
step_day = html.Div(children="Day", style=time_headers)
step_hour = html.Div(children="Hour", style=time_headers)
step_minute = html.Div(children="Minute", style=time_headers)
step_duration = html.Div(children="Duration", style=time_headers)


CONFIRM_TIMES_TEXT = "Confirm start time and duration"
confirm_times_section = dbc.Col(
    html.Div(children=CONFIRM_TIMES_TEXT, style=confirm_start_time))
time_settings_readout = dbc.Col(html.Div(id='show_time_data', style=feedback))
step_time_confirm = dbc.Container(html.Div([dbc.Row([confirm_times_section, time_settings_readout
                                                     ])]))

radar_id = html.Div(id='radar', style={'display': 'none'})

################################################################################################
# ----------------------------- Radar selection components  ------------------------------------
################################################################################################

radar_quantity = html.Div(children="Number of radars", style=smaller_headers)
radar_quantity_section = dbc.Col(html.Div([  # radar_quantity, spacer_mini,
    dcc.Dropdown(['1 radar', '2 radars', '3 radars'],
                 '1 radar', id='radar_quantity',
                 clearable=False)]), width=2,
    style={'vertical-align': 'middle'})

STEP_CHOOSE_FROM_MAP = "Use button at right to display map of radars"

# step_radar_section = dbc.Col(html.Div(children=STEP_CHOOSE_FROM_MAP,style=steps_right))
map_toggle_button = dbc.Col(html.Div([dbc.Button('Show Radar Map', size="lg",
                                                 id='map_btn', n_clicks=0)],
                                     className="d-grid gap-2 col-12 mx-auto"))

confirm_radars = dbc.Col(html.Div([dbc.Button('Make selections', size="lg",
                                              id='confirm_radars_btn', n_clicks=0, disabled=True)],
                                  className="d-grid gap-2 col-12 mx-auto"))
MAP_INSTRUCT_ONE = "Select number of radars, click Show Radar Map to make selection(s), "
MAP_INSTRUCT_TWO = "click Finalize to confirm"
MAP_INSTRUCTIONS = MAP_INSTRUCT_ONE + MAP_INSTRUCT_TWO
map_instructions_component = dbc.Row(
    dbc.Col(html.Div(children=MAP_INSTRUCTIONS, style=steps_center)))
radar_feedback_readout = dbc.Col(html.Div(id='show_radar_selection_feedback',
                                          style=feedback), width=4,
                                 style={'vertical-align': 'middle'})

radar_select_section = dbc.Container(html.Div([map_instructions_component, spacer,
                                               dbc.Row([radar_quantity_section,
                                                        map_toggle_button,
                                                        radar_feedback_readout,
                                                        confirm_radars
                                                        ])]))

full_radar_select_section = dbc.Container([
    dbc.Container([html.Div([radar_select_section],
                            style=section_box_pad)])])
################################################################################################
# ----------------------------- Radar map components  ------------------------------------------
################################################################################################

fig = go.Figure(go.Scattermapbox(
    mode='markers',
    lon=df['lon'],
    lat=df['lat'],
    marker={'size': 26, 'color': 'rgb(50,130,245)', 'opacity': 0.6},
    unselected={'marker': {'opacity': 0.4}},
    selected={'marker': {'opacity': 0.6,
                         'size': 30, 'color': 'rgb(255,255,0)'}},
    hoverinfo='text',
    hovertext=df['radar'],
    customdata=df['radar'],
    text=df['radar']))

fig.update_layout(
    mapbox={'accesstoken': MAP_TOKEN,
            # 'style': "carto-darkmatter",
            'style': "mapbox://styles/mapbox/dark-v10",
            'center': {'lon': -94.4, 'lat': 38.2},
            'zoom': 3.8})


fig.update_layout(uirevision='foo', clickmode='event+select',
                  hovermode='closest', hoverdistance=15,
                  margin={'r': 0, 't': 0, 'l': 0, 'b': 0},)


map_section_style = {'padding-bottom': '2px', 'padding-left': '2px',
                     'height': '72vh', 'width': '100%'}
map_section = html.Div([
    html.Div([dcc.Graph(
        id='graph',
        config={'displayModeBar': False, 'scrollZoom': True},
        style=map_section_style,
        figure=fig)]),
], id='graph-container', style={'display': 'none'})

################################################################################################
# ----------------------------- Transpose component  -------------------------------------------
################################################################################################

transpose_list = sorted(list(df.index))
transpose_list.insert(0, 'None')

STEP_TRANSPOSE_TEXT = "Optional -- Select a radar site to transpose to"

step_transpose_radar = dbc.Col(
    children=STEP_TRANSPOSE_TEXT, style=steps_center)
transpose_radar_dropdown = dbc.Col(html.Div([spacer_mini, dcc.Dropdown(transpose_list, 'None',
                                            id='new_radar_selection', clearable=False)],
                                            className="d-grid gap-2 col-10 mx-auto",
                                            style={'vertical-align': 'top'}))

allow_transpose_section = dbc.Container(dbc.Container(
    dbc.Container(html.Div([dbc.Row([step_transpose_radar, transpose_radar_dropdown],
                                    id='allow_transpose_id', style={'display': 'none'})]))))

# ----------------------------------------------------------------------------------------------
# Skip transpose notificiation section displayed when more than one radar is selected
# ----------------------------------------------------------------------------------------------
STEP_SKIP_TRANSPOSE_TEXT = "Radar Transpose option skipped since more than one radar selected ..."
skip_transpose = dbc.Col(
    html.Div(children=STEP_SKIP_TRANSPOSE_TEXT, style=steps_center))
skip_transpose_section = dbc.Container(dbc.Container(
    dbc.Container(html.Div([dbc.Row([skip_transpose],
                                    id='skip_transpose_id', style={'display': 'none'})]))))


full_transpose_section = dbc.Container([
    dbc.Container([html.Div([skip_transpose_section, allow_transpose_section, spacer_mini],
                            id='full_transpose_section_id',
                            style={'display': 'none'})]),])
# style= section_box_pad
################################################################################################
# ----------------------------- Run Script button  ---------------------------------------------
################################################################################################
RUN_SCRIPTS_TEXT = "Run scripts to set up simulation"
scripts_step = dbc.Col(html.Div(children=RUN_SCRIPTS_TEXT, style=steps_center))
run_scripts_button = dbc.Col(html.Div([dbc.Button('Run Scripts',
                                                  size="lg", id='run_scripts_btn',
                                                  n_clicks=0, disabled=True)],
                                      className="d-grid gap-2 col-12 mx-auto"))
cancel_scripts_button = dbc.Col(html.Div([dbc.Button('Cancel Scripts', color='danger',
                                                     size="lg", id='cancel_scripts',
                                                     n_clicks=0, disabled=True)],
                                         className="d-grid gap-2 col-12 mx-auto"))
scripts_button_row = dbc.Row([run_scripts_button, cancel_scripts_button])
show_script_progress = html.Div(id='show_script_progress', style=feedback)

scripts_button = dbc.Container(
    dbc.Container(html.Div([
        scripts_step, spacer, scripts_button_row, spacer_mini,
        show_script_progress], id='run_scripts_sction', style=section_box_pad))
                  )


################################################################################################
# ----------------------------- Script status components  --------------------------------------
################################################################################################

status_headers = {'padding': '0.05em', 'border': '1em', 'border-radius': '12px',
                  'background': '#555555', 'font-size': '1.3em', 'color': 'white',
                  'text-align': 'center', 'vertical-align': 'top', 'height': '4vh'}

obs_placefile_status_header = html.Div(
    children="Placefile status", style=status_headers)

obs_placefile_status = dbc.Col(html.Div([obs_placefile_status_header,
                                         html.P(id='obs_placefile_status',
                                                style={'color': 'white',
                                                       'font-weight': 'bold',
                                                       'textAlign': 'center'}),]))

radar_status_header = html.Div(
    children="Radar data status", style=status_headers)
radar_status = dbc.Col(html.Div([radar_status_header,
                                 dbc.Progress(id='radar_status', striped=True, value=0),]))

hodo_status_header = html.Div(
    children="Hodograph status", style=status_headers)
hodograph_status = dbc.Col(html.Div([hodo_status_header,
                                     dbc.Progress(id='hodo_status', striped=True, value=0),]))

nse_status_header = html.Div(
    children="NSE placefile status", style=status_headers)
model_status_text = html.P(id='model_status_warning',
                           style={'color': 'red',
                                  'font-weight': 'bold',
                                  'textAlign': 'center'})
model_status_table = dash_table.DataTable(id='model_table',
                                          data=[],
                                          style_cell={'fontSize': 9,
                                                      'text_align': 'center',
                                                      'color': 'black',
                                                      'border': 'none',
                                                      },
                                          style_header={'backgroundColor': 'black',
                                                        'color': 'white',
                                                        'fontWeight': 'bold',
                                                        },
                                          )
nse_status = dbc.Col(
    html.Div([nse_status_header, model_status_table, model_status_text]))

transpose_status_header = html.Div(
    children="Transpose status", style=status_headers)
transpose_status = dbc.Col(html.Div([transpose_status_header,
                                     dbc.Progress(id='transpose_status', striped=True, value=0),]))

status_section = dbc.Container(dbc.Container(
    html.Div([spacer_mini,spacer_mini,
        dbc.Row([radar_status, transpose_status,
             obs_placefile_status, nse_status, hodograph_status])])
))

################################################################################################
# ----------------------------- Polling section  --------------------------------------------
################################################################################################

PLACEFILES_BANNER_TEXT = "Set up GR2Analyst polling and add placefiles using links below"
placefiles_banner = dbc.Row(
    dbc.Col(html.Div(children=PLACEFILES_BANNER_TEXT, style=steps_center)))

group_item_style = {'font-weight': 'bold', 'color': '#bbbbbb', 'border-right': '1.5px solid #10c4c4',
                    'font-size': '1.0em', 'text-align': 'right'}

group_item_style_links = {'font-weight': 'bold', 'color': '#ffffff', 'border-right': '1.5px solid #ffffff',
                    'font-size': '1.0em', 'text-align': 'right'}

group_header_style = {'padding': '0.1em','font-weight': 'bold', 'font-style': 'italic', 'color': 'white',
                    'font-size': '1.3em', 'text-align': 'left', 'text-decoration': 'underline'}

polling_address_label = {'padding': '0.4em','border': '0.3em', 'border-radius': '10px',
                    'font-weight': 'bold', 'font-style': 'italic','color': '#cccccc',
                     'background': steps_background,'font-size': '1.3em', 'text-align': 'center',
                     'height': 'vh5'}

polling_link = {'padding': '0.4em', 'border': '0.3em', 'border-radius': '10px',
                'font-weight': 'bold', 'color': steps_background, 'background': steps_background,
                'font-size': '1.2em', 'text-align': 'center', 'height': 'vh5'}

group_header_sfc_obs = replace_in_dict(group_header_style, 'white', obs_c)

group_header_nse = replace_in_dict(group_header_style, 'white', nse_c)

group_header_links = replace_in_dict(group_header_style, 'white', graphics_c)

group_item_style_no_border = {'font-weight': 'bold', 'color': '#cccc99',
                              'font-size': '1.2em', 'text-align': 'right'}
group_item_style_center = {'font-weight': 'bold', 'color': 'white', 'border': '1px gray solid',
                           'font-size': '1.2em', 'text-align': 'center'}
group_item_style_left = {'font-weight': 'bold', 'color': '#cccccc',
                         'font-size': '1.2em', 'text-align': 'left'}

toggle_placefiles_btn = dbc.Container(dbc.Col(html.Div([dbc.Button(
    'Hide Links Section', size="lg", id='toggle_placefiles_section_btn',
    n_clicks=0)], className="d-grid gap-2 col-12 mx-auto")))

################################################################################################
# ----------------------------- Clock components  ----------------------------------------------
################################################################################################

step_select_time_section = dbc.Container(
    dbc.Col(html.Div(children=STEP_SELECT_TIME, style=steps_center)))
SIMULATION_PLAYBACK_BANNER_TEXT = "Simulation Launch and Playback Controls"
playback_banner = dbc.Row(
    dbc.Col(html.Div(children=SIMULATION_PLAYBACK_BANNER_TEXT, style=steps_center)))

start_playback_btn = dbc.Col(html.Div([dbc.Button('Launch Simulation', size="lg",
                                                  id='playback_btn', disabled=True, n_clicks=0)],
                                      className="d-grid gap-2 col-12 mx-auto"))

pause_resume_playback_btn = dbc.Col(html.Div([dbc.Button('Pause Playback', size="lg",
                                                         id='pause_resume_playback_btn',
                                                         disabled=True, n_clicks=0)],
                                             className="d-grid gap-2 col-12 mx-auto"))

refresh_polling_btn = dbc.Col(html.Div([dbc.Button('Refresh Polling Times', size="lg",
                                                         id='refresh_polling_btn',
                                                         disabled=True, n_clicks=0)],
                                             className="d-grid gap-2 col-12 mx-auto"))

playback_buttons_container = dbc.Container(
    html.Div([dbc.Row([start_playback_btn,
                       pause_resume_playback_btn, refresh_polling_btn])]))

playback_start_label = html.Div(
    children="Simulation Start Time", style=time_headers)
playback_start_readout = html.Div(
    children="Not Ready", id='start_readout', style=feedback)


playback_end_label = html.Div(
    children="Simulation End Time", style=time_headers)
playback_end_readout = html.Div(
    children="Not Ready", id='end_readout', style=feedback)


playback_current_label = html.Div(
    children="Simulation Current Time", style=time_headers)
playback_current_readout = html.Div(
    children="Not Ready", id='current_readout', style=feedback)


playback_start_col = dbc.Col(html.Div([
    playback_start_label, spacer_mini, playback_start_readout]))
playback_end_col = dbc.Col(html.Div([
    playback_end_label, spacer_mini, playback_end_readout]))
playback_current_col = dbc.Col(html.Div([
    playback_current_label, spacer_mini, playback_current_readout]))

playback_timer_readout_container = dbc.Container(
    html.Div([dbc.Row([playback_start_col,
                       playback_current_col,
                       playback_end_col])]))

playback_status_box = dbc.Col(
    html.Div(id='playback_status', children='Not Started', style=feedback))
clock_status_container = dbc.Container(
    html.Div([dbc.Row([playback_status_box])]))

# Playback speed components
playback_speed_label = html.Div(children="Playback Speed", style=time_headers)
playback_speed_dropdown_values = [0.25, 0.5,
                                  0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 10.0]
playback_speed_options = [
    {'label': str(i) + 'x', 'value': i} for i in playback_speed_dropdown_values]

playback_speed_dropdown = dcc.Dropdown(options=playback_speed_options, value=1.0,
                                       id='speed_dropdown', disabled=True, clearable=False)
playback_speed_col = dbc.Col(
    html.Div([playback_speed_label, spacer_mini, playback_speed_dropdown]))


change_playback_time_label = html.Div(
    children="Change Playback Time", style=time_headers)
simulation_playback_section = dbc.Container(
    dbc.Container(
        html.Div([playback_banner,
                  spacer,
                  playback_buttons_container,
                  spacer,
                  playback_timer_readout_container,
                  spacer_mini,
                  clock_status_container,
                  ]), style=section_box_pad))


bottom_section = html.Div([
    html.P(id="counter", style={'display': 'none'}),
    html.P(id="radar_quantity_holder", style={'display': 'none'}),],
    style={'height': '500px'})
