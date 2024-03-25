"""
run.py controls the realtime execution of the mesoanalysis scripts.

This replaces the need to specify file and system PATHS via crontab, and instead bundles
everything within this module's directory.
"""

import os
import schedule
import time
import logging
from glob import glob
from datetime import datetime, timedelta

from utils.cmd import execute
from utils.timing import timeit
from utils.logs import logfile
from configs import PYTHON, MAXSECONDS, MODEL_DIR

script_path = os.path.dirname(os.path.realpath(__file__))
log = logfile('main')
@timeit
def download_data():
    """Pass arguments to the get_data.py script to download data in realtime from either
    the NOMADS, FTPPRD, or GOOGLE servers
    """
    log.info("Starting download function")
    loop_is_done = False

    start = time.time()
    delta = time.time() - start

    target_dt = datetime.utcnow()-timedelta(minutes=51)
    time_str = target_dt.strftime('%Y-%m-%d/%H')

    # Use the RAP except at 00 and 12z cycles when the HRRR is available first.
    model_flag = '-m RAP'
    if target_dt.hour in [12, 0]:
        model_flag = '-m HRRR'

    while not loop_is_done and delta < MAXSECONDS:
        # If we're > 15 minutes delayed, switch to using the HRRR. If the NOMADS/FTPPRD
        # sites are down, it's possible (likely?) that the HRRR is still being pushed to
        # the Google Cloud and this will be caught in get_data.py.
        #if delta >= 900: model_flag = '-m HRRR'

        # Download data
        arg = f"{PYTHON} {script_path}/get_data.py -rt {model_flag} -n 2 -p {MODEL_DIR}"
        log.info(arg)
        execute(arg)

        # Determine download status. If we failed, wait and try again.
        with open("%s/download_status.txt" % (script_path)) as f: file_status = f.read()
        if file_status == 'True':
            loop_is_done = True
            log.info("File found and downloaded")
        else:
            log.info("File not found. Clearing directory and going to bed...")
            files = glob("%s/%s/*" % (MODEL_DIR, time_str))
            for f in files:
                arg = "rm %s" % (f)
                log.info(arg)
                execute(arg)
            time.sleep(60)
        delta = time.time() - start
    return loop_is_done

@timeit
def make_placefiles():
    """Pass arguments to the process.py script to create GR-readable placefiles"""
    arg = f"{PYTHON} {script_path}/process.py -rt -meso -p {MODEL_DIR}"
    execute(arg)

# We can schedule each of the tasks at the same time since the execution of task1
# (download_data) will block the execution of task2 (make_placefiles) until the first task
# has been completed.
task1 = schedule.Scheduler()
task2 = schedule.Scheduler()
task1.every().hour.at(":54").do(download_data)
task2.every().hour.at(":54").do(make_placefiles)
while True:
    task1.run_pending()
    task2.run_pending()
    time.sleep(1)
