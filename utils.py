import subprocess
import os
import signal
from pathlib import Path
from glob import glob
import psutil
import pandas as pd
import config

def exec_script(script_path, args, session_id):
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

    output = {}
    env = os.environ.copy() 
    env['session_id'] = session_id # add the unique session id to the process
    try:
        # Execute scripts as python module to allow config import from higher-level dir:
        # python -m scripts.script-name
        parts = script_path.parts
        arg = f"{script_path.parts[-2]}.{parts[-1]}".replace(".py", "")
        process = subprocess.Popen([PYTHON, '-m', arg] + args, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=env)
        output['stdout'], output['stderr'] = process.communicate()
        output['returncode'] = process.returncode
    except Exception as e:
        output['exception'] = e

    return output

def get_app_processes():
    """
    Reports back all running python processes as a list. Used by the monitoring 
    function and cancel button.
    """
    variables = ['pid', 'cmdline', 'name', 'username', 'cwd', 'status', 'create_time']
    processes = []
    for proc in psutil.process_iter(variables):
        try:
            info = proc.info
            if ('python' in info['name'] or 'wgrib2' in info['name']) and \
                len(info['cmdline']) > 1:
                
                # Tag process with its unique session id (set in exec_script above)
                info['session_id'] = proc.environ().get('session_id')  
                processes.append(info)
        except:
            pass
    return processes

def cancel_all(sa, session_id):
    """
    This function is invoked when the user clicks the Cancel button in the app. See
    app.cancel_scripts.

    Updated to only kill processes associated with this unique session id
    """
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
        process_session_id = process['session_id']
        if process_session_id == session_id:
            name = process['cmdline'][1].rsplit('/')[-1].rsplit('.')[0]
            if process['cmdline'][1] == '-m':
                name = process['cmdline'][2].rsplit('/')[-1].rsplit('.')[-1]
            if process['name'] == 'wgrib2': name = 'wgrib2'

            if name in config.scripts_list:
                sa.log.info(f"Killing process: {name} with pid: {process['pid']}") 
                os.kill(process['pid'], signal.SIGTERM)
            
            if len(process['cmdline']) >= 3 and 'multiprocessing' in process['cmdline'][2]:
                sa.log.info(f"Killing spawned multi-process with pid: {process['pid']}") 
                os.kill(process['pid'], signal.SIGTERM)


def calc_completion_percentage(expected_files, files_on_system):
    percent_complete = 0
    if len(expected_files) > 0:
        percent_complete = 100 * (len(files_on_system) / len(expected_files))

    return percent_complete

def radar_monitor(sa):
    """
    Reads in dictionary of radar files passed from Nexrad.py. Looks for associated 
    radar files on the system and compares to the total expected number and broadcasts a 
    percentage to the radar_status progress bar.
    """
    expected_files = list(sa.radar_files_dict.values())
    files_on_system = [x for x in expected_files if os.path.exists(x)]
          
    percent_complete = calc_completion_percentage(expected_files, files_on_system)
    return percent_complete, files_on_system

def munger_monitor(sa, cfg):
    expected_files = list(sa.radar_files_dict.values())

    # Are the mungered files always .gz?
    files_on_system = glob(f"{cfg['POLLING_DIR']}/**/*.gz", recursive=True)

    percent_complete = calc_completion_percentage(expected_files, files_on_system)
    return percent_complete

def surface_placefile_monitor(_sa, cfg):
    filenames = [
        'wind.txt', 'temp.txt', 'latest_surface_observations.txt',
        'latest_surface_observations_lg.txt', 'latest_surface_observations_xlg.txt'
    ]
    expected_files =  [f"{cfg['PLACEFILES_DIR']}/{i}" for i in filenames]
    files_on_system = [x for x in expected_files if os.path.exists(x)]

    #percent_complete = calc_completion_percentage(expected_files, files_on_system)
    return len(files_on_system), len(expected_files)

def nse_status_checker(_sa, cfg):
    """
    Read in model status text file and query associated file sizes. 
    """
    filename = f"{cfg['MODEL_DIR']}/model_list.txt"
    output = []
    warning_text = ""
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

        if len(output) == 0:
            warning_text = (
                "Warning: No RAP data was found for this request. NSE placefiles "
                "will be unavailable."
            )

    return output, warning_text


def file_stats(filename):
    """Return the size of a specific file.  If it doesn't exist, returns 0"""
    filesize = 0.
    if os.path.exists(filename):
        filesize = os.stat(filename).st_size / 1024000.
    return filesize
