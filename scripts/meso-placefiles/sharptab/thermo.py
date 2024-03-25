from numba import njit
from numba import float64
from numba import vectorize

import numpy as np
from numpy.core.numeric import normalize_axis_index
from .constants import *

from utils.timing import timeit
from time import time

sat_pressure_0c = 6.112
c1 = 0.0498646455
c2 = 2.4082965
c3 = 7.07475
c4 = 38.9114
c5 = 0.0915
c6 = 1.2035

########################################################################################
#
# SOME KINEMATIC AND THERMODYNAMIC FUNCTIONS  FROM SHARPY.SHARPTAB.THERMO
# AND METPY.
#
########################################################################################
def lat_lon_grid_deltas(longitude, latitude, **kwargs):
    """Calculate the delta between grid points that are in a latitude/longitude
    format.

    Calculate the signed delta distance between grid points when the grid spacing is
    defined by delta lat/lon rather than delta x/y

    Parameters
    ----------
    longitude : array_like
        array of longitudes defining the grid
    latitude : array_like
        array of latitudes defining the grid
    kwargs
        Other keyword arguments to pass to :class:`~pyproj.Geod`

    Returns
    -------
    dx, dy:
        at least two dimensional arrays of signed deltas between grid points in the x
        and y direction

    Notes
    -----
    Accepts 1D, 2D, or higher arrays for latitude and longitude Assumes [..., Y, X]
    for >=2 dimensional arrays
    """
    from pyproj import Geod

    # Inputs must be the same number of dimensions
    if latitude.ndim != longitude.ndim:
        raise ValueError("Lat. and lon. must have the same number of dims.")

    # If we were given 1D arrays, make a mesh grid
    if latitude.ndim < 2:
        longitude, latitude = np.meshgrid(longitude, latitude)

    # pyproj requires ndarrays, not Quantities
    try:
        longitude = longitude.m_as("degrees")
        latitude = latitude.m_as("degrees")
    except AttributeError:
        longitude = np.asarray(longitude)
        latitude = np.asarray(latitude)

    geod_args = {"ellps": "sphere"}
    if kwargs:
        geod_args = kwargs

    g = Geod(**geod_args)

    forward_az, _, dy = g.inv(
        longitude[..., :-1, :],
        latitude[..., :-1, :],
        longitude[..., 1:, :],
        latitude[..., 1:, :],
    )
    dy[(forward_az < -90.0) | (forward_az > 90.0)] *= -1

    forward_az, _, dx = g.inv(
        longitude[..., :, :-1],
        latitude[..., :, :-1],
        longitude[..., :, 1:],
        latitude[..., :, 1:],
    )
    dx[(forward_az < 0.0) | (forward_az > 180.0)] *= -1

    return dx, dy


def divergence(u, v, dx, dy):
    """Calculate the horizontal divergence of a vector.

    Parameters
    ----------
    u : (M, N) `pint.Quantity`
        x component of the vector
    v : (M, N) `pint.Quantity`
        y component of the vector
    dx : `pint.Quantity`
        The grid spacing(s) in the x-direction. If an array, there should be one
        item less than the size of `u` along the applicable axis.
    dy : `pint.Quantity`
        The grid spacing(s) in the y-direction. If an array, there should be one
        item less than the size of `u` along the applicable axis.

    Returns
    -------
    (M, N) `pint.Quantity`
        The horizontal divergence

    See Also
    --------
    vorticity

    Notes
    -----
    If inputs have more than two dimensions, they are assumed to have either
    leading dimensions of (x, y) or trailing dimensions of (y, x), depending on
    the value of ``dim_order``.
    """
    dudx = first_derivative(u, delta=dx, axis=-1)
    dvdy = first_derivative(v, delta=dy, axis=-2)
    return dudx + dvdy

def first_derivative(f, **kwargs):
    """Calculate the first derivative of a grid of values.

    Works for both regularly-spaced data and grids with varying spacing.

    Either `x` or `delta` must be specified, or `f` must be given as an
    `xarray.DataArray` with attached coordinate and projection information. If `f` is
    an `xarray.DataArray`, and `x` or `delta` are given, `f` will be converted to a
    `pint.Quantity` and the derivative returned as a `pint.Quantity`, otherwise, if
    neither `x` nor `delta` are given, the attached coordinate information belonging
    to `axis` will be used and the derivative will be returned as an `xarray.DataArray`.

    This uses 3 points to calculate the derivative, using forward or backward at the
    edges of the grid as appropriate, and centered elsewhere. The irregular spacing is
    handled explicitly, using the formulation as specified by [Bowen2005]_.

    Parameters
    ----------
    f : array-like
        Array of values of which to calculate the derivative
    axis : int or str, optional
        The array axis along which to take the derivative. If `f` is ndarray-like, must
        be an integer. If `f` is a `DataArray`, can be a string (referring to either the
        coordinate dimension name or the axis type) or integer (referring to axis
        number), unless using implicit conversion to `pint.Quantity`, in which case it
        must be an integer. Defaults to 0.
    x : array-like, optional
        The coordinate values corresponding to the grid points in `f`.
    delta : array-like, optional
        Spacing between the grid points in `f`. Should be one item less than the size of
        `f` along `axis`.

    Returns
    -------
    array-like
        The first derivative calculated along the selected axis.

    See Also
    --------
    second_derivative
    """
    n, axis, delta = _process_deriv_args(f, kwargs)

    # create slice objects --- initially all are [:, :, ..., :]
    slice0 = [slice(None)] * n
    slice1 = [slice(None)] * n
    slice2 = [slice(None)] * n
    delta_slice0 = [slice(None)] * n
    delta_slice1 = [slice(None)] * n

    # First handle centered case
    slice0[axis] = slice(None, -2)
    slice1[axis] = slice(1, -1)
    slice2[axis] = slice(2, None)
    delta_slice0[axis] = slice(None, -1)
    delta_slice1[axis] = slice(1, None)

    combined_delta = delta[tuple(delta_slice0)] + delta[tuple(delta_slice1)]
    delta_diff = delta[tuple(delta_slice1)] - delta[tuple(delta_slice0)]
    center = (
        -delta[tuple(delta_slice1)]
        / (combined_delta * delta[tuple(delta_slice0)])
        * f[tuple(slice0)]
        + delta_diff
        / (delta[tuple(delta_slice0)] * delta[tuple(delta_slice1)])
        * f[tuple(slice1)]
        + delta[tuple(delta_slice0)]
        / (combined_delta * delta[tuple(delta_slice1)])
        * f[tuple(slice2)]
    )

    # Fill in "left" edge with forward difference
    slice0[axis] = slice(None, 1)
    slice1[axis] = slice(1, 2)
    slice2[axis] = slice(2, 3)
    delta_slice0[axis] = slice(None, 1)
    delta_slice1[axis] = slice(1, 2)

    combined_delta = delta[tuple(delta_slice0)] + delta[tuple(delta_slice1)]
    big_delta = combined_delta + delta[tuple(delta_slice0)]
    left = (
        -big_delta / (combined_delta * delta[tuple(delta_slice0)]) * f[tuple(slice0)]
        + combined_delta
        / (delta[tuple(delta_slice0)] * delta[tuple(delta_slice1)])
        * f[tuple(slice1)]
        - delta[tuple(delta_slice0)]
        / (combined_delta * delta[tuple(delta_slice1)])
        * f[tuple(slice2)]
    )

    # Now the "right" edge with backward difference
    slice0[axis] = slice(-3, -2)
    slice1[axis] = slice(-2, -1)
    slice2[axis] = slice(-1, None)
    delta_slice0[axis] = slice(-2, -1)
    delta_slice1[axis] = slice(-1, None)

    combined_delta = delta[tuple(delta_slice0)] + delta[tuple(delta_slice1)]
    big_delta = combined_delta + delta[tuple(delta_slice1)]
    right = (
        delta[tuple(delta_slice1)]
        / (combined_delta * delta[tuple(delta_slice0)])
        * f[tuple(slice0)]
        - combined_delta
        / (delta[tuple(delta_slice0)] * delta[tuple(delta_slice1)])
        * f[tuple(slice1)]
        + big_delta / (combined_delta * delta[tuple(delta_slice1)]) * f[tuple(slice2)]
    )

    return np.concatenate((left, center, right), axis=axis)


def _process_deriv_args(f, kwargs):
    """Handle common processing of arguments for derivative functions."""
    n = f.ndim
    axis = normalize_axis_index(kwargs.get("axis", 0), n)

    if f.shape[axis] < 3:
        raise ValueError("f must have at least 3 pts along the desired axis.")

    if "delta" in kwargs:
        if "x" in kwargs:
            raise ValueError('Cannot specify both "x" and "delta".')

        delta = np.atleast_1d(kwargs["delta"])
        if delta.size == 1:
            diff_size = list(f.shape)
            diff_size[axis] -= 1
            delta_units = getattr(delta, "units", None)
            delta = np.broadcast_to(delta, diff_size, subok=True)
            if not hasattr(delta, "units") and delta_units is not None:
                delta = delta * delta_units
        else:
            delta = _broadcast_to_axis(delta, axis, n)
    elif "x" in kwargs:
        x = _broadcast_to_axis(kwargs["x"], axis, n)
        delta = np.diff(x, axis=axis)
    else:
        raise ValueError("Must specify either x or delta for value positions.")
    return n, axis, delta

def _broadcast_to_axis(arr, axis, ndim):
    """Handle reshaping coordinate array to have proper dimensionality.

    This puts the values along the specified axis.
    """
    if arr.ndim == 1 and arr.ndim < ndim:
        new_shape = [1] * ndim
        new_shape[axis] = arr.size
        arr = arr.reshape(*new_shape)
    return arr

def dewpoint_from_q(specific_humidity, temperature, pressure):
    """Calculate the dewpoint from specific humidity, temperature, and pressure.

    Parameters
    ----------
    specific_humidity: `pint.Quantity`
        Specific humidity of air
    temperature: `pint.Quantity`
        Air temperature
    pressure: `pint.Quantity`
        Total atmospheric pressure

    Returns
    -------
    `pint.Quantity`
        Dew point temperature

    See Also
    --------
    relative_humidity_from_mixing_ratio, dewpoint_from_relative_humidity
    """
    return dewpoint_from_rh(
        temperature, rh_from_specific_humidity(specific_humidity, temperature, pressure)
    )

def rh_from_specific_humidity(specific_humidity, temperature, pressure):
    """Calculate the relative humidity from specific humidity, temperature, and
    pressure.

    Parameters
    ----------
    specific_humidity: `pint.Quantity`
        Specific humidity of air
    temperature: `pint.Quantity`
        Air temperature
    pressure: `pint.Quantity`
        Total atmospheric pressure

    Returns
    -------
    `pint.Quantity`
        Relative humidity

    Notes
    -----
    Formula based on that from [Hobbs1977]_ pg. 74. and [Salby1996]_ pg. 118.

    .. math:: RH = \frac{q}{(1-q)w_s}

    * :math:`RH` is relative humidity as a unitless ratio
    * :math:`q` is specific humidity
    * :math:`w_s` is the saturation mixing ratio

    See Also
    --------
    relative_humidity_from_mixing_ratio
    """
    return mixing_ratio_from_specific_humidity(
        specific_humidity
    ) / saturation_mixing_ratio(pressure, temperature)

def mixing_ratio_from_specific_humidity(specific_humidity):
    """Calculate the mixing ratio from specific humidity.

    Parameters
    ----------
    specific_humidity: `pint.Quantity`
        Specific humidity of air

    Returns
    -------
    `pint.Quantity`
        Mixing ratio

    Notes
    -----
    Formula from [Salby1996]_ pg. 118.

    .. math:: w = \frac{q}{1-q}

    * :math:`w` is mixing ratio
    * :math:`q` is the specific humidity

    See Also
    --------
    mixing_ratio, specific_humidity_from_mixing_ratio
    """
    return specific_humidity / (1 - specific_humidity)

def saturation_mixing_ratio(tot_press, temperature):
    """Calculate the saturation mixing ratio of water vapor.

    This calculation is given total pressure and the temperature. The
    implementation uses the formula outlined in [Hobbs1977]_ pg.73.

    Parameters
    ----------
    tot_press: `pint.Quantity`
        Total atmospheric pressure
    temperature: `pint.Quantity`
        air temperature

    Returns
    -------
    `pint.Quantity`
        The saturation mixing ratio, dimensionless

    """
    return mixing_ratio(saturation_vapor_pressure(temperature), tot_press)


def mixing_ratio(part_press, tot_press):
    """Calculate the mixing ratio of a gas.

    This calculates mixing ratio given its partial pressure and the total pressure of
    the air. There are no required units for the input arrays, other than that they have
    the same units.

    Parameters
    ----------
    part_press : `pint.Quantity`
        Partial pressure of the constituent gas
    tot_press : `pint.Quantity`
        Total air pressure
    molecular_weight_ratio : `pint.Quantity` or float, optional
        The ratio of the molecular weight of the constituent gas to that assumed for
        air. Defaults to the ratio for water vapor to dry air
        (:math:`\epsilon\approx0.622`).

    Returns
    -------
    `pint.Quantity`
        The (mass) mixing ratio, dimensionless (e.g. Kg/Kg or g/g)

    Notes
    -----
    This function is a straightforward implementation of the equation given in many
    places, such as [Hobbs1977]_ pg.73:

    .. math:: r = \epsilon \frac{e}{p - e}

    See Also
    --------
    saturation_mixing_ratio, vapor_pressure
    """
    return eps * part_press / (tot_press - part_press)

def rh_from_dewpoint(temperature, dewpt):
    """Calculate the relative humidity.

    Uses temperature and dewpoint in celsius to calculate relative humidity using the
    ratio of vapor pressure to saturation vapor pressures.

    Parameters
    ----------
    temperature : numpy array [Kelvin]
        air temperature
    dewpoint : numpy array [Kelvin]
        dewpoint temperature

    Returns
    -------
    relative humidity [unitless]
    """
    e = saturation_vapor_pressure(dewpt)
    e_s = saturation_vapor_pressure(temperature)
    return e / e_s


# @njit
def dewpoint_from_rh(temperature, rh):
    """Calculate the ambient dewpoint given air temperature and relative humidity."""
    if np.any(rh > 1.2):
        print("Relative humidity >120%, ensure proper units.")
    return dewpoint(rh * saturation_vapor_pressure(temperature))


# @njit
def dewpoint(e):
    """Calculate the ambient dewpoint given the vapor pressure."""
    val = np.log(e / sat_pressure_0c)
    return 243.5 * val / (17.67 - val)


# @njit
def saturation_vapor_pressure(temperature):
    """Calculate the saturation water vapor (partial) pressure."""
    # Converted from original in terms of C to use kelvin. Using raw absolute
    # values of C in a formula plays havoc with units support.
    return sat_pressure_0c * np.exp(
        17.67 * (temperature - 273.15) / (temperature - 29.65)
    )

#@njit
def vapor_pressure(pressure, mixing):
    """Calculate water vapor (partial) pressure.
    Given total `pressure` and water vapor `mixing` ratio, calculates the partial
    pressure of water vapor."""
    return pressure * mixing / (mpconsts.epsilon + mixing)

def equivalent_potential_temperature(pressure, temperature, dewpoint):
    """Calculate equivalent potential temperature.

    This calculation must be given an air parcel's pressure, temperature, and dewpoint.
    The implementation uses the formula outlined in [Bolton1980]_:

    First, the LCL temperature is calculated:

    .. math:: T_{L}=\frac{1}{\frac{1}{T_{D}-56}+\frac{ln(T_{K}/T_{D})}{800}}+56

    Which is then used to calculate the potential temperature at the LCL:

    .. math:: \theta_{DL}=T_{K}\left(\frac{1000}{p-e}\right)^k
              \left(\frac{T_{K}}{T_{L}}\right)^{.28r}

    Both of these are used to calculate the final equivalent potential temperature:

    .. math:: \theta_{E}=\theta_{DL}\exp\left[\left(\frac{3036.}{T_{L}}
                                              -1.78\right)*r(1+.448r)\right]

    Parameters
    ----------
    pressure: numpy array
        Total atmospheric pressure [hPa]
    temperature: numpy array
        Temperature of parcel [C]
    dewpoint: numpy array
        Dewpoint of parcel [C]

    Returns
    -------
    th_e : numpy array
        The equivalent potential temperature of the parcel [Kelvin]

    Notes
    -----
    [Bolton1980]_ formula for Theta-e is used, since according to
    [DaviesJones2009]_ it is the most accurate non-iterative formulation
    available.

    """
    t = temperature + ZEROCNK
    td = dewpoint + ZEROCNK
    p = pressure
    e = saturation_vapor_pressure(td)
    r = saturation_mixing_ratio(p, td)
    t_l = 56 + 1. / (1. / (td - 56) + np.log(t / td) / 800.)
    th_l = t * (1000 / (p - e)) ** ROCP * (t / t_l) ** (0.28 * r)
    th_e = th_l * np.exp((3036. / t_l - 1.78) * r * (1 + 0.448 * r))
    return th_e

########################################################################################
#
# THERMODYNAMIC FUNCTIONS SCRAPED FROM SHARPY.SHARPTAB.THERMO
#
########################################################################################
@njit
def temp_at_mixrat(w, p):
    """Returns the temperature (C) of air at the given mixing ratio (g/kg) and
    pressure (hPa)

    Parameters
    ----------
    w : number, numpy array
        Mixing Ratio (g/kg)
    p : number, numpy array
        Pressure (hPa)

    Returns
    -------
    Temperature (C) of air at given mixing ratio and pressure
    """
    x = np.log10(w * p / (622.0 + w))
    x = (
        np.power(10.0, ((c1 * x) + c2))
        - c3
        + (c4 * np.power((np.power(10, (c5 * x)) - c6), 2))
    ) - ZEROCNK
    return x

@njit
def relh(p, t, td):
    """Returns the virtual temperature (C) of a parcel.

    Parameters
    ----------
    p : number
        The pressure of the parcel (hPa)
    t : number
        Temperature of the parcel (C)
    td : number
        Dew point of parcel (C)

    Returns
    -------
    Relative humidity (%) of a parcel
    """
    return 100.0 * vappres(td) / vappres(t)

@njit
def calc_mixratio(p, t):
    """Returns the mixing ratio (g/kg) of a parcel

    Parameters
    ----------
    p : number, numpy array
        Pressure of the parcel (hPa)
    t : number, numpy array
        Temperature of the parcel (hPa)

    Returns
    -------
    Mixing Ratio (g/kg) of the given parcel
    """
    x = 0.02 * (t - 12.5 + (7500.0 / p))
    wfw = 1.0 + (0.0000045 * p) + (0.0014 * x * x)
    fwesw = wfw * vappres(t)
    return 621.97 * (fwesw / (p - fwesw))

@njit
def calc_thetae(p, t, td):
    """Returns the equivalent potential temperature (C) of a parcel.

    Parameters
    ----------
    p : number
        The pressure of the parcel (hPa)
    t : number
        Temperature of the parcel (C)
    td : number
        Dew point of parcel (C)

    Returns
    -------
    Equivalent potential temperature (C)
    """
    p2, t2 = drylift(p, t, td)
    return theta(100.0, wetlift3(p2, t2, 100.0), 1000.0)

@njit
def ctok(t):
    """Convert temperature from Celsius to Kelvin

    Parameters
    ----------
    t : number, numpy array
        The temperature in Celsius

    Returns
    -------
    Temperature in Kelvin (number or numpy array)
    """
    return t + ZEROCNK

@njit
def calc_wetbulb(p, t, td):
    """Calculates the wetbulb temperature (C) for the given parcel

    Parameters
    ----------
    p : number
        Pressure of parcel (hPa)
    t : number
        Temperature of parcel (C)
    td : number
        Dew Point of parcel (C)

    Returns
    -------
    Wetbulb temperature (C)
    """
    p2, t2 = drylift(p, t, td)
    return wetlift3(p2, t2, p)

@njit
def wetlift(p, t, p2):
    """Lifts a parcel moist adiabatically to its new level.

    Parameters
    -----------
    p : number
        Pressure of initial parcel (hPa)
    t : number
        Temperature of initial parcel (C)
    p2 : number
        Pressure of final level (hPa)

    Returns
    -------
    Temperature (C)
    """
    thta = theta(p, t, 1000.0)
    thetam = thta - wobf(thta) + wobf(t)
    return satlift(p2, thetam)

@njit
def wetlift2(p, t, p2):
    """Lifts a parcel moist adiabatically to its new level.

    Parameters
    -----------
    p : number
        Pressure of initial parcel (hPa)
    t : number
        Temperature of initial parcel (C)
    p2 : number
        Pressure of final level (hPa)

    Returns
    -------
    Temperature (C)
    """
    thta = theta(p, t, 1000.0)
    thetam = thta - wobf(thta) + wobf(t)
    return thetam

@njit
def wetlift3(p, t, p2):
    """Lifts a parcel moist adiabatically to its new level.

    Parameters
    -----------
    p : number
        Pressure of initial parcel (hPa)
    t : number
        Temperature of initial parcel (C)
    p2 : number
        Pressure of final level (hPa)

    Returns
    -------
    Temperature (C)
    """
    thta = theta(p, t, 1000.0)
    thetam = thta - wobf2(thta) + wobf2(t)
    return satlift3(p2, thetam)

@njit
def wobf2(t):
    """Implementation of the Wobus Function for computing the moist adiabats.

    .. caution::
        The Wobus function has been found to have a slight pressure dependency
        (Davies-Jones 2008).  This dependency is not included in this implementation.

    Parameters
    ----------
    t : number
        Temperature (C)

    Returns
    -------
    Correction to theta (C) for calculation of saturated potential temperature.
    """
    t = t - 20
    if t <= 0:
        npol = 1.0 + t * (
            -8.841660499999999e-3
            + t
            * (
                1.4714143e-4
                + t
                * (-9.671989000000001e-7 + t * (-3.2607217e-8 + t * (-3.8598073e-10)))
            )
        )
        npol = 15.13 / (np.power(npol, 4))
        return npol
    else:
        ppol = t * (
            4.9618922e-07
            + t
            * (
                -6.1059365e-09
                + t * (3.9401551e-11 + t * (-1.2588129e-13 + t * (1.6688280e-16)))
            )
        )
        ppol = 1 + t * (3.6182989e-03 + t * (-1.3603273e-05 + ppol))
        ppol = (29.93 / np.power(ppol, 4)) + (0.96 * t) - 14.8
        return ppol


@njit
def wobf(t):
    """
    Implementation of the Wobus Function for computing the moist adiabats.

    .. caution::
        The Wobus function has been found to have a slight pressure dependency
        (Davies-Jones 2008).  This dependency is not included in this implementation.

    Parameters
    ----------
    t : number, numpy array
        Temperature (C)

    Returns
    -------
    Correction to theta (C) for calculation of saturated potential temperature.
    """
    t = t - 20
    try:
        # If t is a scalar
        if t <= 0:
            npol = 1.0 + t * (
                -8.841660499999999e-3
                + t
                * (
                    1.4714143e-4
                    + t
                    * (
                        -9.671989000000001e-7
                        + t * (-3.2607217e-8 + t * (-3.8598073e-10))
                    )
                )
            )
            npol = 15.13 / (np.power(npol, 4))
            return npol
        else:
            ppol = t * (
                4.9618922e-07
                + t
                * (
                    -6.1059365e-09
                    + t * (3.9401551e-11 + t * (-1.2588129e-13 + t * (1.6688280e-16)))
                )
            )
            ppol = 1 + t * (3.6182989e-03 + t * (-1.3603273e-05 + ppol))
            ppol = (29.93 / np.power(ppol, 4)) + (0.96 * t) - 14.8
            return ppol

    except:
        # If t is an array
        npol = 1.0 + t * (
            -8.841660499999999e-3
            + t
            * (
                1.4714143e-4
                + t
                * (-9.671989000000001e-7 + t * (-3.2607217e-8 + t * (-3.8598073e-10)))
            )
        )
        npol = 15.13 / (np.power(npol, 4))
        ppol = t * (
            4.9618922e-07
            + t
            * (
                -6.1059365e-09
                + t * (3.9401551e-11 + t * (-1.2588129e-13 + t * (1.6688280e-16)))
            )
        )
        ppol = 1 + t * (3.6182989e-03 + t * (-1.3603273e-05 + ppol))
        ppol = (29.93 / np.power(ppol, 4)) + (0.96 * t) - 14.8
        correction = np.zeros(t.shape, dtype=np.float64)
        correction[t <= 0] = npol[t <= 0]
        correction[t > 0] = ppol[t > 0]
        return correction

@njit
def satlift(p, thetam, conv=0.1):
    """
    Returns the temperature (C) of a saturated parcel (thm) when lifted to a
    new pressure level (hPa)

    .. caution::
        Testing of the SHARPpy parcel lifting routines has revealed that the convergence
        criteria used the SHARP version (and implemented here) may cause drifting the
        pseudoadiabat to occasionally "drift" when high-resolution radiosonde data is
        used.  While a stricter convergence criteria (e.g. 0.01) has shown to resolve
        this problem, it creates a noticable departure from the SPC CAPE values and
        therefore may decalibrate the other SHARPpy functions (e.g. SARS).

    Parameters
    ----------
    p : number
        Pressure to which parcel is raised (hPa)
    thetam : number
        Saturated Potential Temperature of parcel (C)
    conv : number
        Convergence criteria for satlift() (C)

    Returns
    -------
    Temperature (C) of saturated parcel at new level
    """
    if np.fabs(p - 1000.0) - 0.001 <= 0:
        return thetam
    eor = 999
    t2 = None  # All vars must be pre-defined for njit
    e2 = None  # All vars must be pre-defined for njit
    while np.fabs(eor) - 0.1 > 0:
        if eor == 999:  # First Pass
            pwrp = np.power((p / 1000.0), ROCP)
            t1 = (thetam + ZEROCNK) * pwrp - ZEROCNK
            e1 = wobf(t1) - wobf(thetam)
            rate = 1
        else:  # Successive Passes
            rate = (t2 - t1) / (e2 - e1)
            t1 = t2
            e1 = e2
        t2 = t1 - (e1 * rate)
        e2 = (t2 + ZEROCNK) / pwrp - ZEROCNK
        e2 += wobf(t2) - wobf(e2) - thetam
        eor = e2 * rate
    return t2 - eor

@njit
def satlift3(p, thetam, conv=0.1):
    """Returns the temperature (C) of a saturated parcel (thm) when lifted to a new
    pressure level (hPa)

    .. caution::
        Testing of the SHARPpy parcel lifting routines has revealed that the convergence
        criteria used the SHARP version (and implemented here) may cause drifting the
        pseudoadiabat to occasionally "drift" when high-resolution radiosonde data is
        used.  While a stricter convergence criteria (e.g. 0.01) has shown to resolve
        this problem, it creates a noticable departure from the SPC CAPE values and
        therefore may decalibrate the other SHARPpy functions (e.g. SARS).

    Parameters
    ----------
    p : number
        Pressure to which parcel is raised (hPa)
    thetam : number
        Saturated Potential Temperature of parcel (C)
    conv : number
        Convergence criteria for satlift() (C)

    Returns
    -------
    Temperature (C) of saturated parcel at new level
    """
    if np.fabs(p - 1000.0) - 0.001 <= 0:
        return thetam
    eor = 999
    t2 = None  # All vars must be pre-defined for njit
    e2 = None  # All vars must be pre-defined for njit
    while np.fabs(eor) - 0.1 > 0:
        if eor == 999:  # First Pass
            pwrp = np.power((p / 1000.0), ROCP)
            t1 = (thetam + ZEROCNK) * pwrp - ZEROCNK
            e1 = wobf2(t1) - wobf2(thetam)
            rate = 1
        else:  # Successive Passes
            rate = (t2 - t1) / (e2 - e1)
            t1 = t2
            e1 = e2
        t2 = t1 - (e1 * rate)

        #####
        # Offending line of code in minimization loops
        # pwrp tends to 0
        #####
        # if np.abs(pwrp) < 1e-10:
        #    pwrp = 1e-10
        #    print("PWRP", (t2 + ZEROCNK) / pwrp - ZEROCNK)
        e2 = (t2 + ZEROCNK) / pwrp - ZEROCNK
        # e2 = np.divide( (t2 + ZEROCNK), pwrp) - ZEROCNK
        e2 += wobf2(t2) - wobf2(e2) - thetam
        eor = e2 * rate
    return t2 - eor

@njit
def drylift(p, t, td):
    """Lifts a parcel to the LCL and returns its new level and temperature.

    Parameters
    ----------
    p : number, numpy array
        Pressure of initial parcel in hPa
    t : number, numpy array
        Temperature of inital parcel in C
    td : number, numpy array
        Dew Point of initial parcel in C

    Returns
    -------
    p2 : number, numpy array
        LCL pressure in hPa
    t2 : number, numpy array
        LCL Temperature in C
    """
    t2 = lcltemp(t, td)
    p2 = thalvl(theta(p, t, 1000.0), t2)
    return p2, t2

@njit
def lcltemp(t, td):
    """Returns the temperature (C) of a parcel when raised to its LCL.

    Parameters
    ----------
    t : number, numpy array
        Temperature of the parcel (C)
    td : number, numpy array
        Dewpoint temperature of the parcel (C)

    Returns
    -------
    Temperature (C) of the parcel at it's LCL.
    """
    s = t - td
    dlt = s * (1.2185 + 0.001278 * t + s * (-0.00219 + 1.173e-5 * s - 0.0000052 * t))
    return t - dlt

@njit
def thalvl(theta, t):
    """Returns the level (hPa) of a parcel.

    Parameters
    ----------
    theta : number, numpy array
        Potential temperature of the parcel (C)
    t : number, numpy array
        Temperature of the parcel (C)

    Returns
    -------
    Pressure Level (hPa [float]) of the parcel
    """
    t = t + ZEROCNK
    theta = theta + ZEROCNK
    return 1000.0 / (np.power((theta / t), (1.0 / ROCP)))

@njit
def theta(p, t, p2=1000.0):
    """Returns the potential temperature (C) of a parcel.

    Parameters
    ----------
    p : number, numpy array
        The pressure of the parcel (hPa)
    t : number, numpy array
        Temperature of the parcel (C)
    p2 : number, numpy array (default 1000.)
        Reference pressure level (hPa)

    Returns
    -------
    Potential temperature (C)
    """
    return ((t + ZEROCNK) * np.power((p2 / p), ROCP)) - ZEROCNK

@njit
def virtemp(p, t, td):
    """Returns the virtual temperature (C) of a parcel.  If td is masked, then
    it returns the temperature passed to the function.

    Parameters
    ----------
    p : number
        The pressure of the parcel (hPa)
    t : number
        Temperature of the parcel (C)
    td : number
        Dew point of parcel (C)

    Returns
    -------
    Virtual temperature (C)
    """
    tk = t + ZEROCNK
    w = 0.001 * mixratio(p, td)
    vt = (tk * (1.0 + w / eps) / (1.0 + w)) - ZEROCNK
    return vt

@njit
#@vectorize(["float64(float64, float64)"], nopython=True)
def mixratio(p, t):
    """Returns the mixing ratio (g/kg) of a parcel

    Parameters
    ----------
    p : number, numpy array
        Pressure of the parcel (hPa)
    t : number, numpy array
        Temperature of the parcel (hPa)

    Returns
    -------
    Mixing Ratio (g/kg) of the given parcel
    """
    x = 0.02 * (t - 12.5 + (7500.0 / p))
    wfw = 1.0 + (0.0000045 * p) + (0.0014 * x * x)
    fwesw = wfw * vappres(t)
    return 621.97 * (fwesw / (p - fwesw))

#@njit
@vectorize(["float64(float64)"], nopython=True)
def vappres(t):
    """Returns the vapor pressure of dry air at given temperature

    Parameters
    ------
    t : number, numpy array
        Temperature of the parcel (C)

    Returns
    -------
    Vapor Pressure of dry air
    """
    pol = t * (1.1112018e-17 + (t * -3.0994571e-20))
    pol = t * (2.1874425e-13 + (t * (-1.789232e-15 + pol)))
    pol = t * (4.3884180e-09 + (t * (-2.988388e-11 + pol)))
    pol = t * (7.8736169e-05 + (t * (-6.111796e-07 + pol)))
    pol = 0.99999683 + (t * (-9.082695e-03 + pol))
    return 6.1078 / pol ** 8
