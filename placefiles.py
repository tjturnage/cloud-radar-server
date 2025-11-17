"""
Creates and shifts events placefiles for radar simulation.
This is dictated by a csv upload from the user.
"""
from glob import glob
import re
import os
import zipfile
import math
from datetime import datetime, timedelta

import io
import base64
import pandas as pd

# Earth radius (km)
R = 6_378_137

# Regular expressions. First one finds lat/lon pairs, second finds the timestamps.
LAT_LON_REGEX = "[0-9]{1,2}.[0-9]{1,100},[ ]{0,1}[|\\s-][0-9]{1,3}.[0-9]{1,100}"
TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

def zip_original_placefiles(cfg) -> None:
    """
    After the placefiles have been shifted and are ready for download, this function
    zips up the original placefiles.
    """
    zip_filepath = f"{cfg['USER_DOWNLOADS_DIR']}/original_placefiles.zip"
    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        for root, _, files in os.walk(cfg['PLACEFILES_DIR']):
            for file in files:
                if 'txt' in file and 'updated' not in file and 'shifted' not in file:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, file)


def shift_placefiles(PLACEFILES_DIR, sim_times, radar_info) -> None:
    """
    # While the _shifted placefiles should be purged for each run, just ensure we're
    # only querying the "original" placefiles to shift (exclude any with _shifted.txt)        
    """
    filenames = glob(f"{PLACEFILES_DIR}/*.txt")
    filenames = [x for x in filenames if "shifted" not in x]
    filenames = [x for x in filenames if "updated" not in x]
    for file_ in filenames:
        outfilename = f"{file_[0:file_.index('.txt')]}_shifted.txt"
        outfile = open(outfilename, 'w', encoding='utf-8')
        with open(file_, 'r', encoding='utf-8') as f:
            data = f.readlines()

        try:
            for line in data:
                new_line = line

                if sim_times['simulation_seconds_shift'] is not None and \
                        any(x in line for x in ['Valid', 'TimeRange', 'Time']):
                    new_line = shift_time(
                        line, sim_times['simulation_seconds_shift'])

                # Shift this line in space. Only perform if both an original and
                # transpose radar have been specified.
                if radar_info['new_radar'] != 'None' and radar_info['radar'] is not None:
                    regex = re.findall(LAT_LON_REGEX, line)
                    if len(regex) > 0:
                        idx = regex[0].index(',')
                        plat, plon = float(regex[0][0:idx]), float(regex[0][idx+1:])
                        lat_out, lon_out = move_point(plat, plon, radar_info['lat'],
                                                      radar_info['lon'],
                                                      radar_info['new_lat'],
                                                      radar_info['new_lon'])
                        new_line = line.replace(regex[0], f"{lat_out}, {lon_out}")
                outfile.write(new_line)
        except (IOError, ValueError, KeyError) as e:
            outfile.truncate(0)
            outfile.write(f"Errors shifting this placefile: {e}")
        outfile.close()


def shift_time(line: str, simulation_seconds_shift: int) -> str:
    """
    Shifts the time-associated lines in a placefile.
    These look for 'Valid' and 'TimeRange'.
    """
    simulation_time_shift = timedelta(seconds=simulation_seconds_shift)
    new_line = line
    if 'Valid:' in line:
        idx = line.find('Valid:')
        # Leave off \n character
        valid_timestring = line[idx+len('Valid:')+1:-1]
        dt = datetime.strptime(valid_timestring, '%H:%MZ %a %b %d %Y')
        new_validstring = datetime.strftime(dt + simulation_time_shift,
                                            '%H:%MZ %a %b %d %Y')
        new_line = line.replace(valid_timestring, new_validstring)

    if 'TimeRange' in line:
        regex = re.findall(TIME_REGEX, line)
        dt = datetime.strptime(regex[0], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring_1 = datetime.strftime(dt + simulation_time_shift,
                                             '%Y-%m-%dT%H:%M:%SZ')
        dt = datetime.strptime(regex[1], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring_2 = datetime.strftime(dt + simulation_time_shift,
                                             '%Y-%m-%dT%H:%M:%SZ')
        new_line = line.replace(f"{regex[0]} {regex[1]}",
                                f"{new_datestring_1} {new_datestring_2}")

    # For LSR placefiles
    if 'LSR Time' in line:
        regex = re.findall(TIME_REGEX, line)
        dt = datetime.strptime(regex[0], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring = datetime.strftime(dt + simulation_time_shift,
                                           '%Y-%m-%dT%H:%M:%SZ')
        new_line = line.replace(regex[0], new_datestring)

    return new_line


def move_point(plat, plon, lat, lon, new_radar_lat, new_radar_lon):
    """
    Shift placefiles to a different radar site. Maintains the original azimuth and range
    from a specified RDA and applies it to a new radar location. 

    Parameters:
    -----------
    plat: float 
        Original placefile latitude
    plon: float 
        Original palcefile longitude

    lat and lon is the lat/lon pair for the original radar 
    new_lat and new_lon is for the transposed radar. These values are set in 
    the transpose_radar function after a user makes a selection in the 
    new_radar_selection dropdown. 

    """
    def _clamp(n, minimum, maximum):
        """
        Helper function to make sure we're not taking the square root of a negative 
        number during the calculation of `c` below. 
        """
        return max(min(maximum, n), minimum)

    # Compute the initial distance from the original radar location
    phi1, phi2 = math.radians(lat), math.radians(plat)
    d_phi = math.radians(plat - lat)
    d_lambda = math.radians(plon - lon)

    a = math.sin(d_phi/2)**2 + (math.cos(phi1) *
                                math.cos(phi2) * math.sin(d_lambda/2)**2)
    a = _clamp(a, 0, a)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c

    # Compute the bearing
    y = math.sin(d_lambda) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2)) - (math.sin(phi1) * math.cos(phi2) *
                                             math.cos(d_lambda))
    theta = math.atan2(y, x)
    bearing = (math.degrees(theta) + 360) % 360

    # Apply this distance and bearing to the new radar location
    phi_new, lambda_new = math.radians(
        new_radar_lat), math.radians(new_radar_lon)
    phi_out = math.asin((math.sin(phi_new) * math.cos(d/R)) + (math.cos(phi_new) *
                        math.sin(d/R) * math.cos(math.radians(bearing))))
    lambda_out = lambda_new + math.atan2(math.sin(math.radians(bearing)) *
                                         math.sin(d/R) * math.cos(phi_new),
                                         math.cos(d/R) - math.sin(phi_new) * math.sin(phi_out))
    return math.degrees(phi_out), math.degrees(lambda_out)

########################################################################################
# The following functions are associated with the .csv upload callback
########################################################################################
def make_timerange_line(row) -> str:
    """
    This function creates the datetime string for the placefiles
    """
    date_str = row.get('utc_date',"")
    hour = row.get('utc_hour',"")
    minute = row.get('utc_minute',"")
    delay =  row.get('delay_min',"")
    # Handle missing hour or minute values
    if pd.isna(hour):
        hour = 0
    if pd.isna(minute):
        minute = 0
    if pd.isna(delay):
        delay = 0

    # Combine the date, hour, and minute into a datetime object
    datetime_str = f"{date_str} {int(hour):02d}:{int(minute):02d}"

    orig_dtobj = datetime.strptime(datetime_str, '%m/%d/%Y %H:%M')

    dtobj = orig_dtobj + timedelta(minutes=int(delay))
    dtobj_end = dtobj + timedelta(minutes=10)

    time_range_start = dtobj.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_range_end = dtobj_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    timerange_line = f"TimeRange: {time_range_start} {time_range_end}\n"

    return timerange_line

def create_remark(row) -> str:
    """
    This function creates the pop-up text for the placefiles
    """
    typetext= row.get('TYPETEXT',"")
    qualifier = row.get('QUALIFIER',"")
    mag = row.get('MAG',"")
    mag_line = ""
    #if magnitude == "nan" or magnitude == "No_Magnitude":
    if mag in ("nan", "NO MAG", "NA", "No_Magnitude"):
        mag_line = "No Magnitude given"
    else:
        if typetext == 'TSTM WND GST':
            mag_line = f"Wind Gust: {mag} mph"
        if typetext in ('HAIL'):
            mag_line = f"Size: {mag} inches"
        if typetext in ('RAIN', 'SNOW'):
            mag_line = f"Accum: {mag} inches"
    source = row.get('SOURCE',"")
    #fake_rpt = row.get('fake_rpt',"")
    remark = row.get('REMARK',"")
    if remark in ("nan", "No_Comments", "M","NA", "NO MAG"):
        remark_line = ""
    if typetext == 'QUESTION':
        remark_line = f'{typetext}\\nSource: {source}\\n{remark}\nEnd:\n\n'
    else:
        remark_line = f'{typetext}\\n{qualifier}\\n{mag_line}\\nSource: {source}\\n{remark}\nEnd:\n\n'
    return remark_line


def icon_value(event_type) -> int:
    """
    This function assigns an icon value based on the event type
    """
    #if event_type == 'VERIFIED':
    if event_type in ('VERIFIED', 'MEASURED'):
        return 1
    if event_type in ('UNVERIFIED', 'ESTIMATED'):
        return 2
    if event_type == 'QUESTION':
        return 3
    return 3


def make_events_placefile(contents, filename, cfg):
    """
    This function creates the Event Notification placefile for the radar simulation
    """
    top_section = 'RefreshSeconds: 5\
    \nThreshold: 999\
    \nTitle: Event Notifications -- for radar simulation\
    \nColor: 255 200 255\
    \nIconFile: 1, 50, 50, 25, 15, https://raw.githubusercontent.com/tjturnage/cloud-radar-server/main/assets/iconfiles/wessl-three.png\
    \nIconFile: 2, 30, 30, 15, 10, https://raw.githubusercontent.com/tjturnage/cloud-radar-server/main/assets/iconfiles/wessl-three-small.png\
    \nFont: 1, 11, 1, "Arial"\n\n'


    _content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if 'csv' in filename:
            place_fout = open(f'{cfg['PLACEFILES_DIR']}/events.txt', 'w', encoding='utf-8')
            #notifications_csv = open(f'{cfg['DATA_DIR']}/notifications.csv', 'w', encoding='utf-8')
            events_csv = f'{cfg['DATA_DIR']}/events.csv'
            place_fout.write("; RSSiC events file\n")
            place_fout.write(top_section)
            # Assume that the user uploaded a CSV file
            df_orig = pd.read_csv(io.StringIO(decoded.decode('utf-8')), dtype=str)
            df_orig.fillna("NA", inplace=True)
            df = df_orig.loc[df_orig['TYPETEXT'] != 'NO EVENT']

            df.to_csv(events_csv, index=False, encoding='utf-8')

            for _index,row in df.iterrows():
                try:
                    lat = row.get('LAT',"")
                    lon = row.get('LON',"")
                    obj_line = f'Object: {lat},{lon}\n'

                    tr_line = make_timerange_line(row)
                    comments = create_remark(row)
                    icon_code = icon_value(row.get('QUALIFIER',""))
                    icon_line = f"Threshold: 999\nIcon: 0,0,0,2,{icon_code}, {comments}"
                    place_fout.write(tr_line)
                    place_fout.write(obj_line)
                    place_fout.write(icon_line)
                except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
                    return None, f"Error processing file: {e}"
            place_fout.close()
            return df, None
        return None, f"Unsupported file type: {filename}"

    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
        return None, f"Error processing file: {e}"