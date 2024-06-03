import os, sys
import argparse
import numpy as np
from glob import glob
from datetime import datetime, timedelta
from time import time
import re

import calc.compute as compute
import calc.filtering as filtering
import sharptab.interp as interp
import sharptab.winds as winds
from utils.timing import timeit

from plot.plots import write_placefile
from plot.hodographs import parse_vector, compute_parameters, plot_hodograph
#from configs import MODEL_DIR

import IO.read as read
from utils.cmd import execute
from utils.logs import logfile

script_path = os.path.dirname(os.path.realpath(__file__))
log = logfile('process')

def import_for_testing(testfile):
    import pickle
    with open(testfile, 'rb') as datafile:
        return pickle.load(datafile)

def export_for_testing(testfile, data):
    import pickle
    with open(testfile, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

def create_hodograph(data, point, storm_motion='right-mover', sfc_wind=None,
                     storm_relative=False):
    for i in range(len(data)):
        arr = data[i]
        idx = interp.nearest_idx(point, arr['lons'], arr['lats'])
        u, v = winds.vec2comp(arr['wdir'][:,idx[0][0], idx[0][1]],
                              arr['wspd'][:,idx[0][0], idx[0][1]])
        hodo_data = {}
        heights = arr['hght'][:,idx[0][0], idx[0][1]] / 1000.
        heights = np.subtract(heights, heights[0])
        mask = np.where(heights < 12)
        hodo_data['hght'] = heights[mask]
        hodo_data['uwnd'] = u[mask]
        hodo_data['vwnd'] = v[mask]
        hodo_data['valid_time'] = arr['valid_time']
        hodo_data['cycle_time'] = arr['cycle_time']
        hodo_data['fhr'] = arr['fhr']
        hodo_data['lon'], hodo_data['lat'] = point[0][0], point[0][1]
        hodo_data['model_name'] = arr['model_name']

        if sfc_wind:
            surface_wind = parse_vector(sfc_wind)
            surface_wind = winds.vec2comp(surface_wind[0], surface_wind[1])
            hodo_data['uwnd'][0], hodo_data['vwnd'][0] = surface_wind[0], surface_wind[1]

            # Linearly interpolate the surface wind through the first 4 model levels
            hodo_data['uwnd'][1:4] = np.interp([1,2,3], [0, 4], [hodo_data['uwnd'][0],
                                                                 hodo_data['uwnd'][3]])
            hodo_data['vwnd'][1:4] = np.interp([1,2,3], [0, 4], [hodo_data['vwnd'][0],
                                                                 hodo_data['vwnd'][3]])

        params = compute_parameters(hodo_data, storm_motion)
        plot_hodograph(hodo_data, params, storm_relative=storm_relative)

@timeit
def create_placefiles(data, output_path, realtime=False):
    plot_arrays = []
    for i in range(len(data)):
        arr = data[i]
        prof_data = {'pres':arr['pres'], 'tmpc':arr['tmpc'],
                     'dwpc':arr['dwpc'], 'hght':arr['hght'],
                     'wdir':arr['wdir'], 'wspd':arr['wspd'],
                     'lons':arr['lons'], 'lats':arr['lats']}
        plot_arrays.append(compute.sharppy_calcs(**prof_data))

    # Add the model run metadata
    for i in range(len(data)):
        for item in ['valid_time', 'cycle_time', 'fhr', 'lons', 'lats']:
            plot_arrays[i][item] = data[i][item]

    #plot_arrays = import_for_testing('tests/sharppy.pickle')

    # Final filter (smoothing and masking logic) and plotting/placefiles.
    log.info("Entering filtering code")
    plot_arrays = filtering.filter(plot_arrays)

    #export_for_testing('tests/sharppy.pickle', plot_arrays)
    #export_for_testing('tests/standard.pickle', prof_data)

    # Writing to placefiles
    write_placefile(plot_arrays, output_path, realtime=realtime)

def query_files(filepath):
    """
    Return the model file(s) in a particular directory. Probably need to add a check
    based on the model type if user has downloaded multiple into this directory.

    4/15/24: Updated to allow cases with partial data availability to proceed. Fix is
    NOT appropriate for realtime cases where time interpolations occur between 2 files.
    For this use case, realtime runs will not be possible and the -rt flag will never
    be passed to process.py. 
     
    """
    files = glob(filepath + '/*.reduced')
    if len(files) >= 1:
        if len(files) > 1: log.warning("More than 1 model file in %s" % (filepath))
        return files[0]
    else:
        log.warning("No model data found in %s" % (filepath))
        #sys.exit(1)
        return None

def parse_logic(args):
    """
    QC user inputs and send arguments to download functions.

    """

    log.info("----> New processing run")

    timestr_fmt = '%Y-%m-%d/%H'
    dt_end = None
    if args.realtime:
        dt_start = datetime.utcnow() - timedelta(minutes=52)
    else:
        if args.time_str is not None:
            dt_start = datetime.strptime(args.time_str, timestr_fmt)
        elif args.start_time is not None and args.end_time is not None:
            dt_start = datetime.strptime(args.start_time, timestr_fmt)
            dt_start = dt_start - timedelta(hours=1)
            dt_end = datetime.strptime(args.end_time, timestr_fmt)
            dt_end = dt_end - timedelta(hours=1)
        else:
            log.error("Missing one of -rt, -t, or -start/-end flags")
            sys.exit(1)

    if args.hodo is None and args.meso is None:
        log.error("Missing one of -hodo, -meso")
        sys.exit(1)

    #if args.data_path is None:
    #    args.data_path = MODEL_DIR

    # Logic for reading data. Updated to allow for cases with partial data to proceed.
    # Notification of partial downloads or failed downloads likley handled in get_data
    # with download_status.txt file broadcasting to the frontend. 
    data = []
    if dt_end is None: dt_end = dt_start
    dt = dt_start
    while dt <= dt_end:
        filepath = "%s/%s" % (args.data_path, dt.strftime('%Y-%m-%d/%H'))
        if args.realtime:
            for grb in ['0_0', '0_50', '1_0']:
                data.append(read.read_data("%s/%s.grib2" % (filepath, grb)))
        else:
            filename = query_files(filepath)
            if filename is not None: data.append(read.read_data(filename))
        dt += timedelta(hours=1)

    # Direct us to the plotting/output functions.
    if args.hodo:
        point = args.hodo.split('/')
        point = [[float(point[1]), float(point[0])]]
        create_hodograph(data, point, storm_motion=args.storm_motion,
                         sfc_wind=args.sfc_wind, storm_relative=args.storm_relative)
    if args.meso: create_placefiles(data, args.output_path, realtime=args.realtime)
    log.info("===================================================================\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-rt', '--realtime', dest="realtime", action='store_true',
                    help='Realtime mode. Script will look for the most recent model run.')
    ap.add_argument('-s', dest='start_time', help='Initial valid time for analysis of    \
                    multiple hours. Form is YYYY-MM-DD/HH. MUST be accompanied by the    \
                    "-e" flag. No -t flag is taken.')
    ap.add_argument('-e', dest='end_time', help='Last valid time for analysis')
    ap.add_argument('-t', '--time-str', dest='time_str', help='Valid time for archived   \
                    model runs. Script will default to 1-hr forecasts. YYYY-MM-DD/HH')
    ap.add_argument('-p', '--data_path', dest='data_path', help='Directory to store data.\
                    Defaults to MODEL_DIR specified in the config file')
    ap.add_argument('-meso', dest='meso', action='store_true',
                    help='Flag to output mesoanalysis placefiles for GR2/Analyst.')
    ap.add_argument('-hodo', '--hodograph', dest='hodo',
                    help='Hodograph plot at a point ex: 35.03/-101.23')
    ap.add_argument('-sr', '--storm-relative', dest='storm_relative', action='store_true',
                    help='Flag to create a Storm Relative hodograph')
    ap.add_argument('-sw', '--sfc-wind', dest='sfc_wind', help='Surface wind. Form is    \
                    DDD/SS (e.g. 240/25)')
    ap.add_argument('-m', '--storm-motion', dest='storm_motion',
                    help='Storm motion vector. It takes one of two forms. The first is   \
                          either "BRM" for the Bunkers right mover vector, or "BLM" for  \
                          the Bunkers left mover vector. The second is the form DDD/SS,  \
                          where DDD is the direction the storm is coming from, and SS is \
                          the speed in knots (e.g. 240/25).', default='right-mover')
    ap.add_argument('-statuspath', dest='status_path', help='Where to output status      \
                    tracking files.')
    ap.add_argument('-outputpath', dest='output_path', help='Where to output placefiles.')
    args = ap.parse_args()
    parse_logic(args)   # Set and QC user inputs. Pass for downloading

if __name__ == '__main__':
    main()
