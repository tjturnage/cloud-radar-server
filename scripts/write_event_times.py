"""
This script processes input files to convert times and extract values.
"""
import sys
import os
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pytz
import pandas as pd


notif_columns = ['TYPETEXT','QUALIFIER','MAG','SOURCE','utc_date', 'utc_hour', 'utc_minute',
                 'LAT','LON', 'fake_rpt', 'REMARK']
lsr_columns = ['VALID','VALID2','LAT','LON','MAG','WFO','TYPECODE','TYPETEXT',
               'CITY','COUNTY','STATE','SOURCE','REMARK','UGC','UGCNAME','QUALIFIER']

DASHES = '-' * 150 + '\n'
HEAD1 = '| PLAYBACK TIME    | ORIGINAL TIME    | LAT / LON (OR RADAR) '
HEAD2 = '| EVENT             |QUALIFY | MAG    | SOURCE             | REMARKS\n'
HEADER = HEAD1 + HEAD2

HEAD = """<!DOCTYPE html>
<html>
<head>
<title>Events</title>
<link rel="icon" href="https://rssic.nws.noaa.gov/assets/favicon.ico" type="image/x-icon">
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootswatch/4.5.2/cyborg/bootstrap.min.css">
</head>
<body>
<pre>"""

HEAD_NOPRE = """<!DOCTYPE html>
<html>
<head>
<title>Events</title>
<link rel="icon" href="https://rssic.nws.noaa.gov/assets/favicon.ico" type="image/x-icon">
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootswatch/4.5.2/cyborg/bootstrap.min.css">
</head>
<body>
"""

TAIL_NOPRE = """</ul>
</body>
</html>"""

TAIL = """</pre>
</body>
</html>"""

@dataclass
class BaseEventTimes:
    """
    A base class containing common attributes for event times processing.
    """
    seconds_shift: str  #  Input   --  Number of seconds between original and playback times
    csv_dir: str        #  Input   --  DATA directory containing the CSV files
    radar_dir: str      #  Input   --  RADAR DATA directory containing radarinfo.json file
    html_file: str      #  Output  --  HTML file in ASSETS directory for event times
    text_file: str      #  Output  --  TEXT file in ASSETS directory for event times

@dataclass
class WriteEventTimes(BaseEventTimes):
    """
    A class to process input files to convert times and extract values.
    CSV files are parsed and times reformatted to reflect the original and playback times.
    """

    events_csv: str = field(init=False)     #  Input  --  CSV file containing notifications
    lsrs_csv: str = field(init=False)       #  Input  --  CSV file containing LSRs

    def __post_init__(self):
        self.events_csv = os.path.join(self.csv_dir, 'events.csv')
        self.lsrs_csv = os.path.join(self.csv_dir, 'LSR_extracted.csv')
        self.events_list = []

        try:
            self.append_radar_file_info()
        except ValueError as e:
            print(f"Error processing radar files: {e}")
        try:
            self.lsr_df = self.make_lsr_dataframe()
            self.append_output(self.lsr_df)
        except ValueError as e:
            print(f"Error processing file: {e}")

        if os.path.exists(self.events_csv):
            try:
                self.events_df = self.make_events_dataframe()
                self.append_output(self.events_df)
            except (ValueError) as e:
                print(f"Error processing file: {e}")
        else:
            print(f"{self.events_csv} not found")

        # Sort the file contents by the first column
        self.sort_times_and_write_file()


    def make_blank_event_times_page(self) -> None:
        """
        Initializes the file times page with a message that csv wasn't processed
        Not needed anymore since a page is always created with at least radar/LSR times
        """
        with open(self.html_file, 'w', encoding='utf-8') as fout:
            fout.write(HEAD_NOPRE)
            fout.write('<br><br>\n')
            fout.write('<h3>Event Notifications not available. Did you upload a csv?</h3>\n')
            fout.write(TAIL_NOPRE)

        with open(self.text_file, 'w', encoding='utf-8') as fout:
            fout.write('Event Notifications not available. Did you upload a csv?\n')

    def make_events_new_times(self, row):
        """
        This function creates the datetime string for the placefiles
        """
        date_str = row.get('utc_date',"")
        hour = row.get('utc_hour',"")
        minute = row.get('utc_minute',"")
        delay =  row.get('delay_min',"")
        # Handle missing hour or minute values
        if pd.isna(hour):
            hour = 0
        if pd.isna(minute):
            minute = 0
        if pd.isna(delay):
            delay = 0

        # Combine the date, hour, and minute into a datetime object
        datetime_str = f"{date_str} {int(hour):02d}:{int(minute):02d}"
        orig_dtobj = datetime.strptime(datetime_str, '%m/%d/%Y %H:%M')
        new_dtobj = orig_dtobj + timedelta(seconds=int(self.seconds_shift))
        orig_time = orig_dtobj.strftime("%Y-%m-%d %H:%M")
        new_time = new_dtobj.strftime("%Y-%m-%d %H:%M")
        return new_time, orig_time

    def get_radar_filenames(self) -> list:
        """
        This function extracts the radar times from the radarinfo.json file
        """
        try:
            radar_info = os.path.join(self.radar_dir, 'radarinfo.json')
            with open(radar_info, 'r', encoding='utf-8') as f:
                data = json.load(f)
                keys = list(data.keys())
                #print(keys)
                return keys
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error processing file: {e}")
            return None

    def append_radar_file_info(self) -> None:
        """
        extracts timestring from names of downloaded radar files
        writes new and original timestrings to output files
        """
        try:
            files = self.get_radar_filenames()
            for filename in files:
                rda = filename[0:4]
                orig_file_timestr = filename[4:19]
                orig_datetime_obj = datetime.strptime(orig_file_timestr, \
                                                    '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC)
                new_datetime_obj = orig_datetime_obj + timedelta(seconds=int(self.seconds_shift))
                orig_tstr = datetime.strftime(orig_datetime_obj, '%Y-%m-%d %H:%M')
                new_tstr = datetime.strftime(new_datetime_obj, '%Y-%m-%d %H:%M')

                output_line = f"| {new_tstr} | {orig_tstr} |------- {rda} ---------|   \n"
                self.events_list.append(output_line)

        except ValueError as e:
            print(f"Error processing file: {e}")

    def append_output(self, df) -> None:
        """
        This function appends the output to a list
        """
        for _index,row in df.iterrows():
            try:
                ftypetext = f"{row['TYPETEXT']:<17}"
                fqualifier = f"{row['QUALIFIER']:<6}"
                fmag = f"{row['MAG']:<6}"
                fsource = f"{row['SOURCE']:<18}"
                flat = f"{row['LAT']:<8}"
                flon = f"{row['LON']:<9}"
                forig_time = f"{row['orig_time']:<15}"
                fnew_time = f"{row['new_time']:<15}"
                fremark = row.get("REMARK", "")
                fremark = fremark[0:76]
                out1 = f"| {fnew_time} | {forig_time} | {flat} | {flon} | {ftypetext} "
                out2 = f"| {fqualifier} | {fmag} | {fsource} | {fremark}\n"
                output_line = out1 + out2
                self.events_list.append(output_line)
            except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
                print(f"Error processing file: {e}")


    def make_lsr_dataframe(self):
        """
        This function reads the LSRs CSV file and creates a new column with the new time
        """
        df = pd.read_csv(self.lsrs_csv, usecols=lsr_columns, dtype=str)
        df = df.fillna(' ')
        try:
            df['dts_orig_obj'] = pd.to_datetime(df['VALID'], format='%Y%m%d%H%M')
            df['dts_new_obj'] = df['dts_orig_obj'] + pd.Timedelta(seconds=int(self.seconds_shift))
            df['orig_time'] = df['dts_orig_obj'].dt.strftime('%Y-%m-%d %H:%M')
            df['new_time'] = df['dts_new_obj'].dt.strftime('%Y-%m-%d %H:%M')
            self.append_output(df)
            return df
        except ValueError as e:
            print(f"Error processing file: {e}")
            return None

    def make_events_dataframe(self):
        """
        This function reads the notifications CSV file and creates a new column with the new time
        """
        events_csv = open(self.events_csv, 'r', encoding='utf-8')
        df_orig = pd.read_csv(events_csv, usecols=notif_columns, dtype=str)
        df = df_orig.loc[df_orig['TYPETEXT'] != 'NO EVENT']
        df = df.fillna('NA')
        df.replace('QUESTION', 'QUES', inplace=True)
        df.replace('VERIFIED', 'VER', inplace=True)
        df.replace('UNVERIFIED', 'UNVER', inplace=True)
        df.replace('ESTIMATED', 'EST', inplace=True)
        df.replace('MEASURED', 'MEAS', inplace=True)
        df['utc_minute'] = df['utc_minute'].str.zfill(2)
        df['utc_hour'] = df['utc_hour'].str.zfill(2)
        df['full_dts'] = df['utc_date'] + ' ' + df['utc_hour'] + ':' + df['utc_minute']
        try:
            df['dts_orig_obj'] = pd.to_datetime(df['full_dts'], format='%m/%d/%Y %H:%M', \
                                errors='coerce')
            df['dts_new_obj'] = df['dts_orig_obj'] + pd.Timedelta(seconds=int(self.seconds_shift))
            df['orig_time'] = df['dts_orig_obj'].dt.strftime('%Y-%m-%d %H:%M')
            df['new_time'] = df['dts_new_obj'].dt.strftime('%Y-%m-%d %H:%M')
            self.append_output(df)
            return df
        except ValueError as e:
            print(f"Error processing file: {e}")
            return None

    def sort_times_and_write_file(self) -> None:
        """
        This function sorts the file_times.txt file by the first column
        """
        lines = self.events_list
        lines = list(set(lines)) # Remove duplicates

        # Sort lines by the first section (date and time)
        lines.sort(key=lambda line: line.split('|')[1].strip())

        # Insert the header after sorting is done
        lines = [DASHES, HEADER, DASHES] + lines

        with open(self.text_file, 'w', encoding='utf-8') as file:
            file.writelines(lines)

        with open(self.html_file, 'w', encoding='utf-8') as fout:
            fout.write(HEAD)
            for line in lines:
                fout.write(line)
            fout.write(TAIL)

if __name__ == '__main__':
    if sys.platform.startswith('win'):
        pass
        #args = [str(sim_times['simulation_seconds_shift']), cfg['ASSETS_DIR'], cfg['DATA_DIR']]
        #src_dir = 'C:/data/scripts/cloud-radar-server'
        #dest_dir = 'C:/data/scripts/cloud-radar-server'
        #radar_dir = 'C:/data/scripts/cloud-radar-server/data/radar'
        #time_delta = str(60*60*24*32*5 + 497)
        ##time_delta = datetime(2024, 10, 20, 20, 30) - datetime(2024, 5, 7, 21, 30)
        #event_times = WriteEventTimes(time_delta, src_dir, dest_dir, radar_dir)
    #seconds_shift, csv_dir, radar_dir, html_file, text_file
    event_times = WriteEventTimes(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
