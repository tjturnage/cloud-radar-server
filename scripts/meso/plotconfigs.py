from configs import WIND_ICONS, SHEAR1_ICONS, DEVTOR_ICONS

##########################################################################################
# Plotting configurations
##########################################################################################
SCALAR_PARAMS = {
    'esrh': 'Effective Storm-Relative Helicity',
    'mucape': 'Most-Unstable CAPE (J/kg)',
    'mlcin': 'Mixed-Layer CIN (J/kg)',
    'mlcape': 'Mixed-Layer CAPE (J/kg)',
    'cape3km': '0-3 km MLCAPE (J/kg)',
    'estp': 'Effective SigTor Parameter',
    'srh500': '0-500 m Storm-Relative Helicity',
    'srh01km': '0-1 km Storm-Relative Helicity',
    'lr03km': '0-3 km Lapse Rate (C/km)',
    'mllcl': 'Mixed-Layer LCL (m)',
    'nst': 'Non-Supercell Tornado Parameter',
    'deviance': 'Perceived Tornado Deviance',
    'snsq': 'Snow Squall Parameter',
    #'fzl-lfc-diff': 'Freezing Level - MU LFC thickness (m)',
    #'el-lfc-diff': 'MU Parcel EL - LFC thickness (m)',
    #'mu-el': 'MU Parcel Equilibrium Level (m)',
}

VECTOR_PARAMS = {
    'ebwd': 'Effective Bulk Shear (kt)',
    'shr1': '0-1 km shear (kt)',
    'shr3': '0-3 km shear (kt)',
    'shr6': '0-6 km shear (kt)',
    'shr8': '0-8 km shear (kt)',
    'rm5': 'Bunkers Right Vectors (kt)',
    'lm5': 'Bunkers Left Vectors (kt)',
    'devtor': 'Deviant Tornado Motion (kt)',
}

BUNDLES = {
    'QLCS Tornado': ['cape3km_cf', 'cape3km', 'estp', 'shr3'],
    'ML CAPE-CIN': ['mlcin_cf', 'mlcin', 'mlcape'],
#    'bundle_1': ['cape3km', 'shr3'],
#    'low-level-lapse-rates': ['lr03km', 'lr03km_cf']
}

##########################################################################################
# User overrides for plotting configurations. If not specified, plotting specifications
# default to those in barbconfigs and contourconfigs.
#
# Specifying either the `fill_levels` or `fill_colors` keywords will cause a separate
# contour-filled placefile to be output. These will have `_cf` appended to the filename.
##########################################################################################
PLOTCONFIGS = {
    'mllcl': {
        'colors': ['#438a2d','#438a2d','#71d054','#71d054','#000000','#000000','#000000',
                   '#000000', '#000000'],
        'levels': [500, 750, 1000, 1250, 1500, 1750, 2000, 2500, 3000],
        'linewidths': [3, 3, 2, 2, 1, 1, 1, 1, 1]
    },

    'lr03km': {
        'colors': 'k',
        'levels': [6, 7, 8, 9, 10],
        'linewidths': 0.75,
        'fill_levels': [6.5, 999],
        'fill_colors': ['#f1a95d', '#f1a95d']
    },

    'esrh': {
        'colors': ['#81b6f7', '#81b6f7', '#3c6193', '#3c6193', '#3c6193', '#3c6193'],
        'levels': [50, 100, 200, 300, 400, 500, 600, 700, 800],
        'linewidths': [1, 1, 2, 2, 2, 3, 3, 3, 3]
    },

    'srh01km': {
        'colors': ['#81b6f7', '#81b6f7', '#3c6193', '#3c6193', '#3c6193', '#3c6193'],
        'levels': [50, 100, 200, 300, 400, 500, 600, 700, 800],
        'linewidths': [1, 1, 2, 2, 2, 3, 3, 3, 3]
    },

    'srh500': {
        'colors': ['#81b6f7', '#81b6f7', '#3c6193', '#3c6193', '#3c6193', '#3c6193'],
        'levels': [25, 50, 100, 200, 300, 400, 500, 600, 800],
        'linewidths': [1, 1, 2, 2, 2, 3, 3, 3, 3]
    },

    'shr1': {
        'windicons': SHEAR1_ICONS,
    },

    'mucape': {
        'colors': ['#ea908c', '#ea908c', '#da453a', '#da453a', '#da453a', '#c03c32',
                   '#c03c32', '#c03c32', '#c03c32'],
        'levels': [100, 250, 500, 1000, 2000, 3000, 4000, 5000, 6000],
        'linewidths': [1, 1, 1, 2, 2, 3, 3, 3, 3]
    },

    'mlcape': {
        'colors': ['#ea908c', '#ea908c', '#da453a', '#da453a', '#da453a', '#c03c32',
                   '#c03c32', '#c03c32', '#c03c32'],
        'levels': [100, 250, 500, 1000, 2000, 2500, 3000, 3500, 4000],
        'linewidths': [1, 1, 1, 2, 2, 3, 3, 3, 3]
    },

    'cape3km': {
        #'colors': ['#dd564e', '#dd564e', '#dd564e', '#bb2d1d', '#bb2d1d',
        #           '#bb2d1d', '#841f18', '#841f18'],
        'colors': 'k',
        'levels': [25, 75, 100, 150, 300, 500],
        'linewidths': [0.5, 0.5, 1, 1, 1.5, 1.5],
        'fill_levels': [50, 9999],
        'fill_colors': ['#f1b1bc']
    },

    'mlcin': {
        'colors': ['#6beaea', '#4eb0e7', '#0000cf', '#0000cf', '#0000cf'],
        'levels': [25, 75, 150, 300],
        'linewidths': [1, 1, 1, 2, 2],
        'fill_levels': [25, 9999],
        'fill_colors': ['#4eb0e7', '#4eb0e7'],
    },

    'estp': {
        'levels': [0.25, 0.5, 1, 2, 4, 6, 8, 10],
        'colors': ['#ec904a', '#ec904a', '#ec904a', '#e94639', '#c23f34',
                   '#841f18', '#957cca', '#e951f5', '#e951f5'],
        'linewidths': [1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    },

    'nst': {
        'colors': ['#ee8c40', '#ee8c40', '#ea4b3f', '#ea4b3f', '#ea4b3f', '#e848f5',
                   '#e848f5'],
        'levels': [0.5, 1, 2, 3, 4, 5, 6],
        'linewidths': [1, 2, 3, 3, 3, 3, 3]
    },

    # Hail parameters testing
    'fzl-lfc-diff': {
        'levels': [1000, 2000, 3000, 5000, 7000, 9000],
        'colors': ['#000000'],
        'linewidths': [2, 1, 1, 1, 1, 1, 1, 1]
    },

    'el-lfc-diff': {
        'levels': [5000, 6000, 7000, 8000, 9000, 10000],
        'colors': ['#000000'],
        'linewidths': [1, 1, 1, 2, 2, 2]
    },

    'mu-el': {
        'levels': [9000, 10000, 11000, 12000, 13000, 14000, 15000],
        'colors': ['#000000'],
        'linewidths': [1, 1, 2, 2, 2, 3, 3]
    },

    # Vectors/barbs
    'rm5': {
        'skip': 2
    },

    'lm5': {
        'skip': 2
    },

    'shr3': {
        'skip': 3
    },

    'devtor': {
        'windicons': DEVTOR_ICONS,
        'skip': 2
    },

    'deviance': {
        'levels': [0.7, 1, 1.25, 1.5, 1.75, 2, 2.25],
        'linewidths': [1, 1, 2, 2, 3, 3, 3],
        'colors': ['#ec904a', '#e94639', '#841f18', '#957cca', '#e951f5', 
                   '#e951f5', '#e951f5', '#e951f5']
    },

    'snsq': {
        'levels': [0.1, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6],
        'linewidths': [0.5, 0.5, 1, 1, 2, 2, 2, 3, 3, 3],
        'colors': ['#244e83', '#458ff7', '#50b0eb', '#6be8e9', '#8467c6', '#8835e2',
                   '#7a1681', '#ea33f7', '#f3b0b9']
    },

}

##########################################################################################
# Base contour and wind barb configurations. These will be overriden by any corresponding
# entries in the PLOTCONFIGS dictionary
##########################################################################################
barbconfigs = {
    'skip': 3,
    'windicons': WIND_ICONS,
}

contourconfigs = {
    'colors': ['#dd564e', '#dd564e', '#dd564e', '#dd564e', '#bb2d1d', '#bb2d1d',
               '#bb2d1d', '#841f18', '#841f18'],
    'levels': [100, 250, 500, 1000, 2000, 3000, 4000, 5000, 6000],
    'linewidths': [1, 1, 1, 2, 2, 2, 3, 4, 4],
    'fill_levels': None,
    'fill_colors': None,
}

##########################################################################################
# Filtering specifications
##########################################################################################
FILTER_SPECS = {
    'mlcin': {
        'mlcape': ['>', 5],
    },

    'ebwd': {
        'ebwd': ['>', 20],
    },

    'shr1': {
        'shr1': ['>', 15],
    },

    'shr3': {
        'shr3': ['>', 20],
    },

    'shr6': {
        'shr6': ['>', 30],
    },

    'shr8': {
        'shr8': ['>', 40],
    },

    'rm5': {
        'mucape': ['>', 100],
        'ebwd': ['>', 20],
    },

    'lm5': {
        'mucape': ['>', 100],
        'ebwd': ['>', 20],
    },

    'devtor': {
        'mucape': ['>', 100],
        'ebwd': ['>', 20],
    },
}
