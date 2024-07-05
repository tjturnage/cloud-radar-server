#Install Needed Packages
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from metpy.units import units
import pyart
import numpy as np
from metpy.plots import Hodograph
import metpy.calc as mpcalc
from datetime import datetime
import matplotlib.colors as colors
from pint import UnitRegistry
import math
import requests
import os
import sys
import pandas as pd
import warnings
import glob
from pathlib import Path
import hodo_resources as hr
from pathlib import Path
from time import time
from multiprocessing import Pool, freeze_support

#Time and Time Zone
timezone = 'UTC'

radar_id = sys.argv[1]
BASE_DIR = Path(sys.argv[2])
asos_one = sys.argv[3].lower()
try:
  asos_two = sys.argv[4].lower()
except:
  asos_two = None

RADAR_DIR = BASE_DIR / 'data' / 'radar'
HODO_IMAGES = BASE_DIR / 'assets'/ 'hodographs'

THIS_RADAR = RADAR_DIR / radar_id 
os.makedirs(THIS_RADAR, exist_ok=True)
DOWNLOADS = THIS_RADAR / 'downloads'
os.makedirs(DOWNLOADS, exist_ok=True)
CF_DIR = THIS_RADAR / 'cf_radial'
os.makedirs(CF_DIR, exist_ok=True)


#Note: For events in which radar may terminate under 6000 ft AGL:
#You must use User Selected Storm Motion and enter a storm motion below.

#Items that require 6 km of data OR a user selected #storm motion:
# *   Storm Relative Hodographs
# *   SRH and Streamwise Vorticity Calculations

###Items that require 6 km of data and will be #otherwise unavailable
# *   0-6km Mean Wind, Bunkers, and Corfidi Vectors
# *   Deviant Tornado Motion

#Plot Info
data_ceiling = 8000 #Max Data Height in Feet AGL
range_type = 'Static' #Enter Dynamic For Changing Range From Values or Static for Constant Range Value
static_value = 70 # Enter Static Hodo Range or 999 To Not Use


# presumes you have the radar files downloaded already
radar_files = [f.name for f in DOWNLOADS.iterdir()]
radar_filepaths = [p for p in DOWNLOADS.iterdir()]

#Surface Winds
sfc_status = 'Preset'

def create_hodos(filename):
	for p in radar_filepaths:
	  file = p.name
	  fout = CF_DIR / f'{file}.nc'  
	  radar_time = datetime.strptime(file[4:19], '%Y%m%d_%H%M%S')
	  api_tstr = datetime.strftime(radar_time, '%Y%m%d%H%M')
	  if radar_id.startswith('K') or radar_id.startswith('P'):

	    radar = pyart.io.read(p)
	    radar

	    # create a gate filter which specifies gates to exclude from dealiasing
	    gatefilter = pyart.filters.GateFilter(radar)
	    gatefilter.exclude_transition()
	    gatefilter.exclude_invalid("velocity")
	    gatefilter.exclude_invalid("reflectivity")
	    gatefilter.exclude_outside("reflectivity", 0, 80)

	    # perform dealiasing
	    dealias_data = pyart.correct.dealias_region_based(radar, gatefilter=gatefilter)
	    radar.add_field("corrected_velocity", dealias_data)

	    pyart.io.write_cfradial(fout, radar, format='NETCDF4')

	  if radar_id.startswith('T'):
	    radar = pyart.io.read(p)
	    radar

	    pyart.io.write_cfradial(fout, radar, format='NETCDF4')

	  if radar_id.startswith('K') or radar_id.startswith('P'):
	    ncrad = pyart.io.read_cfradial(fout)

	    # Loop on all sweeps and compute VAD
	    zlevels = np.arange(0, data_ceiling+100, 100)  # height above radar
	    u_allsweeps = []
	    v_allsweeps = []

	    for idx in range(ncrad.nsweeps):
		radar_1sweep = ncrad.extract_sweeps([idx])
		vad = pyart.retrieve.vad_browning(
		    radar_1sweep, "corrected_velocity", z_want=zlevels
		)
		u_allsweeps.append(vad.u_wind)
		v_allsweeps.append(vad.v_wind)

	    # Average U and V over all sweeps and compute magnitude and angle
	    u_avg = np.nanmean(np.array(u_allsweeps), axis=0)
	    v_avg = np.nanmean(np.array(v_allsweeps), axis=0)
	    orientation = np.rad2deg(np.arctan2(-u_avg, -v_avg)) % 360
	    speed = np.sqrt(u_avg**2 + v_avg**2)
	    u_avg *= 1.944
	    v_avg *= 1.944

	  if radar_id.startswith('T'):
	    ncrad = pyart.io.read_cfradial(fout)

	    # Loop on all sweeps and compute VAD
	    zlevels = np.arange(0, 8100, 100)  # height above radar
	    u_allsweeps = []
	    v_allsweeps = []

	    for idx in range(ncrad.nsweeps):
		radar_1sweep = ncrad.extract_sweeps([idx])
		vad = pyart.retrieve.vad_browning(
		    radar_1sweep, "velocity", z_want=zlevels
		)
		u_allsweeps.append(vad.u_wind)
		v_allsweeps.append(vad.v_wind)

	    # Average U and V over all sweeps and compute magnitude and angle
	    u_avg = np.nanmean(np.array(u_allsweeps), axis=0)
	    v_avg = np.nanmean(np.array(v_allsweeps), axis=0)
	    orientation = np.rad2deg(np.arctan2(-u_avg, -v_avg)) % 360
	    speed = np.sqrt(u_avg**2 + v_avg**2)
	    u_avg *= 1.944
	    v_avg *= 1.944

	  nancount=0
	  for entry in u_avg[0:62]:
	      if np.isnan(entry):
		nancount +=1

	  if nancount != 0:
	      storm_motion_method = 'User Selected' #Choose Mean Wind, Bunkers Left, Bunkers Right, User Selected, Corfidi Downshear, Corfidi Upshear

	      sm_dir = 308
	      sm_speed = 21

	  else:
	      storm_motion_method = 'Bunkers Right' #Choose Mean Wind, Bunkers Left, Bunkers Right, User Selected, Corfidi Downshear, Corfidi Upshear

	  API_TOKEN = '86eac26a58a647e69b8c69feaef76bae'
	  API_ROOT = "https://api.synopticdata.com/v2/"

	  def mesowest_get_sfcwind(api_args):
	      """
	      For each station in a list of stations, retrieves all observational data
	      within a defined time range using mesowest API. Writes the retrieved data
	      and associated observation times to a destination file. API documentation:

		  https://api.synopticdata.com/v2/stations/nearesttime

	      Parameters
	      ----------
		api_args  : dictionary


	      Returns
	      -------
		  jas_ts  : json file
		          dictionary of all observations for a given station.
		          What is most significant, however, is writing the
		          observed data to a file that then can be manipulated
		          for plotting.

	      """
	      station = api_args["stid"]
	      api_request_url = os.path.join(API_ROOT, "stations/nearesttime")
	      req = requests.get(api_request_url, params=api_args)
	      jas_ts = req.json()
	      for s in range(0,len(jas_ts['STATION'])):
		  try:
		      station = jas_ts['STATION'][s]
		      stn_id = station['STID']
		      ob_times = station['OBSERVATIONS']['wind_speed_value_1']['date_time']
		      wnspd = station['OBSERVATIONS']['wind_speed_value_1']['value']
		      wndir = station['OBSERVATIONS']['wind_direction_value_1']['value']
		  except:
		      pass
	      return wnspd, wndir
	  if sfc_status == 'Preset':
	    track = radar_id
	    nearest_asos = asos_one
	    api_args = {"token":API_TOKEN, "stid": f"{nearest_asos}", "attime":api_tstr, "within": 60,"status":"active", "units":"speed|kts",  "hfmetars":'1'}
	    wnspd, wndir = mesowest_get_sfcwind(api_args)
	    if wndir == ''or wnspd  == '':
	      nearest_asos = asos_two
	      newapi_args = {"token":API_TOKEN, "stid": f"{nearest_asos}", "attime": api_tstr, "within": 60,"status":"active", "units":"speed|kts",  "hfmetars":'1'}
	      wnspd, wndir = mesowest_get_sfcwind(newapi_args)
	    sfc_dir = wndir
	    sfc_spd = wnspd



	  shr005 = hr.calc_bulk_shear(data_ceiling, 500, u_avg, v_avg, zlevels)
	  shr01 = hr.calc_bulk_shear(data_ceiling, 1000, u_avg, v_avg, zlevels)
	  shr03 = hr.calc_bulk_shear(data_ceiling, 3000, u_avg, v_avg, zlevels)
	  shr06 = hr.calc_bulk_shear(data_ceiling, 6000, u_avg, v_avg, zlevels)
	  shr08 = hr.calc_bulk_shear(data_ceiling, 8000, u_avg, v_avg, zlevels)

	  #Calculate Storm Motions
	  if data_ceiling >= 6000:
	    u_mean, v_mean = hr.calc_meanwind(u_avg, v_avg, zlevels, 6000)
	    mean_mag, mean_dir = hr.calc_vector(u_mean, v_mean)
	    if np.isnan(mean_mag) == False:
	      mean_mag = round(mean_mag)
	    if np.isnan(mean_mag):
	      mean_mag = '--'
	    rmu, rmv, lmu, lmv, rmag, rdir, lmag, ldir = hr.calc_bunkers(u_avg, v_avg, zlevels)
	    if np.isnan(rmag) == False:
	      rmag = round(rmag)
	    if np.isnan == False:
	      rmag = '--'
	    if np.isnan(lmag) == False:
	      lmag = round(lmag)
	    if np.isnan(lmag):
	      lmag = '--'
	    cvu_u, cvu_v, cvd_u, cvd_v = hr.calc_corfidi(u_avg, v_avg, zlevels, u_mean, v_mean)
	    cor_u_mag, cor_u_dir = hr.calc_vector(cvu_u, cvu_v)
	    if np.isnan(cor_u_mag) == False:
	      cor_u_mag = round(cor_u_mag)
	    if np.isnan(cor_u_mag):
	      cor_u_mag = '--'
	    cor_d_mag, cor_d_dir = hr.calc_vector(cvd_u, cvd_v)
	    if np.isnan(cor_d_mag) == False:
	      cor_d_mag =  round(cor_d_mag)
	    if np.isnan(cor_d_mag):
	      cor_d_mag = '--'
	  else:
	    mean_mag = '--'
	    mean_dir = '---'
	    rmu = np.nan
	    rmv = np.nan
	    lmu = np.nan
	    lmv = np.nan
	    rmag = '--'
	    rdir = '---'
	    lmag = '--'
	    ldir = '---'
	    cor_u_mag = '--'
	    cor_u_dir = '---'
	    cor_d_mag = '--'
	    cor_d_dir = '---'
	    u_mean = np.nan
	    v_mean = np.nan
	    rmu = np.nan
	    rmv = np.nan
	    lmu = np.nan
	    lmv = np.nan
	    cvu_u = np.nan
	    cvu_v = np.nan
	    cvd_u = np.nan
	    cvd_v = np.nan

	  #Calculate Deviant Tornado Motion
	  if data_ceiling >= 6000:
	    u_300, v_300 = hr.calc_meanwind(u_avg, v_avg, zlevels, 300)
	    dtm_u, dtm_v = hr.calc_dtm(u_300, v_300, rmu, rmv)
	    dtm_mag, dtm_dir = hr.calc_vector(dtm_u, dtm_v)
	    if np.isnan(dtm_mag) == False:
	      dtm_mag =  round(dtm_mag)
	  else:
	    dtm_mag, dtm_dir = '--'
	    dtm_u = np.nan
	    dtm_v = np.nan

	  #Calculate meteorological angles
	  try:
	    mean_dirmet = hr.conv_angle_param(mean_dir)
	    if np.isnan(mean_dirmet) == False:
	      mean_dirmet = round(mean_dirmet)
	    if np.isnan(mean_dirmet):
	      mean_dirmet = '---'
	  except:
	    mean_dirmet = '---'
	  try:
	    rang = hr.conv_angle_param(rdir)
	    if np.isnan(rang) == False:
	      rang =  round(rang)
	    if np.isnan(rang):
	      rang =  '---'
	  except:
	    rang = '---'
	  try:
	    lang = hr.conv_angle_param(ldir)
	    if np.isnan(lang) == False:
	      lang = round(lang)
	    if np.isnan(lang):
	      lang = '---'
	  except:
	    lang = '---'
	  try:
	    down_adj = hr.conv_angle_param(cor_d_dir)
	    if np.isnan(down_adj) == False:
	      down_adj = round(down_adj)
	    if np.isnan(down_adj):
	      down_adj = '---'
	  except:
	    down_adj = '---'
	  try:
	    up_adj = hr.conv_angle_param(cor_u_dir)
	    if np.isnan(up_adj) == False:
	      up_adj = round(up_adj)
	    if np.isnan(up_adj):
	      up_adj = '---'
	  except:
	    up_adj = '---'
	  try:
	    dtm_dir_cor = hr.conv_angle_param(dtm_dir)
	    if np.isnan(dtm_dir_cor) == False:
	      dtm_dir_cor = round(dtm_dir_cor)
	    if np.isnan(dtm_dir_cor):
	      dtm_dir_cor = '---'
	  except:
	    dtm_dir_cor = '---'

	  #Calculate Sfc Wind Components
	  if sfc_dir != 'None':
	    try:
	      sfc_angle = hr.conv_angle_enter(sfc_dir)
	    except:
	      sfc_angle = '---'
	    sfc_u, sfc_v = hr.calc_components(sfc_spd, sfc_angle)
	    if np.isnan(sfc_angle) == False:
	      sfc_angle = round(sfc_angle)
	    if np.isnan(sfc_angle):
	      sfc_angle = '---'

	  #Calculate User Selected Motion Components
	  if storm_motion_method == 'User Selected':
	    try:
	      us_ang_cor = hr.conv_angle_enter(sm_dir)
	    except:
	     us_ang_cor = '---'
	    u_sm, v_sm = hr.calc_components(sm_speed, us_ang_cor)
	    if np.isnan(us_ang_cor) == False:
	      us_ang_cor = round(us_ang_cor)
	    if np.isnan(us_ang_cor):
	      us_ang_cor = '---'

	  #Create Storm Relative Flow Based On Selected Data
	  if storm_motion_method == 'Mean Wind':
	    try:
	      sr_u = u_avg - u_mean
	      sr_v = v_avg - v_mean
	      sr_mw_u = u_mean - u_mean
	      sr_br_u = rmu - u_mean
	      sr_bl_u = lmu - u_mean
	      sr_mw_v = v_mean - v_mean
	      sr_br_v = rmv - v_mean
	      sr_bl_v = lmv - v_mean
	      sr_sfc_u = sfc_u - u_mean
	      sr_sfc_v = sfc_v - v_mean
	      sr_cu_u =  cvu_u - u_mean
	      sr_cd_u = cvd_u - u_mean
	      sr_cu_v = cvu_v - v_mean
	      sr_cd_v = cvd_v - v_mean
	      sr_dtm_u = dtm_u - u_mean
	      sr_dtm_v = dtm_v - v_mean
	    except:
	      warnings.warn('ERROR: Data Missing For Storm Relative calculations with this method: For data missing under 6000m AGL User Selected Storm Motion Required')

	  if storm_motion_method == 'User Selected':
	    sr_u = u_avg - u_sm
	    sr_v = v_avg - v_sm
	    sr_mw_u = u_mean - u_sm
	    sr_br_u = rmu - u_sm
	    sr_bl_u = lmu - u_sm
	    sr_mw_v = v_mean - v_sm
	    sr_br_v = rmv - v_sm
	    sr_bl_v = lmv - v_sm
	    sr_sfc_u = sfc_u - u_sm
	    sr_sfc_v = sfc_v - v_sm
	    sr_cu_u =  cvu_u - u_sm
	    sr_cd_u = cvd_u - u_sm
	    sr_cu_v = cvu_v - v_sm
	    sr_cd_v = cvd_v - v_sm
	    sr_dtm_u = dtm_u - u_sm
	    sr_dtm_v = dtm_v - v_sm
	    sr_sm_u = u_sm - u_sm
	    sr_sm_v = v_sm - v_sm

	  if storm_motion_method == 'Bunkers Right':
	    try:
	      sr_u = u_avg - rmu
	      sr_v = v_avg - rmv
	      sr_mw_u = u_mean - rmu
	      sr_br_u = rmu - rmu
	      sr_bl_u = lmu - rmu
	      sr_mw_v = v_mean - rmv
	      sr_br_v = rmv - rmv
	      sr_bl_v = lmv - rmv
	      sr_sfc_u = sfc_u - rmu
	      sr_sfc_v = sfc_v - rmv
	      sr_cu_u =  cvu_u - rmu
	      sr_cd_u = cvd_u - rmu
	      sr_cu_v = cvu_v - rmv
	      sr_cd_v = cvd_v - rmv
	      sr_dtm_u = dtm_u - rmu
	      sr_dtm_v = dtm_v - rmv
	    except:
	      warnings.warn('ERROR: Data Missing For Storm Relative calculations with this method: For data missing under 6000m AGL User Selected Storm Motion Required')

	  if storm_motion_method == 'Bunkers Left':
	    try:
	      sr_u = u_avg - lmu
	      sr_v = v_avg - lmv
	      sr_mw_u = u_mean - lmu
	      sr_br_u = rmu - lmu
	      sr_bl_u = lmu - lmu
	      sr_mw_v = v_mean - lmv
	      sr_br_v = rmv - lmv
	      sr_bl_v = lmv - lmv
	      sr_sfc_u = sfc_u - lmu
	      sr_sfc_v = sfc_v - lmv
	      sr_cu_u =  cvu_u - lmu
	      sr_cd_u = cvd_u - lmu
	      sr_cu_v = cvu_v - lmv
	      sr_cd_v = cvd_v - lmv
	      sr_dtm_u = dtm_u - lmu
	      sr_dtm_v = dtm_v - lmv
	    except:
	      warnings.warn('ERROR: Data Missing For Storm Relative calculations with this method: For data missing under 6000m AGL User Selected Storm Motion Required')

	  if storm_motion_method == 'Corfidi Downshear':
	    try:
	      sr_u = u_avg - cvd_u
	      sr_v = v_avg - cvd_v
	      sr_mw_u = u_mean - cvd_u
	      sr_br_u = rmu - cvd_u
	      sr_bl_u = lmu - cvd_u
	      sr_mw_v = v_mean - cvd_v
	      sr_br_v = rmv - cvd_v
	      sr_bl_v = lmv - cvd_v
	      sr_sfc_u = sfc_u - cvd_u
	      sr_sfc_v = sfc_v - cvd_v
	      sr_cu_u =  cvu_u - cvd_u
	      sr_cd_u = cvd_u - cvd_u
	      sr_cu_v = cvu_v - cvd_v
	      sr_cd_v = cvd_v - cvd_v
	      sr_dtm_u = dtm_u - cvd_u
	      sr_dtm_v = dtm_v - cvd_v
	    except:
	      warnings.warn('ERROR: Data Missing For Storm Relative calculations with this method: For data missing under 6000m AGL User Selected Storm Motion Required')

	  if storm_motion_method == 'Corfidi Upshear':
	    try:
	      sr_u = u_avg - cvu_u
	      sr_v = v_avg - cvu_v
	      sr_mw_u = u_mean - cvu_u
	      sr_br_u = rmu - cvu_u
	      sr_bl_u = lmu - cvu_u
	      sr_mw_v = v_mean - cvu_v
	      sr_br_v = rmv - cvu_v
	      sr_bl_v = lmv - cvu_v
	      sr_sfc_u = sfc_u - cvu_u
	      sr_sfc_v = sfc_v - cvu_v
	      sr_cu_u =  cvu_u - cvu_u
	      sr_cd_u = cvd_u - cvu_u
	      sr_cu_v = cvu_v - cvu_v
	      sr_cd_v = cvd_v - cvu_v
	      sr_dtm_u = dtm_u - cvu_u
	      sr_dtm_v = dtm_v - cvu_v
	    except:
	      warnings.warn('ERROR: Data Missing For Storm Relative calculations with this method: For data missing under 6000m AGL User Selected Storm Motion Required')


	  SRH05 = hr.calc_srh_from_rm(data_ceiling, 500, u_avg, v_avg, rmu, rmv, zlevels)
	  SRH1 = hr.calc_srh_from_rm(data_ceiling, 1000, u_avg, v_avg, rmu, rmv, zlevels)
	  SRH3 = hr.calc_srh_from_rm(data_ceiling, 3000, u_avg, v_avg, rmu, rmv, zlevels)
	  SRH6 = hr.calc_srh_from_rm(data_ceiling, 6000, u_avg, v_avg, rmu, rmv, zlevels)
	  SRH8 = hr.calc_srh_from_rm(data_ceiling, 8000, u_avg, v_avg, rmu, rmv, zlevels)


	  SRH_units = (units.m*units.m)/(units.s*units.s)

	  ureg=UnitRegistry()
	  ureg.default_format = "~P"
	  for u in (SRH05, SRH1, SRH3, SRH6, SRH8):
	    try:
	      u=ureg(str(u)).m
	    except:
	      pass


	  #Calculate SR Wind
	  SR05 = hr.calc_storm_relative_wind(data_ceiling, 500, sr_u, sr_v, zlevels)
	  SR1 = hr.calc_storm_relative_wind(data_ceiling, 1000, sr_u, sr_v, zlevels)
	  SR3 = hr.calc_storm_relative_wind(data_ceiling, 3000, sr_u, sr_v, zlevels)
	  SR6 = hr.calc_storm_relative_wind(data_ceiling, 6000, sr_u, sr_v, zlevels)
	  SR8 = hr.calc_storm_relative_wind(data_ceiling, 8000, sr_u, sr_v, zlevels)

	  

	  #Calculate Streamwise Vorticity

	  # adopted from Sam Brandt (2022)  and Kyle Gillett (2023)
	  # CONVERT TO m/s (uses `sm_u, sm_v` calculated above)
	  u_ms = (u_avg/1.94384)
	  v_ms = (v_avg/1.94384)
	  sm_u_ms = (sr_u/1.94384)
	  sm_v_ms = (sr_v/1.94384)

	  # INTEROPLATED SRW (send back to knots)
	  srw = mpcalc.wind_speed(sm_u_ms*units('m/s'), sm_v_ms*units('m/s'))
	  srw_knots = (srw.m*1.94384)

	  # SHEAR COMPONENTS FOR VORT CALC
	  # calc example = change in u over change in z
	  dudz = (u_ms[2::]-u_ms[0:-2]) / (zlevels[2::]-zlevels[0:-2])
	  dvdz = (v_ms[2::]-v_ms[0:-2]) / (zlevels[2::]-zlevels[0:-2])
	  dudz = np.insert(dudz,0,dudz[0])
	  dudz = np.insert(dudz,-1,dudz[-1])
	  dvdz = np.insert(dvdz,0,dvdz[0])
	  dvdz = np.insert(dvdz,-1,dvdz[-1])
	  # Shear magnitude,
	  shear=(np.sqrt(dudz**2+dvdz**2)+0.0000001)
	  # Vorticity components
	  uvort=-dvdz
	  vvort=dudz
	  # Total horizontal vorticity
	  totvort = np.sqrt(uvort**2 + vvort**2)
	  # Total streamwise vorticity
	  total_swvort = abs((sm_u_ms*uvort+sm_v_ms*vvort)/(np.sqrt(sm_u_ms**2+sm_v_ms**2)))
	  # Streamwiseness fraction
	  swvper = (total_swvort/shear)*100

	  # layer average streamwiseness and total streamwise vorticity
	  swper05, swvort05 = hr.calc_streamwise_vorticity(data_ceiling, 500, swvper, total_swvort)
	  swper1, swvort1 = hr.calc_streamwise_vorticity(data_ceiling, 1000, swvper, total_swvort)
	  swper3, swvort3 = hr.calc_streamwise_vorticity(data_ceiling, 3000, swvper, total_swvort)
	  swper6, swvort6 = hr.calc_streamwise_vorticity(data_ceiling, 6000, swvper, total_swvort)
	  swper8, swvort8 = hr.calc_streamwise_vorticity(data_ceiling, 8000, swvper, total_swvort)

	  swvort_units = units.s**-1

	  sr_spd = hr.calc_vector(sr_u, sr_v)[0]

	  def round_up_nearest(n):
	      return 5 * math.ceil(n / 5)

	  #Create Figure
	  fig = plt.figure(figsize=(16,9), facecolor='white', edgecolor="black", linewidth = 6)
	  ax=fig.add_subplot(1,1,1)
	  if range_type == 'Dynamic':
	    #Determine Component Ring For Dynamic
	    magar = []
	    magar.append(speed.max())
	    magar.append(mean_mag)
	    magar.append(rmag)
	    magar.append(lmag)
	    magar.append(cor_d_mag)
	    magar.append(cor_u_mag)
	    magar.append(dtm_mag)
	    max2 = max(magar)
	    hodo_rang = round_up_nearest(max2+10)
	    h = Hodograph(ax, component_range = hodo_rang)
	  if range_type == 'Static':
	    h = Hodograph(ax, component_range = static_value)
	  h.add_grid(increment = 10)

	  #Create Colormap
	  boundaries = np.array([0,1000,3000,6000,8000])
	  colors = ['purple', 'red', 'green', 'gold']

	  #Plot Hodograph and Winds
	  l = h.plot_colormapped(u_avg, v_avg, zlevels, intervals = boundaries, colors = colors)
	  try:
	    mw = ax.scatter(u_mean, v_mean, color = 'darkorange', marker = 's', label = f"0-6km MW: {'{:.0f}'.format(mean_dirmet)}°/{'{:.0f} kt'.format(mean_mag)}", s = 125)
	  except:
	    mw = ax.scatter(u_mean, v_mean, color = 'darkorange', marker = 's', label = f"0-6km MW: {mean_dirmet}°/{mean_mag} kt", s = 125)
	  try:
	    rm = ax.scatter(rmu, rmv, color = 'red', marker = 'o', label = f"Bunkers RM: {'{:.0f}'.format(rang)}°/{'{:.0f} kt'.format(rmag)}", s = 125)
	  except:
	    rm = ax.scatter(rmu, rmv, color = 'red', marker = 'o', label = f"Bunkers RM: {rang}°/{rmag} kt", s = 125)
	  try:
	    lm = ax.scatter(lmu, lmv, color = 'blue', marker = 'o', label = f"Bunkers LM: {'{:.0f}'.format(lang)}°/{'{:.0f} kt'.format(lmag)}", s = 125)
	  except:
	    lm = ax.scatter(lmu, lmv, color = 'blue', marker = 'o', label = f"Bunkers LM: {f'{lang}'}°/{f'{lmag} kt'}", s = 125)
	  try:
	    cd = ax.scatter(cvd_u, cvd_v, color = 'deeppink', marker = 'd', s = 125, label = f"Corfidi DS: {'{:.0f}'.format(down_adj)}°/{'{:.0f} kt'.format(cor_d_mag)}")
	  except:
	    cd = ax.scatter(cvd_u, cvd_v, color = 'deeppink', marker = 'd', s = 125, label = f"Corfidi DS: {f'{down_adj}°/{cor_d_mag} kt'}")
	  try:
	    cu = ax.scatter(cvu_u, cvu_v, color = 'green', marker = 'd', s = 125, label = f"Corfidi US: {'{:.0f}'.format(up_adj)}°/{'{:.0f} kt'.format(cor_u_mag)}")
	  except:
	    cu = ax.scatter(cvu_u, cvu_v, color = 'green', marker = 'd', s = 125, label = f"Corfidi US: {f'{up_adj}°/{cor_u_mag} kt'}")
	  try:
	    dtm = ax.scatter(dtm_u, dtm_v, color = 'black', marker = 'v', s = 125, label = f"DTM: {'{:.0f}'.format(dtm_dir_cor)}°/{'{:.0f} kt'.format(dtm_mag)} ")
	  except:
	    dtm = ax.scatter(dtm_u, dtm_v, color = 'black', marker = 'v', s = 125, label = f"DTM: {f'{dtm_dir_cor}°/{dtm_mag} kt'} ")

	  if storm_motion_method == 'User Selected':
	    us = ax.scatter(u_sm, v_sm, color = 'black', marker = 'x', label = f"User SM: {'{:.0f}'.format(sm_dir)}/{'{:.0f}'.format(sm_speed)}", s = 125)
	  if sfc_status != 'None':
	    sfc = ax.scatter(sfc_u, sfc_v, color = 'purple', marker = 'x', s = 85, label = f"Sfc. Wind: {'{:.0f}'.format(sfc_dir)}°/{'{:.0f} kt'.format(sfc_spd)}")
	    plt.plot([sfc_u, u_avg[0]], [sfc_v, v_avg[0]], color="purple", linestyle = '--', linewidth = 2)

	  #Add Colorbar and Fig Text
	  CS = plt.colorbar(l, pad=0.00)
	  CS.set_label('Meters Above Radar')

	  plt.figtext(0.91, 0.9, "BS", fontsize = 14, weight = 'bold')
	  plt.figtext(0.955, 0.9, "SRH", fontsize = 14, weight = 'bold')
	  plt.figtext(1.01, 0.9, "SRW", fontsize = 14, weight = 'bold')
	  plt.figtext(1.055, 0.9, "SWζ%", fontsize = 14, weight = 'bold')
	  plt.figtext(1.11, 0.9, f"SWζ", fontsize = 14, weight = 'bold')

	  try:
	    plt.figtext(0.85,0.85, f" 0-500m:", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(0.85,0.85, f" 0-500m:", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(0.91,0.85, f"{'{:.0f}'.format(shr005)} kt", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	      plt.figtext(0.91,0.85, f"{shr005} kt", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(0.95,0.85, f"{'{:.0f}'.format(SRH05) * SRH_units}", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(0.95,0.85, f"{SRH05 * SRH_units}", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(1.01,0.85, f"{'{:.0f}'.format(SR05) } kt", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(1.01,0.85, f"{SR05} kt", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(1.055,0.85, f"{'{:.0f}'.format(swper05) } %", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(1.055,0.85, f"{swper05} %", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(1.11,0.85, f"{'{:.3f}'.format(swvort05)} ", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(1.11,0.85, f"{swvort05} ", fontsize = 12, weight = 'bold', color = 'purple')

	  try:
	    plt.figtext(0.85,0.80, f" 0-1km: ", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(0.85,0.80, f" 0-1km: ", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	      plt.figtext(0.91,0.80, f"{'{:.0f}'.format(shr01)} kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(0.91,0.80, f"{shr01} kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(0.95,0.80, f"{'{:.0f}'.format(SRH1) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(0.95,0.80, f"{SRH1 * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(1.01,0.80, f"{'{:.0f}'.format(SR1) } kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(1.01,0.80, f"{SR1} kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(1.055,0.80, f"{'{:.0f}'.format(swper1) } %", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(1.055,0.80, f"{swper1} %", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(1.11,0.80, f"{'{:.3f}'.format(swvort1)} ", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(1.11,0.80, f"{swvort1} ", fontsize = 12, weight = 'bold', color = 'darkorchid')

	  try:
	    plt.figtext(0.85,0.75, f" 0-3km: ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(0.85,0.75, f" 0-3km: ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(0.91,0.75, f"{'{:.0f}'.format(shr03)} kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(0.91,0.75, f"{shr03} kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(0.95,0.75, f"{'{:.0f}'.format(SRH3) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(0.95,0.75, f"{SRH3 * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(1.01,0.75, f"{'{:.0f}'.format(SR3) } kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(1.01,0.75, f"{SR3} kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(1.055,0.75, f"{'{:.0f}'.format(swper3) } %", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(1.055,0.75, f"{swper3} %", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(1.11,0.75, f"{'{:.3f}'.format(swvort3)} ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(1.11,0.75, f"{swvort3} ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')

	  try:
	    plt.figtext(0.85,0.70, f" 0-6km: ", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(0.85,0.70, f" 0-6km: ", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(0.91,0.70, f"{'{:.0f}'.format(shr06)} kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(0.91,0.70, f"{shr06} kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(0.95,0.70, f"{'{:.0f}'.format(SRH6) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(0.95,0.70, f"{SRH6 * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(1.01,0.70, f"{'{:.0f}'.format(SR6) } kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(1.01,0.70, f"{SR6} kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(1.055,0.70, f"{'{:.0f}'.format(swper6) } %", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(1.055,0.70, f"{swper6} %", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(1.11,0.70, f"{'{:.3f}'.format(swvort6)} ", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(1.11,0.70, f"{swvort6} ", fontsize = 12, weight = 'bold', color = 'mediumblue')

	  try:
	    plt.figtext(0.85,0.65, f" 0-8km: ", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(0.85,0.65, f" 0-8km: ", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(0.91,0.65, f"{'{:.0f}'.format(shr08)} kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(0.91,0.65, f"{shr08} kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(0.95,0.65, f"{'{:.0f}'.format(SRH8) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(0.95,0.65, f"{SRH8 * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(1.01,0.65, f"{'{:.0f}'.format(SR8) } kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(1.01,0.65, f"{SR8} kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(1.055,0.65, f"{'{:.0f}'.format(swper8) } %", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(1.055,0.65, f"{swper8} %", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(1.11,0.65, f"{'{:.3f}'.format(swvort8)} ", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(1.11,0.65, f"{swvort8} ", fontsize = 12, weight = 'bold', color = 'darkblue')

	  plt.figtext(0.90,0.60, "Storm Motion/Sfc Wind", fontsize = 14, weight = 'bold')

	  plt.legend(loc = 'right', bbox_to_anchor=(1.885, 0.55),
		    ncol=2, fancybox=True, shadow=True, fontsize=11, facecolor='white', framealpha=1.0,
		      labelcolor='k', borderpad=0.7)
	  rts = datetime.strftime(radar_time, "%Y-%m-%d %H:%M:%S")
	  hodo_title = f'Hodograph from {radar_id} Valid {rts} UTC'
	  plt.title(hodo_title, fontsize = 16, weight = 'bold')
	  try:
	    #Plot SRW wrt Hgt
	    sr_plot = plt.axes((0.895, 0.10, 0.095, 0.32))
	    plt.figtext(0.94, 0.45, f'SR Wind (kts)', weight='bold', color='black', fontsize=12, ha='center')
	    sr_plot.set_ylim(0,3000)
	    sr_plot.set_xlim(sr_spd[0:31].min() -6,sr_spd[0:31].max() +6)
	    sr_plot.plot(sr_spd[0:11], zlevels[0:11], color = 'purple', linewidth = 3)
	    sr_plot.plot(sr_spd[10:31], zlevels[10:31], color = 'red', linewidth = 3)
	    plt.ylabel('Height Above Radar (m)')
	    plt.xlabel('SRW (kt)')
	    plt.grid(axis='y')
	  except:
	    pass

	  try:
	    #Plot SW Vort Perc wrt Hgt
	    swv_plot = plt.axes((1.05, 0.10, 0.095, 0.32))
	    plt.figtext(1.1, 0.45, f'SWζ%', weight='bold', color='black', fontsize=12, ha='center')
	    swv_plot.set_ylim(0,3000)
	    swv_plot.set_xlim(00,101)
	    swv_plot.plot(swvper[0:11], zlevels[0:11], color = 'purple', linewidth = 3)
	    swv_plot.plot(swvper[10:31], zlevels[10:31], color = 'red', linewidth = 3)
	    plt.ylabel('Height Above Radar (m)')
	    plt.xlabel('SWζ%')
	    plt.grid(axis='y')
	  except:
	    pass
	  #Add Title and Legend and Save Figure

	  r_date = radar_time.strftime("%Y%m%d")
	  r_time = radar_time.strftime("%H%M%S")
	  hodo_fname = f'Hodograph_{radar_id}_{r_date}_{r_time}.png'
	  hodo_fp = HODO_IMAGES / hodo_fname
	  plt.savefig(hodo_fp, bbox_inches='tight')

	  #Create Figure
	  fig = plt.figure(figsize=(16,9), facecolor='white', edgecolor="black", linewidth = 6)
	  ax=fig.add_subplot(1,1,1)
	  if range_type == 'Dynamic':
	    #Determine Component Ring For Dynamic
	    magar = []
	    magar.append(speed.max())
	    magar.append(mean_mag)
	    magar.append(rmag)
	    magar.append(lmag)
	    magar.append(cor_d_mag)
	    magar.append(cor_u_mag)
	    magar.append(dtm_mag)
	    max2 = max(magar)
	    hodo_rang = round_up_nearest(max2+10)
	    h = Hodograph(ax, component_range = hodo_rang)
	  if range_type == 'Static':
	    h = Hodograph(ax, component_range = static_value)
	  h.add_grid(increment = 10)

	  #Create Colormap
	  boundaries = np.array([0,1000,3000,6000,8000])
	  colors = ['purple', 'red', 'green', 'gold']

	  #Plot Hodograph and Winds
	  l = h.plot_colormapped(sr_u, sr_v, zlevels, intervals = boundaries, colors = colors)
	  try:
	    mw = ax.scatter(sr_mw_u, sr_mw_v, color = 'darkorange', marker = 's', label = f"0-6km MW: {'{:.0f}'.format(mean_dirmet)}°/{'{:.0f} kt'.format(mean_mag)}", s = 125)
	  except:
	    mw = ax.scatter(sr_mw_u, sr_mw_v, color = 'darkorange', marker = 's', label = f"0-6km MW: {mean_dirmet}°/{mean_mag} kt", s = 125)
	  try:
	    rm = ax.scatter(sr_br_u, sr_br_v, color = 'red', marker = 'o', label = f"Bunkers RM: {'{:.0f}'.format(rang)}°/{'{:.0f} kt'.format(rmag)}", s = 125)
	  except:
	    rm = ax.scatter(sr_br_u, sr_br_v, color = 'red', marker = 'o', label = f"Bunkers RM: {rang}°/{rmag} kt", s = 125)
	  try:
	    lm = ax.scatter(sr_bl_u, sr_bl_v, color = 'blue', marker = 'o', label = f"Bunkers LM: {'{:.0f}'.format(lang)}°/{'{:.0f} kt'.format(lmag)}", s = 125)
	  except:
	    lm = ax.scatter(sr_bl_u, sr_bl_v, color = 'blue', marker = 'o', label = f"Bunkers LM: {f'{lang}'}°/{f'{lmag} kt'}", s = 125)
	  try:
	    cd = ax.scatter(sr_cd_u, sr_cd_v, color = 'deeppink', marker = 'd', s = 125, label = f"Corfidi DS: {'{:.0f}'.format(down_adj)}°/{'{:.0f} kt'.format(cor_d_mag)}")
	  except:
	    cd = ax.scatter(sr_cd_u, sr_cd_v, color = 'deeppink', marker = 'd', s = 125, label = f"Corfidi DS: {f'{down_adj}°/{cor_d_mag} kt'}")
	  try:
	    cu = ax.scatter(sr_cu_u, sr_cu_v, color = 'green', marker = 'd', s = 125, label = f"Corfidi US: {'{:.0f}'.format(up_adj)}°/{'{:.0f} kt'.format(cor_u_mag)}")
	  except:
	    cu = ax.scatter(sr_cu_u, sr_cu_v, color = 'green', marker = 'd', s = 125, label = f"Corfidi US: {f'{up_adj}°/{cor_u_mag} kt'}")
	  try:
	    dtm = ax.scatter(sr_dtm_u, sr_dtm_v, color = 'black', marker = 'v', s = 125, label = f"DTM: {'{:.0f}'.format(dtm_dir_cor)}°/{'{:.0f} kt'.format(dtm_mag)} ")
	  except:
	    dtm = ax.scatter(sr_dtm_u, sr_dtm_v, color = 'black', marker = 'v', s = 125, label = f"DTM: {f'{dtm_dir_cor}°/{dtm_mag} kt'} ")

	  if storm_motion_method == 'User Selected':
	    us = ax.scatter(sr_sm_u, sr_sm_v, color = 'black', marker = 'x', label = f"User SM: {'{:.0f}'.format(sm_dir)}/{'{:.0f}'.format(sm_speed)}", s = 125)
	  if sfc_status != 'None':
	    sfc = ax.scatter(sr_sfc_u, sr_sfc_v, color = 'purple', marker = 'x', s = 85, label = f"Sfc. Wind: {'{:.0f}'.format(sfc_dir)}°/{'{:.0f} kt'.format(sfc_spd)}")
	    plt.plot([sr_sfc_u, sr_u[0]], [sr_sfc_v, sr_v[0]], color="purple", linestyle = '--', linewidth = 2)

	  #Add Colorbar and Fig Text
	  CS = plt.colorbar(l, pad=0.00)
	  CS.set_label('Meters Above Radar')

	  plt.figtext(0.91, 0.9, "BS", fontsize = 14, weight = 'bold')
	  plt.figtext(0.955, 0.9, "SRH", fontsize = 14, weight = 'bold')
	  plt.figtext(1.01, 0.9, "SRW", fontsize = 14, weight = 'bold')
	  plt.figtext(1.055, 0.9, "SWζ%", fontsize = 14, weight = 'bold')
	  plt.figtext(1.11, 0.9, f"SWζ", fontsize = 14, weight = 'bold')

	  try:
	    plt.figtext(0.85,0.85, f" 0-500m:", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(0.85,0.85, f" 0-500m:", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(0.91,0.85, f"{'{:.0f}'.format(shr005)} kt", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	      plt.figtext(0.91,0.85, f"{shr005} kt", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(0.95,0.85, f"{'{:.0f}'.format(SRH05) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(0.95,0.85, f"{SRH05 * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(1.01,0.85, f"{'{:.0f}'.format(SR05)} kt", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(1.01,0.85, f"{SR05} kt", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(1.055,0.85, f"{'{:.0f}'.format(swper05) } %", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(1.055,0.85, f"{swper05} %", fontsize = 12, weight = 'bold', color = 'purple')
	  try:
	    plt.figtext(1.11,0.85, f"{'{:.3f}'.format(swvort05)} ", fontsize = 12, weight = 'bold', color = 'purple')
	  except:
	    plt.figtext(1.11,0.85, f"{swvort05} ", fontsize = 12, weight = 'bold', color = 'purple')

	  try:
	    plt.figtext(0.85,0.80, f" 0-1km: ", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(0.85,0.80, f" 0-1km: ", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	      plt.figtext(0.91,0.80, f"{'{:.0f}'.format(shr01)} kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(0.91,0.80, f"{shr01} kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(0.95,0.80, f"{'{:.0f}'.format(SRH1) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(0.95,0.80, f"{SRH1 * SRH_units}", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(1.01,0.80, f"{'{:.0f}'.format(SR1) } kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(1.01,0.80, f"{SR1} kt", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(1.055,0.80, f"{'{:.0f}'.format(swper1) } %", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(1.055,0.80, f"{swper1} %", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  try:
	    plt.figtext(1.11,0.80, f"{'{:.3f}'.format(swvort1)} ", fontsize = 12, weight = 'bold', color = 'darkorchid')
	  except:
	    plt.figtext(1.11,0.80, f"{swvort1} ", fontsize = 12, weight = 'bold', color = 'darkorchid')

	  try:
	    plt.figtext(0.85,0.75, f" 0-3km: ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(0.85,0.75, f" 0-3km: ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(0.91,0.75, f"{'{:.0f}'.format(shr03)} kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(0.91,0.75, f"{shr03} kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(0.95,0.75, f"{'{:.0f}'.format(SRH3) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(0.95,0.75, f"{SRH3 * SRH_units}", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(1.01,0.75, f"{'{:.0f}'.format(SR3) } kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(1.01,0.75, f"{SR3} kt", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(1.055,0.75, f"{'{:.0f}'.format(swper3) } %", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(1.055,0.75, f"{swper3} %", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  try:
	    plt.figtext(1.11,0.75, f"{'{:.3f}'.format(swvort3)} ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')
	  except:
	    plt.figtext(1.11,0.75, f"{swvort3} ", fontsize = 12, weight = 'bold', color = 'mediumslateblue')

	  try:
	    plt.figtext(0.85,0.70, f" 0-6km: ", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(0.85,0.70, f" 0-6km: ", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(0.91,0.70, f"{'{:.0f}'.format(shr06)} kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(0.91,0.70, f"{shr06} kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(0.95,0.70, f"{'{:.0f}'.format(SRH6) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(0.95,0.70, f"{SRH6 * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(1.01,0.70, f"{'{:.0f}'.format(SR6) } kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(1.01,0.70, f"{SR6} kt", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(1.055,0.70, f"{'{:.0f}'.format(swper6) } %", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(1.055,0.70, f"{swper6} %", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  try:
	    plt.figtext(1.11,0.70, f"{'{:.3f}'.format(swvort6)} ", fontsize = 12, weight = 'bold', color = 'mediumblue')
	  except:
	    plt.figtext(1.11,0.70, f"{swvort6} ", fontsize = 12, weight = 'bold', color = 'mediumblue')

	  try:
	    plt.figtext(0.85,0.65, f" 0-8km: ", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(0.85,0.65, f" 0-8km: ", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(0.91,0.65, f"{'{:.0f}'.format(shr08)} kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(0.91,0.65, f"{shr08} kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(0.95,0.65, f"{'{:.0f}'.format(SRH8) * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(0.95,0.65, f"{SRH8 * SRH_units:~P}", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(1.01,0.65, f"{'{:.0f}'.format(SR8) } kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(1.01,0.65, f"{SR8} kt", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(1.055,0.65, f"{'{:.0f}'.format(swper8) } %", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(1.055,0.65, f"{swper8} %", fontsize = 12, weight = 'bold', color = 'darkblue')
	  try:
	    plt.figtext(1.11,0.65, f"{'{:.3f}'.format(swvort8)} ", fontsize = 12, weight = 'bold', color = 'darkblue')
	  except:
	    plt.figtext(1.11,0.65, f"{swvort8} ", fontsize = 12, weight = 'bold', color = 'darkblue')

	  plt.figtext(0.90,0.60, "Storm Motion/Sfc Wind", fontsize = 14, weight = 'bold')

	  plt.legend(loc = 'right', bbox_to_anchor=(1.885, 0.55),
		    ncol=2, fancybox=True, shadow=True, fontsize=11, facecolor='white', framealpha=1.0,
		      labelcolor='k', borderpad=0.7)
	  rts = datetime.strftime(radar_time, "%Y-%m-%d %H:%M:%S")
	  plt.title(f'SR Hodograph from {radar_id} Valid: {rts}', fontsize = 16, weight = 'bold')

	  try:
	  #Plot SRW wrt Hgt
	    sr_plot = plt.axes((0.895, 0.10, 0.095, 0.32))
	    plt.figtext(0.94, 0.45, f'SR Wind (kts)', weight='bold', color='black', fontsize=12, ha='center')
	    sr_plot.set_ylim(0,3000)
	    sr_plot.set_xlim(sr_spd[0:31].min() -6,sr_spd[0:31].max() +6)
	    sr_plot.plot(sr_spd[0:11], zlevels[0:11], color = 'purple', linewidth = 3)
	    sr_plot.plot(sr_spd[10:31], zlevels[10:31], color = 'red', linewidth = 3)
	    plt.ylabel('Height Above Radar (m)')
	    plt.xlabel('SRW (kt)')
	    plt.grid(axis='y')
	  except:
	    pass

	  try:
	    #Plot SW Vort Perc wrt Hgt
	    swv_plot = plt.axes((1.05, 0.10, 0.095, 0.32))
	    plt.figtext(1.1, 0.45, f'SWζ%', weight='bold', color='black', fontsize=12, ha='center')
	    swv_plot.set_ylim(0,3000)
	    swv_plot.set_xlim(00,101)
	    swv_plot.plot(swvper[0:11], zlevels[0:11], color = 'purple', linewidth = 3)
	    swv_plot.plot(swvper[10:31], zlevels[10:31], color = 'red', linewidth = 3)
	    plt.ylabel('Height Above Radar (m)')
	    plt.xlabel('SWζ%')
	    plt.grid(axis='y')
	  except:
	    pass
	  #Add Title and Legend and Save Figure
	  del sfc_angle, sfc_u, sfc_v
	  sr_hodo_fp = HODO_IMAGES / f'SR_Hodograph_{radar_id}_{r_date}_{r_time}.png'
	  plt.savefig(sr_hodo_fp, bbox_inches='tight')
	  return
def execute_multiprocessing():
    # Limited to 8 processes on the AWS instance
    pool = Pool(4)
    pool.map(create_hodos, os.listdir(dir))
    pool.close()
    pool.terminate()

if __name__ == '__main__':
    freeze_support()
    print(f"Reading {len(os.listdir(dir))} radar files")
    execute_multiprocessing()
