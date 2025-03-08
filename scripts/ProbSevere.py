"""
Leverages AWS to download ProbSevere data

"""
import sys
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import boto3
import botocore
from botocore.client import Config


@dataclass
class ProbSevereBase:
    """
    Base class for initiating downloads of ProbSevere data from the NOAA MRMS bucket
    """
    start_tstr:          str    # start time of the simulation in the format 'YYYY-MM-DD HH:MM'
    duration:            str    # duration of the simulation in minutes
    download_directory:  str    # directory to save the downloaded files


@dataclass
class ProbSevereDownloader(ProbSevereBase):
    """
    Downloads ProbSevere data from the NOAA MRMS bucket
    
    """

    def __post_init__(self):
        self.start_time = datetime.strptime(self.start_tstr,'%Y-%m-%d %H:%M')
        self.end_time = self.start_time + timedelta(minutes=int(self.duration))
        self.bucket = boto3.resource('s3', config=Config(signature_version=botocore.UNSIGNED,
                                        user_agent_extra='Resource')).Bucket('noaa-mrms-pds')

        self.prefix_day_one, self.prefix_day_two = self.make_prefix()
        os.makedirs(self.download_directory, exist_ok=True)
        self.process_files()

    def make_prefix(self):
        """
        Determines the prefix for the files in the MRMS bucket.
        If self.endtime falls on the same day as self.starttime, then only one prefix is needed.
        """
        first_folder = self.start_time.strftime('ProbSevere/%Y%m%d/')
        second_folder = self.end_time.strftime('ProbSevere/%Y%m%d/')
        prefix_one = f'{first_folder}'

        if first_folder != second_folder:
            prefix_two = f'{second_folder}'
        else:
            prefix_two = None

        return prefix_one, prefix_two


    def download_file(self, obj) -> None:
        """
        Filters out non-json files that are in the bucket.
        Identifies those files that are within the time range specified by the user.
        This is done by comparing the filename datetime string with the simulation start/end time.
        """
        key = obj.key
        filename = Path(obj.key).name
        if filename.endswith('json'):
            file_dt = datetime.strptime(filename[-20:-5], '%Y%m%d_%H%M%S')
            if self.start_time <= file_dt <= self.end_time:
                #this_file = str(self.download_directory / filename)
                #this_file = os.path.join(self.download_directory, filename)
                this_file = Path(self.download_directory) / filename

                try:
                    self.bucket.download_file(key, this_file)
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == "404":
                        print("The object does not exist.")
                    else:
                        raise

    def process_files(self) -> None:
        """
        Processes the files in the bucket.
        """
        for obj in self.bucket.objects.filter(Prefix=self.prefix_day_one):
            self.download_file(obj)

        if self.prefix_day_two is not None:
            for obj in self.bucket.objects.filter(Prefix=self.prefix_day_two):
                self.download_file(obj)


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        ProbSevereDownloader('2014-05-07 21:30', 60, 'C:/data/ProbSevere')
    else:
        ProbSevereDownloader(sys.argv[1], sys.argv[2], sys.argv[3])
