"""_summary_

    Returns:
    Main page for radar-server
        _type_: _description_
"""

import os
import re
import sys
import time
import pytz
import json
from datetime import datetime
import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash_extensions import EventListener
import dash
# bootstrap is what helps styling for a better presentation
import dash_bootstrap_components as dbc
# dcc = dash core components
from dash import dcc, html
# State allows the user to enter input before proceeding
from dash.dependencies import Input, Output, State

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
next_year = now.year + 1

class RadarSimulator:
    """
    A class representing a radar simulator.

    Attributes:
        start_time (datetime): The start time of the simulation.
        duration (int): The duration of the simulation in seconds.
        radars (list): A list of radar objects.
        product_directory_list (list): A list of directories in the data directory.

    """

    def __init__(self, start_time, duration, radars):
        self.start_time = start_time
        self.duration = duration
        self.radars = radars
        self.geojson = self.populate_map()


    def populate_map(self):
        """
        generates all the radar sites
        """
        radar_list = []
        with open('radars.gis','r', encoding='utf-8') as fin:
            for line in fin.readlines():
                if line[0][0] == 'k':
                    elements = line.split("|")
                    radar_list.append(dict(radar=elements[0][-3:].upper(),lat=float(elements[2]),lon=float(elements[3])))
        geojson = dlx.dicts_to_geojson([{**r, **dict(tooltip=r['radar'])} for r in radar_list])
        return geojson
# ----------------------------------------
#        Initiate Dash app
# ----------------------------------------

sa = RadarSimulator(2000,1000,'radar')

app = dash.Dash(__name__, external_stylesheets= [dbc.themes.DARKLY])
app.title = "Radar Simulator"

# ----------------------------------------
#        Define some webpage layout variables
# ----------------------------------------

bold = {'font-weight': 'bold'}

feedback = {'border': '2px gray solid', 'padding':'0.5em', 'font-weight': 'bold', 'font-size':'1.5em', 'text-align':'center'}

weekdaynames= ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
monthnames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December" ]

top_content = [
            dbc.CardBody([html.H1("Radar Simulator", className="card-title",style={'font-weight': 'bold', 'font-style': 'italic'}),
                html.H4(
                    "An application to provide Displaced Real Time radar simulations for National Weather Service training",
                    className="card-text", style={'color':'rgb(52,152,219)', 'font-weight': 'bold', 'font-style': 'italic'}
                ),
                html.H5(
                    "Developed by many folks ...",
                    className="card-text",
                ),
                html.Div([
                dbc.CardLink("GitHub", href="https://github.com/allenea/Forecast_Search_Wizard")]),
                ])
            ]

step_radar = [
            dbc.CardBody([html.H5("Select up to three radars for your simulation.", 
            className="card-text"),])]

step_year = [
            dbc.CardBody([html.H3("Year", 
            className="card-text"),])]

step_month = [
            dbc.CardBody([html.H3("Month",
            className="card-text"),])]

step_date = [
            dbc.CardBody([html.H3("Date", className="card-text"),])]

step_duration = [
            dbc.CardBody([html.H5("Choose the duration of your simulation", className="card-text"),])]

view_output = [
            dbc.CardBody([html.H5("Output", className="card-title", style=bold),
                html.P(
                    "Results",
                    className="card-text",
                ),])]


################################################################################
#      Build Webpage Layout
################################################################################

app.layout = dbc.Container([
                dbc.Row(dbc.Card(top_content, color="secondary", inverse=True)),

                dbc.Row([
                    html.Div([

                        dbc.Row(dbc.Card(step_year, color="secondary", inverse=True),style={'padding':'2.2em', 'text-align': 'center'}),                  
                    ])
                ]),
                dbc.Row([
                    html.Div([
                            dbc.Col(
                            dcc.Slider(1992,now.year,1,
                                value=next_year-1,
                                id="year_value",
                                #marks={i: str(i) for i in range(1992,next_year)},
                                marks=None,
                                tooltip={"always_visible": True,
                                "style": {"color": "LightSteelBlue", "fontSize": "20px"}},
                                ),style={'padding':'2.2em'},
                            ),
                    ]),
                ]),
                dbc.Row(dbc.Card(step_month, color="secondary", inverse=True),style={'padding':'2.2em', 'text-align': 'center'}),
                dbc.Row([
                    html.Div([
                            dbc.Col(
                            dcc.Slider(1,12,1,
                                value=6,
                                id="month_value",
                                marks=None,
                                tooltip={"always_visible": True,
                                "style": {"color": "LightSteelBlue", "fontSize": "20px"}},
                            ),style={'padding':'2.2em'},
                        ),
                    ]),
                ]),
                dbc.Row(dbc.Card(step_date, color="secondary", inverse=True),style={'padding':'1.5em', 'text-align': 'center'}),

                dbc.Row([
                    html.Div([
                            dbc.Col(
                            dcc.Slider(1,31,1,
                                value=15,
                                id="date_value",
                                marks=None,
                                tooltip={"always_visible": True,
                                "style": {"color": "LightSteelBlue", "fontSize": "20px"}},
                                ),style={'padding':'2.2em'},
                            ),
                    ]),
                ]),

                dbc.Row(dbc.Card(step_radar, color="secondary", inverse=True),style={'padding':'1.5em'}),
                dbc.Row(dl.Map(id='radar_map', style={'height': '75vh'},center = [40, -95],zoom=5,
                    children=[dl.TileLayer(), dl.GeoJSON(data=sa.geojson)])),
              


])

"""
@app.callback(Output('COORDINATE_CLICK_ID', 'children'),
              [Input('radar_map', 'click_lat_lng')])
def click_coord(e):
    if e is not None:
        print(json.dumps(e))
        return json.dumps(e)
    else:
        return "-"

@app.callback(Output('year_value-out', 'children'),
              [Input('year_value', 'value')])
def show_year(input_value):
    return input_value

@app.callback(Output('month_value-out', 'children'),
              [Input('month_value', 'value')])
def show_month(input_value):
    index = input_value -1
    return monthnames[index]


@app.callback(Output('date_value-out', 'children'),
              [Input('date_value', 'value')])
def show_date(input_value):
    
    return input_value
"""

if __name__ == '__main__':
    app.run_server(debug=True)

