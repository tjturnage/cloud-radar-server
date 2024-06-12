import subprocess 
import os, signal
import psutil 
from glob import glob 
import json 
import pandas as pd 
from pathlib import Path 

def exec_script(script_path, args):
    """
    Generalized function to run application scripts. subprocess.run() or similar is 
    required for tracking of spawned python processes and termination if requested
    by the user via the cancel button. Returns Exception object which is parsed to 
    determine exit code/status. 
    """
    # Need to specify the PYTHON executable on the windows laptop. 
    dir_parts = Path.cwd().parts
    PYTHON = "python"
    if 'C:\\' in dir_parts:
        PYTHON = r"C:\\Users\\lee.carlaw\\environments\\cloud-radar\\Scripts\python.exe"

    try:
        subprocess.run([PYTHON, script_path] + args, check=True)
    except Exception as e:
        print(f"Error running {script_path}: {e}")
        return e
    

def get_app_processes():
    """
    Reports back all running python processes as a list. Used by the monitoring 
    function and cancel button.
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'cmdline', 'name', 'username', 'cwd']):
        try:
            info = proc.info
            if ('python' in info['name'] or 'wgrib2' in info['name']) and \
                len(info['cmdline']) > 1: 
                processes.append(info)
        except:
            pass
    return processes 

def cancel_all():
    """
    This function is invoked when the user clicks the Cancel button in the app. See
    app.cancel_scripts.
    """
    # Should move this somewhere else, maybe into the __init__ function? These are 
    # the cancelable scripts
    scripts_list = ["Nexrad.py", "nse.py", "get_data.py", "process.py", 
                    "hodo_plot.py", "munger.py"]
    processes = get_app_processes()

    # ******************************************************************************
    # POTENTIAL ISSUES - Race Conditions?
    # There is a chance a new process could spawn between the initial query above
    # and process(es) being terminated below. Also, a process could end before 
    # getting into the loop. In that case, is it gauranteed that "old" pid isn't 
    # re-used somewhere else, and we end up accidentally terminating something we 
    # shouldn't be?
    # ******************************************************************************
    for process in processes:
        if any(x in process['cmdline'][1] for x in scripts_list) or \
            ('wgrib2' in process['cmdline'][0]):
            print(f"Killing process: {process['cmdline'][1]} with pid: {process['pid']}")
            os.kill(process['pid'], signal.SIGTERM)
        
        if len(process['cmdline']) >= 3 and 'multiprocessing' in process['cmdline'][2]:
            print(f"Killing process: {process['cmdline'][1]} with pid: {process['pid']}")
            os.kill(process['pid'], signal.SIGTERM)
            #p = psutil.Process(process['pid'])
            #p.terminate()

def radar_monitor(sa):
    """
    Reads radar_dict.json file(s) output from the NexradDownloader. Looks for associated 
    radar files on the system and compares to the total expected number and broadcasts a 
    percentage to the radar_status progress bar.
    """
    expected_files = []
    radar_dirs = glob(f"{sa.data_dir}/radar/**")
    for d in radar_dirs:
        json_file = glob(f"{d}/downloads/radar_dict.json")
        if len(json_file) == 1:
            with open(json_file[0], 'r', encoding='utf-8') as f:
                radar_dictionary = json.load(f)
                expected_files.extend(list(radar_dictionary.values()))

    files_on_system = [x for x in expected_files if os.path.exists(x)]
    output = 0
    if len(expected_files) > 0:
        output = 100 * (len(files_on_system) / len(expected_files))
    return output, files_on_system


def nse_status_checker(sa):
    """
    Read in model status text file and query associated file sizes. 
    """
    filename = f"{sa.data_dir}/model_data/model_list.txt"
    output = []
    if os.path.exists(filename):
        model_list = []
        filesizes = []
        with open(filename, 'r', encoding='utf-8') as f:
            text_listing = f.readlines()
            for line in text_listing:
                filename = line[:-1]
                model_list.append(filename.rsplit('/', 1)[1])
                filesizes.append(round(file_stats(filename), 2))

        df = pd.DataFrame({'Model data': model_list, 'Size (MB)': filesizes})
        output = df.to_dict('records')

    return output


def file_stats(filename):
    """Return the size of a specific file.  If it doesn't exist, returns 0"""
    filesize = 0.
    if os.path.exists(filename):
        filesize = os.stat(filename).st_size / 1024000.
    return filesize