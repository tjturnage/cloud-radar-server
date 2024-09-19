"""_summary_

    Returns:
        _type_: _description_
"""
from __future__ import print_function
import sys
from datetime import datetime
from pathlib import Path
from glob import glob
import pytz
import os

class UpdatePlacefiles():
    """
    updates placefiles to remove TimeRange sections later than playback time

         
    current_playback_time: str

    """


    def __init__(self, current_playback_timestr: str, PLACEFILES_DIR: str):

        self.current_playback_timestr = current_playback_timestr
        self.placefiles_directory = Path(PLACEFILES_DIR)
        print(self.placefiles_directory)
        self.current_playback_time = None
        try:
            self.playback_timestamp = datetime.strptime(self.current_playback_timestr, \
                    "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC).timestamp()
        except ValueError as ve:
            print(f'Could not convert timestamp: {ve}')
            self.current_playback_time = 'None'
        
        self.write_updated_placefiles()

    def timerange_end_to_timestamp(self, timerange_line: str):
        """
        - input: timerange_line --> str
            extracts first time string from TimeRange line in placefile
            Example: TimeRange: 2019-03-06T23:14:39Z 2019-03-06T23:16:29Z 
        - returns: time --> float
            timestamp associated with second time string
            Example: 2019-03-06T23:16:39Z --> 1551900879.0
'
        """
        time_str = timerange_line.split(' ')[-1][:-1]   # last element, remove newline
        print(f"Time string: {time_str}")
        timestamp = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).timestamp()
        timestamp += 300 # add 5 minutes to check time
        return timestamp

    def write_updated_placefiles(self) -> None:
        """
        # Grab the _shifted placefiles to make _updated placefiles without any TimeRange
        # extending beyond the simulation playback time        
        """
        #all_filenames = glob(f"{self.placefiles_directory}/*.txt")
        #filenames = [x for x in all_filenames if "shifted" in x]
        #print(all_filenames)

        files = os.listdir(self.placefiles_directory)
        shifted_filenames = [x for x in files if "shifted.txt" in x]
        #print(shifted_filenames)
        # except Exception as e:
        #     print(f"Error listing files in directory: {e}")
        for file in shifted_filenames:
            source_file = os.path.join(self.placefiles_directory, file)
            #print(f"Processing file: {source_file}")
            new_filename = f"{source_file[0:source_file.index('_shifted.txt')]}_updated.txt"
            destination_path = os.path.join(self.placefiles_directory, new_filename)
            fout_path = open(destination_path, 'w', encoding='utf-8')
            fin = open(source_file, 'r', encoding='utf-8')
            data = fin.readlines()
            fin.close()
            line_num = len(data)
            for i, line in enumerate(data):
                if "TimeRange" in line:
                    line_timestamp = self.timerange_end_to_timestamp(line)
                    if line_timestamp > self.playback_timestamp:
                        #print(f"{line_timestamp} ... {self.playback_timestamp}")
                        #print(f"TimeRange line exceeds playback time: {i} {line}")
                        #print(i, line)
                        line_num = i
                        break
            try:
                trimmed_lines = data[:line_num]
                fout_path.writelines(trimmed_lines)
                fout_path.close()

            except (IOError, ValueError, KeyError) as e:
                print(f"Error updating placefile: {e}")
                #outfile.truncate(0)


#-------------------------------
if __name__ == "__main__":
    #playback_time = '2024-09-18 15:45'
    #placefiles_directory = 'C:/data/scripts/cloud-radar-server/assets/placefiles'
    #UpdatePlacefiles(playback_time, placefiles_directory)
    UpdatePlacefiles(sys.argv[1],sys.argv[2])
