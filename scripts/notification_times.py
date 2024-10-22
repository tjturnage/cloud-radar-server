"""
This script processes input files to convert times and extract values.
"""
import sys
import os
import glob
from datetime import datetime, timedelta
import pytz
import pandas as pd

notif_columns = ['TYPETEXT','QUALIFIER','MAG','SOURCE','utc_date', 'utc_hour', 'utc_minute',
                 'LAT','LON', 'fake_rpt', 'REMARK']
lsr_columns = ['VALID','VALID2','LAT','LON','MAG','WFO','TYPECODE','TYPETEXT',
               'CITY','COUNTY','STATE','SOURCE','REMARK','UGC','UGCNAME','QUALIFIER']

class WriteEventTimes:
    """
    A class to process input files to convert times and extract values.
    """

    def __init__(self, seconds_shift, source_dir, destination_dir, rdir):
        self.seconds_shift = int(seconds_shift)
        self.source_dir = source_dir
        self.notifications_csv = os.path.join(self.source_dir, 'notifications.csv')
        #self.lsrs_csv = os.path.join(self.source_dir, 'lsrs.csv')
        self.lsrs_csv = os.path.join(self.source_dir, 'LSR_extracted.csv')
        self.destination_dir = destination_dir
        self.rdir = rdir
        self.destination_path = os.path.join(self.destination_dir, 'file_times.txt')
        # Remove the existing file_times.txt file if it exists
        if os.path.exists(self.destination_path):
            os.remove(self.destination_path)
        try:
            self.lsr_df = self.make_lsr_dataframe()
            self.write_output(self.lsr_df)
        except ValueError as e:
            print(f"Error processing file: {e}")
        try:
            self.make_notifications_df = self.make_notifications_dataframe()
            self.write_output(self.make_notifications_df)
        except ValueError as e:
            print(f"Error processing file: {e}")
        try:
            self.write_radar_files()
        except ValueError as e:
            print(f"Error processing file: {e}")


        # Sort the file_times.txt file by the first column
        self.sort_file_times()

    def make_notifications_new_times(self, row):
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

    def write_radar_files(self) -> None:
        """
        extracts timestring from names of downloaded radar files
        writes new and original timestrings to file_times.txt
        """
        fout = open(self.destination_path, 'a', encoding='utf-8')
        os.chdir(self.rdir)
        files = list(glob.glob('*'))
        for file in files:
            rda = file[0:4]
            orig_file_timestr = file[4:19]
            orig_datetime_obj = datetime.strptime(orig_file_timestr, '%Y%m%d_%H%M%S').replace(tzinfo=pytz.UTC)
            new_datetime_obj = orig_datetime_obj + timedelta(seconds=self.seconds_shift)
            orig_tstr = datetime.strftime(orig_datetime_obj, '%Y-%m-%d %H:%M')
            new_tstr = datetime.strftime(new_datetime_obj, '%Y-%m-%d %H:%M')
            output_line = f"{new_tstr} | {orig_tstr} |                      | {rda} VST\n"
            fout.write(output_line)

    def write_output(self, df) -> None:
        """
        This function writes the output to a file
        """
        fout = open(self.destination_path, 'a', encoding='utf-8')
        for _index,row in df.iterrows():
            try:
                ftypetext = f"{row['TYPETEXT']:<17}"
                fqualifier = f"{row['QUALIFIER']:<6}"
                fmag = f"{row['MAG']:<6}"
                fsource = f"{row['SOURCE']:<18}"
                flat = f"{row['LAT']:<8}"
                flon = f"{row['LON']:<9}"
                #comments = create_remark(row)
                forig_time = f"{row['orig_time']:<15}"
                fnew_time = f"{row['new_time']:<15}"
                fremark = row.get("REMARK", "")
                fremark = fremark[0:45]
                output_line = f"{fnew_time} | {forig_time} | {flat} | {flon} | {ftypetext} | {fqualifier} | {fmag} | {fsource} | {fremark}\n"
                fout.write(output_line)
            except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
                print(f"Error processing file: {e}")

        fout.close()

    def make_lsr_dataframe(self):
        """
        This function reads the LSRs CSV file and creates a new column with the new time
        """
        df = pd.read_csv(self.lsrs_csv, usecols=lsr_columns, dtype=str)
        df = df.fillna(' ')
        try:
            df['dts_orig_obj'] = pd.to_datetime(df['VALID'], format='%Y%m%d%H%M')
            df['dts_new_obj'] = df['dts_orig_obj'] + pd.Timedelta(seconds=self.seconds_shift)
            df['orig_time'] = df['dts_orig_obj'].dt.strftime('%Y-%m-%d %H:%M')
            df['new_time'] = df['dts_new_obj'].dt.strftime('%Y-%m-%d %H:%M')
            self.write_output(df)
            return df
        except ValueError as e:
            print(f"Error processing file: {e}")
            return None

    def make_notifications_dataframe(self):
        """
        This function reads the notifications CSV file and creates a new column with the new time
        """
        notifications_csv = open(self.notifications_csv, 'r', encoding='utf-8')
        df_orig = pd.read_csv(notifications_csv, usecols=notif_columns, dtype=str)
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
            df['dts_orig_obj'] = pd.to_datetime(df['full_dts'], format='%m/%d/%Y %H:%M', errors='coerce')
            df['dts_new_obj'] = df['dts_orig_obj'] + pd.Timedelta(seconds=self.seconds_shift)
            df['orig_time'] = df['dts_orig_obj'].dt.strftime('%Y-%m-%d %H:%M')
            df['new_time'] = df['dts_new_obj'].dt.strftime('%Y-%m-%d %H:%M')
            self.write_output(df)
            return df
        except ValueError as e:
            print(f"Error processing file: {e}")
            return None

    def sort_file_times(self):
        """
        This function sorts the file_times.txt file by the first column
        """
        with open(self.destination_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            lines = list(set(lines)) # Remove duplicates
        
        # Sort lines by the first column (date and time)
        lines.sort(key=lambda line: line.split('|')[0].strip())
        
        with open(self.destination_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        #args = [str(sim_times['simulation_seconds_shift']), cfg['ASSETS_DIR'], cfg['DATA_DIR']]
        src_dir = 'C:/data/scripts/cloud-radar-server'
        dest_dir = 'C:/data/scripts/cloud-radar-server'
        radar_dir = 'C:/data/scripts/cloud-radar-server/data/radar'
        time_delta = str(60*60*24*32*5 + 497)
        #time_delta = datetime(2024, 10, 20, 20, 30) - datetime(2024, 5, 7, 21, 30)        
        event_times = WriteEventTimes(time_delta, src_dir, dest_dir, radar_dir)
    else:
        event_times = WriteEventTimes(sys.argv[1], sys.argv[2], sys.argv[3], sys.orig_argv[4])
