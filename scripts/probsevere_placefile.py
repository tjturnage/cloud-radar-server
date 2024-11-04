"""
This script is adapted from probsevere_gr_placefile.py created by John Cintineo
https://gitlab.ssec.wisc.edu/jcintineo/probsevere/-/blob/master/src/science_utils/probsevere_gr_placefile.py

"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
#import numpy as np
from dataclasses import dataclass
#import pickle as pickle

# The color dictionary is used to determine the color of the ProbSevere object
color = {0: '90 90 90', 1: '108 87 98', 2: '120 85 103', 3: '138 83 110', 4: '150 81 115',
         5: '169 78 122', 6: '181 76 128', 7: '199 73 136', 8: '211 72 141', 9: '228 69 148',
         10: '246 66 155', 11: '246 67 151', 12: '247 68 143', 13: '247 69 138', 14: '247 70 130',
         15: '247 71 125', 16: '249 72 117', 17: '249 73 108', 18: '249 74 104', 19: '250 75 96',
         20: '250 76 91', 21: '250 78 83', 22: '250 78 78', 23: '250 80 70', 24: '250 80 65',
         25: '250 82 56', 26: '252 83 49', 27: '252 84 44', 28: '252 85 36', 29: '252 85 31',
         30: '252 87 23', 31: '252 93 30', 32: '252 103 40', 33: '252 108 47', 34: '252 118 57',
         35: '250 128 68', 36: '250 134 75', 37: '250 143 85', 38: '250 149 92', 39: '250 159 103',
         40: '250 165 110', 41: '249 174 120', 42: '249 184 131', 43: '247 190 138',
         44: '247 199 148', 45: '247 205 155', 46: '246 215 165', 47: '246 221 171',
         48: '246 230 183', 49: '246 237 190', 50: '246 246 200', 51: '246 238 202',
         52: '246 234 203', 53: '246 227 204', 54: '246 222 205', 55: '246 214 206',
         56: '246 209 208', 57: '246 202 209', 58: '246 198 211', 59: '246 190 212',
         60: '246 183 214', 61: '246 178 215', 62: '247 171 217', 63: '247 166 218',
         64: '247 159 220', 65: '247 154 221', 66: '247 147 222', 67: '247 139 224',
         68: '247 135 225', 69: '247 127 227', 70: '249 121 228', 71: '249 115 228',
         72: '249 110 230', 73: '249 103 231', 74: '249 98 233', 75: '249 91 235',
         76: '249 84 236', 77: '249 79 237', 78: '250 71 238', 79: '250 67 240',
         80: '250 59 241', 81: '250 55 243', 82: '250 47 244', 83: '250 42 246', 84: '250 35 246',
         85: '250 27 249', 86: '250 23 250', 87: '250 16 250', 88: '250 11 252', 89: '250 4 253',
         90: '250 0 255', 91: '250 5 253', 92: '250 4 253', 93: '250 4 253', 94: '250 3 253', 95: '250 3 253',
         96: '250 2 255', 97: '250 2 255', 98: '250 1 255', 99: '250 1 255', 100: '250 0 255'}

@dataclass
class ProbSeverePlacefile:
    """
    Create a GR2Analyst compliant placefile from ProbSevere
    """
    lat:            str     #  Input -- latitude to build a bounding box that filters objects
    lon:            str     #  Input -- longitude to build a bounding box that filters objects
    data_directory: str     #  Input -- directory with json files
    outdir:         str     #  Output -- directory for placefiles

    def __post_init__(self):
        self.files = self.make_file_list()
        self.timestrings = self.make_placefile_timestrings()
        self.timerange_lines = self.make_placefile_timerange_lines()
        self.placefile_path = Path(self.outdir) / 'ProbSevere.txt'
        self.lat1, self.lat2, self.lon1, self.lon2 = self.bounding_box()
        self.loop_files()

    def make_file_list(self):
        """
        Create a Pathlib list of json files in the data directory
        """
        scratch_list = []
        source_dir = Path(self.data_directory)
        filenames = sorted(source_dir.iterdir())
        for f in filenames:
            if '.json' in str(f):
                scratch_list.append(f)
        return sorted(scratch_list)

    def loop_files(self) -> None:
        """
        Create a Pathlib list of json files in the data directory
        """
        with open(self.placefile_path, 'w', encoding='utf-8') as pf:
            pf.write('Title: ProbSevere objects loop -- for radar simulation\nRefresh: 1\n\n')
            for n, file in enumerate(self.files):
                timrange_line = f"{self.timerange_lines[n]}\n\n"
                pf.write(timrange_line)
                with open(file, 'r', encoding='utf-8') as fin:
                    data = json.load(fin)
                    for storm in data['features']:
                        coordinates = storm['geometry']['coordinates'][0]
                        in_bounds = self.check_bounds(coordinates)
                        if in_bounds:
                            probsvr_model = storm['models']['probsevere']
                            coordinate_lines = self.get_coordinate_lines(coordinates)
                            combined_string, percent = self.feature_property_text(probsvr_model)

                            color_line = f"Color: {color[(int(percent))]}\n"
                            pf.write(color_line)
                            pf.write(f'Line: 2, 0, "{combined_string}"\n')
                            pf.write(coordinate_lines)
                            pf.write("\nEnd:\n\n")

    def feature_property_text(self,probsvr_models):
        """
        Create a string of feature properties from the json data.
        This will be used to create the pop-up text for the placefile.
        Returns:
        --------
        combined_string: str
            The pop-up text string of feature properties
        percentage: str
            The percentage of the ProbSevere object
            This is used to select the color of the object
        """
        strings_list = []
        for _key, value in probsvr_models.items():
            strings_list.append(value)
        percentage = strings_list[0]
        combined_string = "\\n".join(strings_list[1:])
        return combined_string, percentage

    def check_bounds(self, coordinates) -> bool:
        """
        Check if the coordinates are within the bounding box
        """
        for coord in coordinates:
            if not self.lat1 < coord[1] < self.lat2:
                return False
            if not self.lon1 < coord[0] < self.lon2:
                return False
        return True

    def make_placefile_timestrings(self) -> list:
        """
        Create a list of GR2Analyst compliant time strings from the json filenames
        """
        timestrings = []
        for f in self.files:
            try:
                dt_str = str(f)[-20:-5]
                new_dts = datetime.strptime(dt_str,'%Y%m%d_%H%M%S').strftime('%Y-%m-%dT%H:%M:%SZ')
                timestrings.append(new_dts)
            except ValueError as ve:
                print(f"Value is out of range: {ve}")

        return sorted(timestrings)


    def make_placefile_timerange_lines(self) -> list:
        """
        Create a list of GR2Analyst placefile TimeRange lines for looping capability.
        This uses the previously created timestrings list to build the TimeRange lines.
        """
        timeranges = []
        tstr_length = len(self.timestrings)
        for t in range(1, tstr_length):
            timeranges.append(f'TimeRange: {self.timestrings[t-1]} {self.timestrings[t]}\n')

        timerange_lines = sorted(timeranges)

        # Here we need to supply an extra final time to end the timerange associated
        # with the very last file in the list.
        final_time = datetime.strptime(self.timestrings[-1], '%Y-%m-%dT%H:%M:%SZ') + \
                timedelta(minutes=2)
        final_formatted = final_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Now we can define the final TimeRange and append it to the list of timeranges.
        timerange_lines.append(f'TimeRange: {self.timestrings[-1]} {final_formatted}\n')
        return timerange_lines

    def bounding_box(self):
        """
        Create a bounding box for the ProbSevere objects.
        This trims the placefile to improve performance.
        """
        distance = 5 # degrees
        lat = float(self.lat)
        lon = float(self.lon)
        lat1 = lat - distance
        lat2 = lat + distance
        lon1 = lon - distance
        lon2 = lon + distance
        return lat1, lat2, lon1, lon2

    def get_coordinate_lines(self,coordinates) -> str:
        """
        Create a string of coordinate lines from the json data
        """
        coordinate_lines = ''
        for _c, coord in enumerate(coordinates):
            coordinate_lines += f'{coord[1]}, {coord[0]}\n'
        return coordinate_lines.strip()


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        ProbSeverePlacefile('43.0', '-85.5', 'C:/data/ProbSevere', os.getcwd())
    else:
        # center lat, center lon, data source directory, placefile output directory
        ProbSeverePlacefile(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
