""" Create the Sounding (Profile) Object """
from numba import njit
from numba.experimental import jitclass
from numba import float32, int32, float64

import numpy as np

from sharptab import thermo
from sharptab import utils
from .constants import *

########################################################################################
# Jitted form of sharppy.sharptab.profile.
#
# This code has been heavily re-written and subsequently simplified to work with numba.
#
# For example, **kwargs are not allowed and had to make further refinements to remove
# calls to masked numpy arrays. This should be okay for our purposes since there should
# be no 'missing' data.
#
# In addition, there is some odd behavior in the original code with try/catch blocks.
# These don't necessarily function as anticipated with numba, so several "hacks" had to
# be put in place to specifically call sections of various functions...the main one
# being the wetlift->wobf->satlift sections.
########################################################################################

@njit
def create_profile(pres, tmpc, dwpc, wspd, wdir, hght):
    return Profile(pres, tmpc, dwpc, wspd, wdir, hght)

spec = [
    ("pres", float64[:]),
    ("tmpc", float64[:]),
    ("dwpc", float64[:]),
    ("wspd", float64[:]),
    ("wdir", float64[:]),
    ("hght", float64[:]),
    ("logp", float64[:]),
    ("vtmp", float64[:]),
    ("sfc", int32),
    ("top", int32),
    ("wetbulb", float64[:]),
    ("theta_", float64[:]),
    ("thetae", float64[:]),
    ("wvmr", float64[:]),
    ("relh", float64[:]),
    ("u", float64[:]),
    ("v", float64[:]),
]

@jitclass(spec)

class Profile(object):
    def __init__(self, pres, tmpc, dwpc, wspd, wdir, hght):
        # def __init__(self, pres):
        ## get the data and turn them into arrays
        self.pres = pres
        self.hght = hght
        self.tmpc = tmpc
        self.dwpc = dwpc
        self.wdir = wdir
        self.wspd = wspd

        self.u, self.v = utils.vec2comp(self.wdir, self.wspd)

        self.logp = np.log10(self.pres.copy())
        self.vtmp = thermo.virtemp(self.pres, self.tmpc, self.dwpc)

        # idx = np.where(self.pres > 0)[0]
        # self.vtmp[self.dwpc.mask[idx]] = self.tmpc[self.dwpc.mask[idx]]

        ## get the index of the top and bottom of the profile
        self.sfc = np.where(self.tmpc)[0].min()
        self.top = np.where(self.tmpc)[0].max()

        ## generate the wetbulb profile
        self.wetbulb = self.get_wetbulb_profile()
        ## generate theta-e profile
        self.thetae = self.get_thetae_profile()
        ## generate theta profile
        self.theta_ = self.get_theta_profile()
        ## generate water vapor mixing ratio profile
        self.wvmr = self.get_wvmr_profile()
        ## generate rh profile
        self.relh = self.get_rh_profile()

    def get_rh_profile(self):
        """Function to calculate the relative humidity profile

        Parameters
        ----------
        None

        Returns
        -------
        Array of the relative humidity profile
        """
        rh = thermo.relh(self.pres, self.tmpc, self.dwpc)
        return rh

    def get_wvmr_profile(self):
        """Function to calculate the water vapor mixing ratio profile.

        Parameters
        ----------
        None

        Returns
        -------
        Array of water vapor mixing ratio profile
        """

        wvmr = thermo.calc_mixratio(self.pres, self.dwpc)
        return wvmr

    def get_thetae_profile(self):
        """Function to calculate the theta-e profile.

        Parameters
        ----------
        None

        Returns
        -------
        Array of theta-e profile
        """
        thetae = np.empty(self.pres.shape[0])
        for i in range(len(self.pres)):
            thetae[i] = thermo.ctok(
                thermo.calc_thetae(self.pres[i], self.tmpc[i], self.dwpc[i])
            )
        return thetae

    def get_theta_profile(self):
        """Function to calculate the theta profile.

        Parameters
        ----------
        None

        Returns
        -------
        Array of theta profile
        """
        theta_ = np.empty(self.pres.shape[0])
        for i in range(len(self.pres)):
            theta_[i] = thermo.theta(self.pres[i], self.tmpc[i])
        theta_ = thermo.ctok(theta_)
        return theta_

    def get_wetbulb_profile(self):
        """Function to calculate the wetbulb profile.

        Parameters
        ----------
        None

        Returns
        -------
        Array of wet bulb profile
        """
        wetbulb = np.empty(self.pres.shape[0])
        for i in range(len(self.pres)):
            wetbulb[i] = thermo.calc_wetbulb(self.pres[i], self.tmpc[i], self.dwpc[i])
        return wetbulb
