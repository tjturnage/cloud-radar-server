"""
Leverages AWS to download NEXRAD radar data from the NOAA NEXRAD Level 2 or TDWR bucket.
--downloads all available volume scans for a specific radar in a specific time range
--target data is saved in the data/radar folder in the project directory.

09 Jun 2024:
--older radar files use hourly tar files as obj.key, had to set filenames as Path(obj.key).name
--created identify_radar_files() to filter out non-radar files and those outside the time range

"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
#import json
import boto3
import botocore
from botocore.client import Config

class NexradDownloader:
    """
    Downloads NEXRAD radar data from the NOAA NEXRAD Level 2 or TDWR bucket.
    The radar data are saved in the data/radar folder in the project directory.
    """
    #BASE_DIRECTORY = Path('/data/cloud-radar-server')
    BASE_DIRECTORY = Path.cwd()
    RADAR_DATA_BASE_DIR = BASE_DIRECTORY / 'data' / 'radar'

    def __init__(self, radar_id, start_tstr, duration, download):
        super().__init__()
        self.radar_id = radar_id
        self.start_tstr = start_tstr
        self.start_time = datetime.strptime(self.start_tstr,'%Y-%m-%d %H:%M:%S UTC')
        self.duration = int(duration)
        self.end_time = self.start_time + timedelta(minutes=int(duration))
        self.download = download
        self.radar_files_dict = {}
        self.bucket = boto3.resource('s3', config=Config(signature_version=botocore.UNSIGNED,
                                        user_agent_extra='Resource')).Bucket('noaa-nexrad-level2')

        self.prefix_day_one, self.prefix_day_two = self.make_prefix()
        self.download_directory = self.RADAR_DATA_BASE_DIR / self.radar_id / 'downloads'
        os.makedirs(self.download_directory, exist_ok=True)
        self.process_files()

    def make_prefix(self):
        """
        Determines the prefix for the radar files in the bucket.
        If self.endtime falls on the same day as self.starttime, then only one prefix is needed.
        """
        first_folder = self.start_time.strftime('%Y/%m/%d/')
        second_folder = self.end_time.strftime('%Y/%m/%d/')
        prefix_one = f'{first_folder}{self.radar_id}'

        if first_folder != second_folder:
            prefix_two = f'{second_folder}{self.radar_id}'
        else:
            prefix_two = None

        #print(prefix_one, prefix_two)
        return prefix_one, prefix_two


    def query_files(self, obj) -> None:
        """
        Filters out non-radar files that are in the bucket.
        Identifies those radar files that are within the time range specified by the user.
        This is done by comparing the filename datetime string with the simulation start/end time.
        """
        key = obj.key
        filename = Path(obj.key).name
        if filename.endswith('V06') or filename.endswith('V08') or filename.endswith('.gz'):
            file_dt = datetime.strptime(filename[4:19], '%Y%m%d_%H%M%S')
            if self.start_time <= file_dt <= self.end_time:
                this_filepath = str(self.download_directory / this_filepath)
                print(this_filepath)
                self.radar_files_dict[filename] = {'key': key, 'filepath': filename}


    def download_or_inventory_file(self, obj) -> None:
        """
        Filters out non-radar files that are in the bucket.
        Identifies those radar files that are within the time range specified by the user.
        This is done by comparing the filename datetime string with the simulation start/end time.
        If self.download is True, the radar files are downloaded.
        If self.download is False, a dictionary of radar files is created without downloading the files.
        """
        key = obj.key
        filename = Path(obj.key).name
        if filename.endswith('V06') or filename.endswith('V08') or filename.endswith('.gz'):
            file_dt = datetime.strptime(filename[4:19], '%Y%m%d_%H%M%S')
            if self.start_time <= file_dt <= self.end_time:
                this_file = str(self.download_directory / filename)
                print(this_file)
                if self.download:
                    self.bucket.download_file(key, this_file)
                else:
                    self.radar_files_dict[filename] = this_file

    def process_files(self) -> None:
        """
        Processes the radar files in the bucket.
        """
        for obj in self.bucket.objects.filter(Prefix=self.prefix_day_one):
            self.download_or_inventory_file(obj)

        if self.prefix_day_two is not None:
            for obj in self.bucket.objects.filter(Prefix=self.prefix_day_two):
                self.download_or_inventory_file(obj)

        # if not self.download:
        #     try:
        #         with open(f"{self.download_directory}/radar_dict.json", 'w', encoding='utf-8') as f:
        #             json.dump(self.radar_files_dict, f)
        #     except:
        #         print('No radar files found in the specified time range.')
        # else:
        #     try:
        #         print('Downloaded radar files:')
        #         #with open(f"{self.download_directory}/radar_dict.json", 'r', encoding='utf-8') as f:
        #         #    radar_files = json.load(f)
        #     except:
        #         print('No radar files found in the specified time range.')


if __name__ == "__main__":

    #NexradDownloader('KDTX', '2013-05-20 22:45:00 UTC', 30, False)
    NexradDownloader(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])