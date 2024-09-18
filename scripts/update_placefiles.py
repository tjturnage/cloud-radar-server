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
#from config import POLLING_DIR

class UpdatePlacefiles():
    """
    updates placefiles to remove TimeRange sections later than playback time

         
    current_playback_time: str

    """


    def __init__(self, current_playback_timestr: str, PLACEFILES_DIR: str):

        self.current_playback_timestr = current_playback_timestr
        self.this_placefiles_directory = Path(PLACEFILES_DIR)
        self.current_playback_time = None
        try:
            self.playback_timestamp = datetime.strptime(self.current_playback_timestr, \
                    "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC).timestamp()
        except ValueError as ve:
            print(f'Could not convert timestamp: {ve}')
            self.current_playback_time = 'None'
            return

    def timerange_start_to_timestamp(self, timerange_line: str):
        """
        - input: timerange_line --> str
            extracts first time string from TimeRange line in placefile
            Example: TimeRange: 2019-03-06T23:14:39Z 2019-03-06T23:16:29Z 
        - returns: time --> float
            timestamp associated with first time string
            Example: 2019-03-06T23:14:39Z --> 1551900879.0

        """
        time_str = timerange_line.split(' ')[1]
        timestamp = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).timestamp()
        return timestamp

    def write_updated_placefiles(self,PLACEFILES_DIR) -> None:
        """
        # Grab the _shifted placefiles to make _updated placefiles without any TimeRange
        # extending beyond the simulation playback time        
        """
        filenames = glob(f"{PLACEFILES_DIR}/*.txt")
        filenames = [x for x in filenames if "shifted" in x]
        for this_file in filenames:
            outfilename = f"{this_file[0:this_file.index('_shifted.txt')]}_updated.txt"
            outfile = open(outfilename, 'w', encoding='utf-8')
            with open(this_file, 'r', encoding='utf-8') as f:
                data = f.readlines()

            try:
                for place_line in data:
                    if "TimeRange" in place_line:
                        line_timestamp = self.timerange_start_to_timestamp(place_line)
                        if line_timestamp < self.playback_timestamp:
                            outfile.write(place_line)
                        else:
                            outfile.close()
                            break
                    else:
                        outfile.write(place_line)

            except (IOError, ValueError, KeyError) as e:
                print(f"Error updating placefile: {e}")
                #outfile.truncate(0)


#-------------------------------
if __name__ == "__main__":
    #this_playback_time = '2024-06-01 23:15'
    #this_placefiles_directory = '/data/cloud/assets/placefiles'
    UpdatePlacefiles(sys.argv[1],sys.argv[2])
