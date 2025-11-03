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
    #'fzl-lfc-diff': 'Freezing Level - MU LFC thickness (m)',
    #'el-lfc-diff': 'MU Parcel EL - LFC thickness (m)',
    #'mu-el': 'MU Parcel Equilibrium Level (m)',
    'dcape': 'Downdraft CAPE (J/kg)',

    # Winter parameters
    'snsq': 'Snow Squall Parameter',
    'sfctw': 'Surface Wetbulb Temperature (F)', # auto-generated during snsq step

    # dgzdepth, dgzomega, and oprh are masked if the mean RH in the DGZ is < 60%. 
    # Additionally masked if the surface tw is >= 40 F (see below).
    'dgzdepth': 'Dendritic Growth Layer Depth (m)',
    'dgzomega': 'Dendritic Growth Layer Omega (-microbars/sec)',
    'oprh': 'DGZ Omega, RH, and PWAT',
    
    '925fgen': '925 mb frontogenesis (K/100 km/3 hr)',
    '925T': '925 mb temperature (C)',
    '850fgen': '850 mb frontogenesis (K/100 km/3 hr)',
    '850T': '850 mb temperature (C)',
    '700fgen': '700 mb frontogenesis (K/100 km/3 hr)',
    '700T': '700 mb temperature (C)',
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
#    'QLCS Tornado': ['cape3km_cf', 'cape3km', 'estp', 'shr3'],
#    'ML CAPE-CIN': ['mlcin_cf', 'mlcin', 'mlcape'],
#    'bundle_1': ['cape3km', 'shr3'],
#    'low-level-lapse-rates': ['lr03km', 'lr03km_cf']
    '925MB': ['925T', '925fgen'],
    '850MB': ['850T', '850fgen'],
    '700MB': ['700T', '700fgen'],
}

##########################################################################################
# User overrides for plotting configurations. If not specified, plotting specifications
# default to those in barbconfigs and contourconfigs.
#
# Specifying either the `fill_levels` or `fill_colors` keywords will cause a separate
# contour-filled placefile to be output. These will have `_cf` appended to the filename.
##########################################################################################

# Configurations for isobaric temperature plots
temperature_levels = [-40, -38, -36, -34, -32, -30, -28, -26, -24, -22, -20, -18, -16, -14,
                      -12, -10, -8, -6, -4, -2, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
temperature_cols = ['#4595f8', '#4595f8', '#4595f8', '#4595f8', '#4595f8', '#4595f8',
                    '#4595f8', '#4595f8', '#4595f8', '#4595f8', '#4595f8', '#4595f8',
                    '#4595f8', '#4595f8', '#4595f8', '#4595f8', '#4595f8', '#4595f8', 
                    '#4595f8', '#4595f8', '#4595f8', '#ed6257', '#ed6257', '#ed6257', 
                    '#ed6257', '#ed6257', '#ed6257', '#ed6257', '#ed6257', '#ed6257',
                    '#ed6257', '#ed6257']
idx = temperature_levels.index(0)
temperature_lws = [1] * len(temperature_cols)
temperature_lws[idx] = 2

PLOTCONFIGS = {
    'mllcl': {
        'colors': ['#438a2d','#438a2d','#71d054','#71d054','#000000','#000000','#000000',
                   '#000000', '#000000'],
        'levels': [500, 750, 1000, 1250, 1500, 1750, 2000, 2500, 3000],
        'linewidths': [3, 3, 2, 2, 1, 1, 1, 1, 1]
    },

    'lr03km': {
        'colors': ['#6da55d', '#6da55d', '#ed8433', '#da4238', '#da4238', '#000000'],
        'levels': [6, 6.5, 7, 8, 9, 10],
        'linewidths': [0.75, 0.75, 1.5, 2, 2, 2.5],
        'fill_levels': [6.5, 999],
        'fill_colors': ['#f1a95d', '#f1a95d']
    },

    'esrh': {
        'colors': ['#81b6f7', '#81b6f7', '#3c6193', '#3c6193', '#3c6193', '#3c6193'],
        'levels': [50, 100, 200, 300, 400, 500, 600, 700, 800],
        'linewidths': [1, 1, 2, 2, 2, 2, 2, 3, 3]
    },

    'srh01km': {
        'colors': ['#81b6f7', '#81b6f7', '#3c6193', '#3c6193', '#3c6193', '#3c6193'],
        'levels': [50, 100, 200, 300, 400, 500, 600, 700, 800],
        'linewidths': [1, 1, 2, 2, 2, 2, 2, 3, 3]
    },

    'srh500': {
        'colors': ['#81b6f7', '#81b6f7', '#3c6193', '#3c6193', '#3c6193', '#3c6193'],
        'levels': [25, 50, 100, 200, 300, 400, 500, 600, 800],
        'linewidths': [1, 1, 2, 2, 2, 2, 2, 3, 3]
    },

    'shr1': {
        'windicons': SHEAR1_ICONS,
    },

    'mucape': {
        'colors': ['#ea908c', '#ea908c', '#da453a', '#da453a', '#da453a', '#c03c32',
                   '#811811', '#811811', '#811811'],
        'levels': [100, 250, 500, 1000, 2000, 3000, 4000, 5000, 6000],
        'linewidths': [0.75, 1, 1, 2, 2, 2, 2, 2, 3]
    },

    'mlcape': {
        'colors': ['#ea908c', '#ea908c', '#da453a', '#da453a', '#da453a', '#c03c32',
                   '#c03c32', '#c03c32', '#811811', '#811811'],
        'levels': [100, 250, 500, 1000, 2000, 2500, 3000, 3500, 4000, 6000],
        'linewidths': [0.75, 1, 1, 2, 2, 2, 2, 2, 2, 3]
    },

    'cape3km': {
        'colors': ['#ea908c', '#ea908c', '#da453a', '#bb2d1d', '#bb2d1d',
                   '#bb2d1d', '#841f18', '#841f18'],
        #'colors': 'k',
        'levels': [25, 75, 100, 150, 300, 500],
        'linewidths': [0.75, 0.75, 1, 2, 2, 3],
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

    'dcape': {
        'levels': [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000, 3000, 4000, 5000],
        'colors': ['#d2a663', '#d2a663', '#d2a663', '#df6641', '#90322b', '#90322b', '#90322b',
                   '#90322b', '#90322b', '#90322b', '#90322b', '#90322b', '#90322b', '#90322b'],
        'linewidths': [1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    },

    # Winter parameters
    'snsq': {
        'levels': [0.1, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6],
        'linewidths': [1, 1, 1, 1, 2, 2, 2, 2, 2, 2],
        'colors': ['#244e83', '#458ff7', '#50b0eb', '#6be8e9', '#8467c6', '#8835e2',
                   '#7a1681', '#ea33f7', '#f3b0b9']
    },
    
    'sfctw': {
        'levels': [26, 28, 30, 32, 34, 36, 38],
        'colors': ['#5fa3f6', '#5fa3f6', '#5fa3f6', '#9956ec', '#ed5f54', '#ed5f54', 
                   '#ed5f54', '#ed5f54'],
        'linewidths': [1, 1, 1, 2, 1, 1, 1],
    }, 

    'dgzdepth': {
        'levels': [800, 1000, 1400, 1800, 2200, 2600, 3000],
        'colors': ['#9956ec'],
        'linewidths': [1, 2, 2, 2, 2, 2, 2],
    },

    'dgzomega': {
        'levels': [-32, -28, -24, -20, -16, -14, -10, -8, -6, -4, -2, -1],
        'colors': ['#9956ec'],
        'linewidths': [2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1],
    },

    'oprh': {
        'levels': [-2, -1, -0.5],
        'colors': ['#f3b0b9', '#ea33f7', '#50b0eb'],
        'linewidths': [3, 2, 1],
    },

    '925fgen': {
        'levels': [1, 2, 3, 4, 6, 8, 10],
        'colors': ['#7a1681'],
        'linewidths': [1],
    },

    '850fgen': {
        'levels': [1, 2, 3, 4, 6, 8, 10],
        'colors': ['#7a1681'],
        'linewidths': [1],
    },

    '700fgen': {
        'levels': [1, 2, 3, 4, 6, 8, 10],
        'colors': ['#7a1681'],
        'linewidths': [1],
    },

    '925T': {
        'levels': temperature_levels,
        'colors': temperature_cols,
        'linewidths': temperature_lws
    },

    '850T': {
        'levels': temperature_levels,
        'colors': temperature_cols,
        'linewidths': temperature_lws
    },

    '700T': {
        'levels': temperature_levels,
        'colors': temperature_cols,
        'linewidths': temperature_lws
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
    'oprh':{
        'sfctw': ['<', 40]
    },

    'dgzomega':{
        'sfctw': ['<', 40]
    },
    
    'dgzdepth':{
        'sfctw': ['<', 40]
    },

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

    'dcape': {
        'mucape': ['>', 1]
    }
}
