"""_summary_

Returns:
    _type_: _description_
"""
import os
import numpy as np
import metpy.calc as mpcalc
from metpy.units import units

HODOGRAPHS_DIR = '/data/cloud-radar-server/assets/hodographs'
HODOGRAPHS_HTML_PAGE = '/data/cloud-radar-server/assets/hodographs.html'

def update_hodo_page() -> None:
    head = """<!DOCTYPE html>
    <html>
    <head>
    <title>Hodographs</title>
    </head>
    <body>
    <ul>"""
    tail = """</ul>
    </body>
    </html>"""
    with open(HODOGRAPHS_HTML_PAGE, 'w', encoding='utf-8') as fout:
        fout.write(head)
        image_files = [f for f in os.listdir(HODOGRAPHS_DIR) if f.endswith('.png') or f.endswith('.jpg')]
        for image in image_files:
            print(image[-19:-4])
            line = f'<li><a href="hodographs/{image}">{image}</a></li>\n'
            fout.write(line)
        fout.write(tail)
    return

def calc_components(speed, direction):
    u_comp = speed * np.cos(np.deg2rad(direction))
    v_comp = speed * np.sin(np.deg2rad(direction))
    return u_comp, v_comp

def calc_vector(u_comp, v_comp):
    mag = np.sqrt(u_comp**2 + v_comp**2)
    direction = np.rad2deg(np.arctan2(u_comp, v_comp)) % 360
    return mag, direction

def calc_shear(u_layer, v_layer, height, zlevels):
    layer_top = np.where(zlevels == (height*1000))[0][0]
    u_shr = u_layer[layer_top] - u_layer[0]
    v_shr = v_layer[layer_top] - v_layer[0]
    shrmag = np.hypot(u_shr, v_shr)
    return shrmag

def calc_meanwind(u_layer, v_layer, zlevels, layertop):
    layer_top = np.where(zlevels == (layertop))[0][0]
    mean_u = np.mean(u_layer[:layer_top])
    mean_v = np.mean(v_layer[:layer_top])
    return mean_u, mean_v


def calc_bunkers(u_layer, v_layer, zlevels):
    layer_top = np.where(zlevels == (6000))[0][0]
    mean_u = np.mean(u_layer[:layer_top])
    mean_v = np.mean(v_layer[:layer_top])

    layer_top = np.where(zlevels == (6000))[0][0]
    u_shr = u_layer[layer_top] - u_layer[0]
    v_shr = v_layer[layer_top] - v_layer[0]

    dev = 7.5 * 1.94

    dev_amnt = dev / np.hypot(u_shr, v_shr)
    rstu = mean_u + (dev_amnt * v_shr)
    rstv = mean_v - (dev_amnt * u_shr)
    lstu = mean_u - (dev_amnt * v_shr)
    lstv = mean_v + (dev_amnt * u_shr)
    rmag, rdir = calc_vector(rstu, rstv)
    lmag, ldir = calc_vector(lstu, lstv)

    return rstu, rstv, lstu, lstv, rmag, rdir, lmag, ldir

def calc_corfidi(u_layer, v_layer, zlevels, u_mean, v_mean):
    llj_top = np.where(zlevels == (1500))[0][0]
    llj_u = u_layer[:llj_top]
    llj_v = v_layer[:llj_top]

    mag, _dir = calc_vector(llj_u, llj_v)
    max=0
    i=0
    for a in mag:
        if mag[i] >= mag[i-1]:
            max = i

    u_max = llj_u[i]
    v_max = llj_v[i]

    corfidi_up_u = u_mean - u_max
    corfidi_up_v =  v_mean - v_max

    corfidi_down_u = u_mean + corfidi_up_u
    corfidi_down_v = v_mean + corfidi_up_v

    return corfidi_up_u, corfidi_up_v, corfidi_down_u, corfidi_down_v

def conv_angle_param(ang):
    ang +=180
    if ang < 0:
        ang += 360
    if ang > 360:
        ang -= 360
    return ang

def conv_angle_enter(ang):
    ang = 270 - ang
    if ang < 0:
        ang += 360
    if ang > 360:
        ang -= 360
    return ang

def calc_dtm(u_300, v_300, rmu, rmv):
    dtm_u = rmu + u_300 /2
    dtm_v = rmv + v_300 /2
    return dtm_u, dtm_v

def calc_bulk_shear(data_ceiling, this_ceiling, u,v, zlevels):
    if data_ceiling >= this_ceiling:
        shr = calc_shear(u, v, this_ceiling/1000, zlevels)
        if np.isnan(shr):
            return '--'
        else:
            return round(shr)
    else:
        return '--'

def calc_srh_from_rm(data_ceiling, this_ceiling, u_avg, v_avg, rmu, rmv, zlevels):
    if data_ceiling >= this_ceiling:
        height = this_ceiling/1000
        storm_relative_helicity = (mpcalc.storm_relative_helicity(height = zlevels * units.m, u = u_avg * units.kts, v = v_avg*units.kts, depth = height*units.km, storm_u=rmu*units.kts, storm_v=rmv*units.kts))[0]
        if np.isnan(storm_relative_helicity):
            return '--'
        else:
            return round(storm_relative_helicity)
    else:
        return '--'

def calc_storm_relative_wind(data_ceiling, this_ceiling, sr_u, sr_v, zlevels):
    if data_ceiling >= this_ceiling:
        SR_U, SR_V = calc_meanwind(sr_u, sr_v, zlevels, this_ceiling)
        SR = calc_vector(SR_U, SR_V)[0]
        if np.isnan(SR):
            return '--'
        else:
            return round(SR)
    else:
        return '--'


def calc_streamwise_vorticity(data_ceiling, this_ceiling, swvper, total_swvort):
    cig_index = int(this_ceiling/100)
    if data_ceiling >= this_ceiling:
        swper  = np.mean(swvper[0:cig_index])
        swvort = np.mean(total_swvort[0:cig_index])
        if np.isnan(swvort):
            swper = '--'
        else:
            swper = round(swper)
        if np.isnan(swvort):
            swvort = '---'
        else:
            swvort = round(swvort, 3)
    else:
        swper = '--'
        swvort = '---'
    return swper, swvort



