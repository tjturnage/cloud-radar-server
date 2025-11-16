import utils 
from pathlib import Path 
import signal 
import shutil
import os 
import re 
import zipfile
import json

from scripts.update_dir_list import UpdateDirList
from scripts.update_hodo_page import UpdateHodoHTML
from utils import call_function, write_status_file
from log_registry import SESSION_LOGGERS

def remove_files_and_dirs(cfg) -> None:
    """
    Cleans up files and directories from the previous simulation so these datasets
    are not included in the current simulation.
    """
    dirs = [cfg['RADAR_DIR'], cfg['POLLING_DIR'], cfg['HODOGRAPHS_DIR'], cfg['MODEL_DIR'],
            cfg['PLACEFILES_DIR'], cfg['USER_DOWNLOADS_DIR'], cfg['PROBSEVERE_DIR']]
    for directory in dirs:
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                if name not in ['grlevel2.cfg', 'events.txt']:
                    os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    # Remove the original file_times.txt file. This will get re-created by munger.py
    try:
        os.remove(f"{cfg['ASSETS_DIR']}/file_times.txt")
    except FileNotFoundError:
        pass


def remove_munged_radar_files(cfg) -> None:
    """
    Removes uncompressed and 'munged' radar files within the /data/xx/radar directory 
    after the pre-processing scripts have completed. These files are no longer needed 
    as the appropriate files have been exported to the /assets/xx/polling directory. 
    
    #copies the original files to the user downloads directory so they can be
    #downloaded by the user if desired.
    """
    regex_pattern = r'^(.{4})(\d{8})_(\d{6})$'
    #raw_pattern = r'^(.{4})(\d{8})_(\d{6})_(V\d{2})$'
    # Searches for filenames with either Vxx or .gz. Older radar files are gzipped.
    #raw_pattern = r'^.{4}\d{8}_\d{6}(_V\d{2}|\.gz)$'
    for root, _, files in os.walk(cfg['RADAR_DIR']):
        if Path(root).name == 'downloads':
            for name in files:
                thisfile = os.path.join(root, name)
                matched = re.match(regex_pattern, name)
                #raw_matched = re.match(raw_pattern, name)
                if matched or '.uncompressed' in name:
                    os.remove(thisfile)
                #if raw_matched:
                #    shutil.copy2(thisfile, cfg['USER_DOWNLOADS_DIR'])


def zip_downloadable_radar_files(cfg) -> None:
    """
    After all radar files have been processed and are ready for download, this function
    zips up the radar files into the user downloads directory.
    """
    raw_pattern = r'^.{4}\d{8}_\d{6}(_V\d{2}|\.gz)$'
    zip_filename = f"{cfg['USER_DOWNLOADS_DIR']}/original_radar_files.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(cfg['RADAR_DIR']):
            for f in files: 
                raw_matched = re.match(raw_pattern, f)
                if raw_matched:
                    file_path = os.path.join(root, f)
                    zipf.write(file_path, f)


def copy_grlevel2_cfg_file(cfg) -> None:
    """
    Ensures a grlevel2.cfg file is copied into the polling directory.
    This file is required for GR2Analyst to poll for radar data.
    """
    source = f"{cfg['BASE_DIR']}/grlevel2.cfg"
    destination = f"{cfg['POLLING_DIR']}/grlevel2.cfg"
    try:
        shutil.copyfile(source, destination)
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error copying {source} to {destination}: {e}")


################################################################################################
# ----------------------------- Processing Scripts  --------------------------------------------
################################################################################################
def query_radar_files(cfg, radar_info, sim_times):
    """
    Helper function utilized by query_and_download_radars to make an initial query of 
    available radar files. Writes out a json file which is then used by the app to 
    monitor radar download status. 
    """
    # Need to reset the expected files dictionary with each call. Otherwise, if a user
    # cancels a request, the previously-requested files will still be in the dictionary.
    # radar_files_dict = {}
    logger = SESSION_LOGGERS[cfg['SESSION_ID']]
    radar_info['radar_files_dict'] = {}
    for _r, radar in enumerate(radar_info['radar_list']):
        radar = radar.upper()
        args = [radar, str(sim_times['event_start_str']), str(sim_times['event_duration']),
                str(False), cfg['RADAR_DIR']]
        results = utils.exec_script(
            Path(cfg['NEXRAD_SCRIPT_PATH']), args, cfg['SESSION_ID'])
        if results['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            logger.warning(
                f"{cfg['SESSION_ID']} :: User cancelled query_radar_files()")
            break

        json_data = results['stdout'].decode('utf-8')
        logger.info(
            f"{cfg['SESSION_ID']} :: Nexrad.py returned with {json_data}")
        radar_info['radar_files_dict'].update(json.loads(json_data))

    # Write radar metadata for this simulation to a text file. More complicated updating 
    # dcc.Store object with this information since this function isn't a callback.
    with open(f'{cfg['RADAR_DIR']}/radarinfo.json', 'w', encoding='utf-8') as json_file:
        json.dump(radar_info['radar_files_dict'], json_file)

    return results


def query_and_download_radars(radar_info, configs, sim_times):
    """
    Queries data from AWS and downloads radar files. Additionally copies grlevel2.cfg 
    file for this sim, initializes links.html page, and zips original radar data for 
    user download.
    """
    logger = SESSION_LOGGERS[configs['SESSION_ID']]
    try:
        copy_grlevel2_cfg_file(configs)
    except (IOError, ValueError, KeyError) as e:
        logger.exception("Error creating radar dict or cfg file: %s",e,exc_info=True)

    radar_list = radar_info.get('radar_list', [])
    session_id = configs['SESSION_ID']
    status = 'cancelled'

    # Write the links html page. 
    try:
        args = [configs['LINK_BASE'], configs['LINKS_HTML_PAGE']]
        res = call_function(utils.exec_script, session_id, 
                            Path(configs['LINKS_PAGE_SCRIPT_PATH']),
                            args, session_id)
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
            return status
    except Exception as e:
        logger.exception("Error creating links.html page")
        write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
        return status

    # Query all radar files
    try:
        res = call_function(query_radar_files, session_id, configs, radar_info, sim_times)
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            logger.warning("Query radar files was cancelled.")
            write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
            return status
    except Exception as e:
        logger.exception("Radar file query failed.")

    # Download all radar files
    for radar in radar_list:
        radar = radar.upper()
        logger.info(f"Downloading radar: {radar}")
        args = [radar, str(sim_times['event_start_str']),
                str(sim_times['event_duration']), str(True), configs['RADAR_DIR']]
        try:
            res = call_function(utils.exec_script, session_id, 
                                Path(configs['NEXRAD_SCRIPT_PATH']), 
                                args, session_id)
            if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
                logger.warning(f"Radar download for {radar} was cancelled.")
                write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
                return status
        except Exception as e:
            logger.exception(f"Radar download failed for {radar}")

    # Now that all radar files are in assets/{}/downloads dir, zip them up
    try:
        zip_downloadable_radar_files(configs)
    except KeyError as e:
        logger.exception("Error zipping radar files ", exc_info=True)

    logger.info(f"Downloads completed for radars: {radar_list}")
    status = 'running'
    write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
    return status


def munger_radar(radar_info, configs, sim_times):
    """
    Transposes radar in time and/or space. Creates initial dir.list file(s). 
    """
    logger = SESSION_LOGGERS[configs['SESSION_ID']]
    status = 'cancelled'
    radar_list = radar_info.get('radar_list', [])
    for radar in radar_list:
        radar = radar.upper()  
        try:
            if radar_info['new_radar'] == 'None':
                new_radar = radar
            else:
                new_radar = radar_info['new_radar'].upper()
        except (IOError, ValueError, KeyError) as e:
            logger.exception("Error defining new radar: %s",e,exc_info=True)

        args = [radar, str(sim_times['playback_start_str']), 
                str(sim_times['event_duration']),
                str(sim_times['simulation_seconds_shift']), configs['RADAR_DIR'],
                configs['POLLING_DIR'], configs['USER_DOWNLOADS_DIR'], 
                configs['L2MUNGER_FILEPATH'], configs['DEBZ_FILEPATH'],
                new_radar]
        res = call_function(utils.exec_script, configs['SESSION_ID'], 
                            Path(configs['MUNGER_SCRIPT_FILEPATH']),
                            args, configs['SESSION_ID'])
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            logger.warning(f"Munging for {radar} was cancelled.")
            write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
            return status
        
        # this gives the user some radar data to poll while other scripts are running
        try:
            UpdateDirList(new_radar, 'None', configs['POLLING_DIR'], initialize=True)
        except (IOError, ValueError, KeyError) as e:
            print(f"Error with UpdateDirList: {e}")
            logger.exception("Error with UpdateDirList: %s",e, exc_info=True)
        
    # Delete the uncompressed/munged radar files from the data directory
    try:
        remove_munged_radar_files(configs)
    except KeyError as e:
        logger.exception("Error removing munged radar files ", exc_info=True)

    status = 'running'
    write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
    return status


def generate_fast_placefiles(radar_info, configs, sim_times, lsr_delay):
    """
    Handles processing of the fast placefiles
    """
    logger = SESSION_LOGGERS[configs['SESSION_ID']]
    status = 'cancelled'
    # --------- LSRs ----------------------------------------------------------------
    args = [str(radar_info['lat']), str(radar_info['lon']),
            str(sim_times['event_start_str']), str(sim_times['event_duration']),
            configs['DATA_DIR'], configs['PLACEFILES_DIR'], str(lsr_delay)]
    res = call_function(utils.exec_script, configs['SESSION_ID'], 
                        Path(configs['LSR_SCRIPT_PATH']), args, configs['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        logger.warning("LSR placefile generation was cancelled.")
        write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
        return status

    # --------- Surface observations placefiles -------------------------------------
    args = [str(radar_info['lat']), str(radar_info['lon']),
            sim_times['event_start_str'], str(sim_times['event_duration']),
            configs['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, configs['SESSION_ID'], 
                        Path(configs['OBS_SCRIPT_PATH']), args, configs['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        logger.warning("Surface observations placefile generation was cancelled.")
        write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
        return status
    
    # --------- ProbSevere download -------------------------------------------------
    args = [str(sim_times['event_start_str']), str(sim_times['event_duration']),
            configs['PROBSEVERE_DIR']]
    res = call_function(utils.exec_script, configs['SESSION_ID'],
                        Path(configs['PROBSEVERE_DOWNLOAD_SCRIPT_PATH']),
                        args, configs['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        logger.warning("ProbSevere download was cancelled.")
        write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
        return status
    
    # --------- ProbSevere placefiles -----------------------------------------------
    args = [str(radar_info['lat']), str(radar_info['lon']), configs['PROBSEVERE_DIR'],
            configs['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, configs['SESSION_ID'],
                        Path(configs['PROBSEVERE_PLACEFILE_SCRIPT_PATH']),
                        args, configs['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        logger.warning("ProbSevere placefile generation was cancelled.")
        write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
        return status
    
    status = 'running'
    write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
    return status


def generate_events_files(configs, sim_times):
    """
    Creates the events.html and events.txt reference files. 
    """
    logger = SESSION_LOGGERS[configs['SESSION_ID']]
    # Always write an event times placefile, and events.txt and events.html output.
    args = [str(sim_times['simulation_seconds_shift']), configs['DATA_DIR'], 
            configs['RADAR_DIR'], configs['EVENTS_HTML_PAGE'], 
            configs['EVENTS_TEXT_FILE']]
    res = call_function(utils.exec_script, configs['SESSION_ID'], 
                        Path(configs['EVENT_TIMES_SCRIPT_PATH']), 
                        args, configs['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        logger.warning("Events placefile generation was cancelled.")
        write_status_file('cancelled', f"{configs['DATA_DIR']}/script_status.txt")
        return 'cancelled'
    
    status = 'running'
    write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
    return status


def generate_nse_placefiles(configs, sim_times):
    """
    Handles nse placefile generation
    """
    status = 'cancelled'
    args = [str(sim_times['event_start_str']), str(sim_times['event_duration']),
            configs['SCRIPTS_DIR'], configs['DATA_DIR'], configs['PLACEFILES_DIR']]
    res = call_function(utils.exec_script, configs['SESSION_ID'], 
                        Path(configs['NSE_SCRIPT_PATH']), args,
                        configs['SESSION_ID'])
    if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
        write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
        return status
        
    status = 'running'
    write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
    return status


def generate_hodographs(radar_info, configs, sim_times):
    """
    Handles hodograph plot generation
    """
    logger = SESSION_LOGGERS[configs['SESSION_ID']]
    status = 'cancelled'
    for radar, data in radar_info['radar_dict'].items():
        try:
            asos_one = data['asos_one']
            asos_two = data['asos_two']
        except KeyError as e:
            logger.exception("Error getting radar metadata: ", exc_info=True)

        # Execute hodograph script
        args = [radar, radar_info['new_radar'], asos_one, asos_two,
                str(sim_times['simulation_seconds_shift']), configs['RADAR_DIR'],
                configs['HODOGRAPHS_DIR']]
        res = call_function(utils.exec_script, configs['SESSION_ID'], 
                            Path(configs['HODO_SCRIPT_PATH']), 
                            args, configs['SESSION_ID'])
        if res['returncode'] in [signal.SIGTERM, -1*signal.SIGTERM]:
            write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
            return status

        try:
            UpdateHodoHTML('None', configs['HODOGRAPHS_DIR'], configs['HODOGRAPHS_PAGE'])
        except (IOError, ValueError, KeyError) as e:
            print("Error updating hodo html: ", e)
            logger.exception("Error updating hodo html: %s",e, exc_info=True)

    status = 'running'
    write_status_file(status, f"{configs['DATA_DIR']}/script_status.txt")
    return status