"""Functions used during the parameter calculation steps. See calc.compute and the
`worker` function for specifics.
"""

from numba import njit
import numpy as np

from sharptab.constants import MS2KTS, KTS2MS
import sharptab.interp as interp
import sharptab.winds as winds
import sharptab.utils as utils
import sharptab.params as params
import sharptab.thermo as thermo
from calc.vector import transform

@njit
def hail_parms(prof, mupcl):
    """
    Compute additional hail parameters for Nixon, Kumjian, and Fowle research.
    """
    hght0c = interp.hght(prof, params.temp_lvl(prof, 0.))

    # mupcl.lfchght is -99 if undef. Deal with negative values here. 
    if mupcl.lfchght > 0:
        el_lfc_diff = mupcl.elhght - mupcl.lfchght
        fzl_lfc_diff = hght0c - mupcl.lfchght
    else:
        el_lfc_diff = -99.
        fzl_lfc_diff = -99.
    return mupcl.elhght, el_lfc_diff, fzl_lfc_diff

@njit
def snsq(prof):
    """
    Compute the Snow Squall Parameter
    """
    pbot = interp.pres(prof, interp.to_msl(prof, 2.))
    ptop = interp.pres(prof, interp.to_msl(prof, 2000.))

    # 2m wetbulb temperature for masking 
    p2m = interp.pres(prof, interp.to_msl(prof, 2.))
    tw = interp.generic_interp_pres(np.log10(p2m), prof.logp[::-1], prof.wetbulb[::-1])

    # Don't perform any calculations if wetbulb is too warm
    snsq = 0. 
    if tw <= 1:

        # 0-2 km mean RH
        dp = -1
        p = np.arange(pbot, ptop+dp, dp)
        rh = interp.generic_interp_pres(np.log10(p), prof.logp[::-1], prof.relh[::-1])
        mean_rh = utils.weighted_average(rh, p)
        A = (mean_rh - 60.) / 15.

        # 0-2 km theta-e delta
        t1 = interp.generic_interp_pres(np.log10(pbot), prof.logp[::-1], prof.thetae[::-1])
        t2 = interp.generic_interp_pres(np.log10(ptop), prof.logp[::-1], prof.thetae[::-1])
        B = (4. - (t2 - t1)) / 4.

        # 0-2 km mean wind speed (prof object stores in knots, not m/s)
        C = winds.mean_wind(prof, pbot=pbot, ptop=ptop)
        mean_windspd = np.sqrt(np.square(C[0]) + np.square(C[1]))
        C = mean_windspd / 17.4946    

        if A >= 0 and B >= 0:
            snsq = A * B * C
    
    # Seems like the snowsquall parameter is capped online. 
    snsq = np.clip(snsq, 0, 5.4)
    return snsq

@njit
def nst(cape3km, mlcin, vort, prof):
    u, v = bulk_shear(prof, height=6000)
    shear = np.sqrt(u*u + v*v)
    gamma = lapse_rate(prof, lower=0, upper=1000)

    # The profile object has winds in kts, so bulk_shear method returns kts. Altered shear
    # term coefficients to match
    nst = (gamma/9) * (cape3km/100) * ((225-mlcin)/200) * ((34.9892-shear)/9.71922) * \
          (vort/8e-5)
    return nst

def vorticity(u, v, longitude, latitude):
    """
    Compute the relative vertical vorticity

    Parameters:
    -----------
    u: array_like
        Wind components (m/s) in the x-direction
    v: array_like
        Wind components (m/s) in the y-direction
    longitude: array_like
        Grid of longitudes
    latitude: array_like
        Grid of latitudes

    Returns:
    --------
    vorticity: array_like
        Vertical vorticity (s-1)

    """
    from sharptab.thermo import lat_lon_grid_deltas, first_derivative

    dx, dy = lat_lon_grid_deltas(longitude, latitude)
    dudy = first_derivative(u, delta=dy, axis=-2)
    dvdx = first_derivative(v, delta=dx, axis=-1)
    return np.asarray(dvdx - dudy)

@njit
def lapse_rate(prof, lower=0, upper=3000):
    """
    Compute the lapse rate between two layers.

    Parameters:
    -----------
    prof: SHARPpy Profile object
    lower: number (optional; default 0)
        Bottom layer (m) for lapse rate calculation.
    upper: number (optional; default 0)
        Top layer (m) for lapse rate calculation.

    Returns:
    --------
    gamma: number
        Lapse rate compute between top and bottom layers (C/km)

    """
    z1 = interp.to_msl(prof, lower)
    z2 = interp.to_msl(prof, upper)
    p1 = interp.pres(prof, z1)
    p2 = interp.pres(prof, z2)
    tv1 = interp.vtmp(prof, p1)
    tv2 = interp.vtmp(prof, p2)
    return (tv2 - tv1) / (z2 - z1) * -1000.

@njit
def srh(prof, lower=None, upper=None, effective_inflow_layer=None):
    """
    Compute storm-relative helicity.

    Parameters:
    -----------
    prof: SHARPpy Profile object
    lower: number (optional; default None)
        Bottom layer (m) for SRH calculation
    upper: number (optional; default None)
        Top layer (m) for SRH calculation
    effective_inflow_layer: array_like, tuple, or list (optional, default None)
        Bottom and Top (in mb) of the effective inflow layer

    Returns:
    --------
    srh: number
        Storm-relative helicity value (m2/s2)

    """
    RM5 = rm5(prof)
    if effective_inflow_layer is not None:
        ebot = interp.to_agl(prof, interp.hght(prof, effective_inflow_layer[0]))
        etop = interp.to_agl(prof, interp.hght(prof, effective_inflow_layer[1]))
        srh = winds.helicity(prof, ebot, etop, stu=RM5[0], stv=RM5[1])[0]
    elif lower is not None and upper is not None:
        srh = winds.helicity(prof, lower, upper, stu=RM5[0], stv=RM5[1])[0]
    return srh

@njit
def estp(mlcape, mlcin, esrh, ebwd_u, ebwd_v, mlpcl, eff_inflow_base, prof):
    eshr = utils.mag(ebwd_u, ebwd_v)
    estp = params.stp_cin(mlcape, esrh, eshr*KTS2MS, mlpcl.lclhght, mlcin)

    ebot = interp.to_agl(prof, interp.hght(prof, eff_inflow_base))
    if ebot > 10 or ~np.isfinite(ebot): estp = 0.
    return estp

@njit
def devtor(prof):
    """
    Deviant tornado motion following Cameron Nixon's work:
    https://journals.ametsoc.org/view/journals/wefo/36/1/WAF-D-20-0056.1.xml

    Updates: Email correspondence on 5/10 to create tornado "deviance" (i.e. how deviant
    could these deviant motions be?)

    """
    # Deviant tornado motion
    sfc = prof.pres[prof.sfc]
    A = winds.mean_wind(prof, pbot=sfc, ptop=interp.pres(prof, interp.to_msl(prof, 300)))
    RM5 = rm5(prof)
    u_tor = 0.5 * (A[0] + RM5[0])
    v_tor = 0.5 * (A[1] + RM5[1])

    # Storm motion (Bunkers right for now):
    u_sr = u_tor - RM5[0]
    v_sr = v_tor - RM5[1]
    storm_relative_deviance = np.sqrt(np.square(u_sr) + np.square(v_sr))
    tornado_speed = np.sqrt(np.square(u_tor) + np.square(v_tor))
    storm_speed = np.sqrt(np.square(RM5[0]) + np.square(RM5[1]))
    deviance = (storm_relative_deviance) / ((tornado_speed + storm_speed) / 2)

    return (u_tor, v_tor, deviance)

@njit
def lm5(prof):
    sfc = prof.pres[prof.sfc]
    A = winds.mean_wind(prof, pbot=sfc, ptop=interp.pres(prof, interp.to_msl(prof, 500.)))
    B = winds.mean_wind(prof, pbot=interp.pres(prof, interp.to_msl(prof, 5500.)),
                        ptop=interp.pres(prof, interp.to_msl(prof, 6000.)))
    blkshr_u = B[0] - A[0]
    blkshr_v = B[1] - A[1]

    p6km = interp.pres(prof, interp.to_msl(prof, 6000.))
    mean_u, mean_v = winds.mean_wind(prof, pbot=sfc,ptop=p6km)

    temp = transform(blkshr_u, blkshr_v, 0., 5.0*MS2KTS, -5.0*MS2KTS, 0.)
    BlkMag = np.hypot(blkshr_u, blkshr_v)

    u = mean_u - (temp[0]/BlkMag)
    v = mean_v  - (temp[1]/BlkMag)
    return (u, v)

@njit
def rm5(prof):
    sfc = prof.pres[prof.sfc]
    A = winds.mean_wind(prof, pbot=sfc, ptop=interp.pres(prof, interp.to_msl(prof, 500.)))
    B = winds.mean_wind(prof, pbot=interp.pres(prof, interp.to_msl(prof, 5500.)),
                        ptop=interp.pres(prof, interp.to_msl(prof, 6000.)))
    blkshr_u = B[0] - A[0]
    blkshr_v = B[1] - A[1]

    p6km = interp.pres(prof, interp.to_msl(prof, 6000.))
    mean_u, mean_v = winds.mean_wind(prof, pbot=sfc,ptop=p6km)

    temp = transform(blkshr_u, blkshr_v, 0., 7.5*MS2KTS, -7.5*MS2KTS, 0.)
    BlkMag = np.hypot(blkshr_u, blkshr_v)

    u = mean_u + (temp[0]/BlkMag)
    v = mean_v  + (temp[1]/BlkMag)
    return (u, v)

@njit
def bulk_shear(prof, height=1000):
    sfc = prof.pres[prof.sfc]
    hght = interp.pres(prof, interp.to_msl(prof, height))
    u, v = winds.wind_shear(prof, pbot=sfc, ptop=hght)
    return (u, v)

@njit
def ebwd(prof, mupcl, eff_inflow):
    ebot_hght = interp.to_agl(prof, interp.hght(prof, eff_inflow[0]))
    height_top = (mupcl.elhght + ebot_hght) / 2.
    ptop = interp.pres(prof, interp.to_msl(prof, height_top))
    u, v = winds.wind_shear(prof, pbot=eff_inflow[0], ptop=ptop)
    if ~np.isfinite(u): u = 0.
    if ~np.isfinite(v): v = 0.
    return (u, v)

@njit 
def dcape(prof):    
    sfc_pres = prof.pres[prof.sfc]
    pres = prof.pres
    hght = prof.hght
    #dwpc = prof.dwpc
    tmpc = prof.tmpc
    idx = np.where(pres >= sfc_pres - 400.)[0]

    # Find the minimum average theta-e in a 100 mb layer
    mine = 1000.0
    minp = -999.0
    for i in idx:
        thta_e_mean = params.mean_thetae(prof, pbot=pres[i], ptop=pres[i]-100.)
        if thta_e_mean < mine:
            minp = pres[i] - 50.
            mine = thta_e_mean

    upper = minp
    uptr = np.where(pres >= upper)[0]
    uptr = uptr[-1]
    
    # Define parcel starting point
    tp1 = thermo.wetbulb(upper, interp.temp(prof, upper), interp.dwpt(prof, upper))
    pe1 = upper
    te1 = interp.temp(prof, pe1)
    h1 = interp.hght(prof, pe1)
    tote = 0
    lyre = 0

    # To keep track of the parcel trace from the downdraft
    #ttrace = [tp1] 
    #ptrace = [upper]

    # Lower the parcel to the surface moist adiabatically and compute
    # total energy (DCAPE)
    iter_ranges = range(uptr, -1, -1)
    ttraces = np.zeros(len(iter_ranges))
    ptraces = np.zeros(len(iter_ranges))
    for i in iter_ranges:
        pe2 = pres[i]
        te2 = tmpc[i]
        h2 = hght[i]
        tp2 = thermo.wetlift3(pe1, tp1, pe2)

        #if utils.QC(te1) and utils.QC(te2):
        tdef1 = (tp1 - te1) / (thermo.ctok(te1))
        tdef2 = (tp2 - te2) / (thermo.ctok(te2))
        lyrlast = lyre
        lyre = 9.8 * (tdef1 + tdef2) / 2.0 * (h2 - h1)
        tote += lyre

        ttraces[i] = tp2
        ptraces[i] = pe2

        pe1 = pe2
        te1 = te2
        h1 = h2
        tp1 = tp2
    #drtemp = tp2 # Downrush temp in Celsius

    return tote
