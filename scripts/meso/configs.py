from collections import OrderedDict

##########################################################################################
# User configurations: Must be edited
#
# Adjust the following variables to point to Python, WGRIB2, and WGET executables on the
# filesystem. See README for notes on WGRIB2 requirements.
#
# OUTPUT_DIR, MODEL_DIR, and LOG_DIR are used by run.py to automate scripting.
##########################################################################################
#PYTHON = '/Users/leecarlaw/mambaforge/envs/cloud-radar/bin/python'
#WGRIB2 = '/usr/local/bin/wgrib2'
#WGET = '/usr/local/bin/wget'
#PYTHON = '/opt/miniforge3/envs/cloud-radar/bin/python'
#WGRIB2 = '/usr/local/bin/wgrib2'
#WGET = '/usr/bin/wget'

#OUTPUT_DIR = '/Users/leecarlaw/scripts/cloud-radar-server/assets/placefiles'            
#MODEL_DIR = '/Users/leecarlaw/scripts/cloud-radar-server/data'
#LOG_DIR = '/Users/leecarlaw/scripts/cloud-radar-server/scripts/meso/logs/'

# URL or local path to wind icon files
WIND_ICONS = 'https://rssic.nws.noaa.gov/assets/iconfiles/windicons.png'
SHEAR1_ICONS = 'https://rssic.nws.noaa.gov/assets/iconfiles/shr1icons.png'
DEVTOR_ICONS = 'https://rssic.nws.noaa.gov/assets/iconfiles/devtor.png'

# Specifies number of threads for numba to use. 
NUM_THREADS = 4     

##########################################################################################
# Download configurations
#
# You likely won't need (or want) to change these. Download priority is set by the order
# of the dictionary keys in the DATA_SOURCES variable.
##########################################################################################
TIMEOUT = 200       # Seconds after which to timeout the data download function
MAXSECONDS = 1800   # Number of seconds after which to abort data download in run.py
MINSIZE = 5         # Grib files under this size (MB) will result in a download error
SIGMA = 1.         # For smoothing function. Larger = more smoothing, but amplitude loss
ALPHA = 50          # Alpha level for filled placefiles. 0 = transparent; 255 = opaque

DATA_SOURCES = OrderedDict({
    'NOMADS': 'https://nomads.ncep.noaa.gov/pub/data/nccf/com',
    'GOOGLE': 'https://storage.googleapis.com',
    'FTPPRD': 'https://ftpprd.ncep.noaa.gov/data/nccf/com',
    'THREDDS': 'https://www.ncei.noaa.gov/thredds/fileServer',
})

GOOGLE_CONFIGS = {
    'RAP': 'rapid-refresh',
    'HRRR': 'high-resolution-rapid-refresh'
}

THREDDS_CONFIGS = {
    'RAP-current': 'model-rap130anl',
    'RAP': 'model-rap130anl-old',
    'RUC': 'model-ruc130anl'
}

vars = ':(HGT|TMP|SPFH|UGRD|VGRD|PRES):'
# 13-km CONUS
#grid_info = 'lambert:262.5:38.5 -120:360:13545.000000 23:215:13545.000000'

# 20-km CONUS
grid_info = 'lambert:262.5:38.5 -120:245:20318.000000 23:145:20318.000000'