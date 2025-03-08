"""
Shift placefiles to a new radar site and forwards or backwards in time

Assumptions:
    - Lat/lon pairs for original radar and radar to shift to will be within the local 
    scope of radar-server.py within a callback function. 
    - Path to the placefile holding directory is self.placefiles_dir within radar-server.

    
Usage: (shift from KLOT to KGRR, 2000 minutes ahead in time)
python shift_placefiles.py -orig 41.60445/-88.08451 -target 42.8939/-85.54479 -timeshift 2000 -p 'path/to/placefiles'

"""
import math
import argparse
from glob import glob
import re
from datetime import datetime, timedelta

# Earth radius (km)
R = 6_378_137

# Regular expressions. First one finds lat/lon pairs, second finds the timestamps.
LAT_LON_REGEX = "[0-9]{1,2}.[0-9]{1,100},[ ]{0,1}[|\\s-][0-9]{1,3}.[0-9]{1,100}"
TIME_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

def move_point(radar1_lat, radar1_lon, radar2_lat, radar2_lon, lat, lon):
    """
    Shift placefiles to a different radar site. Maintains the original azimuth and range
    from a specified RDA and applies it to a new radar location. 

    Parameters:
    -----------
    radar1_lat: float 
        Original radar latitude in decimal degrees
    radar1_lon: float 
        Original radar longitude in decimal degrees
    radar2_lat: float 
        New radar latitude in decimal degrees
    radar2_lon: float 
        New radar longitude in decimal degrees
    lat: float 
        Original placefile latitude
    lon: float 
        Original palcefile longitude
    """
    def _clamp(n, minimum, maximum):
        """
        Helper function to make sure we're not taking the square root of a negative 
        number during the calculation of `c` below. Same as numpy.clip(). 
        """
        return max(min(maximum, n), minimum)

    # Compute the initial distance from the original radar location
    phi1, phi2 = math.radians(radar1_lat), math.radians(lat)
    d_phi = math.radians(lat - radar1_lat)
    d_lambda = math.radians(lon - radar1_lon)

    a = math.sin(d_phi/2)**2 + (math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda/2)**2)
    a = _clamp(a, 0, a)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c

    # Compute the bearing
    y = math.sin(d_lambda) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2)) - (math.sin(phi1) * math.cos(phi2) * \
                                             math.cos(d_lambda))
    theta = math.atan2(y, x)
    bearing = (math.degrees(theta) + 360) % 360

    # Apply this distance and bearing to the new radar location
    phi_new, lambda_new = math.radians(radar2_lat), math.radians(radar2_lon)
    phi_out = math.asin((math.sin(phi_new) * math.cos(d/R)) + (math.cos(phi_new) * \
                        math.sin(d/R) * math.cos(math.radians(bearing))))
    lambda_out = lambda_new + math.atan2(math.sin(math.radians(bearing)) *    \
                 math.sin(d/R) * math.cos(phi_new), math.cos(d/R) - math.sin(phi_new) * \
                 math.sin(phi_out))
    return math.degrees(phi_out), math.degrees(lambda_out)


def shift_time(line, timeshift):
    new_line = line
    if 'Valid:' in line:
        idx = line.find('Valid:')
        valid_timestring = line[idx+len('Valid:')+1:-1] # Leave off \n character
        dt = datetime.strptime(valid_timestring, '%H:%MZ %a %b %d %Y')
        new_validstring = datetime.strftime(dt + timedelta(minutes=timeshift),
                                            '%H:%MZ %a %b %d %Y')
        new_line = line.replace(valid_timestring, new_validstring)

    if 'TimeRange' in line:
        regex = re.findall(TIME_REGEX, line)
        dt = datetime.strptime(regex[0], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring_1 = datetime.strftime(dt + timedelta(minutes=timeshift),
                                            '%Y-%m-%dT%H:%M:%SZ')
        dt = datetime.strptime(regex[1], '%Y-%m-%dT%H:%M:%SZ')
        new_datestring_2 = datetime.strftime(dt + timedelta(minutes=timeshift),
                                            '%Y-%m-%dT%H:%M:%SZ')
        new_line = line.replace(f"{regex[0]} {regex[1]}",
                                f"{new_datestring_1} {new_datestring_2}")
    return new_line

def shift_placefiles(source, target, filepath, timeshift):
    filenames = glob(f"{filepath}/*.txt")
    for file_ in filenames:
        print(f"Shifting placefile: {file_}")
        with open(file_, 'r', encoding='utf-8') as f: data = f.readlines()
        outfilename = f"{file_[0:file_.index('.txt')]}.shifted"
        outfile = open(outfilename, 'w', encoding='utf-8')

        for line in data:
            new_line = line

            if timeshift is not None and any(x in line for x in ['Valid', 'TimeRange']):
                new_line = shift_time(line, int(timeshift))

            # Shift this line in space
            # This regex search finds lines with valid latitude/longitude pairs
            regex = re.findall(LAT_LON_REGEX, line)
            if len(regex) > 0:
                idx = regex[0].index(',')
                lat, lon = float(regex[0][0:idx]), float(regex[0][idx+1:])
                lat_out, lon_out = move_point(source['lat'], source['lon'], 
                                                target['lat'], target['lon'],
                                                lat, lon)
                new_line = line.replace(regex[0], f"{lat_out}, {lon_out}")

            outfile.write(new_line)
        outfile.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-orig',  dest='original_lat_lon',
                    help='The original radar lat/lon pair. Example: 41.60445/-88.08451')
    ap.add_argument('-target',  dest='target_lat_lon', 
                    help='The target radar lat/lon pair. Example: 42.8939/-85.54479')
    ap.add_argument('-timeshift',  dest='timeshift', 
                    help='Number of minutes to shift data. Can be negative (backwards in time).')
    ap.add_argument('-p', '--filepath', dest='filepath', help='Path to placefile directory')
    args = ap.parse_args()

    source = args.original_lat_lon.split('/')
    target = args.target_lat_lon.split('/')

    source_dict = {
        'lat': float(source[0]),
        'lon':float(source[1])
    }

    target_dict = {
        'lat': float(target[0]),
        'lon':float(target[1])
    }

    shift_placefiles(source_dict, target_dict, args.filepath, timeshift=args.timeshift)

if __name__ == '__main__':
    main()
