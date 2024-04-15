"""
Leverages AWS to download NEXRAD radar data from the NOAA NEXRAD Level 2 or TDWR bucket.
- downloads all available data (volume scans) for a specific radar station, for a specific time period.
- target data is saved in the data/radar folder in the project directory.
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import boto3
import botocore
from botocore.client import Config


class NexradDownloader:
    def __init__(self, radar_id, start_tstr, duration):
        super().__init__()
        self.radar_id = radar_id.upper()
        self.start_tstr = start_tstr
        self.start_time = datetime.strptime(self.start_tstr,'%Y-%m-%d %H:%M:%S UTC')
        self.duration = int(duration)
        self.end_time = self.start_time + timedelta(minutes=int(duration))
        self.bucket = boto3.resource('s3', config=Config(signature_version=botocore.UNSIGNED,
                                                         user_agent_extra='Resource')).Bucket('noaa-nexrad-level2')
     
        self.prefix_day_one, self.prefix_day_two = self.make_prefix()
        self.radar_directory = Path.cwd() / 'data' / 'radar' / self.radar_id
        os.makedirs(self.radar_directory, exist_ok=True)
        self.download_directory = self.radar_directory / 'downloads'
        os.makedirs(self.download_directory, exist_ok=True)
        self.download_files()


    def make_prefix(self):
        first_folder = self.start_time.strftime('%Y/%m/%d/')
        second_folder = self.end_time.strftime('%Y/%m/%d/')
        prefix_one = f'{first_folder}{self.radar_id}'
        
        if first_folder != second_folder:
            prefix_two = f'{second_folder}{self.radar_id}'
        else:
            prefix_two = None
        
        print(prefix_one, prefix_two)
        return prefix_one, prefix_two


    def download_files(self):
        for obj in self.bucket.objects.filter(Prefix=self.prefix_day_one):
            file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
            if file_dt >= self.start_time and file_dt <= self.end_time:
                if obj.key.endswith('V06') or obj.key.endswith('V08'):
                    self.bucket.download_file(obj.key, str(self.download_directory / Path(obj.key).name))


        if self.prefix_day_two is not None:
            for obj in self.bucket.objects.filter(Prefix=self.prefix_day_two):
                file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
                if file_dt >= self.start_time and file_dt <= self.end_time:
                    if obj.key.endswith('V06') or obj.key.endswith('V08'):
                        self.bucket.download_file(obj.key, str(self.download_directory / Path(obj.key).name))

        return


if __name__ == "__main__":

    #NexradDownloader('KGRR', '2023-08-24 23:45:00 UTC', 30)
    NexradDownloader(sys.argv[1], sys.argv[2], sys.argv[3])

