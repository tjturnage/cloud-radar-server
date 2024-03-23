"""
Functions for reading in model data. Currently only GRIB2 data is supported, although some
GRIB1 files may work. If data is stored on isobaric coordinates, 2- and 10-m data are
inserted at the surface and checks are applied to ensure pressure (heights) monotonically
decrease (increase).

"""
import pygrib
import numpy as np
import logging

import sharptab.winds as winds
import sharptab.thermo as thermo
from sharptab.constants import MS2KTS, ZEROCNK

def make_data_monotonic(data):
    """For data in isobaric coordinates, need to ensure pressure monotonically decreases
    and height monotonically increases with height. There are still likely edge cases
    that haven't been tested here.

    Parameters:
    -----------
    data : dictionary
        Dictionary containing the processed data cube.

    Returns:
    data : dictionary
        Monotonic dataset with the same dimensions as the input. NaNs inserted where data
        has been shifted.

    """
    logging.info("Re-ordering data for monotonic heights and pressure")
    original_data = data
    full_keys = list(original_data.keys())
    keys = ['tmpc', 'dwpc', 'hght', 'wdir', 'wspd', 'pres']
    arr_shape = data['tmpc'].shape
    for j in range(arr_shape[1]):
        for i in range(arr_shape[2]):

            # Small differences in height and pressure arrays such that one might be
            # just out of sync with the other.
            shift1 = np.where(data['pres'][:,j,i] < data['pres'][0,j,i])[0][0]
            shift2 = np.where(data['hght'][:,j,i] > data['hght'][0,j,i])[0][0]
            shift = np.maximum(shift1, shift2)
            for key in keys:
                last_val = data[key][-1,j,i]
                data[key][:,j,i] = np.append(np.insert(data[key][shift:,j,i], 0,
                                             data[key][0,j,i]), [last_val]*(shift-1))

                # This is a terrible hack. Add in some fake data above if we've shifted
                # data. Since this will be above 100 mb, this won't materially impact our
                # thermodynamic calcs.
                if shift > 0:
                    if key == 'pres':
                        data[key][-shift:,j,i] = [(1./last_val**2)*10 for i in range(shift)]
                    elif key == 'hght':
                        data[key][-shift:,j,i] = [last_val+10*i for i in range(shift)]

    remaining_keys = list(np.setdiff1d(full_keys, keys))
    for key in remaining_keys:
        data[key] = original_data[key]
    return data

def read_data(filename):
    logging.info("Reading file %s" % (filename))
    grb = pygrib.open(filename)
    sfc = grb.select(name='Orography')[0]
    lats, lons = sfc.latlons()

    temperatures = grb.select(name='Temperature')[0]
    order = 1
    delta = 1

    # For realtime runs, this is easy if we use the native hybrid-sigma coordinate files.
    # By definition, we're guaranteed each vertical slice is higher than the one below.
    if temperatures.typeOfLevel == 'hybrid':
        native = True
        level_type = 'hybrid'
        temperatures = grb.select(name='Temperature', typeOfLevel=level_type)
        heights = grb.select(name='Geopotential height', typeOfLevel=level_type)
        pressure = grb.select(name='Pressure', typeOfLevel=level_type)
        specific_humidity = grb.select(name='Specific humidity', typeOfLevel=level_type)

    # If this is isobaric data, we need to "drop in" the surface fields and mask out
    # data that's below the ground. Additionally, we need to check if the data is stored
    # top-down (this changes with certain RAP versions/epochs)
    elif temperatures.typeOfLevel == 'isobaricInhPa':
        native = False
        level_type = 'isobaricInhPa'
        heights = grb.select(name='Geopotential height', typeOfLevel=level_type)
        psfc = grb.select(name='Surface pressure')[0].values
        t2m = grb.select(name='2 metre temperature')[0].values
        u10m = grb.select(name='10 metre U wind component')[0].values
        v10m = grb.select(name='10 metre V wind component')[0].values

        try:
            rh = grb.select(name='Relative humidity', typeOfLevel=level_type)
        except ValueError:
            q = grb.select(name='Specific humidity', typeOfLevel=level_type)

        try:
            td2m = grb.select(name='2 metre dewpoint temperature')[0].values
        except ValueError:
            q2m = grb.select(name='Specific humidity', level=2)[0].values
            td2m = thermo.dewpoint_from_q(q2m, t2m, psfc)

        # Determine how the data is oriented vertically
        if heights[0].values[0,0] > heights[-1].values[0,0]:
            order = -1
            delta = 0

    temperatures = grb.select(name='Temperature', typeOfLevel=level_type)
    uwind = grb.select(name='U component of wind', typeOfLevel=level_type)
    vwind = grb.select(name='V component of wind', typeOfLevel=level_type)

    arr_shape = heights[0].values.shape
    num_levels = len(heights)

    if not native:
        logging.info("    Data is in ISOBARIC coordinates")
        num_levels += 1
    else:
        logging.info("    Data is in HYBRID-SIGMA coordinates")

    hght = np.zeros((num_levels, arr_shape[0], arr_shape[1]))
    tmpc = np.full_like(hght, 0)
    pres = np.full_like(hght, 0)
    dwpc = np.full_like(hght, 0)
    wdir = np.full_like(hght, 0)
    wspd = np.full_like(hght, 0)

    # First build the height array. Do this in order, starting with the surface level
    # Note that array will still be flipped if order = -1, we'll take care of that later.
    knt = 0
    for lev in range(num_levels)[::order]:
        # Isobaric coordinates
        if not native:
            if knt == 0:
                pres[lev] = psfc / 100.
                hght[lev] = sfc.values
                tmpc[lev] = t2m - ZEROCNK
                dwpc[lev] = td2m - ZEROCNK
                wdir[lev], wspd[lev] = winds.wind_vecs(u10m, v10m)
            else:
                pres[lev] = np.full_like(heights[0].values, heights[lev-delta].level)
                tmpc[lev] = temperatures[lev-delta].values - 273.15
                wdir[lev], wspd[lev] = winds.wind_vecs(uwind[lev-delta].values,
                                                       vwind[lev-delta].values)
                hght[lev] = heights[lev-delta].values
                try:
                    dwpc[lev] = thermo.dewpoint_from_rh(temperatures[lev-delta].values,
                                                        rh[lev-delta].values/100)
                except:
                    dwpc[lev] = thermo.dewpoint_from_q(q[lev].values,
                                                       temperatures[lev].values,
                                                       pres[lev])

        # Native coordinates
        else:
            hght[lev] = heights[lev].values
            tmpc[lev] = temperatures[lev].values - 273.15
            wdir[lev], wspd[lev] = winds.wind_vecs(uwind[lev].values, vwind[lev].values)
            pres[lev] = pressure[lev].values / 100.
            dwpc[lev] = thermo.dewpoint_from_q(specific_humidity[lev].values,
                                               temperatures[lev].values,
                                               pres[lev])
        knt += 1

    tmpc = np.array(tmpc[::order], dtype='float64')
    dwpc = np.array(dwpc[::order], dtype='float64')
    hght = np.array(hght[::order], dtype='float64')
    wdir = np.array(wdir[::order], dtype='float64')
    wspd = np.array(wspd[::order], dtype='float64') * MS2KTS
    pres = np.array(pres[::order], dtype='float64')

    model = 'HRRR'
    if 'rap' in filename:
        model = 'RAP'

    data = {
        'tmpc': tmpc,
        'dwpc': dwpc,
        'hght': hght,
        'wdir': wdir,
        'wspd': wspd,
        'pres': pres,
        'lons': lons,
        'lats': lats,
        'cycle_time': sfc.analDate,
        'valid_time': sfc.validDate,
        'fhr': sfc.forecastTime,
        'model_name': model,
    }

    if not native: data = make_data_monotonic(data)
    return data
