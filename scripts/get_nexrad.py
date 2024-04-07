import os
import boto3
import botocore
from botocore.client import Config
from pathlib import Path
from datetime import datetime, timedelta

p = Path('.')
RAW_RADAR_DIR = p.parent / 'data' / 'radar'
os.makedirs(RAW_RADAR_DIR, exist_ok=True)


class NexradDownloader:
    def __init__(self, radar_id, start_time, duration):
        self.radar_id = radar_id
        self.start_time = start_time
        self.duration = duration
        self.end_time = self.start_time + timedelta(minutes=duration)
        self.bucket = boto3.resource('s3', config=Config(signature_version=botocore.UNSIGNED,
                                                         user_agent_extra='Resource')).Bucket('noaa-nexrad-level2')
     
        self.prefix_day_one, self.prefix_day_two = self.make_prefix()
        self.make_destination_folder()
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

    def make_destination_folder(self):
            self.destination_folder = RAW_RADAR_DIR / self.radar_id
            os.makedirs(self.destination_folder, exist_ok=True)

    def download_files(self):
        for obj in self.bucket.objects.filter(Prefix=self.prefix_day_one):
            file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
            if file_dt >= self.start_time and file_dt <= self.end_time:
                if obj.key.endswith('V06') or obj.key.endswith('V08'):
                    print(obj.key)
                    file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
                    self.bucket.download_file(obj.key, str(self.destination_folder / Path(obj.key).name))


        if self.prefix_day_two is not None:
            for obj in self.bucket.objects.filter(Prefix=self.prefix_day_two):
                file_dt = datetime.strptime(obj.key[20:35], '%Y%m%d_%H%M%S')
                if file_dt >= self.start_time and file_dt <= self.end_time:
                    if obj.key.endswith('V06'):
                        print(obj.key)
                        self.bucket.download_file(obj.key, str(self.destination_folder / Path(obj.key).name))

        return


if __name__ == "__main__":
    # need to changes time to string format since the datetime object is not shared in Dash
    NexradDownloader('KGRR', datetime(2023, 8, 24, 23, 30, 0), 60)
