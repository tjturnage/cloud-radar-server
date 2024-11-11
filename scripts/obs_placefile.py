"""
Retrieves observations via the Mesowest API.
Learn more about setting up your own account at: https://synopticdata.com/

Get latest obs: https://developers.synopticdata.com/mesonet/v2/stations/latest/
Obs network/station providers: https://developers.synopticdata.com/about/station-providers
Selecting stations: https://developers.synopticdata.com/mesonet/v2/station-selectors/
"""
from dataclasses import dataclass, field
from pathlib import Path
import sys
import os
import math
from datetime import datetime, timedelta
import pytz
import requests
from dotenv import load_dotenv
load_dotenv()
API_TOKEN = os.getenv("SYNOPTIC_API_TOKEN")
API_ROOT = "https://api.synopticdata.com/v2/"

parts = Path.cwd().parts
idx = parts.index('cloud-radar-server')
BASE_DIR =  Path(*parts[0:idx+1])

PUBLIC_WIND_ZOOM = 400
RWIS_WIND_ZOOM = 150
PUBLIC_T_ZOOM = 600
RWIS_T_ZOOM = 75
GRAY = '180 180 180'
WHITE = '255 255 255'

NETWORK = "1,2,96,162"
VARIABLES = 'air_temp,dew_point_temperature,wind_speed,wind_direction,wind_gust,visibility'
#VARIABLES += ',road_temp'
UNITS = 'temp|F,speed|kts,precip|in'
FONT_CODE = 2
WIND_ICON_NUMBER = 1
GUST_DISTANCE = 35

ICON_FONT_TEXT = '\n\nRefresh: 1\
        \nColor: 255 200 255\
        \nIconFile: 1, 18, 32, 2, 31, "https://mesonet.agron.iastate.edu/request/grx/windbarbs.png"\
        \nIconFile: 2, 15, 15, 8, 8, "https://mesonet.agron.iastate.edu/request/grx/cloudcover.png"\
        \nIconFile: 3, 25, 25, 12, 12, "https://mesonet.agron.iastate.edu/request/grx/rwis_cr.png"\
        \nIconFile: 4, 13, 24, 2, 23, "https://rssic.nws.noaa.gov/assets/iconfiles/windbarbs-small.png"\
        \nFont: 1, 11, 1, "Arial"\
        \nFont: 2, 14, 1, "Arial"\n\n'

station_dict = {
    'public': {
        't': {'threshold': PUBLIC_T_ZOOM, 'color': '225 75 75', 'position': '-17,13, 2'},
        'td': {'threshold': PUBLIC_T_ZOOM, 'color': '0 255 0', 'position': '-17,-13, 2'},
        'rh': {'threshold': PUBLIC_T_ZOOM, 'color': '255 165 0', 'position': '17,-17, 2'},
        'vis': {'threshold': PUBLIC_T_ZOOM, 'color': '180 180 255', 'position': '17,-13, 2'},
        'wind': {'threshold': PUBLIC_WIND_ZOOM, 'color': WHITE, 'position': 'NA'},
        'wspd': {'threshold': PUBLIC_WIND_ZOOM, 'color': WHITE, 'position': 'NA'},
        'wdir': {'threshold': PUBLIC_WIND_ZOOM, 'color': WHITE, 'position': 'NA'},
        'wgst': {'threshold': PUBLIC_WIND_ZOOM, 'color': WHITE, 'position': 'NA'},
        'font_code': 2,
        'wind_icon_number': 1,
        'gust_distance': 35},
    'rwis': {
        't': {'threshold': RWIS_T_ZOOM, 'color': '200 100 100', 'position': '-16,12, 1'},
        'td': {'threshold': RWIS_T_ZOOM, 'color': '25 225 25', 'position': '-16,-12, 1'},
        'rh': {'threshold': RWIS_T_ZOOM, 'color': '255 165 0', 'position': '16,-16, 1'},
        'vis': {'threshold': RWIS_T_ZOOM, 'color': '180 180 255', 'position': '16,-12, 1'},
        'rt': {'threshold': RWIS_T_ZOOM, 'color': '255 255 0', 'position': '16,12, 1'},
        'wind': {'threshold': RWIS_WIND_ZOOM, 'color': GRAY, 'position': 'NA'},
        'wspd': {'threshold': RWIS_WIND_ZOOM, 'color': GRAY, 'position': 'NA'},
        'wdir': {'threshold': RWIS_WIND_ZOOM, 'color': GRAY, 'position': 'NA'},
        'wgst': {'threshold': RWIS_WIND_ZOOM, 'color': GRAY, 'position': 'NA'},
        'font_code': 1,
        'wind_icon_number': 4,
        'gust_distance': 28
    }
}

short_dict = {'air_temp_value_1':'t',
        'dew_point_temperature_value_1d':'dp',
        'wind_speed_value_1':'wspd',
        'wind_direction_value_1':'wdir',
        'wind_gust_value_1':'wgst',
        'visibility_value_1':'vis',
        #'road_temp_value_1': 'rt'
        }

@dataclass
class MesowestBase():
    """
    Base class for Mesowest placefile creation
    """

    lat:                str     #  Input -- latitude to build a bounding box that filters objects
    lon:                str     #  Input -- longitude to build a bounding box that filters objects
    event_timestr:      str     #  Input -- event time string
    duration:           str     #  Input -- duration of event in minutes
    output_directory:   str     #  Output -- directory for placefiles

    api:                str = 'mesowest'              #  Define network
    steps:              int = field(init=False)       #  Derived based on duration
    d_t:                int = 5                      #  Time interval in minutes


    def __post_init__(self):
        self.lat = float(self.lat)
        self.lon = float(self.lon)
        self.duration = int(self.duration)

@dataclass
class Mesowest(MesowestBase):
    """
    Create a GR2Analyst compliant placefile from Mesowest observations
    """

    def __post_init__(self):
        self.placefiles_dir = Path(self.output_directory)
        self.bbox = f'{self.lon-4},{self.lat-4},{self.lon+4},{self.lat+4}'
 
        self.api_args = {"token":API_TOKEN,
                "bbox":self.bbox,
                "status":"active",
                "network":NETWORK,
                "vars":VARIABLES,
                "units":UNITS,
                "within":"30"}

        self.steps = int((int(self.duration)/5) + 1)
        self.base_time = datetime.strptime(self.event_timestr,'%Y-%m-%d %H:%M')
        self.base_ts = datetime.strftime(self.base_time,'%Y%m%d%H%M')
        self.place_time = self.base_time
        self.place_ts = datetime.strftime(self.place_time,'%Y%m%d%H%M')
        self.direction = 'forward'

        self.station_dict = station_dict

        # No references to time kept in the placefile title
        place_text = '-- for radar simulation'
        self.all_title = f'All Elements {place_text}'
        self.t_title = f'Air Temperature {place_text}'
        self.wind_place_title = f'Wind and Gust {place_text}'
        self.td_place_title = f'Dewpoint Temperature {place_text}'
        self.rh_place_title = f'Relative Humidity {place_text}'
        self.times = self.time_shift()
        self.build_placefile()


    def convert_met_values(self,num,short):
        """
        Convert a number to a string and build a text object for the placefile
        -------------------------------------------------------------------------------
        Input   |  num        | str   | number to be converted
                |  short      | str   | short name of the variable
                |  this_dict  | dict  | dictionary of threshold, color, and position
        Returns |  new_str    | str   | number as a string
                |  text_info  | str   | threshold, color, and position
        -------------------------------------------------------------------------------
        """
        #text_info = 'ignore'
        numfloat = float(num)
        new_str = 'NA'
        if num != 'NA':
            if short in ('t', 'dp', 'td', 'rt', 'rh'):
                new_value = int(round(numfloat))
                new_str = '" ' + str(new_value) + ' "'
            elif short == 'wgst':
                new_value = int(round(numfloat,1))
                new_str = '" ' + str(new_value) + ' "'
            elif short == 'vis':
                vis_string = self.visibility_code(num)
                new_str = '" ' + vis_string + ' "'
            elif short == 'wspd':
                new_value = self.placefile_wind_speed_code(numfloat)
                new_str = str(new_value)
            elif short == 'wdir':
                new_value = int(num)
                new_str = str(new_value)
            return new_str
        
    def build_placefile(self):
        """
        go through the steps
        """

        self.t_placefile = f'Title: Mesowest {self.t_title}{ICON_FONT_TEXT}'
        self.wind_placefile = f'Title: Mesowest {self.wind_place_title}{ICON_FONT_TEXT}'
        self.td_placefile = f'Title: Mesowest {self.td_place_title}{ICON_FONT_TEXT}'
        self.rh_placefile = f'Title: Mesowest {self.rh_place_title}{ICON_FONT_TEXT}'
        self.all_placefile = f'Title: Mesowest {self.all_title}{ICON_FONT_TEXT}'

        for _t,this_time in enumerate(self.times):
            time_str = this_time[0]
            jas = self.mesowest_get_nearest_time_data(time_str)
            present = this_time[1]
            future = this_time[2]

            #Example of TimeRange line:
            #TimeRange: 2019-03-06T23:14:39Z 2019-03-06T23:16:29Z
            time_text = f'TimeRange: {present} {future}\n\n'

            self.t_placefile += time_text
            self.wind_placefile += time_text
            self.td_placefile += time_text
            self.rh_placefile += time_text
            self.all_placefile += time_text

            for j,station in enumerate(jas['STATION']):
                try:
                    t_str, td_str, wdir_str, wspd_str = 'NA', 'NA', 'NA', 'NA'
                    wgst_str, vis_str, rt_str = 'NA', 'NA', 'NA'
                    lon = station['LONGITUDE']
                    lat = station['LATITUDE']
                    object_line = f'Object: {lat},{lon}\n'
                    status = station['STATUS']
                    network = int(station['MNET_ID'])
                    if int(network) == 162:
                        net_dict = self.station_dict['rwis']
                    else:
                        net_dict = self.station_dict['public']

                    wind_zoom = net_dict['wind']['threshold']
                    other_zoom = net_dict['t']['threshold']   

                    dataset = jas['STATION'][j]['OBSERVATIONS']
                    if status == 'ACTIVE':
                        for _n,element in enumerate(list(short_dict.keys())):
                            
                            short_name = str(short_dict[element])
                            data = dataset[element]['value']
                            if short_name == 't':
                                t_str = self.convert_met_values(data,short_name)
                            elif short_name == 'dp':
                                td_str = self.convert_met_values(data,short_name)
                            elif short_name == 'rt':
                                rt_str = self.convert_met_values(data,short_name)
                            elif short_name == 'vis':
                                vis_str = 'NA'
                                if int(network) != 162:
                                    vis_str = self.convert_met_values(data,short_name)
                            elif short_name == 'wspd':
                                wspd_str = self.convert_met_values(data,short_name)
                            elif short_name == 'wdir':
                                wdir_str = self.convert_met_values(data,short_name)
                            elif short_name == 'wgst':
                                wgst_str = data
                            else:
                                continue

                        if wdir_str != 'NA' and wspd_str != 'NA':
                            color_line = f'Color: {net_dict['wind']['color']}\n'
                            wind_icon = net_dict['wind_icon_number']
                            new_text1 = f'{object_line}  Threshold: {wind_zoom}\n  {color_line}\n'
                            new_text2 = f'Icon: 0,0,{wdir_str},{wind_icon},{wspd_str}\n End:\n\n'
                            self.all_placefile += f'{new_text1} {new_text2}'
                            self.wind_placefile += f'{new_text1} {new_text2}'

                        if t_str != 'NA':
                            add_text = self.build_object(net_dict['t'], t_str)
                            new_text = f'{object_line} {add_text}'
                            self.all_placefile += new_text
                            self.t_placefile += new_text

                        if td_str != 'NA':
                            add_text = self.build_object(net_dict['td'], td_str)
                            new_text = f'{object_line} {add_text}'
                            self.all_placefile += new_text
                            self.td_placefile += new_text

                        if vis_str != 'NA':
                            add_text = self.build_object(net_dict['vis'], vis_str)
                            new_text = f'{object_line} {add_text}'
                            self.all_placefile += new_text

                        if t_str != 'NA' and td_str != 'NA':
                            rh_text = self.return_rh_object(t_str, td_str)
                            add_text = self.build_object(net_dict['rh'], rh_text)
                            self.rh_placefile += f'{object_line} {add_text}'

                        if wgst_str != 'NA' and wdir_str != 'NA':
                            location, wgust_popup = self.gust_obj(wdir_str, wgst_str)
                            font_code = net_dict['font_code']
                            color_line = f'  Color: {net_dict['wgst']['color']}\n'
                            #print(color_line)
                            new_text1 = f'{object_line}  Threshold: {wind_zoom}\n' 
                            new_text2 = f'Text: {location},{font_code},{wgust_popup}\n End:\n\n'
                            final_text = f'{new_text1} {color_line} {new_text2}'
                            self.all_placefile += final_text
                            self.wind_placefile += final_text

                        if rt_str != 'NA':
                            self.all_placefile += f'{object_line}  Threshold: {other_zoom}\n{rt_str} End:\n\n'
                            
                    else:
                        continue

                        
                except KeyError as _ke:
                    continue


        with open((self.placefiles_dir / 'temp.txt'), 'w', encoding='utf8') as outfile:
            outfile.write(self.t_placefile)

        with open((self.placefiles_dir / 'wind.txt'), 'w', encoding='utf8') as outfile:
            outfile.write(self.wind_placefile)

        with open((self.placefiles_dir / 'dwpt.txt'), 'w', encoding='utf8') as outfile:
            outfile.write(self.td_placefile)

        with open((self.placefiles_dir / 'rh.txt'), 'w', encoding='utf8') as outfile:
            outfile.write(self.rh_placefile)

        surface_obs_file = self.placefiles_dir / 'latest_surface_observations.txt'

        # Write "original" surface observations placefile
        with open(surface_obs_file, 'w', encoding='utf8') as outfile:
            outfile.write(self.all_placefile)

        # Reopen the "original" file
        with open(surface_obs_file ,'r', encoding='utf8') as fin:
            data = fin.readlines()

            # Create large and xlarge font placefile versions based on original
            with open((self.placefiles_dir / 'latest_surface_observations_lg.txt'), \
                'w', encoding='utf8') as largefout:
                with open((self.placefiles_dir / 'latest_surface_observations_xlg.txt'), \
                    'w', encoding='utf8') as xlargefout:
                    for line in data:
                        if 'Font: 1' in line:
                            largefout.write('Font: 1, 14, 1, "Arial"\n')
                            xlargefout.write('Font: 1, 18, 1, "Arial"\n')
                        elif 'Font: 2' in line:
                            largefout.write('Font: 2, 16, 1, "Arial"\n')
                            xlargefout.write('Font: 2, 20, 1, "Arial"\n')
                        else:
                            largefout.write(line)
                            xlargefout.write(line)



    def build_object(self,element_dict,text_str):
        """
        Create a text object for the placefile
        """
        thresh_line = f'Threshold: {element_dict['threshold']}\n'
        color_line = f'  Color: {element_dict['color']}\n'
        position = f'  Text: {element_dict['position']}, {text_str}\n'
        text_info = f'{thresh_line} {color_line} {position} End:\n\n'
        return text_info


    def placefile_wind_speed_code(self,wspd):
        """
        Returns the proper code for the wind speed icon
        ------------------------------------------------------------------------------------
        Input   |  wspd      | str   | Wind speed in knots
        Returns |            | str   | string of integer that references the placefile icon
        ------------------------------------------------------------------------------------
        """
        speed = float(wspd)
        speed_ranges = [
        (52, '11'), (47, '10'), (42, '9'), (37, '8'), (32, '7'),
        (27, '6'), (22, '5'), (17, '4'), (12, '3'), (7, '2')]

        for speed_threshold, label in speed_ranges:
            if speed > speed_threshold:
                return label
        return '1'


    def return_rh_object(self, temp, dewpoint):
        """
        Calculate the relative humidity and return a string object for the placefile
        ------------------------------------------------------------------------------------
        Input   |  temp      | str   | Temperature in degrees Fahrenheit
        Input   |  dewpoint  | str   | Dewpoint in degrees Fahrenheit
        Returns |            | str   | Relative humidity in percent
        ------------------------------------------------------------------------------------
        """
        # Convert Fahrenheit to Celsius
        temp_c = (int(temp[2:-2]) - 32) * 5.0 / 9.0
        dewpoint_c = (int(dewpoint[2:-2]) - 32) * 5.0 / 9.0

        # Calculate relative humidity
        rh = 100 * (math.exp((17.625 * dewpoint_c) / (243.04 + dewpoint_c)) / \
            math.exp((17.625 * temp_c) / (243.04 + temp_c)))

        return f'" {round(rh)} "'


    def visibility_code(self,v) -> str:
        """
        Converts decimal visibility to a string representing fractional visibility
        ------------------------------------------------------------------------------------
         Input   |  v  | str   | Visibility in miles
         Returns |     | str   | String representing factional visibility in statute miles
        ------------------------------------------------------------------------------------
        """
        vis = float(v)
        visibility_ranges = [
        (0.0, '0'), (0.125, '1/8'), (0.25, '1/4'), (0.5, '1/2'), (0.75, '3/4'),
        (1.0, '1'), (1.25, '1 1/4'), (1.5, '1 1/2'), (1.75, '1 3/4'), (2.0, '2'),
        (2.25, '2 1/4'), (2.5, '2 1/2'), (2.75, '2 3/4'), (3.0, '3'), (4.0, '4'),
        (5.0, '5'), (6.0, '6'),(6.5, '7+')]

        for vis_threshold, label in visibility_ranges:
            if vis <= vis_threshold:
                return label
        return '7+'


    def gust_obj(self,wdir, wgst):
        """
        Converts wind gust data to a string object for the placefile
        ------------------------------------------------------------------------------------
        Input   |  wdir      | str   | Wind direction in degrees
                |  wgst      | str   | Wind gust in knots
        Returns |  location  | str   | x,y location of the gust icon
                |  wgst_str  | str   | Wind gust in knots
        ------------------------------------------------------------------------------------
        """
        wgst_int = int(wgst)
        wgst_str = f'" {wgst_int} "'
        direction = int(wdir)
        x = int(math.sin(math.radians(direction)) * GUST_DISTANCE)
        y = int(math.cos(math.radians(direction)) * GUST_DISTANCE)
        location = f'{x},{y}'
        return location, wgst_str


    def time_shift(self) -> list:
        """
        Returns list of timestrings associated with a list of time intervals
        -------------------------------------------------------------------------------
        Input   |  timeStr   | str   | 'YYYYmmddHHMM' format
                |  num       | int   | number of time steps
                |  dt        | int   | number of minutes per step
                |  direction | str   | 'backward' or 'forward'
                |  api       | str   | 'mesowest' or 'mping' format
                                         - 'mesowest' - '2020-01-10T06:35:12Z'
                                         = 'mping'    - '2020-01-10 06:35:12'
        Returns |  times     | list  | list of time intervals
                                     | [YYYYmmddHHMM, str, str]
                                     | [YYYYmmddHHMM, interval start time, interval end time]
        -------------------------------------------------------------------------------
        """
        times = []
        init_time = self.base_time
        orig_time = init_time

        for step in range(0,self.steps):
            mins = step * self.d_t
            new_time = orig_time + timedelta(minutes=mins)
            next_time = new_time + timedelta(minutes=self.d_t)
            new_str = datetime.strftime(new_time, '%Y%m%d%H%M')
            if self.api == 'mesowest':
                new = datetime.strftime(new_time, '%Y-%m-%dT%H:%M:%SZ')
                next_time_str = datetime.strftime(next_time, '%Y-%m-%dT%H:%M:%SZ')
            else:
                new = datetime.strftime(new_time, '%Y-%m-%d %H:%M:%S')
                next_time_str = datetime.strftime(next_time, '%Y-%m-%d %H:%M:%S')
            times.append([new_str,new,next_time_str])
        return times


    def mesowest_get_nearest_time_data(self,time_str) -> dict:
        """
        Mesowest API request for data at the nearest available time defined by a time string.
        ------------------------------------------------------------------------------------
        Input   | time_str  | datetime string   | YYYYmmddHHMM (example: '202405311830')
        Returns | jas       | dict              | json file of observational data
        ------------------------------------------------------------------------------------
        """
        api_request_url = os.path.join(API_ROOT, "stations/nearesttime")
        self.api_args['attime'] = time_str
        req = requests.get(api_request_url, params=self.api_args, timeout=20)
        jas = req.json()
        return jas

if __name__ == "__main__":

    # use this for testing on Windows
    if sys.platform.startswith('win'):
        OUTPUT_DIR = 'C:/data/placefiles'
        DURATION = 60   # minutes
        now = datetime.now(pytz.utc)
        total_minutes = DURATION + now.minute % 5
        rounded_now = now - timedelta(minutes=total_minutes, seconds=now.second, microseconds=now.microsecond)
        start_timestr = rounded_now.strftime('%Y-%m-%d %H:%M')
        test = Mesowest(42.9634, -85.6681, start_timestr, DURATION, OUTPUT_DIR)
        #  center lat, center lon, start_timestr, duration, placefile dir

    else:
        test = Mesowest(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
