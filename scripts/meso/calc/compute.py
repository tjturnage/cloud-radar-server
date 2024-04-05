"""Contains functions to compute SHARPpy-specific and other derived meteorological
variables.
"""

from numba import njit, prange, set_num_threads
from numba.typed import List, Dict
from numba.core import types
import numpy as np

from configs import NUM_THREADS
from plotconfigs import SCALAR_PARAMS, VECTOR_PARAMS
import sharptab.profile as profile
import sharptab.params as params
from sharptab.winds import vec2comp
from sharptab.constants import KTS2MS
from calc import derived
from utils.timing import timeit

float_array = types.float64[:,:] # No type expressions allowed in jitted functions
@timeit
@njit(parallel=True)
def worker(pres, tmpc, hght, dwpc, wspd, wdir, vort, SCALARS, VECTORS):
    """
    While numba massively speeds up our computations, we're limited in how we store and
    process our data. A dictionary registry of parameter calculations doesn't work, so
    instead, embed specific if blocks (CASE?) to direct our workflow appropriately, while
    maintaining some degree of expandability to different parameters. This isn't ideal,
    however.

    Parameters:
    -----------
    pres: array_like
        Array of pressure values (MB) [z,y,x]
    tmpc: array_like
        Array of temperature values (C) [z,y,x]
    hght: array_like
        Array of geopotential height values (m) [z,y,x]
    dwpc: array_like
        Array of dewpoint values (C) [z,y,x]
    wspd: array_like
        Array of wind speed values (KTS) [z,y,x]
    wdir: array_like
        Array of wind direction values (DEG) [z,y,x]
    vort: array_like
        Array of vertical vorticity values (s-1) at the surface [y,x]
    SCALARS: Numba typed List
        Scalar parameter keys, passed in from SCALAR_PARAMS in the config file
    VECTORS: Numba typed List
        Vector parameter keys, passed in from VECTOR_PARAMS in the config file

    Returns:
    --------
    d : Numba typed Dictionary
        Dictionary containing the derived values. [Key,j,i]

    """

    # Declare 'jit-able' dictionary and fill it with empty arrays
    d = Dict.empty(
        key_type=types.unicode_type,
        value_type=float_array,
    )
    for scalar in SCALARS:
        d[scalar] = np.zeros((tmpc.shape[1], tmpc.shape[2]), dtype='float64')
    for vector in VECTORS:
        d[vector+'_u'] = np.zeros((tmpc.shape[1], tmpc.shape[2]), dtype='float64')
        d[vector+'_v'] = np.zeros((tmpc.shape[1], tmpc.shape[2]), dtype='float64')

    for j in prange(tmpc.shape[1]):
        for i in prange(tmpc.shape[2]):
            prof = profile.create_profile(pres=pres[:,j,i], tmpc=tmpc[:,j,i],
                                          hght=hght[:,j,i], dwpc=dwpc[:,j,i],
                                          wspd=wspd[:,j,i], wdir=wdir[:,j,i])

            # Compile the big jitted methods. This will slow down the very 1st iteration.
            mlpcl = params.parcelx(prof, flag=4)
            eff_inflow = params.effective_inflow_layer(prof)
            mupcl = params.parcelx(prof, flag=3)    
            
            # Scalars
            if ('fzl-lfc-diff' in SCALARS) and ('el-lfc-diff' in SCALARS) and \
                ('mu-el' in SCALARS):
                hail = derived.hail_parms(prof, mupcl) 
                d['mu-el'][j,i], d['el-lfc-diff'][j,i], d['fzl-lfc-diff'][j,i] = hail 
            if 'esrh' in SCALARS:
                d['esrh'][j,i] = derived.srh(prof, effective_inflow_layer=eff_inflow)
            if 'mucape' in SCALARS:
                d['mucape'][j,i] = mupcl.bplus
            if 'mlcin' in SCALARS:
                d['mlcin'][j,i] = mlpcl.bminus * -1
            if 'mlcape' in SCALARS:
                d['mlcape'][j,i] = mlpcl.bplus
            if 'cape3km' in SCALARS:
                d['cape3km'][j,i] = mlpcl.b3km
            if 'srh500' in SCALARS:
                d['srh500'][j,i] = derived.srh(prof, lower=0, upper=500)
            if 'srh01km' in SCALARS:
                d['srh01km'][j,i] = derived.srh(prof, lower=0, upper=1000)
            if 'lr03km' in SCALARS:
                d['lr03km'][j,i] = derived.lapse_rate(prof, lower=0, upper=3000)
            if 'mllcl' in SCALARS:
                d['mllcl'][j,i] = mlpcl.lclhght
            if 'snsq' in SCALARS:
                d['snsq'][j,i] = derived.snsq(prof)

            # Vectors: returned as (u, v) tuples
            if 'ebwd' in VECTORS:
                d['ebwd_u'][j,i], d['ebwd_v'][j,i] = derived.ebwd(prof, mupcl, eff_inflow)
            if 'shr1' in VECTORS:
                d['shr1_u'][j,i], d['shr1_v'][j,i] = derived.bulk_shear(prof, height=1000)
            if 'shr3' in VECTORS:
                d['shr3_u'][j,i], d['shr3_v'][j,i] = derived.bulk_shear(prof, height=3000)
            if 'shr6' in VECTORS:
                d['shr6_u'][j,i], d['shr6_v'][j,i] = derived.bulk_shear(prof, height=6000)
            if 'shr8' in VECTORS:
                d['shr8_u'][j,i], d['shr8_v'][j,i] = derived.bulk_shear(prof, height=8000)
            if 'rm5' in VECTORS:
                d['rm5_u'][j,i], d['rm5_v'][j,i] = derived.rm5(prof)
            if 'lm5' in VECTORS:
                d['lm5_u'][j,i], d['lm5_v'][j,i] = derived.lm5(prof)
            if 'devtor' in VECTORS:
                devtor = derived.devtor(prof)
                d['devtor_u'][j,i], d['devtor_v'][j,i], d['deviance'][j,i] = devtor

            # Special parameters: prohibitive to re-compute all of the inputs...
            if 'estp' in SCALARS: d['estp'][j,i] = derived.estp(d['mlcape'][j,i],
                                                                mlpcl.bminus,
                                                                d['esrh'][j,i],
                                                                d['ebwd_u'][j,i],
                                                                d['ebwd_v'][j,i],
                                                                mlpcl, eff_inflow[0],
                                                                prof)
            if 'nst' in SCALARS: d['nst'][j,i] = derived.nst(d['cape3km'][j,i],
                                                             d['mlcin'][j,i], vort[j,i],
                                                             prof)
    return d

def sharppy_calcs(**kwargs):
    """
    Perform the parcel lifting and calculations. Leverages numba's automatic parallel
    processing and prange.

    """
    set_num_threads(NUM_THREADS)

    tmpc = kwargs.get('tmpc')
    dwpc = kwargs.get('dwpc')
    hght = kwargs.get('hght')
    wdir = kwargs.get('wdir')
    wspd = kwargs.get('wspd')
    pres = kwargs.get('pres')
    lons = kwargs.get('lons')
    lats = kwargs.get('lats')

    # Vorticity calculations for NST parameter. 0th index from hybrid files is ~10m agl.
    u, v = vec2comp(wdir[0,:,:], wspd[0,:,:]*KTS2MS)
    vort = derived.vorticity(u, v, lons, lats)

    # Convert list of dictionary keys to numba typed list.
    ret = worker(pres, tmpc, hght, dwpc, wspd, wdir, vort, List(SCALAR_PARAMS.keys()),
                 List(VECTOR_PARAMS.keys()))

    # Converison back to a 'normal' Python dictionary
    output = {}
    for k, v in ret.items(): output[k] = v
    return output
