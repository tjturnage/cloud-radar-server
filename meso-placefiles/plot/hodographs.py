from datetime import datetime
import numpy as np
import math
import os

import pylab
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from matplotlib.lines import Line2D

from sharptab.interp import generic_interp_hght
from sharptab.winds import vec2comp, comp2vec

script_path = os.path.dirname(os.path.realpath(__file__))
plt.style.use('%s/style.mplstyle' % (script_path))

_seg_hghts = [0, 3, 6, 9, 12, 18]
_seg_colors = ['r', '#00ff00', '#008800', '#993399', 'c']
_vwp_colors = ['#737373','#a2cdde','#1987cc','#1ac015','#014b00','#ff7a09',
               '#fe2101','#e205e0','000000']

def parse_vector(vec_str):
    return tuple(int(v) for v in vec_str.strip().split("/"))

def _clip_profile(prof, alt, clip_alt, intrp_prof):
    try:
        idx_clip = np.where((alt[:-1] <= clip_alt) & (alt[1:] > clip_alt))[0][0]
    except IndexError:
        return np.nan * np.ones(prof.size)

    prof_clip = prof[:(idx_clip + 1)]
    prof_clip = np.append(prof_clip, intrp_prof)

    return np.array(prof_clip)

def compute_bunkers(data):
    d = 7.5 * 1.94     # Deviation value emperically derived as 7.5 m/s
    hght = 6

    # SFC-6km Mean Wind
    u, v = data['uwnd'], data['vwnd']
    u_hght = generic_interp_hght(hght, data['hght'], u)
    v_hght = generic_interp_hght(hght, data['hght'], v)
    u_clip = _clip_profile(u, data['hght'], hght, u_hght)
    v_clip = _clip_profile(v, data['hght'], hght, v_hght)

    mnu6 = u_clip.mean()
    mnv6 = v_clip.mean()

    # SFC-6km Shear Vector
    shru = u_hght - u[0]
    shrv = v_hght - v[0]

    # Bunkers Right Motion
    tmp = d / np.hypot(shru, shrv)
    rstu = mnu6 + (tmp * shrv)
    rstv = mnv6 - (tmp * shru)
    lstu = mnu6 - (tmp * shrv)
    lstv = mnv6 + (tmp * shru)

    return comp2vec(rstu, rstv), comp2vec(lstu, lstv), comp2vec(mnu6, mnv6)

def compute_shear_mag(data, hght1, hght2=None):
    u, v = data['uwnd'], data['vwnd']
    u1 = generic_interp_hght(hght1, data['hght'], u)
    v1 = generic_interp_hght(hght1, data['hght'], v)
    V1 = u1, v1
    if hght2 is not None:
        u2 = generic_interp_hght(hght2, data['hght'], u)
        v2 = generic_interp_hght(hght2, data['hght'], v)
        V2 = u2, v2
    else:
        V2 = u[0], v[0]
    return np.hypot(V1[0] - V2[0], V1[1] - V2[1])

def compute_srh(data, storm_motion, hght):
    u, v = data['uwnd'], data['vwnd']
    if len(u) < 2 and len(v) < 2:
        return np.nan

    storm_u, storm_v = vec2comp(*storm_motion)

    sru = (u - storm_u) / 1.94
    srv = (v - storm_v) / 1.94

    sru_hght = generic_interp_hght(hght, data['hght'], sru)
    srv_hght = generic_interp_hght(hght, data['hght'], srv)
    sru_clip = _clip_profile(sru, data['hght'], hght, sru_hght)
    srv_clip = _clip_profile(srv, data['hght'], hght, srv_hght)

    layers = (sru_clip[1:] * srv_clip[:-1]) - (sru_clip[:-1] * srv_clip[1:])
    return layers.sum()

def compute_crit_angl(data, storm_motion):
    """Modified to compute a 0-3-km weighted critical angle?
    """

    u, v = data['uwnd'], data['vwnd']
    storm_u, storm_v = vec2comp(*storm_motion)

    hght_base = 0
    heights = np.arange(.25, 1.75, .25)
    angles = []
    for hght in heights:
        u_base = generic_interp_hght(hght_base, data['hght'], u)
        v_base = generic_interp_hght(hght_base, data['hght'], v)

        u_intrp = generic_interp_hght(hght, data['hght'], u)
        v_intrp = generic_interp_hght(hght, data['hght'], v)

        base_u = storm_u - u_base
        base_v = storm_v - v_base

        ang_u = u_intrp - u_base
        ang_v = v_intrp - v_base

        len_base = np.hypot(base_u, base_v)
        len_ang = np.hypot(ang_u, ang_v)

        base_dot_ang = base_u * ang_u + base_v * ang_v
        angle = np.degrees(np.arccos(base_dot_ang / (len_base * len_ang)))
        angles.append(angle)
        hght_base = hght

    mean_angle = np.nanmean(angles)
    return round(mean_angle,1)

def compute_parameters(data, storm_motion):
    params = {}

    try:
        params['bunkers_right'], params['bunkers_left'], params['mean_wind'] = compute_bunkers(data)
    except (IndexError, ValueError):
        params['bunkers_right'] = (np.nan, np.nan)
        params['bunkers_left'] = (np.nan, np.nan)
        params['mean_wind'] = (np.nan, np.nan)

    if storm_motion.lower() in ['blm', 'left-mover']:
        params['storm_motion'] = params['bunkers_left']
    elif storm_motion.lower() in ['brm', 'right-mover']:
        params['storm_motion'] = params['bunkers_right']
    elif storm_motion.lower() in ['mnw', 'mean-wind']:
        params['storm_motion'] = params['mean_wind']
    else:
        params['storm_motion'] = tuple(int(v) for v in storm_motion.split('/'))


    try:
        params['critical'] = compute_crit_angl(data, params['storm_motion'])
    except (IndexError, ValueError):
        params['critical'] = np.nan

    for hght in [1, 2, 3, 6]:
        try:
            params["shear_mag_%dkm" % hght] = compute_shear_mag(data, hght)
        except (IndexError, ValueError):
            params["shear_mag_%dkm" % hght] = np.nan

    # Mid-level shear
    params["shear_mag_16km"] = compute_shear_mag(data, 1, 6)

    for hght in [1, 2, 3]:
        params["srh_%dkm" % hght] = compute_srh(data, params['storm_motion'], hght)

    return params

def _total_seconds(td):
    return td.days * 24 * 3600 + td.seconds + td.microseconds * 1e-6

def _fmt_timedelta(td):
    seconds = int(_total_seconds(td))
    periods = [
            ('dy', 60*60*24),
            ('hr',    60*60),
            ('min',      60),
            ('sec',       1)
            ]

    strings=[]
    for period_name,period_seconds in periods:
            if seconds > period_seconds:
                    period_value, seconds = divmod(seconds,period_seconds)
                    strings.append("%s %s" % (period_value, period_name))

    return " ".join(strings)

def _plot_background(min_u, max_u, min_v, max_v):
    max_ring = int(np.ceil(max(
        np.hypot(min_u, min_v),
        np.hypot(min_u, max_v),
        np.hypot(max_u, min_v),
        np.hypot(max_u, max_v)
    )))

    pylab.axvline(x=0, linestyle='-', linewidth=1, color='#999999')
    pylab.axhline(y=0, linestyle='-', linewidth=1, color='#999999')

    for irng in range(10, max_ring, 10):
        ring = Circle((0., 0.), irng, linestyle='dashed', fc='none', ec='#999999')
        pylab.gca().add_patch(ring)

        if irng <= max_u - 10:
            rng_str = "%d kts" % irng if max_u - 20 < irng <= max_u - 10 else "%d" % irng
            pylab.text(irng + 0.5, -0.5, rng_str, ha='left', va='top', fontsize=9,
                       color='#999999', clip_on=True, clip_box=pylab.gca().get_clip_box())

def _plot_data(data, parameters, storm_relative=False):
    if storm_relative:
        original_SM = vec2comp(parameters['storm_motion'][0], parameters['storm_motion'][1])
        parameters['storm_motion'] = (0, 0)

    storm_dir, storm_spd = parameters['storm_motion']
    bl_dir, bl_spd = parameters['bunkers_left']
    br_dir, br_spd = parameters['bunkers_right']
    mn_dir, mn_spd = parameters['mean_wind']

    u, v = data['uwnd'], data['vwnd']
    alt = data['hght']

    storm_u, storm_v = vec2comp(storm_dir, storm_spd)
    bl_u, bl_v = vec2comp(bl_dir, bl_spd)
    br_u, br_v = vec2comp(br_dir, br_spd)
    mn_u, mn_v = vec2comp(mn_dir, mn_spd)

    seg_idxs = np.searchsorted(alt, _seg_hghts)
    try:
        seg_u = np.interp(_seg_hghts, alt, u, left=np.nan, right=np.nan)
        seg_v = np.interp(_seg_hghts, alt, v, left=np.nan, right=np.nan)
        ca_u = np.interp(0.5, alt, u, left=np.nan, right=np.nan)
        ca_v = np.interp(0.5, alt, v, left=np.nan, right=np.nan)
    except ValueError:
        seg_u = np.nan * np.array(_seg_hghts)
        seg_v = np.nan * np.array(_seg_hghts)
        ca_u = np.nan
        ca_v = np.nan

    mkr_z = np.arange(16)
    mkr_u = np.interp(mkr_z, alt, u, left=np.nan, right=np.nan)
    mkr_v = np.interp(mkr_z, alt, v, left=np.nan, right=np.nan)

    for idx in range(len(_seg_hghts) - 1):
        idx_start = seg_idxs[idx]
        idx_end = seg_idxs[idx + 1]

        if not np.isnan(seg_u[idx]):
            pylab.plot([seg_u[idx], u[idx_start]], [seg_v[idx], v[idx_start]], '-',
                       color=_seg_colors[idx], linewidth=1.5)

        #if idx_start < len(data['rms_error']) and data['rms_error'][idx_start] == 0.:
        #    # The first segment is to the surface wind, draw it in a dashed line
        #    pylab.plot(u[idx_start:(idx_start + 2)], v[idx_start:(idx_start + 2)], '--',
        #               color=_seg_colors[idx], linewidth=1.5)
        #    pylab.plot(u[(idx_start + 1):idx_end], v[(idx_start + 1):idx_end], '-',
        #               color=_seg_colors[idx], linewidth=1.5)
        #else:
        pylab.plot(u[idx_start:idx_end], v[idx_start:idx_end], '-',
                   color=_seg_colors[idx], linewidth=1.5)

        if not np.isnan(seg_u[idx + 1]):
            pylab.plot([u[idx_end - 1], seg_u[idx + 1]], [v[idx_end - 1], seg_v[idx + 1]],
                        '-', color=_seg_colors[idx], linewidth=1.5)


        #for upt, vpt, rms in list(zip(u, v, data['rms_error']))[idx_start:idx_end]:
        #    pylab.text(upt, vpt, str(int(round(rms,0))))
        #    rad = np.sqrt(2) * rms
        #    circ = Circle((upt, vpt), rad, color=_seg_colors[idx], alpha=0.05)
        #    pylab.gca().add_patch(circ)

    pylab.plot(mkr_u, mkr_v, 'wo', ms=11)
    pylab.plot(mkr_u, mkr_v, 'ko', ms=10)
    for um, vm, zm in zip(mkr_u, mkr_v, mkr_z):
        if not np.isnan(um):
            pylab.text(um, vm - 0.1, str(zm), va='center', ha='center', color='white',
                       size=6.5, fontweight='bold')
    try:
        pylab.plot([storm_u, u[0]], [storm_v, v[0]], 'c-', linewidth=0.75)
        pylab.plot([u[0], ca_u], [v[0], ca_v], 'm-', linewidth=0.75)
    except IndexError:
        pass


    if not (np.isnan(bl_u) or np.isnan(bl_v)):
        pylab.plot(bl_u, bl_v, 'wo', markersize=5, mfc='none')
        pylab.text(bl_u + 0.5, bl_v - 0.5, "LM", ha='left', va='top', color='#fafafa',
                   fontsize=10)

    if not (np.isnan(br_u) or np.isnan(br_v)):
        pylab.plot(br_u, br_v, 'wo', markersize=5, mfc='none')
        pylab.text(br_u + 0.5, br_v - 0.5, "RM", ha='left', va='top', color='#fafafa',
                   fontsize=10)

    if not (np.isnan(mn_u) or np.isnan(mn_v)):
        pylab.plot(mn_u, mn_v, 's', color='#a04000', markersize=5, mfc='none')
        pylab.text(mn_u + 0.6, mn_v - 0.6, "MEAN", ha='left', va='top', color='#a04000',
                   fontsize=10)

    smv_is_brm = (storm_u == br_u and storm_v == br_v)
    smv_is_blm = (storm_u == bl_u and storm_v == bl_v)
    smv_is_mnw = (storm_u == mn_u and storm_v == mn_v)

    if not (np.isnan(storm_u) or np.isnan(storm_v)) and not \
           (smv_is_brm or smv_is_blm or smv_is_mnw):
        pylab.plot(storm_u, storm_v, 'w+', markersize=6)
        pylab.text(storm_u + 0.5, storm_v - 0.5, "SM", ha='left', va='top',
                   color='#fafafa', fontsize=10)

    if storm_relative:
        pylab.arrow(0, 0, original_SM[0], original_SM[1], width=1, length_includes_head=True)

def _plot_param_table(parameters, web=False):
    storm_dir, storm_spd = parameters['storm_motion']
    trans = pylab.gca().transAxes
    line_space = 0.033
    start_x = 1.02
    start_y = 1.0 - line_space

    line_y = start_y

    kwargs = {'color':'#fafafa', 'fontsize':10, 'clip_on':False, 'transform':trans}

    pylab.text(start_x+0.175, start_y, "Parameter Table", ha='center', fontweight='bold',
               **kwargs)

    spacer = Line2D([start_x, start_x+0.361], [line_y-line_space*0.48]*2, color='#dcdcdc',
                    linestyle='-', transform=trans, clip_on=False)
    pylab.gca().add_line(spacer)
    line_y -= line_space * 1.5

    pylab.text(start_x+0.095, line_y-0.0025, "BWD (kts)", fontweight='bold', **kwargs)
    if not web:
        pylab.text(start_x+0.22, line_y-0.0025, "SRH (m$^2$s$^{-2}$)", fontweight='bold',
                   **kwargs)
    else:
        # Awful, awful hack for matplotlib without a LaTeX distribution
        pylab.text(start_x+0.22, line_y-0.0025, "SRH (m s  )", fontweight='bold', **kwargs)
        pylab.text(start_x+0.305, line_y+0.009, "2   -2", fontweight='bold', color='k',
                   fontsize=6, clip_on=False, transform=trans)

    line_y -= line_space

    pylab.text(start_x, line_y, "0-1 km", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['shear_mag_1km']) else "%d" % \
                           int(parameters['shear_mag_1km'])
    pylab.text(start_x+0.095, line_y, val, **kwargs)
    val = "--" if np.isnan(parameters['srh_1km']) else "%d" % int(parameters['srh_1km'])
    pylab.text(start_x+0.22,  line_y, val, **kwargs)

    line_y -= line_space

    pylab.text(start_x, line_y, "0-3 km", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['shear_mag_3km']) else "%d" % \
                           int(parameters['shear_mag_3km'])
    pylab.text(start_x+0.095, line_y, val, **kwargs)
    val = "--" if np.isnan(parameters['srh_3km']) else "%d" % int(parameters['srh_3km'])
    pylab.text(start_x+0.22,  line_y, val, **kwargs)

    line_y -= line_space

    pylab.text(start_x, line_y, "0-6 km", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['shear_mag_6km']) else "%d" % \
                           int(parameters['shear_mag_6km'])
    pylab.text(start_x+0.095, line_y, val, **kwargs)

    # Mid-level shear (1-6 km)
    line_y -= line_space
    #cstop = np.clip(0.033*parameters['shear_mag_16km']-0.33, 0, 1)
    #font_color = plt.get_cmap('RdYlBu_r')(cstop)[:-1]
    pylab.text(start_x, line_y, "1-6 km", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['shear_mag_16km']) else "%d" % \
                           int(parameters['shear_mag_16km'])
    pylab.text(start_x+0.095, line_y, val, **kwargs)

    spacer = Line2D([start_x, start_x+0.361], [line_y-line_space*0.48]*2, color='#dcdcdc',
                    linestyle='-', transform=trans, clip_on=False)
    pylab.gca().add_line(spacer)
    line_y -= 1.5 * line_space

    pylab.text(start_x, line_y, "Storm Motion:", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['storm_motion']).any() else "%03d/%02d kts" %\
                           (storm_dir, storm_spd)
    pylab.text(start_x+0.26, line_y+0.001, val, **kwargs)

    line_y -= line_space

    bl_dir, bl_spd = parameters['bunkers_left']
    pylab.text(start_x, line_y, "Bunkers Left:", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['bunkers_left']).any() else "%03d/%02d kts" % \
                          (bl_dir, bl_spd)
    pylab.text(start_x + 0.26, line_y + 0.001, val, **kwargs)

    line_y -= line_space

    br_dir, br_spd = parameters['bunkers_right']
    if not web:
        pylab.text(start_x, line_y, "Bunkers Right:", fontweight='bold', **kwargs)
    else:
        pylab.text(start_x, line_y-0.005, "Bunkers Right:", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['bunkers_right']).any() else "%03d/%02d kts" % \
                          (br_dir, br_spd)
    if not web:
        pylab.text(start_x + 0.26, line_y + 0.001, val, **kwargs)
    else:
        pylab.text(start_x + 0.26, line_y - 0.001, val, **kwargs)

    line_y -= line_space

    mn_dir, mn_spd = parameters['mean_wind']
    pylab.text(start_x, line_y, "0-6 km Mean Wind:", fontweight='bold', **kwargs)
    val = "--" if np.isnan(parameters['mean_wind']).any() else "%03d/%02d kts" % \
                          (mn_dir, mn_spd)
    pylab.text(start_x + 0.26, line_y + 0.001, val, **kwargs)

    spacer = Line2D([start_x, start_x + 0.361], [line_y - line_space * 0.48] * 2,
                    color='#dcdcdc', linestyle='-', transform=trans, clip_on=False)
    pylab.gca().add_line(spacer)
    line_y -= 1.5 * line_space

    if not web:
        pylab.text(start_x, line_y, "Mean Critical Angle:", fontweight='bold', **kwargs)
        val = "--" if np.isnan(parameters['critical']) else "%d$^{\circ}$" % \
                               int(parameters['critical'])
        pylab.text(start_x+0.33, line_y-0.0025, val, **kwargs)
    else:
        pylab.text(start_x, line_y-0.0075, "Mean Critical Angle:", fontweight='bold',
                   **kwargs)
        val = "--" if np.isnan(parameters['critical']) else "%d deg" % \
                               int(parameters['critical'])
        pylab.text(start_x+0.33, line_y-0.0075, val, **kwargs)

def plot_hodograph(data, parameters, storm_relative=False):
    img_filename = "%s_hodograph.png" % (data['valid_time'].strftime('%Y%m%d%H'))
    sat_age = 6 * 3600
    u, v = data['uwnd'], data['vwnd']
    if storm_relative:
        u_storm, v_storm = vec2comp(parameters['storm_motion'][0],
                                    parameters['storm_motion'][1])
        u -= u_storm
        v -= v_storm
        ctr_u, ctr_v = 0, 0
        #size = parameters['storm_motion'][1] * 2.5
        size = max(u.max() - u.min(), v.max() - v.min()) + 20

        # Re-orient the storm motions
        uu, vv = vec2comp(parameters['mean_wind'][0], parameters['mean_wind'][1])
        parameters['mean_wind'] = comp2vec(uu-u_storm, vv-v_storm)
        uu, vv = vec2comp(parameters['bunkers_right'][0], parameters['bunkers_right'][1])
        parameters['bunkers_right'] = comp2vec(uu-u_storm, vv-v_storm)
        uu, vv = vec2comp(parameters['bunkers_left'][0], parameters['bunkers_left'][1])
        parameters['bunkers_left'] = comp2vec(uu-u_storm, vv-v_storm)

        # To rotate for "along-storm-relative"
        #radians = np.deg2rad(parameters['storm_motion'][0]-180.)
        #data['uwnd'] = u * math.cos(radians) - v * math.sin(radians)
        #data['vwnd'] = u * math.sin(radians) + v * math.cos(radians)

    else:
        ctr_u = u.mean()
        ctr_v = v.mean()
        size = max(u.max() - u.min(), v.max() - v.min()) + 20
        size = max(120, size)

    min_u = ctr_u - size / 2
    max_u = ctr_u + size / 2
    min_v = ctr_v - size / 2
    max_v = ctr_v + size / 2

    now = datetime.utcnow()
    img_age = now - data['valid_time']
    age_cstop = min(_total_seconds(img_age) / sat_age, 1) * 0.4
    age_color = plt.get_cmap('hot')(age_cstop)[:-1]

    age_str = "Image created on %s (%s old)" % (now.strftime("%d %b %Y %H%M UTC"),
              _fmt_timedelta(img_age))

    pylab.figure(figsize=(10, 7.5), dpi=150)
    fig_wid, fig_hght = pylab.gcf().get_size_inches()
    fig_aspect = fig_wid / fig_hght

    axes_left = 0.005
    axes_bot = 0.01
    axes_hght = 0.95
    axes_wid = axes_hght / fig_aspect
    pylab.axes((axes_left, axes_bot, axes_wid, axes_hght))

    _plot_background(min_u, max_u, min_v, max_v)
    _plot_data(data, parameters, storm_relative=storm_relative)
    _plot_param_table(parameters)

    loc_str = "%s, %s" % (round(data['lon'], 2), round(data['lat'], 2))
    valid_str = data['valid_time'].strftime('%HZ %a %b %d %Y')
    time_str = "%sZ %s | F%s Valid: %s" % (str(data['cycle_time'].hour).zfill(2),
                                           data['model_name'],
                                           str(data['fhr']).zfill(2), valid_str)
    pylab.text(0, 1.01, "%s | %s" % (time_str, loc_str), transform=pylab.gca().transAxes,
               ha='left', va='bottom', fontsize=10, fontweight='bold', color='#fafafa')

    pylab.xlim(min_u, max_u)
    pylab.ylim(min_v, max_v)
    pylab.xticks([])
    pylab.yticks([])

    '''
    if not archive:
        pylab.title(img_title, color=age_color)
        pylab.text(0., -0.01, age_str, transform=pylab.gca().transAxes, ha='left', va='top',
                   fontsize=9, color=age_color)
    else:
        pylab.title(img_title)

    if web:
        web_brand = "http://www.autumnsky.us/vad/"
        pylab.text(1.0, -0.01, web_brand, transform=pylab.gca().transAxes, ha='right',
                   va='top', fontsize=9)

    '''

    pylab.savefig(img_filename, dpi=pylab.gcf().dpi)
    pylab.close()
