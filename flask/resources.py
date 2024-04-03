import os
import math
from datetime import datetime, timedelta
import requests


API_TOKEN = "292d36a692d74badb6ca011f4413ae1b"
API_ROOT = "https://api.synopticdata.com/v2/"


public_wind_zoom = 400
rwis_wind_zoom = 150
public_t_zoom = 600
rwis_t_zoom = 75
gray = '180 180 180'
white= '255 255 255'

net = "1,2,96,162"
variables = 'air_temp,dew_point_temperature,wind_speed,wind_direction,wind_gust,visibility,road_temp'
units = 'temp|F,speed|kts,precip|in'


station_dict = {
    'public': {
        't': {'threshold': public_t_zoom, 'color': '225 75 75', 'position': '-17,13, 2,'},
        'dp': {'threshold': public_t_zoom, 'color': '0 255 0', 'position': '-17,-13, 2,'},
        'vis': {'threshold': public_t_zoom, 'color': '180 180 255', 'position': '17,-13, 2,'},
        'wind': {'threshold': rwis_wind_zoom, 'color': gray, 'position': 'NA'},
        'wspd': {'threshold': public_wind_zoom, 'color': white, 'position': 'NA'},
        'wdir': {'threshold': public_wind_zoom, 'color': white, 'position': 'NA'},
        'wgst': {'threshold': public_wind_zoom, 'color': white, 'position': 'NA'},
        'font_code': 2,
        'wind_icon_number': 1,
        'gust_distance': 35,
    },
    'rwis': {
        't': {'threshold': rwis_t_zoom, 'color': '200 100 100', 'position': '-16,12, 1,'},
        'dp': {'threshold': rwis_t_zoom, 'color': '25 225 25', 'position': '-16,-12, 1,'},
        'vis': {'threshold': rwis_t_zoom, 'color': '180 180 255', 'position': '16,-12, 1,'},
        'rt': {'threshold': rwis_t_zoom, 'color': '255 255 0', 'position': '16,12, 1,'},
        'wind': {'threshold': rwis_wind_zoom, 'color': gray, 'position': 'NA'},
        'wspd': {'threshold': rwis_wind_zoom, 'color': gray, 'position': 'NA'},
        'wdir': {'threshold': rwis_wind_zoom, 'color': gray, 'position': 'NA'},
        'wgst': {'threshold': rwis_wind_zoom, 'color': gray, 'position': 'NA'},
        'font_code': 1,
        'wind_icon_number': 4,
        'gust_distance': 28,
    }
}

short_dict = {'air_temp_value_1':'t',
        'dew_point_temperature_value_1d':'dp',
        'wind_speed_value_1':'wspd',
        'wind_direction_value_1':'wdir',
        'wind_gust_value_1':'wgst',
        'visibility_value_1':'vis',
        'road_temp_value_1': 'rt'
        }


class Placefile():
    def __init__(self,bbox,network,var_str,unit_str):

        self.bbox = bbox
        self.network = network
        self.var_str = var_str
        self.unit_str = unit_str

        self.api_args = {"token":API_TOKEN,
                "bbox":self.bbox,
                "status":"active",
                "network":self.network,
                "vars":self.var_str,
                "units":self.unit_str,
                "within":"30"}

    def placefile_wind_speed_code(self,wspd):
        """
        Returns the proper code for plotting wind speeds in a GR2Analyst placefile.
        This code is then used for the placefile IconFile method described at:
            http://www.grlevelx.com/manuals/gis/files_places.htm

        Parameters
        ----------
                wspd : string
                        wind speed in knots

        Returns
        -------
                code : string
                        string of integer to be used to reference placefile icon

        """
        speed = float(wspd)
        if speed > 52:
            code = '11'
        elif speed > 47:
            code = '10'
        elif speed > 42:
            code = '9'
        elif speed > 37:
            code = '8'
        elif speed > 32:
            code = '7'
        elif speed > 27:
            code = '6'
        elif speed > 22:
            code = '5'
        elif speed > 17:
            code = '4'
        elif speed > 12:
            code = '3'
        elif speed > 7:
            code = '2'
        elif speed > 2:
            code = '1'
        else:
            code = '1'

        return code

    def vis_code(self,numfloat):
        final = '10'
        if numfloat < 6.5:
            final = str(int(round(numfloat)))
        if numfloat <= 2.75:
            final = '2 3/4'
        if numfloat <= 2.50:
            final = '2 1/2'
        if numfloat <= 2.25:
            final = '2 1/4'
        if numfloat <= 2.0:
            final = '2'
        if numfloat <= 1.75:
            final = '1 3/4'
        if numfloat <= 1.50:
            final = '1 1/2'
        if numfloat <= 1.25:
            final = '1 1/4'
        if numfloat <= 1.00:
            final = '1'
        if numfloat <= 0.75:
            final = '3/4'
        if numfloat <= 0.50:
            final = '1/2'
        if numfloat <= 0.25:
            final = '1/4'
        if numfloat <= 0.125:
            final = '1/8'
        if numfloat == 0.0:
            final = ''
        return final
    
    def mesowest_get_nearest_time_data(self,time_str):
        """
        Mesowest API request for data at the nearest available time defined by a time string.

        Parameters
        ----------
            timeStr : string
                        format is YYYYmmDDHHMM (ex. 202002290630)
        Returns
        -------
                jas : json file
                        observational data
        """
        api_request_url = os.path.join(API_ROOT, "stations/nearesttime")
        self.api_args['attime'] = time_str
        req = requests.get(api_request_url, params=self.api_args, timeout=10)

        jas = req.json()
        return jas
