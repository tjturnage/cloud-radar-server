""" Wind Manipulation Routines """
import numpy as np
from numba import njit
from sharptab import interp, utils
from sharptab.constants import *

def vec2comp(wdir, wspd):
    u = -wspd * np.sin(np.radians(wdir))
    v = -wspd * np.cos(np.radians(wdir))
    return u, v

def comp2vec(u, v):
    vmag = np.hypot(u, v)
    vdir = 90 - np.degrees(np.arctan2(-v, -u))
    vdir = np.where(vdir < 0, vdir + 360, vdir)
    vdir = np.where(vdir >= 360, vdir - 360, vdir)
    return vdir, vmag

def wind_vecs(u, v):
    wdir = wind_direction(u, v)
    wspd = wind_speed(u, v)
    return wdir, wspd

def wind_direction(u, v):
    """Convert U, V components into direction and magnitude

    Parameters
    ----------
    u : number, array_like
        U-component of the wind
    v : number, array_like
        V-component of the wind

    Returns
    -------
    wdir : number, array_like (same as input)
        Angle in meteorological degrees
    """
    wdir = np.degrees(np.arctan2(-u, -v))
    wdir[wdir < 0] += 360
    wdir[np.fabs(wdir) < TOL] = 0.0
    return wdir

def wind_speed(u, v):
    """Compute the wind speed from u and v-components.
    """
    speed = np.sqrt(u ** 2 + v ** 2)
    return speed

@njit
def mean_wind(prof, pbot=850, ptop=250, dp=-1, stu=0, stv=0):
    """Calculates a pressure-weighted mean wind through a layer. The default layer is
    850 to 200 hPa.

    Parameters
    ----------
    prof: profile object
        Profile object
    pbot : number (optional; default 850 hPa)
        Pressure of the bottom level (hPa)
    ptop : number (optional; default 250 hPa)
        Pressure of the top level (hPa)
    dp : negative integer (optional; default -1)
        The pressure increment for the interpolated sounding
    stu : number (optional; default 0)
        U-component of storm-motion vector (kts)
    stv : number (optional; default 0)
        V-component of storm-motion vector (kts)

    Returns
    -------
    mnu : number
        U-component (kts)
    mnv : number
        V-component (kts)
    """
    if dp > 0:
        dp = -dp
    ps = np.arange(pbot, ptop + dp, dp)
    u, v = interp.components(prof, ps)
    # u -= stu; v -= stv

    mnu = utils.weighted_average(u, ps) - stu
    mnv = utils.weighted_average(v, ps) - stv
    return mnu, mnv

@njit
def wind_shear(prof, pbot=850, ptop=250):
    """Calculates the shear between the wind at (pbot) and (ptop).

    Parameters
    ----------
    prof: profile object
        Profile object
    pbot : number (optional; default 850 hPa)
        Pressure of the bottom level (hPa)
    ptop : number (optional; default 250 hPa)
        Pressure of the top level (hPa)

    Returns
    -------
    shu : number
        U-component (kts)
    shv : number
        V-component (kts)
    """
    ubot, vbot = interp.components(prof, pbot)
    utop, vtop = interp.components(prof, ptop)
    shu = utop - ubot
    shv = vtop - vbot
    return shu, shv

@njit
def helicity(prof, lower, upper, stu=0, stv=0, dp=-1, exact=True):
    """Calculates the relative helicity (m2/s2) of a layer from lower to upper. If
    storm-motion vector is supplied, storm-relative helicity, both positve and negative,
    is returned.

    Parameters
    ----------
    prof : profile object
        Profile Object
    lower : number
        Bottom level of layer (m, AGL)
    upper : number
        Top level of layer (m, AGL)
    stu : number (optional; default = 0)
        U-component of storm-motion (kts)
    stv : number (optional; default = 0)
        V-component of storm-motion (kts)
    dp : negative integer (optional; default -1)
        The pressure increment for the interpolated sounding (mb)
    exact : bool (optional; default = True)
        Switch to choose between using the exact data (slower) or using
        interpolated sounding at 'dp' pressure levels (faster)

    Returns
    -------
    phel+nhel : number
        Combined Helicity (m2/s2)
    phel : number
        Positive Helicity (m2/s2)
    nhel : number
        Negative Helicity (m2/s2)
    """
    if lower != upper:
        lower = interp.to_msl(prof, lower)
        upper = interp.to_msl(prof, upper)
        plower = interp.pres(prof, lower)
        pupper = interp.pres(prof, upper)
        if np.isnan(plower) or np.isnan(pupper):
            return -999.0, -999.0, -999.0

        if exact:
            ind1 = np.where(plower >= prof.pres)[0].min()
            ind2 = np.where(pupper <= prof.pres)[0].max()
            u1, v1 = interp.components(prof, plower)
            u2, v2 = interp.components(prof, pupper)
            u_temp = prof.u[ind1 : ind2 + 1]
            u_temp = u_temp[~np.isnan(u_temp)]
            v_temp = prof.v[ind1 : ind2 + 1]
            v_temp = v_temp[~np.isnan(v_temp)]
            u = ()
            u = np.append(u, u1)
            u = np.append(u, u_temp)
            u = np.append(u, u2)
            v = ()
            v = np.append(v, v1)
            v = np.append(v, v_temp)
            v = np.append(v, v2)
        else:
            ps = np.arange(plower, pupper + dp, dp)
            u, v = interp.components(prof, ps)
        sru = utils.KTS2MS(u - stu)
        srv = utils.KTS2MS(v - stv)
        layers = (sru[1:] * srv[:-1]) - (sru[:-1] * srv[1:])
        phel = layers[layers > 0].sum()
        nhel = layers[layers < 0].sum()
    else:
        phel = nhel = 0
    return phel + nhel, phel, nhel
