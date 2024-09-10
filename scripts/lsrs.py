import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta

class LsrCreator:
    def __init__(self, sim_start, event_duration, data_path, output_path):
        self.sim_start = datetime.strptime(sim_start, '%Y-%m-%d %H:%M')
        self.sim_end = self.sim_start + timedelta(minutes=int(event_duration))
        self.start_date = datetime.strftime(self.sim_start, "%Y-%m-%d")
        self.start_time = datetime.strftime(self.sim_start, "%H:%M")
        self.end_date = datetime.strftime(self.sim_end, "%Y-%m-%d")
        self.end_time = datetime.strftime(self.sim_end, "%H:%M")
        self.output_folder = output_path
        self.data_path = data_path
        self.outfilename = "LSRs.txt"
        self.output_file = os.path.join(self.output_folder, self.outfilename)

        # URL for downloading the LSR Data
        URL_BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/lsr.py?sts"
        self.url = (f'{URL_BASE}={self.start_date}T{self.start_time}Z&ets={self.end_date}'
                    f'T{self.end_time}Z&wfo=ALL&fmt=csv')
        # Filename for downloaded file
        self.lsr_file = f"{self.data_path}/LSR_extracted.csv"  

        # Download data, generate placefile, and purge .csv from disk
        self.download_and_save_file()
        self.write_placefile()
        self.delete_file()

    # Download the LSR csv file from IEM
    def download_and_save_file(self):         
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()  

            with open(self.lsr_file, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded {self.lsr_file}")

        except Exception as e:
            print(f"An error occurred: {e}")

    # Delete files when needed. CSV file is deleted when complete
    def delete_file(self):
        if os.path.exists(self.lsr_file):
            os.remove(self.lsr_file)

    # Open the outputFile for writing
    def write_placefile(self):
        # Read the CSV file 
        df = pd.read_csv(self.lsr_file, low_memory=False)
        df['REMARK'] = df['REMARK'].fillna(' ') # removing nan values from output text in LSR hover text

        keyword1 = ["FATAL"]
        keyword2 = ["INJ"]

        with open(self.output_file, "w") as f:
            f.write("//Created by the NWS Central Region Convective Warning Improvement Project (CWIP Team) 2024\n")
            f.write("Refresh: 1\n")
            f.write("Threshold: 999\n")
            f.write('Title: Local Storm Reports\n')
            f.write('IconFile: 1, 25, 25, 10, 10, "https://rssic.nws.noaa.gov/assets/iconfiles/IconSheets/lsr_icons_96.png"\n')
            f.write('IconFile: 2, 25, 32, 10, 10, "https://rssic.nws.noaa.gov/assets/iconfiles/IconSheets/LSR_Hail_Icons.tif"\n')
            f.write('IconFile: 3, 25, 32, 10, 10, "https://rssic.nws.noaa.gov/assets/iconfiles/IconSheets/wind_icons_96.png"\n')
            f.write('IconFile: 4, 25, 32, 10, 10, "https://rssic.nws.noaa.gov/assets/iconfiles/IconSheets/Lsr_TstmWndGst_Icons.tif"\n')
            f.write('IconFile: 5, 25, 32, 10, 10, "https://rssic.nws.noaa.gov/assets/iconfiles/IconSheets/Lsr_NonTstmWndGst_Icons.tif"\n')
            f.write('IconFile: 6, 25, 32, 10, 10, "https://rssic.nws.noaa.gov/assets/iconfiles/IconSheets/Lsr_HeavyRain_Icons.tif"\n')
            f.write('Font: 1, 11, 1, "Courier New"\n\n')

            # Define the format of the original time
            original_time_format = "%Y/%m/%d %H:%M"

            # Iterate over each row in DataFrame
            for index, row in df.iterrows():
                event = row.get("TYPETEXT", "")
                source = row.get("SOURCE", "")
                location = row.get("CITY", "")
                county = row.get("COUNTY", "")
                state = row.get("STATE", "")
                remark = row.get("REMARK", "")
                magnitude = row.get("MAG", 0)
                original_time_str = row.get("VALID2", "")
                lat = row.get("LAT", 0)
                lon = row.get("LON", 0)

                wIcon = (magnitude/5 + 1)  #to find correct Icon number for wind gusts.
                hIcon = (magnitude*4 +1)
                if magnitude < 6:
                    rIcon = (magnitude *2 +1)
                else:
                    rIcon = magnitude + 7
                
                icon2 = 'Icon: 0,0,0,1,7,'
                icon3 = 'Icon: 0,0,0,1,15,'

                # Convert original time string to datetime object
                try:
                    datetime_org = datetime.strptime(original_time_str, original_time_format)
                    datetime_obj = datetime_org + timedelta(minutes=30)# timedelta is how long the LSR will stay visible in GR.

                    # Convert datetime object to ISO 8601 format
                    iso_startdate_str = datetime_org.isoformat().replace('+00:00', 'Z')
                    iso_enddate_str = datetime_obj.isoformat().replace('+00:00', 'Z')

                except ValueError:
                    print(f"Date format error for row index {index}")
                    continue

                # Determine icon based on event type
                if event == "TORNADO":
                    icon = 'Icon: 0,0,0,1,20,'
                    mag = " "
                elif event == "TSTM WND DMG":
                    icon = 'Icon: 0,0,0,1,22,'
                    mag = " "
                elif event == "TSTM WND GST":
                    icon = f'Icon: 0,0,0,4, {wIcon},'
                    mag = str(magnitude) + " mph"
                elif event == "HAIL":
                    icon = f'Icon: 0,0,0,2,{hIcon},'

                    mag = str(magnitude) + " inch"
                elif event == "RAIN":
                    icon = f'Icon: 0,0,0,6,{rIcon},'
                    mag = str(magnitude) + " inches"
                elif event == "FUNNEL CLOUD":
                    icon = 'Icon: 0,0,0,1,11,'
                    mag = " "
                elif event == "NON-TSTM WND DMG":
                    icon = 'Icon: 0,0,0,1,17,'
                    mag = " "
                elif event == "NON-TSTM WND GST":
                    #icon = 'Icon: 0,0,0,1,17,'
                    icon = f'Icon: 0,0,0,5, {wIcon},'
                    mag = str(magnitude) + " mph"
                elif event == "FLOOD":
                    icon = 'Icon: 0,0,0,1,9,'
                    mag = " "
                elif event == "FLASH FLOOD":
                    icon = 'Icon: 0,0,0,1,9,'
                    mag = " "
                else:
                    continue
                    #icon = 'Icon: 0,0,0,1,23,'

                # Write event data to the output file
                f.write(f'TimeRange: {iso_startdate_str}Z {iso_enddate_str}Z\n')
                f.write(f'Object: {lat},{lon}\n')
                f.write('Threshold: 999\n')
                f.write(
                    f'{icon} Event: {event}\\nTime: {original_time_str}\\nPlace: {location} {state}\\n'
                    f'County: {county}\\nSource: {source}\\n{mag} {event}\\n{remark}\n')

                if any(keyword in str(remark) for keyword in keyword1):
                    f.write(f'{icon2}\n')
                elif any(keyword in str(remark) for keyword in keyword2):
                    f.write(f'{icon3}\n')
                    
                f.write('END:\n\n')


if __name__ == '__main__':
    LsrCreator(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])