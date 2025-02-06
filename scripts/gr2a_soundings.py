"""
test
"""
from datetime import datetime, timedelta
import re
from dataclasses import dataclass, field
import sys
import requests


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

@dataclass
class Gr2aSoundings(Gr2aSoundingsBase):
    """
    Get model soundings from Iowa State University
    """

    output_filepath: str = field(init=False)

    def __post_init__(self):
        pass

    def find_hours_in_range(self) -> list:
        """
        Find the times rounded to the nearest hour within a time range defined 
        by a start datetime and duration.

        :param start_datetime: Start datetime in the format 'YYYY-MM-DD HH:MM'
        :param duration_minutes: Duration of the time range in minutes
        :return: List of times rounded to the nearest hour within the time range
        """
        start_dt = datetime.strptime(self.sim_start, '%Y-%m-%d %H:%M')
        end_dt = start_dt + timedelta(minutes=self.event_duration)

        hours_in_range = []
        current_dt = start_dt

        while current_dt <= end_dt:
            rounded_hour = current_dt.replace(minute=0, second=0, microsecond=0)
            if rounded_hour not in hours_in_range:
                hours_in_range.append(rounded_hour.strftime('%Y-%m-%d %H:00'))
            current_dt += timedelta(hours=1)

        return hours_in_range

    def define_model_soundings(self):
        """
        Define the radar/model timesCreate the start and end time strings for the API request
        """


        # Create the output file path
        self.output_filepath = 'model_sounding.txt'
    def request_model_sounding(self,url):
        """
        Requests data from the Iowa State site
        """
        # Create a session with retries disabled
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=0)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        # Fetch the data
        try:
            response = session.get(url, verify=False, timeout=10)
            data = response.text

            regex = re.findall(TIME_REGEX, data)
            fixed = regex[0][:-5] + '1:00Z'
            new_text = data.replace(regex[0], fixed)
            with open('model_sounding.txt', 'w', encoding='utf-8') as fout:
                fout.write(new_text)
            return "model_sounding.txt file created successfully"
        except requests.RequestException as e:
            return f"Sounding creation failed! Error: {e}"


    def get_model_sounding_url(self, UTC_date, UTC_hour, lat, lon):
        """
        Retrieves model from ISU json Bufkit API:
        https://mesonet.agron.iastate.edu/api/1/nws/bufkit.json
        """
        hour_str = f"{UTC_hour}:01:00"
        address = f"{MODEL_BASE_URL}?time={UTC_date}T{hour_str}&lon={lon}&lat={lat}&gr=1"
        return address




if __name__ == "__main__":
    #radar_info:                 dict    # latitude to build a bounding box that filters reports
    #sim_start:                  str     # simulation start time in the format 'YYYY-MM-DD HH:MM'
    #event_duration:             str     # duration of the simulation in minutes
    #sim_seconds_shift:          str     # # of seconds between event start and simulation start

    if sys.platform.startswith('win'):
        Gr2aSoundings({'kgrr':'None'}, '2014-05-07 21:30', '60', '100000')
    else:
        Gr2aSoundings(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
