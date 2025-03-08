from numba import njit
from numba.experimental import jitclass
from numba import int32, float64
from numba import vectorize

import numpy as np
import numpy.ma as ma

from sharptab import interp
from sharptab import thermo
from sharptab import utils
from sharptab import winds

from .constants import *

spec = [
    ("flag", int32),
    ("presval", float64),
    ("pres", float64),
    ("tmpc", float64),
    ("dwpc", float64),
]

@jitclass(spec)
class DefineParcel_2(object):
    def __init__(self, prof, flag):
        self.flag = flag
        if flag == 3:
            self.presval = 300
            self.__mu(prof)

    def __mu(self, prof):
        """Create the most unstable parcel within the lowest XXX hPa, where XXX is
        supplied. Default XXX is 400 hPa.
        """
        # self.desc = 'Most Unstable Parcel in Lowest %.2f hPa' % self.presval
        pbot = prof.pres[prof.sfc]
        ptop = pbot - self.presval
        self.pres = most_unstable_level(prof)
        self.tmpc = interp.temp(prof, self.pres)
        self.dwpc = interp.dwpt(prof, self.pres)

spec = [
    ("flag", int32),
    ("presval", float64),
    ("pres", float64),
    ("tmpc", float64),
    ("dwpc", float64),
    ("pbot", float64),
    ("ptop", float64),
    ("mtheta", float64),
]

@jitclass(spec)
class DefineParcel(object):
    """Create a parcel from a supplied profile object.

    Parameters
    ----------
    prof : profile object
        Profile object

    Optional Keywords
        flag : int (default = 1)
        Parcel Selection

    1 - Observed Surface Parcel
    2 - Forecast Surface Parcel
    3 - Most Unstable Parcel
    4 - Mean Mixed Layer Parcel
    5 - User Defined Parcel
    6 - Mean Effective Layer Parcel

    Optional Keywords (Depending on Parcel Selected)
    Parcel (flag) == 1: Observed Surface Parcel
        None

    Parcel (flag) == 2: Forecast Surface Parcel
    pres : number (default = 100 hPa)
        Depth over which to mix the boundary layer; only changes
        temperature; does not affect moisture

    Parcel (flag) == 3: Most Unstable Parcel
    pres : number (default = 400 hPa)
        Depth over which to look for the the most unstable parcel
    starting from the surface pressure
        Parcel (flag) == 4: Mixed Layer Parcel
    pres : number (default = 100 hPa)
        Depth over which to mix the surface parcel

    Parcel (flag) == 5: User Defined Parcel
    pres : number (default = SFC - 100 hPa)
        Pressure of the parcel to lift
    tmpc : number (default = Temperature at the provided pressure)
        Temperature of the parcel to lift
    dwpc : number (default = Dew Point at the provided pressure)
        Dew Point of the parcel to lift

    Parcel (flag) == 6: Effective Inflow Layer
    ecape : number (default = 100)
        The minimum amount of CAPE a parcel needs to be considered
        part of the inflow layer
    ecinh : number (default = -250)
        The maximum amount of CINH allowed for a parcel to be
        considered as part of the inflow layer
    """
    def __init__(self, prof, flag):
        self.flag = flag
        if flag == 1:
            self.presval = prof.pres[prof.sfc]
            self.__sfc(prof)
        # elif flag == 2:
        #    self.presval = 100
        #    self.__fcst(prof)
        elif flag == 3:
            self.presval = 300
            self.__mu(prof)
        elif flag == 4:
            self.presval = 100
            self.__ml(prof)
        # elif flag == 5:
        #    self.presval = prof.pres[prof.sfc]
        #    self.__user(prof)

        # Since numba doesn't support recursive class calls, we'll need to
        # call the effective inflow functions specifically in script
        elif flag == 6:
            self.presval = 100
            self.__effective(prof)

        # else:
        #    self.presval = kwargs.get('pres', prof.gSndg[prof.sfc])
        #    self.__sfc(prof)

    def __sfc(self, prof):
        """Create a parcel using surface conditions"""
        # self.desc = 'Surface Parcel'
        self.pres = prof.pres[prof.sfc]
        self.tmpc = prof.tmpc[prof.sfc]
        self.dwpc = prof.dwpc[prof.sfc]

    """
    def __fcst(self, prof):
        '''
            Create a parcel using forecast conditions.

            '''
        #self.desc = 'Forecast Surface Parcel'
        self.tmpc = max_temp(prof)
        self.pres = prof.pres[prof.sfc]
        pbot = self.pres; ptop = self.pres - 100.
        self.dwpc = thermo.temp_at_mixrat(mean_mixratio(prof, pbot, ptop, exact=True), self.pres)
    """

    def __mu(self, prof):
        """Create the most unstable parcel within the lowest XXX hPa, where XXX is
        supplied. Default XXX is 400 hPa.
        """
        # self.desc = 'Most Unstable Parcel in Lowest %.2f hPa' % self.presval
        pbot = prof.pres[prof.sfc]
        ptop = pbot - self.presval
        self.pres = most_unstable_level(prof)
        self.tmpc = interp.temp(prof, self.pres)
        self.dwpc = interp.dwpt(prof, self.pres)

    def __ml(self, prof):
        """Create a mixed-layer parcel with mixing within the lowest XXX hPa, where XXX
        is supplied. Default is 100 hPa.
        """
        # self.desc = '%.2f hPa Mixed Layer Parcel' % self.presval
        pbot = prof.pres[prof.sfc]
        ptop = pbot - self.presval
        self.pres = pbot
        mtheta = mean_theta(prof, pbot, ptop, exact=True)
        self.tmpc = thermo.theta(1000.0, mtheta, self.pres)
        mmr = mean_mixratio(prof, pbot, ptop, exact=True)
        self.dwpc = thermo.temp_at_mixrat(mmr, self.pres)

    # def __user(self, prof):
    #    '''
    #        Create a user defined parcel.
    #
    #        '''
    #    #self.desc = '%.2f hPa Parcel' % self.presval
    #    self.pres = self.presval
    #    self.tmpc = interp.temp(prof, self.pres)
    #    self.dwpc = interp.dwpt(prof, self.pres)

    def __effective(self, prof):
        """Create the mean-effective layer parcel."""
        pbot, ptop = effective_inflow_layer(prof)
        if pbot > 0:
            mtha = mean_theta(prof, pbot, ptop)
            mmr = mean_mixratio(prof, pbot, ptop)
            self.pres = (pbot + ptop) / 2.0
            self.tmpc = thermo.theta(1000.0, mtha, self.pres)
            self.dwpc = thermo.temp_at_mixrat(mmr, self.pres)
        else:
            self.pres = prof.pres[prof.sfc]
            self.tmpc = prof.tmpc[prof.sfc]
            self.dwpc = prof.dwpc[prof.sfc]

        if pbot > 0:
            self.pbot = pbot
        else:
            self.pbot = -999

    """
        if utils.QC(pbot) and pbot > 0:
            self.desc = '%.2f hPa Mean Effective Layer Centered at %.2f' % ( pbot-ptop, (pbot+ptop)/2.)
            mtha = mean_theta(prof, pbot, ptop)
            mmr = mean_mixratio(prof, pbot, ptop)
            self.pres = (pbot+ptop)/2.
            self.tmpc = thermo.theta(1000., mtha, self.pres)
            self.dwpc = thermo.temp_at_mixrat(mmr, self.pres)
        else:
            self.desc = 'Defaulting to Surface Layer'
            self.pres = prof.pres[prof.sfc]
            self.tmpc = prof.tmpc[prof.sfc]
            self.dwpc = prof.dwpc[prof.sfc]
        if utils.QC(pbot): self.pbot = pbot
        else: self.pbot = ma.masked
        if utils.QC(ptop): self.ptop = ptop
        else: self.pbot = ma.masked
    """

def integrate_parcel(pres, tbot):
    pcl_tmpc = np.empty(pres.shape, dtype=pres.dtype)
    pcl_tmpc[0] = tbot
    for idx in range(1, len(pres)):
        pcl_tmpc[idx] = thermo.wetlift(pres[idx - 1], pcl_tmpc[idx - 1], pres[idx])

    return pcl_tmpc

@njit
def parcelx(prof, flag, *args):
    """Lifts the specified parcel, calculates various levels and parameters from the
    profile object. B+/B- are calculated based on the specified layer. Such parameters
    include CAPE, CIN, LCL height, LFC height, buoyancy minimum. EL height, MPL height.

    !! All calculations use the virtual temperature correction unless noted. !!

    Parameters
    ----------
    prof : profile object
        Profile Object
    flag : number (optional; default = 5)
        Flag to determine what kind of parcel to create; See DefineParcel for
        flag values

    Returns
    -------
        Parcel Object
    """
    dp = -1
    pcl = Parcel()

    # In order to allow *args functionality. This is only needed for the bunkers
    # storm motion call into parcelx in which a mulplval is passed into this
    # function.
    if len(args) == 0:
        LPLVALS = DefineParcel(prof, flag)
    else:
        LPLVALS = args[0]

    # Variables
    pres = LPLVALS.pres
    tmpc = LPLVALS.tmpc
    dwpc = LPLVALS.dwpc
    # pcl.lplhght = interp.to_agl(prof, interp.hght(prof, pres))
    pcl.lplhght = interp.hght(prof, pres)
    pcl.pres = pres
    pcl.tmpc = tmpc
    pcl.dwpc = dwpc

    # cap_strength = -9999.
    # cap_strengthpres = -9999.
    # li_max = -9999.
    # li_maxpres = -9999.
    totp = 0.0
    totn = 0.0
    tote = 0.0
    cinh_old = 0.0

    # See if default layer is specified

    pbot = prof.pres[prof.sfc]
    pcl.blayer = pbot
    pcl.pbot = pbot

    ptop = prof.pres[prof.pres.shape[0] - 1]
    pcl.tlayer = ptop
    pcl.ptop = ptop

    # Make sure this is a valid layer
    if pbot > pres:
        pbot = pres
        pcl.blayer = pbot

    # if type(interp.vtmp(prof, pbot)) == type(ma.masked) or type(interp.vtmp(prof, ptop)) == type(ma.masked):
    #    return pcl

    # Begin with the Mixing Layer
    pe1 = pbot
    h1 = interp.hght(prof, pe1)
    tp1 = thermo.virtemp(pres, tmpc, dwpc)
    ttrace = [tp1]
    ptrace = [pe1]

    # Lift parcel and return LCL pres (hPa) and LCL temp (C)
    pe2, tp2 = thermo.drylift(pres, tmpc, dwpc)

    # CALCS SAME TO HERE...

    # if type(pe2) == type(ma.masked) or np.isnan(pe2):
    #    return pcl
    blupper = pe2
    h2 = interp.hght(prof, pe2)
    te2 = interp.vtmp(prof, pe2)

    pcl.lclpres = min(pe2, prof.pres[prof.sfc])  # Make sure the LCL pressure is
    # never below the surface
    pcl.lclhght = interp.to_agl(prof, h2)

    ptrace.append(pe2)
    ttrace.append(thermo.virtemp(pe2, tp2, tp2))

    # Calculate lifted parcel theta for use in iterative CINH loop below
    # RECALL: lifted parcel theta is CONSTANT from LPL to LCL
    theta_parcel = thermo.theta(pe2, tp2, 1000.0)

    # Environmental theta and mixing ratio at LPL
    bltheta = thermo.theta(pres, interp.temp(prof, pres), 1000.0)
    blmr = thermo.mixratio(pres, dwpc)

    # ACCUMULATED CINH IN THE MIXING LAYER BELOW THE LCL
    # This will be done in 'dp' increments and will use the virtual
    # temperature correction where possible
    pp = np.arange(pbot, blupper + dp, dp, dtype=type(pbot))
    hh = interp.hght(prof, pp)
    tmp_env_theta = thermo.theta(pp, interp.temp(prof, pp), 1000.0)
    tmp_env_dwpt = interp.dwpt(prof, pp)
    tv_env = thermo.virtemp(pp, tmp_env_theta, tmp_env_dwpt)
    tmp1 = thermo.virtemp(pp, theta_parcel, thermo.temp_at_mixrat(blmr, pp))
    tdef = (tmp1 - tv_env) / thermo.ctok(tv_env)
    # tdef = np.divide((tmp1 - tv_env), thermo.ctok(tv_env))

    tidx1 = np.arange(0, len(tdef) - 1, 1)
    tidx2 = np.arange(1, len(tdef), 1)
    lyre = G * (tdef[tidx1] + tdef[tidx2]) / 2 * (hh[tidx2] - hh[tidx1])
    # lyre = np.divide(G * (tdef[tidx1]+tdef[tidx2]),  2 * (hh[tidx2]-hh[tidx1]))
    totn = lyre[lyre < 0].sum()
    if not totn:
        totn = 0.0

    # Move the bottom layer to the top of the boundary layer
    if pbot > pe2:
        pbot = pe2
        pcl.blayer = pbot

    # Calculate height of various temperature levels
    #p0c = temp_lvl(prof, 0.)

    #pm10c = temp_lvl(prof, -10.)
    #pm20c = temp_lvl(prof, -20.)
    #pm30c = temp_lvl(prof, -30.)
    #hgt0c = interp.hght(prof, p0c)

    #hgtm10c = interp.hght(prof, pm10c)
    #hgtm20c = interp.hght(prof, pm20c)
    #hgtm30c = interp.hght(prof, pm30c)
    #pcl.p0c = p0c
    #pcl.pm10c = pm10c
    #pcl.pm20c = pm20c
    #pcl.pm30c = pm30c
    #pcl.hght0c = hgt0c

    #pcl.hghtm10c = hgtm10c
    #pcl.hghtm20c = hgtm20c
    #pcl.hghtm30c = hgtm30c

    if pbot < prof.pres[-1]:
        # Check for the case where the LCL is above the
        # upper boundary of the data (e.g. a dropsonde)
        return pcl

    # Find lowest observation in layer
    lptr = np.where(pbot >= prof.pres)[0].min()
    uptr = np.where(ptop <= prof.pres)[0].max()

    # START WITH INTERPOLATED BOTTOM LAYER
    # Begin moist ascent from lifted parcel LCL (pe2, tp2)
    pe1 = pbot
    h1 = interp.hght(prof, pe1)
    te1 = interp.vtmp(prof, pe1)

    tp1 = thermo.wetlift3(pe2, tp2, pe1)

    lyre = 0
    lyrlast = 0

    iter_ranges = np.arange(lptr, prof.pres.shape[0])
    ttraces = np.zeros(len(iter_ranges))
    ptraces = np.zeros(len(iter_ranges))

    for i in iter_ranges:
        pe2 = prof.pres[i]
        h2 = prof.hght[i]
        te2 = prof.vtmp[i]
        tp2 = thermo.wetlift3(pe1, tp1, pe2)
        tdef1 = (thermo.virtemp(pe1, tp1, tp1) - te1) / thermo.ctok(te1)
        # tdef1 = np.divide((thermo.virtemp(pe1, tp1, tp1) - te1), thermo.ctok(te1))
        tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / thermo.ctok(te2)
        # tdef2 = np.divide((thermo.virtemp(pe2, tp2, tp2) - te2), thermo.ctok(te2))

        ptraces[i - iter_ranges[0]] = pe2
        ttraces[i - iter_ranges[0]] = thermo.virtemp(pe2, tp2, tp2)
        lyrlast = lyre
        lyre = G * (tdef1 + tdef2) / 2.0 * (h2 - h1)
        # lyre = np.divide(G * (tdef1 + tdef2), 2. * (h2 - h1))

        # print(pe1, pe2, te1, te2, tp1, tp2, lyre, totp, totn)

        # Add layer energy to total positive if lyre > 0
        if lyre > 0:
            totp += lyre
        # Add layer energy to total negative if lyre < 0, only up to EL
        else:
            if pe2 > 500.0:
                totn += lyre

        # Check for Max LI
        # mli = thermo.virtemp(pe2, tp2, tp2) - te2
        # if  mli > li_max:
        #    li_max = mli
        #    li_maxpres = pe2

        # Check for Max Cap Strength
        # mcap = te2 - mli
        # if mcap > cap_strength:
        #    cap_strength = mcap
        #    cap_strengthpres = pe2

        tote += lyre
        pelast = pe1
        pe1 = pe2
        te1 = te2
        tp1 = tp2

        # Is this the top of the specified layer
        if i >= uptr:
            pe3 = pe1
            h3 = h2
            te3 = te1
            tp3 = tp1
            lyrf = lyre
            if lyrf > 0:
                pcl.bplus = totp - lyrf
                pcl.bminus = totn
            else:
                pcl.bplus = totp
                if pe2 > 500.0:
                    pcl.bminus = totn + lyrf
                else:
                    pcl.bminus = totn
            pe2 = ptop
            h2 = interp.hght(prof, pe2)
            te2 = interp.vtmp(prof, pe2)
            tp2 = thermo.wetlift3(pe3, tp3, pe2)
            tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / thermo.ctok(te3)
            tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / thermo.ctok(te2)
            lyrf = G * (tdef3 + tdef2) / 2.0 * (h2 - h3)

            # tdef3 = np.divide((thermo.virtemp(pe3, tp3, tp3) - te3), thermo.ctok(te3))
            # tdef2 = np.divide((thermo.virtemp(pe2, tp2, tp2) - te2), thermo.ctok(te2))
            # lyrf = np.divide(G * (tdef3 + tdef2), 2. * (h2 - h3))

            if lyrf > 0:
                pcl.bplus += lyrf
            else:
                if pe2 > 500.0:
                    pcl.bminus += lyrf
            if pcl.bplus == 0:
                pcl.bminus = 0.0

        # Is this the freezing level
        if te2 < 0.0:
            pe3 = pelast
            h3 = interp.hght(prof, pe3)
            te3 = interp.vtmp(prof, pe3)
            tp3 = thermo.wetlift3(pe1, tp1, pe3)
            lyrf = lyre
            # if lyrf > 0.: pcl.bfzl = totp - lyrf
            # else: pcl.bfzl = totp
            # if p0c > pe3:
            #    pcl.bfzl = 0

            # elif utils.QC(pe2):
            #    te2 = interp.vtmp(prof, pe2)
            #    tp2 = thermo.wetlift(pe3, tp3, pe2)
            #    tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / \
            #        thermo.ctok(te3)
            #    tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / \
            #        thermo.ctok(te2)
            #    lyrf = G * (tdef3 + tdef2) / 2. * (hgt0c - h3)
            #    if lyrf > 0: pcl.bfzl += lyrf
        # Is this the -10C level
        if te2 < -10.0:
            pe3 = pelast
            h3 = interp.hght(prof, pe3)
            te3 = interp.vtmp(prof, pe3)
            tp3 = thermo.wetlift3(pe1, tp1, pe3)
            lyrf = lyre
            # if lyrf > 0.: pcl.wm10c = totp - lyrf
            # else: pcl.wm10c = totp
            # if not utils.QC(pm10c) or pm10c > pcl.lclpres:
            #    pcl.wm10c = 0
            # elif utils.QC(pe2):
            #    te2 = interp.vtmp(prof, pe2)
            #    tp2 = thermo.wetlift(pe3, tp3, pe2)
            #    tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / \
            #        thermo.ctok(te3)
            #    tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / \
            #        thermo.ctok(te2)
            #    lyrf = G * (tdef3 + tdef2) / 2. * (hgtm10c - h3)
            #    if lyrf > 0: pcl.wm10c += lyrf

        # Is this the -20C level
        if te2 < -20.0:
            pe3 = pelast
            h3 = interp.hght(prof, pe3)
            te3 = interp.vtmp(prof, pe3)
            tp3 = thermo.wetlift3(pe1, tp1, pe3)
            lyrf = lyre
            # if lyrf > 0.: pcl.wm20c = totp - lyrf
            # else: pcl.wm20c = totp
            # if not utils.QC(pm20c) or pm20c > pcl.lclpres:
            #    pcl.wm20c = 0
            # elif utils.QC(pe2):
            #    te2 = interp.vtmp(prof, pe2)
            #    tp2 = thermo.wetlift(pe3, tp3, pe2)
            #    tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / \
            #        thermo.ctok(te3)
            #    tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / \
            #        thermo.ctok(te2)
            #    lyrf = G * (tdef3 + tdef2) / 2. * (hgtm20c - h3)
            #    if lyrf > 0: pcl.wm20c += lyrf

        # Is this the -30C level
        if te2 < -30.0:
            pe3 = pelast
            h3 = interp.hght(prof, pe3)
            te3 = interp.vtmp(prof, pe3)
            tp3 = thermo.wetlift3(pe1, tp1, pe3)
            lyrf = lyre
            # if lyrf > 0.: pcl.wm30c = totp - lyrf
            # else: pcl.wm30c = totp
            # if not utils.QC(pm30c) or pm30c > pcl.lclpres:
            #    pcl.wm30c = 0
            # elif utils.QC(pe2):
            #    te2 = interp.vtmp(prof, pe2)
            #    tp2 = thermo.wetlift(pe3, tp3, pe2)
            #    tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / \
            #        thermo.ctok(te3)
            #    tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / \
            #        thermo.ctok(te2)
            #    lyrf = G * (tdef3 + tdef2) / 2. * (hgtm30c - h3)
            #    if lyrf > 0: pcl.wm30c += lyrf

        # Is this the 3km level
        if pcl.lclhght < 3000.0:
            if interp.to_agl(prof, h1) <= 3000.0 and interp.to_agl(prof, h2) >= 3000.0:
                pe3 = pelast
                h3 = interp.hght(prof, pe3)
                te3 = interp.vtmp(prof, pe3)
                tp3 = thermo.wetlift3(pe1, tp1, pe3)
                lyrf = lyre
                if lyrf > 0:
                    pcl.b3km = totp - lyrf
                else: pcl.b3km = totp
                h4 = interp.to_msl(prof, 3000.)
                pe4 = interp.pres(prof, h4)
                # if utils.QC(pe2):
                te2 = interp.vtmp(prof, pe4)
                tp2 = thermo.wetlift3(pe3, tp3, pe4)
                tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / \
                         thermo.ctok(te3)
                tdef2 = (thermo.virtemp(pe4, tp2, tp2) - te2) / \
                         thermo.ctok(te2)
                lyrf = G * (tdef3 + tdef2) / 2. * (h4 - h3)
                if lyrf > 0: pcl.b3km += lyrf
        else: pcl.b3km = 0.
        # Is this the 6km level
        if pcl.lclhght < 6000.0:
            if interp.to_agl(prof, h1) <= 6000.0 and interp.to_agl(prof, h2) >= 6000.0:
                pe3 = pelast
                h3 = interp.hght(prof, pe3)
                te3 = interp.vtmp(prof, pe3)
                tp3 = thermo.wetlift3(pe1, tp1, pe3)
                lyrf = lyre
                # if lyrf > 0: pcl.b6km = totp - lyrf
                # else: pcl.b6km = totp
                # h4 = interp.to_msl(prof, 6000.)
                # pe4 = interp.pres(prof, h4)
                # if utils.QC(pe2):
                #    te2 = interp.vtmp(prof, pe4)
                #    tp2 = thermo.wetlift(pe3, tp3, pe4)
                #    tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / \
                #        thermo.ctok(te3)
                #    tdef2 = (thermo.virtemp(pe4, tp2, tp2) - te2) / \
                #        thermo.ctok(te2)
                #    lyrf = G * (tdef3 + tdef2) / 2. * (h4 - h3)
                #    if lyrf > 0: pcl.b6km += lyrf
        # else: pcl.b6km = 0.

        h1 = h2

        # LFC Possibility
        if lyre >= 0.0 and lyrlast <= 0.0:
            tp3 = tp1
            # te3 = te1
            pe2 = pe1
            pe3 = pelast
            if interp.vtmp(prof, pe3) < thermo.virtemp(
                pe3, thermo.wetlift3(pe2, tp3, pe3), thermo.wetlift3(pe2, tp3, pe3)
            ):
                # Found an LFC, store height/pres and reset EL/MPL
                pcl.lfcpres = pe3
                pcl.lfchght = interp.to_agl(prof, interp.hght(prof, pe3))
                pcl.elpres = -999.0
                pcl.elhght = -999.0
                pcl.mplpres = -999.0

            else:

                ###############################################################
                # This minimization block (while loop) was causing
                # ZeroDivisionErrors
                ###############################################################
                # while interp.vtmp(prof, pe3) > thermo.virtemp(pe3, thermo.wetlift3(pe2, tp3, pe3),
                #                                              thermo.wetlift3(pe2, tp3, pe3)) and pe3 > 0:
                while (
                    interp.vtmp(prof, pe3)
                    > thermo.virtemp(
                        pe3,
                        thermo.wetlift3(pe2, tp3, pe3),
                        thermo.wetlift3(pe2, tp3, pe3),
                    )
                    and pe3 > 5
                ):
                    pe3 -= 5
                if pe3 > 0:
                    # Found a LFC, store height/pres and reset EL/MPL
                    pcl.lfcpres = pe3
                    pcl.lfchght = interp.to_agl(prof, interp.hght(prof, pe3))
                    cinh_old = totn
                    tote = 0.0
                    li_max = -9999.0
                    # if cap_strength < 0.: cap_strength = 0.
                    # pcl.cap = cap_strength
                    # pcl.cappres = cap_strengthpres

                    pcl.elpres = -999.0
                    pcl.elhght = -999.0
                    pcl.mplpres = -999.0

            # Hack to force LFC to be at least at the LCL
            if pcl.lfcpres >= pcl.lclpres:
                pcl.lfcpres = pcl.lclpres
                pcl.lfchght = pcl.lclhght

        # EL Possibility
        if lyre <= 0.0 and lyrlast >= 0.0:
            tp3 = tp1
            # te3 = te1
            pe2 = pe1
            pe3 = pelast
            while interp.vtmp(prof, pe3) < thermo.virtemp(
                pe3, thermo.wetlift3(pe2, tp3, pe3), thermo.wetlift3(pe2, tp3, pe3)
            ):
                pe3 -= 5
            pcl.elpres = pe3
            pcl.elhght = interp.to_agl(prof, interp.hght(prof, pcl.elpres))
            # pcl.mplpres = ma.masked
            # pcl.limax = -li_max
            # pcl.limaxpres = li_maxpres
        """
        # MPL Possibility
        if tote < 0.:
            pe3 = pelast
            h3 = interp.hght(prof, pe3)
            te3 = interp.vtmp(prof, pe3)
            tp3 = thermo.wetlift3(pe1, tp1, pe3)
            totx = tote - lyre
            pe2 = pelast
            while totx > 0:
                pe2 -= 1
                te2 = interp.vtmp(prof, pe2)
                tp2 = thermo.wetlift3(pe3, tp3, pe2)
                h2 = interp.hght(prof, pe2)
                tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / \
                    thermo.ctok(te3)
                tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / \
                    thermo.ctok(te2)
                lyrf = G * (tdef3 + tdef2) / 2. * (h2 - h3)
                totx += lyrf
                tp3 = tp2
                te3 = te2
                pe3 = pe2
            pcl.mplpres = pe2
            pcl.mplhght = interp.to_agl(prof, interp.hght(prof, pe2))

        # 500 hPa Lifted Index
        if prof.pres[i] <= 500. and not utils.QC(pcl.li5):
            a = interp.vtmp(prof, 500.)
            b = thermo.wetlift(pe1, tp1, 500.)
            pcl.li5 = a - thermo.virtemp(500, b, b)

        # 300 hPa Lifted Index
        if prof.pres[i] <= 300. and not utils.QC(pcl.li3):
            a = interp.vtmp(prof, 300.)
            b = thermo.wetlift(pe1, tp1, 300.)
            pcl.li3 = a - thermo.virtemp(300, b, b)

#    pcl.bminus = cinh_old
    """
    pcl.bplus = totp
    """
    # Calculate BRN if available
    bulk_rich(prof, pcl)

    # Save params
    if np.floor(pcl.bplus) == 0: pcl.bminus = 0.
    pcl.ptrace = ma.concatenate((ptrace, ptraces))
    pcl.ttrace = ma.concatenate((ttrace, ttraces))

    # Find minimum buoyancy from Trier et al. 2014, Part 1
    idx = np.ma.where(pcl.ptrace >= 500.)[0]
    if len(idx) != 0:
        b = pcl.ttrace[idx] - interp.vtmp(prof, pcl.ptrace[idx])
        idx2 = np.ma.argmin(b)
        pcl.bmin = b[idx2]
        pcl.bminpres = pcl.ptrace[idx][idx2]
    """
    return pcl

spec = [
    ("pres", float64),
    ("tmpc", float64),
    ("dwpc", float64),
    ("ptrace", float64),
    ("ttrace", float64),
    ("blayer", float64),
    ("tlayer", float64),
    ("entrain", float64),
    ("lclpres", float64),
    ("lclhght", float64),
    ("lfcpres", float64),
    ("lfchght", float64),
    ("elpres", float64),
    ("elhght", float64),
    ("mplpres", float64),
    ("mplhght", float64),
    ("bplus", float64),
    ("bminus", float64),
    ("pbot", float64),
    ("ptop", float64),
    ("lplhght", float64),
    ("b3km", float64),
    #("hght0c", float64),
]

@jitclass(spec)
class Parcel(object):
    def __init__(self):
        self.pres = -99  # Parcel beginning pressure (mb)
        self.tmpc = -99.0  # Parcel beginning temperature (C)
        self.dwpc = -99.0  # Parcel beginning dewpoint (C)
        self.ptrace = -99.0  # Parcel trace pressure (mb)
        self.ttrace = -99.0  # Parcel trace temperature (C)
        self.blayer = (
            -99.0
        )  # Pressure of the bottom of the layer the parcel is lifted (mb)
        self.tlayer = (
            -99.0
        )  # Pressure of the top of the layer the parcel is lifted (mb)
        self.entrain = 0.0  # A parcel entrainment setting (not yet implemented)
        self.lclpres = -99.0  # Parcel LCL (lifted condensation level) pressure (mb)
        self.lclhght = -99.0  # Parcel LCL height (m AGL)
        self.lfcpres = -99.0  # Parcel LFC (level of free convection) pressure (mb)
        self.lfchght = -99.0  # Parcel LFC height (m AGL)
        self.elpres = -99.0  # Parcel EL (equilibrium level) pressure (mb)
        self.elhght = -99.0  # Parcel EL height (m AGL)
        self.mplpres = -99.0  # Maximum Parcel Level (mb)
        self.mplhght = -99.0  # Maximum Parcel Level (m AGL)
        self.bplus = -99.0  # Parcel CAPE (J/kg)
        self.bminus = -99.0  # Parcel CIN (J/kg)
        self.pbot = -99.0
        self.ptop = -99.0
        self.lplhght = -99.0  # Lifted Parcel Height (m AGL)
        #self.bfzl = ma.masked # Parcel CAPE up to freezing level (J/kg)
        self.b3km = -99.0 # Parcel CAPE up to 3 km (J/kg)
        
        #self.b6km = ma.masked # Parcel CAPE up to 6 km (J/kg)
        #self.p0c = ma.masked # Pressure value at 0 C  (mb)
        #self.pm10c = ma.masked # Pressure value at -10 C (mb)
        #self.pm20c = ma.masked # Pressure value at -20 C (mb)
        #self.pm30c = ma.masked # Pressure value at -30 C (mb)
        #self.hght0c = -99.0 # Height value at 0 C (m AGL)
        #self.hghtm10c = ma.masked # Height value at -10 C (m AGL)
        #self.hghtm20c = ma.masked # Height value at -20 C (m AGL)
        #self.hghtm30c = ma.masked # Height value at -30 C (m AGL)
        #self.wm10c = ma.masked # w velocity at -10 C ?
        #self.wm20c = ma.masked # w velocity at -20 C ?
        #self.wm30c = ma.masked # Wet bulb at -30 C ?
        #self.li5 = ma.masked # Lifted Index at 500 mb (C)
        #self.li3 = ma.masked # Lifted Index at 300 mb (C)
        #self.brnshear = ma.masked # Bulk Richardson Number Shear
        #self.brnu = ma.masked # Bulk Richardson Number U (kts)
        #self.brnv = ma.masked # Bulk Richardson Number V (kts)
        #self.brn = ma.masked # Bulk Richardson Number (unitless)
        #self.limax = ma.masked # Maximum Lifted Index (C)
        #self.limaxpres = ma.masked # Pressure at Maximum Lifted Index (mb)
        #self.cap = ma.masked # Cap Strength (C)
        #self.cappres = ma.masked # Cap strength pressure (mb)
        #self.bmin = ma.masked # Buoyancy minimum in profile (C)
        #self.bminpres = ma.masked # Buoyancy minimum pressure (mb)
        # for kw in kwargs: setattr(self, kw, kwargs.get(kw))


@njit
def mean_mixratio(prof, pbot=None, ptop=None, exact=False):
    """Calculates the mean mixing ratio from a profile object within the specified layer.

    Parameters
    ----------
    prof : profile object
        Profile Object
    pbot : number (optional; default surface)
        Pressure of the bottom level (hPa)
    ptop : number (optional; default 400 hPa)
        Pressure of the top level (hPa)
    dp : negative integer (optional; default = -1)
        The pressure increment for the interpolated sounding (mb)
    exact : bool (optional; default = False)
        Switch to choose between using the exact data (slower) or using
        interpolated sounding at 'dp' pressure levels (faster)

    Returns
    -------
    Mean Mixing Ratio : number
    """
    if not pbot:
        pbot = prof.pres[prof.sfc]
    if not ptop:
        ptop = prof.pres[prof.sfc] - 100.0
    if exact:
        ind1 = np.where(pbot > prof.pres)[0].min()
        ind2 = np.where(ptop < prof.pres)[0].max()
        dwpt1 = interp.dwpt(prof, pbot)
        dwpt2 = interp.dwpt(prof, ptop)
        dwpt = prof.dwpc[ind1 : ind2 + 1]
        dwpt_out = ()
        dwpt_out = np.append(dwpt_out, dwpt1)
        dwpt_out = np.append(dwpt_out, dwpt)
        dwpt_out = np.append(dwpt_out, dwpt)
        dwpt_out = np.append(dwpt_out, dwpt2)
        dwpt = dwpt_out

        # np.concatenate failures for njit/numba
        # dwpt = np.concatenate([[dwpt1], prof.dwpc[ind1:ind2+1][mask], prof.dwpc[ind1:ind2+1][mask], [dwpt2]])
        # p = np.concatenate([[pbot], prof.pres[ind1:ind2+1][mask],prof.pres[ind1:ind2+1][mask], [ptop]])

        p = ()
        p = np.append(p, pbot)
        p = np.append(p, prof.pres[ind1 : ind2 + 1])
        p = np.append(p, prof.pres[ind1 : ind2 + 1])
        p = np.append(p, ptop)
        totd = dwpt.sum() / 2.0
        totp = p.sum() / 2.0
        num = float(len(dwpt)) / 2.0
        w = thermo.mixratio(totp / num, totd / num)
    else:
        dp = -1
        p = np.arange(pbot, ptop + dp, dp, dtype=type(pbot))
        dwpt = interp.dwpt(prof, p)

        #################
        ## Is this an oversight? Shouldn't the mixing ratio also be pressure-
        ## weighted? Maybe isn't a big deal though since we shouldn't be in
        ## here in the ML call...exact=True there

        # Numba does not support np.average(). Without weights, this is the same
        # as np.mean, but with weights=p we must make some alterations.
        # w = ma.average(thermo.mixratio(p, dwpt))
        w = thermo.mixratio(p, dwpt)
        w = np.mean(w)
        # c = 0.
        # cw = 0.
        # for ind in range(thermo.shape[0]):
        #    c += thermo[ind] * p[ind]
        #    cw += p[ind]
        # theta = c / cw
    return w

@njit
def mean_theta(prof, pbot=None, ptop=None, exact=False):
    """Calculates the mean theta from a profile object within the specified layer.

    Parameters
    ----------
    prof : profile object
        Profile Object
    pbot : number (optional; default surface)
        Pressure of the bottom level (hPa)
    ptop : number (optional; default 400 hPa)
        Pressure of the top level (hPa)
    dp : negative integer (optional; default = -1)
        The pressure increment for the interpolated sounding (mb)
    exact : bool (optional; default = False)
        Switch to choose between using the exact data (slower) or using
        interpolated sounding at 'dp' pressure levels (faster)

    Returns
    -------
    Mean Theta : number
    """
    if not pbot:
        pbot = prof.pres[prof.sfc]
    if not ptop:
        ptop = prof.pres[prof.sfc] - 100.0
    if exact:
        ind1 = np.where(pbot > prof.pres)[0].min()
        ind2 = np.where(ptop < prof.pres)[0].max()
        theta1 = thermo.theta(pbot, interp.temp(prof, pbot))
        theta2 = thermo.theta(ptop, interp.temp(prof, ptop))
        theta = thermo.theta(prof.pres[ind1 : ind2 + 1], prof.tmpc[ind1 : ind2 + 1])

        # no numba support to lists in np.concatenate?
        # theta = np.concatenate([[theta1], [theta], [theta2]])
        theta_out = ()
        theta_out = np.append(theta_out, theta1)
        theta_out = np.append(theta_out, theta)
        theta_out = np.append(theta_out, theta)
        theta_out = np.append(theta_out, theta2)
        theta = theta_out
        tott = theta.sum() / 2.0
        num = float(len(theta)) / 2.0
        thta = tott / num
    else:
        dp = -1
        p = np.arange(pbot, ptop + dp, dp, dtype=type(pbot))
        temp = interp.temp(prof, p)
        theta = thermo.theta(p, temp)

        # Numba does not support np.average(). Without weights, this is the same
        # as np.mean, but with weights=p we must make some alterations.
        # thta = np.average(theta, weights=p)
        thta = utils.weighted_average(theta, p)
        # c = 0.
        # cw = 0.
        # for ind in range(theta.shape[0]):
        #    c += theta[ind] * p[ind]
        #    cw += p[ind]
        # thta = c / cw
    return thta

@njit
def mean_thetae(prof, pbot=None, ptop=None, dp=-1, exact=False):
    '''
    Calculates the mean theta-e from a profile object within the
    specified layer.
    
    Parameters
    ----------
    prof : profile object
        Profile Object
    pbot : number (optional; default surface)
        Pressure of the bottom level (hPa)
    ptop : number (optional; default 400 hPa)
        Pressure of the top level (hPa)
    dp : negative integer (optional; default = -1)
        The pressure increment for the interpolated sounding (mb)
    exact : bool (optional; default = False)
        Switch to choose between using the exact data (slower) or using
        interpolated sounding at 'dp' pressure levels (faster)
    
    Returns
    -------
    Mean Theta-E : number
    
    '''
    if not pbot: pbot = prof.pres[prof.sfc]
    if not ptop: ptop = prof.pres[prof.sfc] - 100.
    if exact:
        ind1 = np.where(pbot > prof.pres)[0].min()
        ind2 = np.where(ptop < prof.pres)[0].max()
        thetae1 = thermo.thetae(pbot, interp.temp(prof, pbot), interp.dwpt(prof, pbot))
        thetae2 = thermo.thetae(ptop, interp.temp(prof, ptop), interp.dwpt(prof, pbot))
        thetae = np.zeros(prof.pres[ind1:ind2+1].shape)
        for i in np.arange(0, len(thetae), 1):
            thetae[i] = thermo.thetae(prof.pres[ind1:ind2+1][i],  prof.tmpc[ind1:ind2+1][i], 
                                      prof.dwpc[ind1:ind2+1][i])
        #mask = ~thetae.mask
        #thetae = np.concatenate([[thetae1], thetae[mask], thetae[mask], [thetae2]])
        # no numba support to lists in np.concatenate?
        # theta = np.concatenate([[theta1], [theta], [theta2]])
        thetae_out = ()
        thetae_out = np.append(thetae_out, thetae1)
        thetae_out = np.append(thetae_out, thetae)
        thetae_out = np.append(thetae_out, thetae)
        thetae_out = np.append(thetae_out, thetae2)
        thetae = thetae_out
        tott = thetae.sum() / 2.
        num = float(len(thetae)) / 2.
        thtae = tott / num
    else:
        dp = -1
        p = np.arange(pbot, ptop+dp, dp, dtype=type(pbot))
        thetae = interp.thetae(prof, p)
        # Numba does not support np.average(). Without weights, this is the same
        # as np.mean, but with weights=p we must make some alterations.
        #thtae = ma.average(thetae, weights=p)
        thtae = utils.weighted_average(thetae, p)
    return thtae

###############################################################################
#
# PARCEL LIFTING LEVEL CALCULATIONS
#
###############################################################################
@njit
def effective_inflow_layer(prof, *args):
    """NUMBA DOES NOT SUPPORT RECURSIVE CLASS CALLS!

    Calculate the top and bottom of the effective inflow layer based on research by [3]_.

    Parameters
    ----------
    prof : profile object
        Profile object
    ecape : number (optional; default=100)
        Minimum amount of CAPE in the layer to be considered part of the
        effective inflow layer.
    echine : number (optional; default=250)
        Maximum amount of CINH in the layer to be considered part of the
        effective inflow layer
    mupcl : parcel object
        Most Unstable Layer parcel

    Returns
    -------
    pbot : number
        Pressure at the bottom of the layer (hPa)
    ptop : number
        Pressure at the top of the layer (hPa)
    """
    ecape = 100.0
    ecinh = -250.0

    # The bunkers_storm_motion function passes a mupcl kwarg here. Add this
    # in with *args which is supported by numba. Less flexibility, but all we
    # have at this point.
    if len(args) == 0:
        mulplvals = DefineParcel_2(prof, 3)
        mupcl = cape1(prof, mulplvals)
    else:
        mupcl = args[0]

    mucape = mupcl.bplus
    mucinh = mupcl.bminus
    pbot = -999
    ptop = -999
    if mucape != 0:
        if mucape >= ecape and mucinh > ecinh:
            # Begin at surface and search upward for effective surface
            for i in range(prof.sfc, prof.top):
                pcl = cape(prof, prof.pres[i], prof.tmpc[i], prof.dwpc[i])

                if pcl.bplus >= ecape and pcl.bminus > ecinh:
                    pbot = prof.pres[i]
                    break
            bptr = i
            # Keep searching upward for the effective top
            for i in range(bptr + 1, prof.top):
                if not prof.dwpc[i] or not prof.tmpc[i]:
                    continue
                pcl = cape(prof, prof.pres[i], prof.tmpc[i], prof.dwpc[i])

                if (
                    pcl.bplus < ecape or pcl.bminus <= ecinh
                ):  # Is this a potential "top"?
                    j = 1
                    if (prof.dwpc[i - j] < -999) and (prof.tmpc[i - j] < -999.0):
                        j += 1
                    ptop = prof.pres[i - j]
                    if ptop > pbot:
                        ptop = pbot
                    break
    return pbot, ptop


@njit
def cape(prof, pres, tmpc, dwpc):
    """This is the main cape helper function which takes four arguments from
    effective_inflow_layer. This was done to get around the lack of **kwarg support in
     numba jit.
     """
    dp = -1
    new_lifter = False
    trunc = False
    flag = 5
    pcl = Parcel()

    # Variables
    pcl.pres = pres
    pcl.tmpc = tmpc
    pcl.dwpc = dwpc
    totp = 0.0
    totn = 0.0
    cinh_old = 0.0

    pbot = prof.pres[prof.sfc]
    pcl.blayer = pbot
    pcl.pbot = pbot

    ptop = prof.pres[prof.pres.shape[0] - 1]
    pcl.tlayer = ptop
    pcl.ptop = ptop

    # Make sure this is a valid layer
    if pbot > pres:
        pbot = pres
        pcl.blayer = pbot

    # Begin with the Mixing Layer
    pe1 = pbot
    h1 = interp.hght(prof, pe1)
    tp1 = thermo.virtemp(pres, tmpc, dwpc)

    # Lift parcel and return LCL pres (hPa) and LCL temp (C)
    pe2, tp2 = thermo.drylift(pres, tmpc, dwpc)
    blupper = pe2

    # Calculate lifted parcel theta for use in iterative CINH loop below
    # RECALL: lifted parcel theta is CONSTANT from LPL to LCL
    theta_parcel = thermo.theta(pe2, tp2, 1000.0)

    # Environmental theta and mixing ratio at LPL
    blmr = thermo.mixratio(pres, dwpc)

    # ACCUMULATED CINH IN THE MIXING LAYER BELOW THE LCL
    # This will be done in 'dp' increments and will use the virtual
    # temperature correction where possible
    pp = np.arange(pbot, blupper + dp, dp, dtype=type(pbot))
    hh = interp.hght(prof, pp)
    tmp_env_theta = thermo.theta(pp, interp.temp(prof, pp), 1000.0)
    tmp_env_dwpt = interp.dwpt(prof, pp)
    tv_env = thermo.virtemp(pp, tmp_env_theta, tmp_env_dwpt)
    tmp1 = thermo.virtemp(pp, theta_parcel, thermo.temp_at_mixrat(blmr, pp))
    tdef = (tmp1 - tv_env) / thermo.ctok(tv_env)

    lyre = G * (tdef[:-1] + tdef[1:]) / 2 * (hh[1:] - hh[:-1])
    totn = lyre[lyre < 0].sum()
    if not totn:
        totn = 0.0

    # Move the bottom layer to the top of the boundary layer
    if pbot > pe2:
        pbot = pe2
        pcl.blayer = pbot

    if pbot < prof.pres[-1]:
        # Check for the case where the LCL is above the
        # upper boundary of the data (e.g. a dropsonde)
        return pcl

    # Find lowest observation in layer
    lptr = np.where(pbot > prof.pres)[0].min()
    uptr = np.where(ptop < prof.pres)[0].max()

    # START WITH INTERPOLATED BOTTOM LAYER
    # Begin moist ascent from lifted parcel LCL (pe2, tp2)
    pe1 = pbot
    h1 = interp.hght(prof, pe1)
    te1 = interp.vtmp(prof, pe1)
    tp1 = tp2
    lyre = 0

    if new_lifter:
        env_temp = prof.vtmp[lptr:]
        keep = np.ones(env_temp.shape, dtype=bool)

        env_temp = np.append(te1, env_temp[keep])
        env_pres = np.append(pe1, prof.pres[lptr:][keep])
        env_hght = np.append(h1, prof.hght[lptr:][keep])
        pcl_temp = integrate_parcel(env_pres, tp1)
        tdef = (thermo.virtemp(env_pres, pcl_temp, pcl_temp) - env_temp) / thermo.ctok(
            env_temp
        )
        lyre = G * (tdef[1:] + tdef[:-1]) / 2 * (env_hght[1:] - env_hght[:-1])

        totp = lyre[lyre > 0].sum()
        neg_layers = (lyre <= 0) & (env_pres[1:] > 500)
        if np.any(neg_layers):
            totn += lyre[neg_layers].sum()

        if lyre[-1] > 0:
            pcl.bplus = totp - lyre[-1]
            pcl.bminus = totn
        else:
            pcl.bplus = totp
            if env_pres[-1] > 500.0:
                pcl.bminus = totn + lyre[-1]
            else:
                pcl.bminus = totn

        if pcl.bplus == 0:
            pcl.bminus = 0.0
    else:
        for i in range(lptr, prof.pres.shape[0]):
            pe2 = prof.pres[i]
            h2 = prof.hght[i]
            te2 = prof.vtmp[i]
            tp2 = thermo.wetlift3(pe1, tp1, pe2)
            tdef1 = (thermo.virtemp(pe1, tp1, tp1) - te1) / thermo.ctok(te1)
            tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / thermo.ctok(te2)
            lyre = G * (tdef1 + tdef2) / 2.0 * (h2 - h1)

            # Add layer energy to total positive if lyre > 0
            if lyre > 0:
                totp += lyre
            # Add layer energy to total negative if lyre < 0, only up to EL
            else:
                if pe2 > 500.0:
                    totn += lyre

            pe1 = pe2
            h1 = h2
            te1 = te2
            tp1 = tp2
            # Is this the top of the specified layer
            # Because CIN is only computed below 500 mb, we can cut off additional lifting when
            # computing convective temperature!
            if (trunc is True and pe2 <= 500) or (i >= uptr):
                pe3 = pe1
                h3 = h1
                te3 = te1
                tp3 = tp1
                lyrf = lyre
                if lyrf > 0:
                    pcl.bplus = totp - lyrf
                    pcl.bminus = totn
                else:
                    pcl.bplus = totp
                    if pe2 > 500.0:
                        pcl.bminus = totn + lyrf
                    else:
                        pcl.bminus = totn
                pe2 = ptop
                h2 = interp.hght(prof, pe2)
                te2 = interp.vtmp(prof, pe2)
                tp2 = thermo.wetlift3(pe3, tp3, pe2)
                tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / thermo.ctok(te3)
                tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / thermo.ctok(te2)
                lyrf = G * (tdef3 + tdef2) / 2.0 * (h2 - h3)
                if lyrf > 0:
                    pcl.bplus += lyrf
                else:
                    if pe2 > 500.0:
                        pcl.bminus += lyrf
                if pcl.bplus == 0:
                    pcl.bminus = 0.0
                break
    return pcl


@njit
def cape1(prof, lplvals):
    """This is the first cape helper function which takes two arguments from
    effective_inflow_layer. A second version will also have to be developed to handle
    the issue with numba and **kwargs.
    """
    dp = -1
    new_lifter = False
    trunc = False
    flag = 5
    pcl = Parcel()

    # Variables
    pres = lplvals.pres
    tmpc = lplvals.tmpc
    dwpc = lplvals.dwpc
    pcl.pres = pres
    pcl.tmpc = tmpc
    pcl.dwpc = dwpc
    totp = 0.0
    totn = 0.0
    cinh_old = 0.0

    pbot = prof.pres[prof.sfc]
    pcl.blayer = pbot
    pcl.pbot = pbot

    ptop = prof.pres[prof.pres.shape[0] - 1]
    pcl.tlayer = ptop
    pcl.ptop = ptop

    # Make sure this is a valid layer
    if pbot > pres:
        pbot = pres
        pcl.blayer = pbot

    # Begin with the Mixing Layer
    pe1 = pbot
    h1 = interp.hght(prof, pe1)
    tp1 = thermo.virtemp(pres, tmpc, dwpc)

    # Lift parcel and return LCL pres (hPa) and LCL temp (C)
    pe2, tp2 = thermo.drylift(pres, tmpc, dwpc)
    blupper = pe2

    # Calculate lifted parcel theta for use in iterative CINH loop below
    # RECALL: lifted parcel theta is CONSTANT from LPL to LCL
    theta_parcel = thermo.theta(pe2, tp2, 1000.0)

    # Environmental theta and mixing ratio at LPL
    blmr = thermo.mixratio(pres, dwpc)

    # ACCUMULATED CINH IN THE MIXING LAYER BELOW THE LCL
    # This will be done in 'dp' increments and will use the virtual
    # temperature correction where possible
    pp = np.arange(pbot, blupper + dp, dp, dtype=type(pbot))
    hh = interp.hght(prof, pp)
    tmp_env_theta = thermo.theta(pp, interp.temp(prof, pp), 1000.0)
    tmp_env_dwpt = interp.dwpt(prof, pp)
    tv_env = thermo.virtemp(pp, tmp_env_theta, tmp_env_dwpt)
    tmp1 = thermo.virtemp(pp, theta_parcel, thermo.temp_at_mixrat(blmr, pp))
    tdef = (tmp1 - tv_env) / thermo.ctok(tv_env)

    lyre = G * (tdef[:-1] + tdef[1:]) / 2 * (hh[1:] - hh[:-1])
    totn = lyre[lyre < 0].sum()
    if not totn:
        totn = 0.0

    # Move the bottom layer to the top of the boundary layer
    if pbot > pe2:
        pbot = pe2
        pcl.blayer = pbot

    if pbot < prof.pres[-1]:
        # Check for the case where the LCL is above the
        # upper boundary of the data (e.g. a dropsonde)
        return pcl

    # Find lowest observation in layer
    lptr = np.where(pbot > prof.pres)[0].min()
    uptr = np.where(ptop < prof.pres)[0].max()

    # START WITH INTERPOLATED BOTTOM LAYER
    # Begin moist ascent from lifted parcel LCL (pe2, tp2)
    pe1 = pbot
    h1 = interp.hght(prof, pe1)
    te1 = interp.vtmp(prof, pe1)
    tp1 = tp2
    lyre = 0

    if new_lifter:
        env_temp = prof.vtmp[lptr:]
        keep = np.ones(env_temp.shape, dtype=bool)

        env_temp = np.append(te1, env_temp[keep])
        env_pres = np.append(pe1, prof.pres[lptr:][keep])
        env_hght = np.append(h1, prof.hght[lptr:][keep])
        pcl_temp = integrate_parcel(env_pres, tp1)
        tdef = (thermo.virtemp(env_pres, pcl_temp, pcl_temp) - env_temp) / thermo.ctok(
            env_temp
        )
        lyre = G * (tdef[1:] + tdef[:-1]) / 2 * (env_hght[1:] - env_hght[:-1])

        totp = lyre[lyre > 0].sum()
        neg_layers = (lyre <= 0) & (env_pres[1:] > 500)
        if np.any(neg_layers):
            totn += lyre[neg_layers].sum()

        if lyre[-1] > 0:
            pcl.bplus = totp - lyre[-1]
            pcl.bminus = totn
        else:
            pcl.bplus = totp
            if env_pres[-1] > 500.0:
                pcl.bminus = totn + lyre[-1]
            else:
                pcl.bminus = totn

        if pcl.bplus == 0:
            pcl.bminus = 0.0
    else:
        for i in range(lptr, prof.pres.shape[0]):
            pe2 = prof.pres[i]
            h2 = prof.hght[i]
            te2 = prof.vtmp[i]
            tp2 = thermo.wetlift3(pe1, tp1, pe2)
            tdef1 = (thermo.virtemp(pe1, tp1, tp1) - te1) / thermo.ctok(te1)
            tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / thermo.ctok(te2)
            lyre = G * (tdef1 + tdef2) / 2.0 * (h2 - h1)

            # Add layer energy to total positive if lyre > 0
            if lyre > 0:
                totp += lyre
            # Add layer energy to total negative if lyre < 0, only up to EL
            else:
                if pe2 > 500.0:
                    totn += lyre

            pe1 = pe2
            h1 = h2
            te1 = te2
            tp1 = tp2
            # Is this the top of the specified layer
            # Because CIN is only computed below 500 mb, we can cut off additional lifting when
            # computing convective temperature!
            if (trunc is True and pe2 <= 500) or (i >= uptr):
                pe3 = pe1
                h3 = h1
                te3 = te1
                tp3 = tp1
                lyrf = lyre
                if lyrf > 0:
                    pcl.bplus = totp - lyrf
                    pcl.bminus = totn
                else:
                    pcl.bplus = totp
                    if pe2 > 500.0:
                        pcl.bminus = totn + lyrf
                    else:
                        pcl.bminus = totn
                pe2 = ptop
                h2 = interp.hght(prof, pe2)
                te2 = interp.vtmp(prof, pe2)
                tp2 = thermo.wetlift3(pe3, tp3, pe2)
                tdef3 = (thermo.virtemp(pe3, tp3, tp3) - te3) / thermo.ctok(te3)
                tdef2 = (thermo.virtemp(pe2, tp2, tp2) - te2) / thermo.ctok(te2)
                lyrf = G * (tdef3 + tdef2) / 2.0 * (h2 - h3)
                if lyrf > 0:
                    pcl.bplus += lyrf
                else:
                    if pe2 > 500.0:
                        pcl.bminus += lyrf
                if pcl.bplus == 0:
                    pcl.bminus = 0.0
                break
    return pcl


@njit
def most_unstable_level(prof):
    """Finds the most unstable level between the lower and upper levels.

    Parameters
    ----------
    prof : profile object
        Profile Object
    pbot : number (optional; default surface)
        Pressure of the bottom level (hPa)
    ptop : number (optional; default 400 hPa)
        Pressure of the top level (hPa)
    dp : negative integer (optional; default = -1)
        The pressure increment for the interpolated sounding (mb)
    exact : bool (optional; default = False)
        Switch to choose between using the exact data (slower) or using
        interpolated sounding at 'dp' pressure levels (faster)

    Returns
    -------
    Pressure level of most unstable level (hPa) : number
    """
    pbot = prof.pres[prof.sfc]
    ptop = prof.pres[prof.sfc] - 300
    # if not utils.QC(interp.temp(prof, pbot)): pbot = prof.pres[prof.sfc]
    # if not utils.QC(interp.temp(prof, ptop)): return ma.masked

    dp = -1
    p = np.arange(pbot, ptop + dp, dp, dtype=type(pbot))

    t = interp.temp(prof, p)
    d = interp.dwpt(prof, p)

    p2, t2 = thermo.drylift(p, t, d)
    mt = thermo.wetlift2(p2, t2, 1000.)
    ind = np.where(np.fabs(mt - np.nanmax(mt)) < TOL)[0]
    return p[ind[0]]

@njit
def temp_lvl(prof, temp, wetbulb=False):
    '''
        Calculates the level (hPa) of the first occurrence of the specified
        temperature.
        Parameters
        ----------
        prof : profile object
            Profile Object
        temp : number
            Temperature being searched (C)
        wetbulb : boolean
            Flag to indicate whether or not the wetbulb profile should be used instead
        Returns
        -------
        First Level of the temperature (hPa) : number
        '''
    if wetbulb is False:
        profile = prof.tmpc
    else:
        profile = prof.wetbulb

    difft = profile - temp

    if not np.any(difft <= 0) or not np.any(difft >= 0):
        # Temp doesn't occur anywhere; return masked
        return -9999.
    elif np.any(difft == 0):
        # Temp is one of the data points; don't bother interpolating
        out = prof.pres[difft == 0][0]
        return out

    # logical_or throwing errors with numba. Assuming no masked data since we'll be using
    # model data for all of this. 
    #mask = np.logical_or(difft.mask, prof.logp.mask)
    #difft = difft[~mask]
    #profile = profile[~mask]
    logp = prof.logp

    # Find where subsequent values of difft are of opposite sign (i.e. when multiplied together, the result is negative)
    ind = np.where((difft[:-1] * difft[1:]) < 0)[0]
    ind = ind.min()
    #try:
    #    ind = ind.min()
    #except:
    #    ind = ind1[-1]

    return np.power(10, np.interp(temp, [profile[ind+1], profile[ind]],
                            [logp[ind+1], logp[ind]]))

@njit
def stp_cin(mlcape, esrh, ebwd, mllcl, mlcinh):
    """Significant Tornado Parameter (w/CIN)

    Formulated using the methodology outlined in [1]_.  Used to detect environments
    where significant tornadoes are possible within the United States.  Uses the
    effective inflow layer calculation in [3]_ and was created as an alternative to [2]_.

    .. [1] Thompson, R. L., B. T. Smith, J. S. Grams, A. R. Dean, and C. Broyles, 2012:
               Convective modes for significant severe thunderstorms in the contiguous
                nited States.Part II: Supercell and QLCS tornado environments. Wea.
                Forecasting, 27, 1136–1154, doi:https://doi.org/10.1175/WAF-D-11-00116.1.

    .. [3] Thompson, R. L., C. M. Mead, and R. Edwards, 2007: Effective storm-relative
               helicity and bulk shear in supercell thunderstorm environments. Wea.
               Forecasting, 22, 102–115, doi:https://doi.org/10.1175/WAF969.1.

    Parameters
    ----------
    mlcape : float
        Mixed-layer CAPE from the parcel class (J/kg)
    esrh : float
        effective storm relative helicity (m2/s2)
    ebwd : float
        effective bulk wind difference (m/s)
    mllcl : float
        mixed-layer lifted condensation level (m)
    mlcinh : float
        mixed-layer convective inhibition (J/kg)

    Returns
    -------
    stp_cin : number
        significant tornado parameter (unitless)

    See Also
    --------
    stp_fixed
    """
    cape_term = mlcape / 1500.0
    eshr_term = esrh / 150.0

    if ebwd < 12.5:
        ebwd_term = 0.0
    elif ebwd > 30.0:
        ebwd_term = 1.5
    else:
        ebwd_term = ebwd / 20.0

    if mllcl < 1000.0:
        lcl_term = 1.0
    elif mllcl > 2000.0:
        lcl_term = 0.0
    else:
        lcl_term = (2000.0 - mllcl) / 1000.0

    if mlcinh > -50:
        cinh_term = 1.0
    elif mlcinh < -200:
        cinh_term = 0
    else:
        cinh_term = (mlcinh + 200.0) / 150.0

    stp_cin = np.maximum(cape_term * eshr_term * ebwd_term * lcl_term * cinh_term, 0)
    return stp_cin




def bunkers_storm_motion(prof):
    '''Compute the Bunkers Storm Motion for a right moving supercell using a parcel
    based approach. This code is consistent with the findings in Bunkers et. al 2014,
    using the Effective Inflow Base as the base, and 65% of the most unstable parcel
    equilibrium level height using the pressure weighted mean wind.

    Parameters
    ----------
    prof : profile object
        Profile Object
    pbot : float (optional)
        Base of effective-inflow layer (hPa)
    mupcl : parcel object (optional)
        Most Unstable Layer parcel

    Returns
    -------
    rstu : number
        Right Storm Motion U-component (kts)
    rstv : number
        Right Storm Motion V-component (kts)
    lstu : number
        Left Storm Motion U-component (kts)
    lstv : number
        Left Storm Motion V-component (kts)
    '''
    d = utils.MS2KTS(7.5)   # Deviation value emperically derived at 7.5 m/s
    mulplvals = DefineParcel_2(prof, 3)

    # Numba failure here presumably due to recursive parcelx call. May need to
    # brute force this into a separate function.
    mupcl = parcelx(prof, mulplvals)
    mucape = mupcl.bplus
    mucinh = mupcl.bminus
    muel = mupcl.elhght
    pbot, ptop = effective_inflow_layer(prof, mupcl)
    base = interp.to_agl(prof, interp.hght(prof, pbot))
    if mucape > 100.:
        depth = muel - base
        htop = base + ( depth * (65./100.) )
        ptop = interp.pres(prof, interp.to_msl(prof, htop))
        mnu, mnv = winds.mean_wind(prof, pbot, ptop)
        sru, srv = winds.wind_shear(prof, pbot, ptop)
        srmag = utils.mag(sru, srv)
        uchg = d / srmag * srv
        vchg = d / srmag * sru
        rstu = mnu + uchg
        rstv = mnv - vchg
        lstu = mnu - uchg
        lstv = mnv + vchg
    #else:
        #rstu, rstv, lstu, lstv = winds.non_parcel_bunkers_motion(prof)

    return rstu, rstv, lstu, lstv
