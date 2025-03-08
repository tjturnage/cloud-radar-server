"""
test
"""
from datetime import datetime, timedelta
import re
from dataclasses import dataclass, field
import sys
import os
import zipfile
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

MODEL_BASE_URL = 'https://mesonet.agron.iastate.edu/api/1/nws/bufkit.json'

ENDING = """
"units": {"pressure": ["MB", "millibars", "hPa", "hectopascals"],
"height": ["M", "meters"],
"temperature": ["C", "celsius"],
"dewpoint": ["C", "celsius"],
"wind_from": ["DEG", "degrees"],
"wind_speed": ["MPS", "meters per second"],
"uvv": ["UBS", "microbars per second"]}
}
"""

@dataclass
class Gr2aSoundingsBase:
    """
    Base class for creating a placefile of Local Storm Reports (LSRs) for the radar simulation
    """
    radar_info:                 dict    # latitude to build a bounding box that filters reports
    sim_start:                  str     # simulation start time in the format 'YYYY-MM-DD HH:MM'
    event_duration:             str     # duration of the simulation in minutes
    sim_seconds_shift:          str     # number of seconds between event start and simulation start
    ASSETS_DIR:                 str     # directory to save the soundings

@dataclass
class Gr2aSoundings(Gr2aSoundingsBase):
    """
    Get model soundings from Iowa State University
    """

    output_filepath: str = field(init=False)

    def __post_init__(self):
        """
        Initialize the class
        """
        self.start_dt = datetime.strptime(self.sim_start, '%Y-%m-%d %H:%M')
        self.end_dt = self.start_dt + timedelta(minutes=int(self.event_duration))
        self.datetimes = self.find_hours_in_range()
        self.radar_lat_lon = self.get_all_lat_lon()
        self.created_files = []
        for lat_lon in self.radar_lat_lon:
            for dt in self.datetimes:
                url = self.create_model_sounding_url(dt, lat_lon)
                self.request_model_sounding(lat_lon[0], dt, url)
        self.create_zip_of_soundings()
    def get_all_lat_lon(self) -> list:
        """
        Get all latitude and longitude values from radar_info dictionary.
        
        :return: List of tuples containing (lat, lon) for each radar site
        """
        lat_lon_list = []
        for key, value in self.radar_info.items():
            lat_lon_list.append((key, value['lat'], value['lon']))
        return lat_lon_list

    def find_hours_in_range(self) -> list:
        """
        Find the times rounded to the nearest hour within a time range defined 
        by a start datetime and duration.

        :param start_datetime: Start datetime in the format 'YYYY-MM-DD HH:MM'
        :param duration_minutes: Duration of the time range in minutes
        :return: List of strings
                 strings are times rounded to the nearest hour within the time range
                 example: 2024-05-07T22:00:00
        """


        hours_in_range = []
        current_dt = self.start_dt
        while current_dt <= self.end_dt:
            rounded_hour = current_dt.replace(minute=0, second=0, microsecond=0)
            if rounded_hour not in hours_in_range:
                hours_in_range.append(rounded_hour.strftime('%Y-%m-%dT%H:%M:%S'))
            current_dt += timedelta(hours=1)

        return hours_in_range

    def request_model_sounding(self,radar,dt,url):
        """
        Requests data from the Iowa State site
        """
        # Create a session with retries disabled
        dt_obj = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
        new_time = dt_obj + timedelta(seconds=int(self.sim_seconds_shift))
        rounded = new_time.replace(minute=1, second=0, microsecond=0)
        new_time_str = rounded.strftime('%Y-%m-%dT%H:%M:%S')
        prefix_time_str = rounded.strftime('%Y%m%dT%H%M')
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=0)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        try:
            response = session.get(url, verify=False, timeout=10)
            data = response.text
            prefix = f"{radar}-{prefix_time_str}"
            filename = f"{prefix}_model_sounding.txt"
            regex = re.findall(TIME_REGEX, data)
            new_text = data.replace(regex[0], new_time_str)
            with open(filename, 'w', encoding='utf-8') as fout:
                fout.write(new_text)
            self.created_files.append(filename)
            print(f"{filename} created successfully")
        except requests.RequestException as e:
            return f"Sounding creation failed! Error: {e}"

    def create_model_sounding_url(self, dt, radar_info):
        """
        Input: datetime object, radar_info dictionary

        Retrieves model from ISU json Bufkit API:
        https://mesonet.agron.iastate.edu/api/1/nws/bufkit.json
        example:
        https://mesonet.agron.iastate.edu/api/1/nws/bufkit.json?time=2024-05-07T22:00:00&lon=-85.54&lat=42.89&gr=1

        """
        lat = radar_info[1]
        lon = radar_info[2]
        #dt_obj = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
        #full_time = dt_obj.strftime('%Y-%m-%dT%H:%M:%S')
        address = f"{MODEL_BASE_URL}?time={dt}&lon={lon}&lat={lat}&gr=1"
        return address

    def create_zip_of_soundings(self):
        """
        Create a zip file containing all the created text files.
        """
        zip_filename = "model_soundings.zip"
        zipfilepath =  os.path.join(self.ASSETS_DIR, zip_filename)
        with zipfile.ZipFile(zipfilepath, 'w') as zipf:
            for file in self.created_files:
                zipf.write(file)
                os.remove(file)
        print(f"{zip_filename} created successfully")

if __name__ == "__main__":
    #radar_info:                 dict    # latitude to build a bounding box that filters reports
    #sim_start:                  str     # simulation start time in the format 'YYYY-MM-DD HH:MM'
    #event_duration:             str     # duration of the simulation in minutes
    #sim_seconds_shift:          str     # # of seconds between event start and simulation start
    radar_dict = {'KGRR': {'lat':42.8939, 'lon':-85.54479},
                  'KDTX': {'lat':42.69997, 'lon':-83.47167}}
    SIM_START = '2024-05-07 21:30'
    ASSETS_DIR = 'C:/data/scripts/cloud-radar-server/assets'
    if sys.platform.startswith('win'):
        Gr2aSoundings(radar_dict, SIM_START, '120', '24835500', ASSETS_DIR)
    else:
        Gr2aSoundings(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
