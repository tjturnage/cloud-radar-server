import matplotlib
matplotlib.use('Agg')       # Avoids Qt platform errors
import matplotlib.pyplot as plt
import numpy as np
import geojsoncontour
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
#import logging as log

import sharptab.winds as winds
from configs import ALPHA
from plotconfigs import (SCALAR_PARAMS, VECTOR_PARAMS, BUNDLES, PLOTCONFIGS, barbconfigs,
                         contourconfigs)

PARAMS = {**SCALAR_PARAMS, **VECTOR_PARAMS}

def contour(lon, lat, data, time_str, timerange_str, **kwargs):
    """
    Contour plot using geojsoncontour.

    Parameters:
    -----------
    lon : array_like
        2-D array of longitudes. Must be same shape as data
    lat : array_like
        2-D array of latitudes. Must be same shape as data
    data : array_like [N, M]
        Values over which contour is drawn.
    time_str : string
        Valid time for this plot. Included in the placefile title.
    timerange_str : string
        Valid time range over which to display in GR

    Other Parameters:
    -----------------
    levels : list, array
        Contour levels to plot.
    linewidths: list, array
        Linewidths corresponding to each contour level
    colors : color string (hexademicals)
        Colors corresponding to each contour level
    plotinfo : string
        Brief description of the plot

    Returns:
    --------
    out : list
        List of strings, each corresponding to a new line for the placefile

    """

    fig = plt.figure()
    ax = fig.add_subplot(111)

    levels = list(kwargs.get('levels'))
    colors = list(kwargs.get('colors'))
    plotinfo = kwargs.get('varname', 'None')
    linewidths = kwargs.get('linewidths')
    try:
        linewidths = list(linewidths)
    except TypeError: 
        linewidths = [linewidths]
    
    # Extend linewidths to match the length of the levels. 
    diff = len(levels) - len(colors)
    if diff > 0: linewidths.extend([linewidths[-1]] * diff)

    if levels is not None and colors is not None:
        c = None
        if np.nanmax(data) >= np.min(levels):
            c = ax.contour(lon, lat, data, levels, colors=colors)
    else:
        c = ax.contour(lon, lat, data)
    
    segments = c.allsegs
    # Get the full range of colors from the collections object 
    collections = c.collections 
    colors = [rgba_to_rgb_255(i.get_edgecolor()[0][:3]) for i in collections]

    out = []
    out.append('Title: %s | %s\n' % (plotinfo, time_str))
    out.append('RefreshSeconds: 60\n')
    out.append('Font: 1, 14, 1, "Arial"\n')
    out.append('TimeRange: %s\n' % (timerange_str))

    # Max of data array is greater than minimum contour threshold
    if c is not None:
        # Each contour level 
        for i, contour_level in enumerate(segments):
            level = levels[i] 
            color = colors[i] 

            # Each area
            for element in contour_level: 
                if len(element) > 0:
                    clabs = defaultdict(list)
                    out.append(f'Color: {color[0]} {color[1]} {color[2]} 255\n')
                    out.append(f'Line: {linewidths[i]}, 0, "{plotinfo}: {level}"\n')
                    
                    knt = 0
                    for coord in element: 
                        out.append(f' {coord[1]}, {coord[0]}\n')
                        if knt % 30 == 0: clabs[levels[i]].append([coord[1], coord[0]])
                        knt += 1
                    out.append('End:\n\n')

                    for lev in clabs.keys():
                        for val in clabs[lev]:
                            if float(lev) >= 9: lev = int(float(lev))
                            out.append('Text: %s, %s, 1, "%s", ""\n' % (val[0], val[1], lev))
                            out.append(f'Text: {val[0]}, {val[1]}, 1, {lev}, ""\n')
                    out.append('\n')
    
    # Close the plotting figure
    plt.close(fig)
    
    # No contour values found. Would otherwise result in a
    # UserWarning: No contour levels were found within the data range
    #else:
    #    out = ["\n"]
    return out

'''
def contour(lon, lat, data, time_str, timerange_str, **kwargs):
    """
    Contour plot using geojsoncontour.

    Parameters:
    -----------
    lon : array_like
        2-D array of longitudes. Must be same shape as data
    lat : array_like
        2-D array of latitudes. Must be same shape as data
    data : array_like [N, M]
        Values over which contour is drawn.
    time_str : string
        Valid time for this plot. Included in the placefile title.
    timerange_str : string
        Valid time range over which to display in GR

    Other Parameters:
    -----------------
    levels : list, array
        Contour levels to plot.
    linewidths: list, array
        Linewidths corresponding to each contour level
    colors : color string (hexademicals)
        Colors corresponding to each contour level
    plotinfo : string
        Brief description of the plot

    Returns:
    --------
    out : list
        List of strings, each corresponding to a new line for the placefile

    """

    fig = plt.figure()
    ax = fig.add_subplot(111)

    levels = kwargs.get('levels')
    colors = kwargs.get('colors')
    plotinfo = kwargs.get('varname', 'None')
    linewidths = kwargs.get('linewidths')

    if levels is not None and colors is not None:
        c = None
        if np.nanmax(data) >= np.min(levels):
            c = ax.contour(lon, lat, data, levels, colors=colors)
    else:
        c = ax.contour(lon, lat, data)

    out = []
    out.append('Title: %s | %s\n' % (plotinfo, time_str))
    out.append('RefreshSeconds: 60\n')
    out.append('Font: 1, 14, 1, "Arial"\n')
    out.append('TimeRange: %s\n' % (timerange_str))

    # Max of data array is greater than minimum contour threshold
    if c is not None:
        geojson = json.loads(geojsoncontour.contour_to_geojson(contour=c, ndigits=2))

        #clabs = defaultdict(list) # Store contour labels
        for feature in geojson['features']:
            clabs = defaultdict(list) # Store contour labels
            coords = feature['geometry']['coordinates']
            level = '%s' % (round(feature['properties']['level-value'], 1))
            idx = feature['properties']['level-index']
            if int(levels[idx]) == int(float(level)):
                try:
                    lws = list(kwargs['linewidths'])
                    linewidth = lws[idx]
                except:
                    linewidth = kwargs['linewidths']
            else:
                linewidth = 1

            rgb = hex2rgb(feature['properties']['stroke'])
            out.append('Color: %s 255\n' % (' '.join(rgb)))
            out.append('Line: %s, 0, "%s: %s"\n' % (linewidth, plotinfo, level))

            KNT = 0
            for coord in coords:
                out.append(' %s, %s\n' % (coord[1], coord[0]))
                if KNT % 30 == 0: clabs[level].append([coord[1], coord[0]])
                KNT += 1
            out.append('End:\n\n')

            # Contour labels
            for lev in clabs.keys():
                for val in clabs[lev]:
                    if float(lev) >= 9: lev = int(float(lev))
                    out.append('Text: %s, %s, 1, "%s", ""\n' % (val[0], val[1], lev))
            out.append('\n')

        plt.close(fig)

    # No contour values found. Would otherwise result in a
    # UserWarning: No contour levels were found within the data range
    #else:
    #    out = ["\n"]

    return out
'''

def contourf(lon, lat, data, time_str, timerange_str, **kwargs):
    """Contour-filled plot. Updates to attempt to limit "cross-over" lines when plotting
    Polygons in GR.

    Parameters:
    -----------
    lon : array_like
        2-D array of longitudes. Must be same shape as data
    lat : array_like
        2-D array of latitudes. Must be same shape as data
    data : array_like [N, M]
        Values over which contour fill is drawn
    time_str : string
        Valid time for this plot. Included in the placefile title
    timerange_str : string
        Valid time range over which to display in GR

    Other Parameters:
    -----------------
    levels : list, array
        Number and positions of the contour lines / regions
    colors : color string (hexademicals)
        Colors corresponding to each contour-fill level
    plotinfo : string
        Brief description of the plot

    Returns:
    --------
    out : list
        List of strings, each corresponding to a new line for the placefile

    """

    fig = plt.figure()
    ax = fig.add_subplot(111)

    levels = kwargs.get('fill_levels')
    colors = kwargs.get('fill_colors')
    plotinfo = kwargs.get('varname', 'None')

    c = ax.contourf(lon, lat, np.where(data < levels[0], np.nan, data))

    out = []
    out.append('Title: %s Filled Contour | %s\n' % (plotinfo, time_str))
    out.append('RefreshSeconds: 60\n')
    out.append('TimeRange: %s\n' % (timerange_str))
    rgb = hex2rgb(colors[0])
    for collection in c.collections:
        for path in collection.get_paths():
            coords = path.vertices
            if len(coords) < 3:
                continue
            out.append('Polygon:\n')
            first_line = True
            for i in range(len(coords)):
                COLOR = ""
                if first_line:
                    COLOR ='%s, %s' % (', '.join(rgb), ALPHA)
                out.append(f" {coords[i][1]}, {coords[i][0]}, {COLOR}\n")
                first_line = False
            out.append("End:\n")
            out.append("\n")
    plt.close(fig)
    return out

def write_placefile(arrs, output_path, realtime=False):
    """
    Main function controlling the plotting of GR2/Analyst-readable placefiles. Called
    by the primary run.py script.

    Parameters:
    -----------
    arrs : dictionary
        List of dictionaries storing values necessary for plotting. This includes
        longitudes, latitudes, valid times, and any 2-d arrays. Each list entry
        corresponds to a new forecast time.
    output_path : string
        Full path describing where to save placefiles. 

    Other Parameters:
    -----------------
    realtime: bool (default: False)
        If this is a realtime run (True), appends the valid time to the end of the
        filename.

    """
    parms = list(SCALAR_PARAMS.keys()) + list(VECTOR_PARAMS.keys())
    out_dict = defaultdict(list)

    for i in range(len(arrs)):
        arr = arrs[i]
        lon, lat = arr['lons'], arr['lats']
        valid_str = "Valid: %s" % (arr['valid_time'].strftime('%H:%MZ %a %b %d %Y'))

        # Construct the time range string

        if realtime is True:
            start = arr['valid_time'] - timedelta(minutes=15)
            end = arr['valid_time'] + timedelta(minutes=15)
        elif not realtime:
            start = arr['valid_time'] - timedelta(seconds=1799)
            end = arr['valid_time'] + timedelta(seconds=1800)
        else:   # For special testing mode.
            start = datetime(2000, 1, 1, 0)
            end = datetime(2300, 1, 1, 0)

        timerange_str = "%s %s" % (start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                   end.strftime('%Y-%m-%dT%H:%M:%SZ'))
        #time_str = "%sZ RAP" % (str(arr['cycle_time'].hour).zfill(2))

        out_parms = []
        for parm in parms:
            plot_type = None
            if parm in VECTOR_PARAMS.keys():
                plot_type = 'barb'
                base_configs = barbconfigs
            else:
                base_configs = contourconfigs

            # Add any user-requested ploting configurations to the base. Add the variable
            # name to the configuration dictionary.
            configs = base_configs.copy()
            if parm in PLOTCONFIGS:
                config_overrides = PLOTCONFIGS[parm]
                configs.update(config_overrides)
            configs['varname'] = PARAMS[parm]

            # If plot_type hasn't been assigned yet, this is either a filled or contoured
            # SCALAR parameter
            if not plot_type:
                if configs['fill_levels'] or configs['fill_colors']:
                    plot_type = 'contourf'
                else:
                    plot_type = 'contour'

            # Contour plots
            if plot_type == 'contour':
                out = contour(lon, lat, arr[parm], valid_str, timerange_str, **configs)

            # Filled contour plots
            elif plot_type == 'contourf':

                # Always want contoured output.
                out = contour(lon, lat, arr[parm], valid_str, timerange_str, **configs)
                out_dict[parm].extend(out)

                out = contourf(lon, lat, arr[parm], valid_str, timerange_str, **configs)
                parm = "%s_cf" % (parm)

            # Barb plots
            elif plot_type == 'barb':

                if parm not in ['devtor']:
                    out = barbs(lon, lat, arr[parm+'_u'], arr[parm+'_v'], valid_str,
                                timerange_str, **configs)
                else:
                    out = barbs_devtor(lon, lat, arr[parm+'_u'], arr[parm+'_v'],
                                       arr['deviance'], valid_str, timerange_str,
                                        **configs)
            else:
                raise ValueError("%s is an invalid plot_type entry" % (plot_type))
            out_dict[parm].extend(out)

    save_time = None
    for parm in out_dict.keys():
        output = out_dict[parm]
        #if not realtime:
        #    save_time = "%s-%s" % (arrs[0]['valid_time'].strftime('%Y%m%d%H'),
        #                           arrs[-1]['valid_time'].strftime('%Y%m%d%H'))
        #    out_file = '%s/%s_%s.txt' % (output_path, parm, save_time)
        #else:
        out_file = '%s/%s.txt' % (output_path, parm)
        with open(out_file, 'w') as f: f.write("".join(output))

    # Write any bundled placefiles
    write_bundles(save_time, output_path)

def write_bundles(save_time, output_path):
    """
    Write out bundled placefiles. Works for archived runs.

    GR (at least GR2Analyst v2.8) can display multiple placefiles that have been
    concatenated together. The "first" file will display on the bottom of the bundled
    stack, while the "last" file will display on top.

    """
    def replace_title_lines():
        """
        Inner function that searches through each placefile and replaces the title string
        """
        indices = [i for i in range(len(lines)) if 'Title:' in lines[i]]
        for idx in indices:
            mark = lines[idx].rfind('|')
            lines[idx] = "Title: %s Bundle %s" % (bundle_name, lines[idx][mark:])
        return lines

    # If entries exist in the BUNDLES dictionary, output bundled placefiles
    for bundle_name, parameters in BUNDLES.items():
        #log.info("Writing bundle: %s with components: %s" % (bundle_name, parameters))
        bundle_file = '%s/%s.txt' % (output_path, bundle_name)
        #if save_time:
        #    bundle_file = '%s/%s_%s.txt' % (output_path, bundle_name, save_time)

        with open(bundle_file, 'w') as f:
            for parm in parameters:
                filename = '%s/%s.txt' % (output_path, parm)
                if save_time:
                    filename = '%s/%s_%s.txt' % (output_path, parm, save_time)
                try:
                    in_file = open(filename, 'r')
                    lines = in_file.readlines()
                    lines = replace_title_lines()
                    f.write("".join(lines))
                except IOError:
                    pass
                    #log.error("%s not found. Skipped during bundling step" % (in_file))

def barbs(lon, lat, U, V, time_str, timerange_str, **kwargs):
    """
    Write out a wind barb placefile.

    Parameters:
    -----------
    lon : array_like
        2-D array of longitudes. Must be same shape as data
    lat : array_like
        2-D array of latitudes. Must be same shape as data
    U : array_like
        u-wind components
    V : array_like
        v-wind components
    time_str : string
        Valid time for this plot. Included in the placefile title
    timerange_str : string
        Valid time range over which to display in GR

    Other Parameters:
    -----------------
    windicons : string
        Path or url containing the wind icons referenced in this placefile
    varname : string
        Parameter information
    skip : int
        Number of wind barbs to skip in the i and j directions

    Returns:
    --------
    out : list
        List of strings, each corresponding to a new line for the placefile

    """
    iconfile = kwargs.get('windicons', 'Missing: Specify `WIND_ICONDS` in cofigs.py!')
    plotinfo = kwargs.get('varname', 'None')
    skip = kwargs.get('skip', 6)
    out = []
    out.append('Title: %s | %s\n' % (plotinfo, time_str))
    out.append('RefreshSeconds: 60\n')
    out.append('TimeRange: %s\n' % (timerange_str))
    out.append('Color: 255 255 255\n')
    out.append('IconFile: 1, 28, 28, 14, 14, "%s"\n' % (iconfile))
    out.append('Font: 1, 10, 4, "Arial"\n\n')
    for j in range(U.shape[0])[::skip]:
        for i in range(V.shape[1])[::skip]:
            wdir, wspd = winds.comp2vec(float(U[j,i]), float(V[j,i]))
            wspd = np.clip(wspd, 2.5, 52) # For time being, limit max storm speed
            if wspd > 0:
                wspd_rounded = 5 * round(wspd/5)
                numref = int(wspd_rounded//5)
                out.append('Object: ' + str(lat[j,i]) + ',' + str(lon[j,i]) +'\n')
                out.append('  Threshold: 999\n')
                out.append('  Icon: 0,0,%s,1,%s,%s: %s\n' % (wdir, np.clip(numref,1,999),
                                                             plotinfo, round(wspd,1)))
                out.append('End:\n\n')
    return out

def barbs_devtor(lon, lat, U, V, deviance, time_str, timerange_str, **kwargs):
    """
    Write out a wind barb placefile. This is an override to plot deviant tornado vectors
    while color-coding based on the deviance scalar.

    Parameters:
    -----------
    lon : array_like
        2-D array of longitudes. Must be same shape as data
    lat : array_like
        2-D array of latitudes. Must be same shape as data
    U : array_like
        u-wind components
    V : array_like
        v-wind components
    deviance : array_like
        Relative deviance (scalar)
    time_str : string
        Valid time for this plot. Included in the placefile title
    timerange_str : string
        Valid time range over which to display in GR

    Other Parameters:
    -----------------
    windicons : string
        Path or url containing the wind icons referenced in this placefile
    varname : string
        Parameter information
    skip : int
        Number of wind barbs to skip in the i and j directions

    Returns:
    --------
    out : list
        List of strings, each corresponding to a new line for the placefile

    """
    iconfile = kwargs.get('windicons', 'Missing: Specify `DEVTOR_ICONS` in cofigs.py!')
    plotinfo = kwargs.get('varname', 'None')
    skip = kwargs.get('skip', 3)
    out = []
    out.append('Title: %s | %s\n' % (plotinfo, time_str))
    out.append('RefreshSeconds: 60\n')
    out.append('TimeRange: %s\n' % (timerange_str))
    out.append('Color: 255 255 255\n')
    out.append('IconFile: 1, 28, 28, 14, 14, "%s"\n' % (iconfile))
    out.append('Font: 1, 10, 4, "Arial"\n\n')
    for j in range(U.shape[0])[::skip]:
        for i in range(V.shape[1])[::skip]:
            wdir, wspd = winds.comp2vec(float(U[j,i]), float(V[j,i]))
            wspd = np.clip(wspd, 2.5, 52)
            if wspd > 2.5 and deviance[j,i] >= 0.5:
                # Determine reference column based on deviant tornado motion speed. 
                wspd_rounded = 5 * round(wspd/5)
                column = int(wspd_rounded//5)

                # ========================================================================
                # Row and column lookup logic will need to change if the number of barbs
                # in the DEVTOR_ICONS file change!
                # ========================================================================
                rounded_deviance = np.clip(round(deviance[j,i]*4) / 4, 0, 2)
                row = (rounded_deviance//.25) - 3
                row = np.clip(row, 0, 4)
                numref = column + (row * 10)

                out.append('Object: ' + str(lat[j,i]) + ',' + str(lon[j,i]) +'\n')
                out.append('  Threshold: 999\n')

                # Override the plotinfo string for the deviant tornado motion vectors.
                # Add relative deviance and speed to the output text string.
                info = f"Deviance: {round(deviance[j,i],2)} | Speed: {round(wspd,1)}"
                infostring = f"{plotinfo}: {info}"
                out.append(f"  Icon: 0,0,{wdir},1,{numref},{infostring}\n")
                out.append('End:\n\n')
    return out

def rgba_to_rgb_255(rgba):
    return tuple(int(rgba[i] * 255) for i in range(3))

def hex2rgb(hex):
    """Convert hexadecimal string to rgb tuple
    """
    h = hex.lstrip('#')
    return tuple(str(int(h[i:i+2], 16)) for i in (0, 2, 4))
