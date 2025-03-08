from datetime import datetime, timedelta, timezone 
import pytz 
import requests
import os, sys, shutil
from pathlib import Path
from glob import glob
import argparse
from multiprocessing import Pool, freeze_support
import numpy as np
import timeout_decorator

from configs import (TIMEOUT, MINSIZE, DATA_SOURCES,
                     GOOGLE_CONFIGS, THREDDS_CONFIGS, vars, grid_info)
from utils.cmd import execute
from utils.logs import logfile
from pathlib import Path

script_path = os.path.dirname(os.path.realpath(__file__))
log = logfile("nse", f"{Path(__file__).parents[2]}/data/logs")

# Find the wgrib2 and wget executables. If None, kill the NSE script. 
WGRIB2 = shutil.which('wgrib2')
WGET = shutil.which('wget')
if WGRIB2 is None or WGET is None: 
    log.error('Either or both WGRIB2 or WGET executables are missing. Exiting.')
    sys.exit(1)

def interpolate_in_time(download_dir):
    """Interpolate 1 and 2 hour forecasts in time every 15 minutes using WGRIB2. Used for
    realtime runs.

    Parameters:
    -----------
    download_dir : string
        Directory containing downloaded grib2 files

    """

    files = sorted(glob(download_dir + '/*.reduced'))
    arg = "%s %s %s %s %s %s %s %s/%s" % (
         WGRIB2, files[0], '-rpn sto_1 -import_grib', files[1],
         '-rpn sto_2 -set_grib_type same -if',
         '":1 hour fcst:" -rpn "rcl_1:0.5:*:rcl_2:0.5:*:+"',
         '-set_ftime "90 min fcst" -set_scaling same same -grib_out',
         download_dir, '0_50.grib2'
         )
    execute(arg)

    # Copy start and end files. Remove the original datafiles.
    for i in range(len(files)):
        arg = "cp %s %s/%s_0.grib2" % (files[i], download_dir, i)
        p = execute(arg)
        if p.returncode == 0: log.info(arg)

        arg = "rm %s" % (files[i])
        p = execute(arg)
        if p.returncode == 0: log.info(arg)

def test_url(url):
    """Test for online file existence.

    Parameters
    ----------
    url : string
        URL we're testing for

    """
    try:
        ru = requests.head(url, timeout=1)
        status = ru.ok
    except:
        status = False
    return status

def execute_regrid(full_name):
    """
    Performs subsetting of the original data files to help speed up plotting routines.
    The `grid_info` variable is specified in the configuration file and controls the final
    model domain.

    Parameters:
    -----------
    full_name : string
        Filepath and filename

    """

    save_name = "%s.reduced" % (full_name)
    if not os.path.exists(save_name):
        if 'ncei' in full_name:
            # Need to re-order the ugrd and vgrd entries
            arg = "%s %s -new_grid_order - junk | %s - -new_grid %s %s" % (WGRIB2,
                                                                           full_name,
                                                                           WGRIB2,
                                                                           grid_info,
                                                                           save_name)
        else:
            arg = "%s %s -new_grid %s %s" % (WGRIB2, full_name, grid_info, save_name)

        log.info("CMD %s" % (arg))
        p = execute(arg)

        if p.returncode != 0:
            log.error("Failure in execute_regrid. Check that WGRIB2 path is specified in "
                      "configs.py")

    # Remove the original file
    p = execute("rm %s" % (full_name))
    if p.returncode == 0: log.info("Removed %s" % (full_name))

# Catch hung download processes with this decorator function. TIMEOUT specified in config
@timeout_decorator.timeout(TIMEOUT, timeout_exception=StopIteration)
def execute_download(full_name, url):
    """Download the requested files

    Parameters:
    -----------
    full_name : string
        Filepath and filename
    url : string
        URL to requested file

    """
    arg2 = None
    if 'storage.googleapis.com' in url:
        arg1 = '%s -O %s %s' % (WGET, full_name, url)
        arg2 = "%s %s -s | egrep '%s' | %s -i %s -grib %s.tmp" % (WGRIB2, full_name, vars,
                                                                  WGRIB2, full_name,
                                                                  full_name)
    elif 'ncei' in url:
        arg1 = '%s -O %s %s' % (WGET, full_name, url)
    else:
        arg1 = "%s/IO/get_inv.pl %s.idx | egrep '%s' | %s/IO/get_grib.pl %s %s" % (
                script_path, url, vars, script_path, url, full_name
                )

    # Download data if not on the current filesystem
    if not os.path.exists(full_name + '.reduced'):
        p = execute(arg1)
        if p.returncode != 0:
            log.error("Failed to download from source. Check WGET variable in configs.py")
    else:
        log.info("Data already exists locally at %s.reduced" % (full_name))
        pass

    # For GOOGLE-based downloads
    if arg2 is not None:
        execute(arg2)
        #execute("rm %s" % (full_name))
        execute("mv %s.tmp %s" % (full_name, full_name))

def make_dir(run_time, data_path):
    download_dir = "%s/%s" % (data_path, run_time)
    if not os.path.exists(download_dir): os.makedirs(download_dir)
    return download_dir

# Catch hung download processes with this decorator function. TIMEOUT specified in config
#@timeout_decorator.timeout(TIMEOUT, timeout_exception=StopIteration)
def download_data(dts, data_path, model='RAP', num_hours=1, 
                  status_path=None):
    """Function called by main() to control download of model data.

    Parameters
    ----------
    dts : list
        List of datetime objects, each corresponding to a desired model cycle
    data_path: string
        Path to download data to. Defaults to IO/data
    model : string
        Desired model. Options are HRRR and RAP. Default: RAP
    num_hours : int
        Last forecast hour. Default: 1

    Returns
    -------
    status : boolean
        Availability of the dataset. False if unavailable.
    download_dir: string
        Path to downloaded model file(s)

    """

    sources = list(DATA_SOURCES.keys())
    fhrs = np.arange(1, int(num_hours)+1, 1)
    downloads = {}
    urls = {}
    expected_files = 0
    for dt in dts:
        for fhr in fhrs:
            download_dir = make_dir(dt.strftime('%Y-%m-%d/%H'), data_path)
            if model == 'HRRR':
                CONUS = 'conus'
                filename = "hrrr.t%sz.wrfnatf%s.grib2" % (str(dt.hour).zfill(2),
                                                          str(fhr).zfill(2))
            elif model == 'RAP':
                CONUS = ''
                filename = "rap.t%sz.awp130bgrbf%s.grib2" % (str(dt.hour).zfill(2),
                                                             str(fhr).zfill(2))
            else:
                log.error("Bad model type `%s` passed" % (model))
                sys.exit(1)

            ##############################################################################
            # Online source checks
            ##############################################################################
            # If it's too early, don't try to use the FTPPRD backup site (slower download)
            delta = abs((datetime.now(timezone.utc) - dt).total_seconds())
            if delta < 3900:
                if 'FTPPRD' in sources: sources.remove('FTPPRD')
            full_name = "%s/%s" % (download_dir, filename)

            for source in sources:
                base_url = DATA_SOURCES[source]

                # NOMADS or backup FTPPRD site. Priority 1 and 3
                if source in ['NOMADS', 'FTPPRD']:
                    url = "%s/%s/prod/%s.%s/%s/%s" % (base_url,model.lower(),
                                                      model.lower(),dt.strftime('%Y%m%d'),
                                                      CONUS, filename)
                # GOOGLE. Priority 2
                elif source == 'GOOGLE':
                    # As of 9/15/2021, RAP data is now near-realtime! HRRR is realtime.
                    # RAP data goes back to the 2021-02-22/00z run.
                    model_name = GOOGLE_CONFIGS[model]
                    url = "%s/%s/%s.%s/%s/%s" % (base_url, model_name, model.lower(),
                                                 dt.strftime('%Y%m%d'), CONUS, filename)
                    full_name = "%s/%s" % (download_dir, filename)

                # THREDDS. Priority 4. Only for reanalysis runs. Only RAP available.
                elif source == 'THREDDS':
                    # Two cases: the RAP and the old RUC. The RAP took over on the
                    # 2020-05-01/12z cycle.
                    for case in THREDDS_CONFIGS.keys():
                        name = 'rap'
                        if case == 'RUC': name = 'ruc2anl'
                        base_name = THREDDS_CONFIGS[case]
                        filename = "%s-ncei.t%sz.%sf%s.%s" % (case.lower(),
                                                              str(dt.hour).zfill(2),
                                                              'awp130pgrb',
                                                              str(fhr).zfill(2),
                                                              'grib2')

                        url = "%s/%s/%s/%s/%s_%s_%s_%s00_%s.%s" % (base_url,
                                                                   THREDDS_CONFIGS[case],
                                                                   dt.strftime('%Y%m'),
                                                                   dt.strftime('%Y%m%d'),
                                                                   name, '130',
                                                                   dt.strftime('%Y%m%d'),
                                                                   str(dt.hour).zfill(2),
                                                                   str(fhr).zfill(3),
                                                                   'grb2')

                        if test_url(url):
                            full_name = "%s/%s" % (download_dir, filename)
                            break

                idx = url.index('//') + 2
                url = url[0:idx] + url[idx:].replace('//', '/')
                status = test_url(url)
                log.info(f"{url} returned {status}")
                if status:
                    log.info("  [GOOD STATUS]: Download source: %s" % (source))
                    log.info("  [GOOD STATUS]: URL: %s" % (url))
                    downloads[full_name] = url
                    break

            log.info("Target file: %s" % (full_name))
            expected_files += 1

    # Write expected datafiles to output text file for tracking by app.py
    with open(f"{status_path}/model_list.txt", 'w') as f:
        for filename in downloads.keys():
            f.write(f"{filename}.reduced\n")

    # Download requested files via separate processes
    if len(downloads.keys()) >= 1:
        my_pool = Pool(np.clip(1, len(downloads), 4))
        my_pool.starmap(execute_download, zip(downloads.keys(), downloads.values()))
        my_pool.map(execute_regrid, downloads.keys())
        my_pool.close()
        my_pool.terminate()
    else:
        log.error("Some or all requested data was not found.")

def check_configs():
    """
    Test to make sure the user-specified WGET and WGRIB2 files exist on the system. Exits
    if either file can't be found.

    """
    for item in [WGET, WGRIB2]:
        if not Path(item).is_file():
            error_message = "%s not found on filesystem. Check configs.py file." % (item)
            print(error_message)
            log.error(error_message)
            sys.exit(1)

def parse_logic(args):
    """
    QC user inputs and send arguments to download functions.

    """
    #if args.data_path is None:
    #    args.data_path = MODEL_DIR

    timestr_fmt = '%Y-%m-%d/%H'
    #log.info("----> New download processing")

    # USER has specified the -rt flag or a specific cycle time
    curr_time = datetime.now(timezone.utc)
    if args.realtime or args.time_str:
        args.start_time, args.end_time = None, None
        if args.realtime:
            args.num_hours = 2
            target = curr_time - timedelta(minutes=51)

            # If 0 or 12z, RAP is delayed until ~01:28z or ~13:28z
            if target.hour in [0, 12] and curr_time.minute < 29 and args.model == 'RAP':
                log.info("Realtime RAP not available for 0 or 12z cycle. Setting to HRRR")
                args.model = 'HRRR'

            cycle_dt = [datetime(target.year, target.month, target.day, target.hour)]

        else:
            cycle_dt = [datetime.strptime(args.time_str, timestr_fmt)]

    # USER has specified starting and ending cycle times
    elif args.start_time and args.end_time:
        start_dt = datetime.strptime(args.start_time, timestr_fmt)
        end_dt = datetime.strptime(args.end_time, timestr_fmt)
        if start_dt > end_dt:
            log.error("Requested start time is after the end time")
            sys.exit(1)

        cycle_dt = []
        while start_dt <= end_dt:
            cycle_dt.append(start_dt-timedelta(hours=1))
            #cycle_dt.append(start_dt)
            start_dt += timedelta(hours=1)

    else:
        log.error("Missing time flags. Need one of -rt, -t, or -s and -e")
        sys.exit(1)

    cycle_dt = [dt.replace(tzinfo=pytz.UTC) for dt in cycle_dt]

    # RAP/RUC data via NCEI. Analyses and 1-hour forecasts only.
    if args.model in ['RAP', None] and cycle_dt[-1] < datetime(2021,2,21,23,tzinfo=pytz.UTC):
        log.warning("Only 1 hour of forecast data available. Setting -n to 1")
        args.num_hours=1

    #log.info(f"Saving model data to: {args.data_path}")
    download_data(list(cycle_dt), data_path=args.data_path, model=args.model, 
                  num_hours=args.num_hours, status_path=args.status_path)

    # If this is realtime, interpolate the 1 and 2-hour forecasts in time
    #if not args.num_hours: args.num_hours = 0
    #if status and args.realtime: interpolate_in_time(download_dir)
    #log.info("===================================================================\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-rt', '--realtime', dest="realtime", action='store_true',
                    help='Realtime mode')
    ap.add_argument('-m', '--model', dest='model', default='RAP', help='RAP or HRRR.     \
                    Default is RAP')
    ap.add_argument('-n', '--num-hours', dest='num_hours', default=1, help='Number of    \
                    forecast hours to download. Default is 1 hour')
    ap.add_argument('-t', '--time-str', dest='time_str', help='For an individual cycle.  \
                    Form is YYYY-MM-DD/HH. No -s or -e flags taken.')
    ap.add_argument('-s', dest='start_time', help='Initial valid time for analysis of    \
                    multiple hours. Form is YYYY-MM-DD/HH. MUST be accompanied by the    \
                    "-e" flag. No -t flag is taken.')
    ap.add_argument('-e', dest='end_time', help='Last valid time for analysis')
    ap.add_argument('-p', '--data_path', dest='data_path', help='Directory to store data.\
                    Defaults to MODEL_DIR specified in the config file')
    ap.add_argument('-statuspath', dest='status_path', help='Where to output status      \
                    tracking files.')
    args = ap.parse_args()
    log.info("============================== get_data.py ==============================\n")
    log.info(args)
    parse_logic(args)   # Set and QC user inputs. Pass for downloading

if __name__ == '__main__':
    freeze_support()    # Needed for multiprocessing.Pool
    check_configs()     # Test USER paths from config file
    main()              # Parse inputs
