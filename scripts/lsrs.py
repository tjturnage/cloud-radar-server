"""
create LSRs for the radar simulation
"""
import os
import sys
from datetime import datetime, timedelta
import requests
import pandas as pd

class LsrCreator:
    """
    Create a placefile of Local Storm Reports (LSRs) for the radar simulation
    """
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

        # Entries are in minutes. lsr_delay = how long to withhold lsr after event occurrence.
        # lsr_duration = how long to display lsr
        self.lsr_delay = 12
        self.lsr_duration = 20

        # URL for downloading the LSR Data
        URL_BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/lsr.py?sts"
        self.url = (f'{URL_BASE}={self.start_date}T{self.start_time}Z&ets={self.end_date}'
                    f'T{self.end_time}Z&wfo=ALL&fmt=csv')
        # Filename for downloaded file
        self.lsr_file = f"{self.data_path}/LSR_extracted.csv"

        # Download data, generate placefile, and purge .csv from disk
        self.download_and_save_file()
        self.write_placefile()
        #self.delete_file()

    def download_and_save_file(self):
        """
        Download the LSR csv file from the IEM website
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()

            with open(self.lsr_file, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded {self.lsr_file}")

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the HTTP request: {e}")
        except OSError as e:
            print(f"An error occurred while writing the file: {e}")

    def delete_file(self):
        """
        Delete the LSR csv file after the placefile has been created
        """
        if os.path.exists(self.lsr_file):
            os.remove(self.lsr_file)

    def write_placefile(self):
        """
        Write the LSR data to a placefile
        """
        icon_url = "https://raw.githubusercontent.com/tjturnage/cloud-radar-server/main/assets/iconfiles/IconSheets"
        # Read the CSV file 
        columns = ['VALID','VALID2','LAT','LON','MAG','WFO','TYPECODE','TYPETEXT','CITY','COUNTY','STATE','SOURCE','REMARK','UGC','UGCNAME','QUALIFIER']
        #columns = ['VALID2', 'LAT', 'LON', 'TYPETEXT', 'MAG', 'REMARK', 'SOURCE']
        df = pd.read_csv(self.lsr_file, usecols=columns,low_memory=False, on_bad_lines='warn')
        df['REMARK'] = df['REMARK'].fillna(' ') # removing nan values from output text in LSR hover text

        keyword1 = ["FATAL"]
        keyword2 = ["INJ"]
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("//Created by the NWS Central Region Convective Warning Improvement Project (CWIP Team) 2024\n")
            f.write("Refresh: 1\n")
            f.write("Threshold: 999\n")
            f.write('Title: Local Storm Reports -- for radar simulation\n')
            f.write(f'IconFile: 1, 25, 25, 10, 10, {icon_url}/lsr_icons_96.png\n')
            f.write(f'IconFile: 2, 25, 32, 10, 10, {icon_url}/Lsr_Hail_Icons.png\n')
            f.write(f'IconFile: 3, 25, 32, 10, 10, {icon_url}/wind_icons_96.png\n')
            f.write(f'IconFile: 4, 25, 32, 10, 10, {icon_url}/Lsr_TstmWndGst_Icons.png\n')
            f.write(f'IconFile: 5, 25, 32, 10, 10, {icon_url}/Lsr_NonTstmWndGst_Icons.png\n')
            f.write(f'IconFile: 6, 25, 32, 10, 10, {icon_url}/Lsr_HeavyRain_Icons.png\n')
            f.write('Font: 1, 11, 1, "Courier New"\n\n')

            # Define the format of the original time
            original_time_format = "%Y/%m/%d %H:%M"

            # Iterate over each row in DataFrame
            for index, row in df.iterrows():
                event = row.get("TYPETEXT", "")
                source = row.get("SOURCE", "")
                # commented these out to remove specific location and county
                #location = row.get("CITY", "")
                #county = row.get("COUNTY", "")
                #state = row.get("STATE", "")
                remark = row.get("REMARK", "")
                magnitude = row.get("MAG", 0)
                original_time_str = row.get("VALID2", "")
                lat = row.get("LAT", 0)
                lon = row.get("LON", 0)

                wIcon = min(magnitude/5 + 1, 20)
                hIcon = (magnitude*4 +1)
                rIcon = magnitude * 2 + 1 if magnitude < 6 else magnitude + 7
                
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
                        icon = f'Icon: 0,0,0,4,{round(wIcon)},'
                        mag = str(magnitude) + " mph"
                    elif event == "HAIL":
                        icon = f'Icon: 0,0,0,2,{round(hIcon)},'
                        mag = str(magnitude) + " inch"
                    elif event == "RAIN":
                        icon = f'Icon: 0,0,0,6,{round(rIcon)},'
                        mag = str(magnitude) + " inches"
                    elif event == "FUNNEL CLOUD":
                        icon = 'Icon: 0,0,0,1,11,'
                        mag = " "
                    elif event == "NON-TSTM WND DMG":
                        icon = 'Icon: 0,0,0,1,17,'
                        mag = " "
                    elif event == "NON-TSTM WND GST":
                        icon = f'Icon: 0,0,0,5,{round(wIcon)},'
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
        LsrCreator('2024-05-07 22:00','120', os.getcwd(), os.getcwd())
    else:
        #str(sim_times['event_start_str']), str(sim_times['event_duration']),
        #cfg['DATA_DIR'], cfg['PLACEFILES_DIR']]
        LsrCreator(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

