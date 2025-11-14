"""_summary_

    Returns:
        _type_: _description_
"""
#from __future__ import print_function
import sys
from datetime import datetime, timedelta
from pathlib import Path
import os
import pytz


class UpdatePlacefiles():
    """
    updates placefiles to remove TimeRange sections later than playback time

         
    current_playback_time: str

    """
    def __init__(self, current_playback_timestr: str, PLACEFILES_DIR: str):

        self.current_playback_timestr = current_playback_timestr
        self.placefiles_directory = Path(PLACEFILES_DIR)
        self.current_playback_time = None
        try:
            self.playback_timestamp = datetime.strptime(self.current_playback_timestr, \
                    "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC).timestamp()
        except ValueError as ve:
            print(f'Could not convert timestamp: {ve}')
            self.current_playback_time = 'None'

        self.write_updated_placefiles()

    def timerange_to_timestamp(self, timerange_line: str):
        """
        - input: timerange_line --> str
            extracts first time string from TimeRange line in placefile
            Example: TimeRange: 2019-03-06T23:14:39Z 2019-03-06T23:16:29Z 
        - returns: time --> float
            timestamp associated with first time string
            Example: 2019-03-06T23:16:39Z --> 1551900879.0
'
        """
        time_str = timerange_line.split(' ')[1]         # first element
        timestamp = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).timestamp()
        #timestamp = timestamp + 300 # add 5 minutes to check time
        return timestamp

    def extract_placefile_lines(self, placefile: str) -> list:
        """
        - input: placefile --> str
            path to placefile
        - returns: data --> list
            list of lines in placefile
        """
        try:
            with open(placefile, 'r', encoding='utf-8') as fin:
                data = fin.readlines()
            return data
        except (IOError, ValueError, KeyError) as e:
            print(f"Error extracting placefile lines: {e}")
            return []

    def write_updated_placefiles(self) -> None:
        """
        Grab the _shifted placefiles to make _updated placefiles
        _updated placefiles omit TimeRange sections beyond the playback time
        """

        files = os.listdir(self.placefiles_directory)
        shifted_filenames = [x for x in files if "shifted.txt" in x]
        now = datetime.now(pytz.utc) + timedelta(minutes=10)
        for file in shifted_filenames:
            source_file = os.path.join(self.placefiles_directory, file)
            new_filename = f"{source_file[0:source_file.index('_shifted.txt')]}_updated.txt"
            destination_path = os.path.join(self.placefiles_directory, new_filename)
            fout_path = open(destination_path, 'w', encoding='utf-8')

            try:
                data = self.extract_placefile_lines(source_file)
                line_num = len(data)

                # Identify valid and invalid TimeRange blocks
                tr_indices = [i for i, line in enumerate(data) if "TimeRange" in line]
                valid_tr_indices = []
                for i in tr_indices:
                    line = data[i]
                    line_timestamp = self.timerange_to_timestamp(line)
                    if line_timestamp <= self.playback_timestamp:
                        valid_tr_indices.append(i)

                header_end_index = tr_indices[0] if tr_indices else len(data)
                header_lines = data[:header_end_index]
                trimmed_lines = header_lines # Start the output with the header

                # Find entries that should be visible based on the current simulation time. Roll
                # the "end" time forward 10 minutes from real time. 
                # This gets around a bug in GR where the last polled volume scan is presumed to be
                # real world time, even if the scan time is old. 
                for i, tr_index in enumerate(tr_indices):
                    is_valid = tr_index in valid_tr_indices
                        
                    if is_valid:
                        # Define the block boundaries
                        block_start = tr_index
                        
                        # Block ends right before the next TimeRange line, or at EOF
                        if i + 1 < len(tr_indices):
                            block_end = tr_indices[i+1] 
                        else:
                            block_end = len(data) # End of file
                            
                        block_lines = data[block_start:block_end]
                        tr_string = block_lines[0]
                        tr_parts = tr_string.split(' ')
                        end_valid_time = tr_parts[2].strip() 
                        
                        # Get timestamp of end time
                        end_valid_dt = datetime.strptime(end_valid_time, '%Y-%m-%dT%H:%M:%SZ')
                        end_valid_dt = end_valid_dt.replace(tzinfo=pytz.UTC).timestamp()

                        # Replace the end time with 'now' timestamp -- this is the most 
                        # recent valid time range. 'now' is rolled 10 minutes forward 
                        # from real time. 
                        if end_valid_dt > self.playback_timestamp:
                            new_end_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')
                            new_tr = f"{tr_parts[0]} {tr_parts[1]} {new_end_time}\n"
                            block_lines[0] = new_tr
                        trimmed_lines.extend(block_lines)

                fout_path.writelines(trimmed_lines)
                fout_path.close()

            except (IOError, ValueError, KeyError) as e:
                print(f"Error updating placefile: {e}")
                continue

#-------------------------------
if __name__ == "__main__":
    #playback_time = '2024-09-18 15:45'
    #placefiles_directory = 'C:/data/scripts/cloud-radar-server/assets/placefiles'
    #UpdatePlacefiles(playback_time, placefiles_directory)
    UpdatePlacefiles(sys.argv[1],sys.argv[2])
