"""
Wrapper to control processing of model data and nse placefile scripts 
"""

import subprocess
from datetime import datetime, timedelta

class Nse:
    def __init__(self, sim_start, event_duration, scripts_path, data_path):
        self.sim_start = sim_start
        self.sim_end = sim_start + timedelta(minutes=int(event_duration))
        self.start_string = datetime.strftime(self.sim_start,"%Y-%m-%d/%H")
        self.end_string = datetime.strftime(self.sim_end,"%Y-%m-%d/%H")

        # Add one hour to the end time. Need at least two model data files for every sim. 
        if self.start_string == self.end_string:
            self.end_string = datetime.strftime(self.sim_end + timedelta(hours=1),"%Y-%m-%d/%H")
        
        self.scripts_path = scripts_path
        self.data_path = f"{data_path}/model_data"
        self.download_model_data()

    def download_model_data(self):
        args = (
            f"-s {self.start_string} -e {self.end_string} -p {self.data_path} "
            f"-statuspath {self.data_path}"
        ).split()
        print(args)

        # Blocking call to download model data. 
        subprocess.call(["python", f"{self.scripts_path}/meso/get_data.py"] + args)

        # Need to figure out if this was a full, partial, or bad download
        # Once create_nse_placefiles returns, the next process to produce the placefiles
        # can be dispatched. Need someway to show we've moved to this next step with the 
        # status bar. Currently, fills to 100% with completion of the step above. 
        args = f"-s {self.start_string} -e {self.end_string} -p {self.data_path} -meso".split()
        subprocess.call(["python", f"{self.scripts_path}/meso/process.py"] + args)
        print('done')
        return
     
