"""
create LSRs for the radar simulation
"""
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import requests
import pandas as pd

ICON_URL = "https://raw.githubusercontent.com/tjturnage/cloud-radar-server/"
URL_DIRECTORY = "main/assets/iconfiles/IconSheets"
ICON_DIRECTORY = f"{ICON_URL}{URL_DIRECTORY}"

HEAD = """//Created by the NWS Central Region Convective Warning Improvement Project (CWIP Team)
Refresh: 1
Threshold: 999
Title: Local Storm Reports -- for radar simulation
"""
@dataclass
class LsrBase:
    """
    Base class for creating a placefile of Local Storm Reports (LSRs) for the radar simulation
    """
    lat:            str     # latitude to build a bounding box that filters reports
    lon:            str     # longitude to build a bounding box that filters reports
    sim_start:      str     # start time of the simulation in the format 'YYYY-MM-DD HH:MM'
    event_duration: str     # duration of the simulation in minutes
    data_dir:       str     # directory with the LSR csv file
    output_dir:     str     # directory for the placefile

@dataclass
class LsrCreator(LsrBase):
    """
    Create a placefile of Local Storm Reports (LSRs) for the radar simulation
    #lat, lon, event_start_str, duration, 'DATA_DIR', 'PLACEFILES_DIR
    """

    output_filepath: str = field(init=False)
    start_api: str = field(init=False)
    end_api: str = field(init=False)

    def __post_init__(self):
        self.placefile_name = "LSRs.txt"
        self.lsr_csv_path = f"{self.data_dir}/LSR_extracted.csv"
        self.output_file = os.path.join(self.output_dir, self.placefile_name)
        self.sim_start = datetime.strptime(self.sim_start, '%Y-%m-%d %H:%M')
        self.sim_end = self.sim_start + timedelta(minutes=int(self.event_duration))

        # Format the start and end time strings for the LSR API request syntax
        self.start_api = datetime.strftime(self.sim_start, '%Y-%m-%dT%H:%MZ')
        self.end_api = datetime.strftime(self.sim_end, '%Y-%m-%dT%H:%MZ')

        self.lsr_delay = 10
        self.lsr_duration = 20
        self.url = self.construct_lsr_request_str()
        # Download data, generate placefile, keep csv for future use
        self.download_and_save_file()
        self.write_placefile()

    def construct_lsr_request_str(self) -> str:
        """
        construct the URL for the LSR data request with needed arguments
        defining the bounding box for the LSR data is part of the URL
        """
        lat1, lat2, lon1, lon2 = self.bounding_box()

        url_base = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/lsr.py"
        bounds = f"?west={lon1}&east={lon2}&north={lat2}&south={lat1}"
        times = f"&sts={self.start_api}&ets={self.end_api}"
        url = f'{url_base}{bounds}{times}&fmt=csv'
        return url

    def bounding_box(self):
        """
        Create a bounding box for the LSR data
        An arbitrary distance of +/- 3 degrees lat/lon from the radar location is used
        """
        distance = 3 # degrees
        lat = float(self.lat)
        lon = float(self.lon)
        lat1 = lat - distance
        lat2 = lat + distance
        lon1 = lon - distance
        lon2 = lon + distance
        return lat1, lat2, lon1, lon2

    def download_and_save_file(self):
        """
        Download the LSR csv file from the IEM website
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()

            with open(self.lsr_csv_path, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded {self.lsr_csv_path}")

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the HTTP request: {e}")
        except OSError as e:
            print(f"An error occurred while writing the file: {e}")

    def delete_file(self):
        """
        Delete the LSR csv file after the placefile has been created
        Currently not used since the csv file is kept for future use.
        """
        if os.path.exists(self.lsr_csv_path):
            os.remove(self.lsr_csv_path)

    def write_placefile(self):
        """
        Write the LSR data to a placefile
        """

        # Read the CSV file
        columns = ['VALID','VALID2','LAT','LON','MAG','WFO','TYPECODE','TYPETEXT','CITY',
                   'COUNTY','STATE','SOURCE','REMARK','UGC','UGCNAME','QUALIFIER']
        df = pd.read_csv(self.lsr_csv_path, usecols=columns,low_memory=False, on_bad_lines='warn')
        df['REMARK'] = df['REMARK'].fillna(' ') # removing nan values from LSR hover text

        keyword1 = ["FATAL"]
        keyword2 = ["INJ"]
        with open(self.output_file, "w", encoding="utf-8") as f:

            #f.write(f'IconFile: 1, 25, 25, 10, 10, {icon_url}/lsr_icons_96.png\n')
            #f.write(f'IconFile: 2, 25, 32, 10, 10, {icon_url}/Lsr_Hail_Icons.png\n')
            #f.write(f'IconFile: 3, 25, 32, 10, 10, {icon_url}/wind_icons_96.png\n')
            #f.write(f'IconFile: 4, 25, 32, 10, 10, {icon_url}/Lsr_TstmWndGst_Icons.png\n')
            #f.write(f'IconFile: 5, 25, 32, 10, 10, {icon_url}/Lsr_NonTstmWndGst_Icons.png\n')
            #f.write(f'IconFile: 6, 25, 32, 10, 10, {icon_url}/Lsr_HeavyRain_Icons.png\n')

            #---------- begin writing placefile top section --------------------
            f.write(HEAD)

            # Icon definition lines
            file_stems = ['lsr_icons_96', 'Lsr_Hail_Icons', 'wind_icons_96',
                         'Lsr_TstmWndGst_Icons', 'Lsr_NonTstmWndGst_Icons',
                         'Lsr_HeavyRain_Icons']

            for number, stem in zip(range(1,7), file_stems):
                if number == 1:
                    f.write(f'IconFile: {number}, 25, 25, 10, 10, {ICON_DIRECTORY}/{stem}.png\n')
                else:
                    f.write(f'IconFile: {number}, 25, 32, 10, 10, {ICON_DIRECTORY}/{stem}.png\n')

            # Font definition(s)
            f.write('Font: 1, 11, 1, "Courier New"\n\n')
            #---------- end writing placefile top section --------------------

            original_time_format = "%Y/%m/%d %H:%M"

            # Iterate over each row in DataFrame
            for index, row in df.iterrows():
                event = row.get("TYPETEXT", "")
                source = row.get("SOURCE", "")
                remark = row.get("REMARK", "")
                magnitude = row.get("MAG", 0)
                original_time_str = row.get("VALID2", "")
                lat = row.get("LAT", 0)
                lon = row.get("LON", 0)

                wind_icon = min(magnitude/5 + 1, 20)
                hail_icon = magnitude*4 + 1
                rain_icon = magnitude * 2 + 1 if magnitude < 6 else magnitude + 7

                icon2 = 'Icon: 0,0,0,1,7,'
                icon3 = 'Icon: 0,0,0,1,15,'

                # Convert original time string to datetime object
                good_date = True
                try:
                    lsr_datetime = datetime.strptime(original_time_str, original_time_format)
                    datetime_org = lsr_datetime + timedelta(minutes=int(self.lsr_delay))
                    datetime_obj = lsr_datetime + timedelta(minutes=int(self.lsr_duration))
                    iso_startdate_str = datetime_org.isoformat().replace('+00:00', 'Z')
                    iso_enddate_str = datetime_obj.isoformat().replace('+00:00', 'Z')
                    lsr_datetime_str = lsr_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    print(f"Date format error for row index {index}")
                    good_date = False
                    continue

                if good_date:
                    if event == "TORNADO":
                        icon = 'Icon: 0,0,0,1,20,'
                        mag = " "
                    elif event == "TSTM WND DMG":
                        icon = 'Icon: 0,0,0,1,22,'
                        mag = " "
                    elif event == "TSTM WND GST":
                        icon = f'Icon: 0,0,0,4,{round(wind_icon)},'
                        mag = str(magnitude) + " mph"
                    elif event == "HAIL":
                        icon = f'Icon: 0,0,0,2,{round(hail_icon)},'
                        mag = str(magnitude) + " inch"
                    elif event == "RAIN":
                        icon = f'Icon: 0,0,0,6,{round(rain_icon)},'
                        mag = str(magnitude) + " inches"
                    elif event == "FUNNEL CLOUD":
                        icon = 'Icon: 0,0,0,1,11,'
                        mag = " "
                    elif event == "NON-TSTM WND DMG":
                        icon = 'Icon: 0,0,0,1,17,'
                        mag = " "
                    elif event == "NON-TSTM WND GST":
                        icon = f'Icon: 0,0,0,5,{round(wind_icon)},'
                        mag = str(magnitude) + " mph"
                    elif event == "FLOOD":
                        icon = 'Icon: 0,0,0,1,9,'
                        mag = " "
                    elif event == "FLASH FLOOD":
                        icon = 'Icon: 0,0,0,1,9,'
                        mag = " "
                    else:
                        continue

                    # Write event data to the output file
                    f.write(f'TimeRange: {iso_startdate_str}Z {iso_enddate_str}Z\n')
                    f.write(f'Object: {lat},{lon}\n')
                    f.write('Threshold: 999\n')
                    f.write(
                        f'{icon} Event: {event}\\nLSR Time: {lsr_datetime_str}\\n'
                        #  Omit specific location and county to conceal the actual location
                        #f'Place: {location} {state}\\nCounty: {county}\\n'
                        f'Source: {source}\\n{mag} {event}\\n{remark}\n')

                    if any(keyword in str(remark) for keyword in keyword1):
                        f.write(f'{icon2}\n')
                    elif any(keyword in str(remark) for keyword in keyword2):
                        f.write(f'{icon3}\n')
                    f.write('END:\n\n')


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        LsrCreator('42','-85','2024-05-07 22:00','120', os.getcwd(), os.getcwd())
    else:
        #lat, lon, event_start_str, duration, 'DATA_DIR', 'PLACEFILES_DIR
        LsrCreator(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
