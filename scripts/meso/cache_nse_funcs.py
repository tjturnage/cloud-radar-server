import pickle
from numba import set_num_threads
from calc import derived
from sharptab.winds import vec2comp
from sharptab.constants import KTS2MS
from calc.compute import worker 

from numba.typed import List
from plotconfigs import SCALAR_PARAMS, VECTOR_PARAMS
from time import time

if __name__ == '__main__':
    set_num_threads(4)
    fname = '../../tests/standard.pickle'
    with open(fname, 'rb') as f: data = pickle.load(f)

    pres = data['pres']
    tmpc = data['tmpc']
    dwpc = data['dwpc']
    wspd = data['wspd']
    wdir = data['wdir']
    hght = data['hght']
    lons = data['lons']
    lats = data['lats']

    # Vorticity calculations for NST parameter. 0th index from hybrid files is ~10m agl.
    u, v = vec2comp(wdir[0,:,:], wspd[0,:,:]*KTS2MS)
    vort = derived.vorticity(u, v, lons, lats)

    t1 = time()
    results = worker(pres, tmpc, hght, dwpc, wspd, wdir, vort, 
                     List(SCALAR_PARAMS.keys()), List(VECTOR_PARAMS.keys()))
    t2 = time()
    results = worker(pres, tmpc, hght, dwpc, wspd, wdir, vort,
                     List(SCALAR_PARAMS.keys()), List(VECTOR_PARAMS.keys()))
    t3 = time()

    print("=====================================")
    print(f"Slow compilation loop 1: {t2-t1} seconds")
    print(f"Fast loop 2: {t3-t2} seconds")
    