from numba import njit
import numpy as np
from scipy import spatial

def nearest_idx(points, lon, lat):
    """Searches for the nearest grid point using a KDTree

    Parameters
    ----------
    points : list
        List of lists indicating lon/lat pais: [[LON1, LAT1], [LON2, LAT2]]
    lat : np.array
        2-d array of gridded latitudes
    lon : np.arrat
        2-d array of gridded longitudes
    """

    lonlat = np.column_stack((lon.ravel(), lat.ravel()))
    tree = spatial.cKDTree(lonlat)
    dist, idx = tree.query(points, k=1)
    ind = np.column_stack(np.unravel_index(idx, lon.shape))
    return [(j,i) for j,i in ind]

@njit
def pres(prof, h):
    """Interpolates the given data to calculate a pressure at a given height

    Parameters
    ----------
    prof : profile object
        Profile object
    h : number, numpy array
        Height (m) of the level for which pressure is desired

    Returns
    -------
    Pressure (hPa) at the given height : number, numpy array
    """
    return generic_interp_hght(h, prof.hght, prof.logp, log=True)

@njit
def components(prof, p):
    """Interpolates the data to calculate the U and V components at a given pressure

    Parameters
    ----------
    prof : profile object
        Profile object
    p : number, numpy array
        Pressure (hPa) of a level

    Returns
    -------
    U and V components at the given pressure (kts) : number, numpy array
    """
    # Note: numpy's interpoloation routine expects the interpolation
    # routine to be in ascending order. Because pressure decreases in the
    # vertical, we must reverse the order of the two arrays to satisfy
    # this requirement.
    U = generic_interp_pres(np.log10(p), prof.logp[::-1], prof.u[::-1])
    V = generic_interp_pres(np.log10(p), prof.logp[::-1], prof.v[::-1])
    return U, V

@njit
def to_msl(prof, h):
    """Convert a height from above ground-level (AGL) to mean sea-level (MSL)

    Parameters
    ----------
    h : number, numpy array
        Height of a level
    prof : profile object
        Profile object

    Returns
    -------
    Converted height (m MSL) : number, numpy array
    """
    return h + prof.hght[prof.sfc]

@njit
def to_agl(prof, h):
    """Convert a height from mean sea-level (MSL) to above ground-level (AGL)

    Parameters
    ----------
    h : number, numpy array
        Height of a level
    prof : profile object
        Profile object

    Returns
    -------
    Converted height (m AGL) : number, numpy array
    """
    return h - prof.hght[prof.sfc]

@njit
def dwpt(prof, p):
    """Interpolates the data to calculate a dew point temperatureat a given pressure

    Parameters
    ----------
    prof : profile object
        Profile object
    p : number, numpy array
        Pressure (hPa) of the level for which dew point temperature is desired

    Returns
    -------
    Dew point tmperature (C) at the given pressure : number, numpy array
    """
    # Note: numpy's interpoloation routine expects the interpolation
    # routine to be in ascending order. Because pressure decreases in the
    # vertical, we must reverse the order of the two arrays to satisfy
    # this requirement.
    return generic_interp_pres(np.log10(p), prof.logp[::-1], prof.dwpc[::-1])

@njit
def temp(prof, p):
    """Interpolates the given data to calculate a temperature at a given pressure

    Parameters
    ----------
    prof : profile object
        Profile object
    p : number, numpy array
        Pressure (hPa) of the level for which temperature is desired

    Returns
    -------
    Temperature (C) at the given pressure : number, numpy array
    """
    # Note: numpy's interpoloation routine expects the interpolation
    # routine to be in ascending order. Because pressure decreases in the
    # vertical, we must reverse the order of the two arrays to satisfy
    # this requirement.
    return generic_interp_pres(np.log10(p), prof.logp[::-1], prof.tmpc[::-1])

@njit
def hght(prof, p):
    """Interpolates the given data to calculate a height at a given pressure

    Parameters
    ----------
    prof : profile object
        Profile object
    p : number, numpy array
        Pressure (hPa) of the level for which height is desired

    Returns
    -------
    Height (m) at the given pressure : number, numpy array
    """
    # Note: numpy's interpoloation routine expects the interpolation
    # routine to be in ascending order. Because pressure decreases in the
    # vertical, we must reverse the order of the two arrays to satisfy
    # this requirement.
    return generic_interp_pres(np.log10(p), prof.logp[::-1], prof.hght[::-1])

@njit
def vtmp(prof, p):
    """Interpolates the data to calculate a virtual temperature at a given pressure

    Parameters
    ----------
    prof : profile object
        Profile object
    p : number, numpy array
        Pressure (hPa) of the level for which virtual temperature is desired

    Returns
    -------
    Virtual tmperature (C) at the given pressure : number, numpy array
    """
    return generic_interp_pres(np.log10(p), prof.logp[::-1], prof.vtmp[::-1])

@njit
def generic_interp_hght(h, hght, field, log=False):
    """Generic interpolation routine

    Parameters
    ----------
    h : number, numpy array
        Height (m) of the level for which pressure is desired
    hght : numpy array
        The array of heights
    field : numpy array
        The variable which is being interpolated
    log : bool
        Flag to determine whether the 'field' variable is in log10 space

    Returns
    -------
    Value of the 'field' variable at the given height : number, numpy array
    """
    field_intrp = np.interp(h, hght, field)
    if log:
        return 10 ** field_intrp
    else:
        return field_intrp

@njit
def generic_interp_pres(p, pres, field):
    """Generic interpolation routine

    Parameters
    ----------
    p : number, numpy array
        Pressure (hPa) of the level for which the field variable is desired
    pres : numpy array
        The array of pressure
    field : numpy array
        The variable which is being interpolated
    log : bool
        Flag to determine whether the 'field' variable is in log10 space

    Returns
    -------
    Value of the 'field' variable at the given pressure : number, numpy array
    """
    not_masked1 = np.ones(pres.shape)
    not_masked1[:] = True

    not_masked2 = np.ones(field.shape)
    not_masked2[:] = True
    not_masked = not_masked1 * not_masked2
    field_intrp = np.interp(p, pres, field)
    return field_intrp
