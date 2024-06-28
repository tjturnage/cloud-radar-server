import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import geojsoncontour
import json
import pickle 
from datetime import timedelta
from collections import defaultdict 

def hex2rgb(hex):
    """Convert hexadecimal string to rgb tuple
    """
    h = hex.lstrip('#')
    return tuple(str(int(h[i:i+2], 16)) for i in (0, 2, 4))

def rgba_to_rgb_255(rgba):
    return tuple(int(rgba[i] * 255) for i in range(3))

with open('/Users/leecarlaw/scripts/tmp/data/sharppy.pickle', 'rb') as f: data = pickle.load(f)

arr = data[1]
lon, lat = arr['lons'], arr['lats']
fig = plt.figure()
ax = fig.add_subplot(111)

###################################################
levels = [100, 250, 500, 1000, 2000, 2500, 3000, 3500, 4000]
colors = ['#ea908c', '#ea908c', '#da453a', '#da453a', '#da453a', '#c03c32']
linewidths = [1, 1, 1, 2, 2, 3, 3, 3, 3]
plotinfo = 'Mixed-Layer CAPE (J/kg)'
start = arr['valid_time'] - timedelta(seconds=1799)
end = arr['valid_time'] + timedelta(seconds=1800)
timerange_str = "%s %s" % (start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            end.strftime('%Y-%m-%dT%H:%M:%SZ'))
time_str = "Valid: %s" % (arr['valid_time'].strftime('%H:%MZ %a %b %d %Y'))
###################################################

c = ax.contour(lon, lat, arr['mlcape'], levels, colors=colors)
collections = c.collections 
colors = [rgba_to_rgb_255(i.get_edgecolor()[0][:3]) for i in collections]



plt.savefig('test.png', dpi=300, bbox_inches='tight')
segs = c.allsegs
plt.close(fig)

out = []
out.append('Title: %s | %s\n' % (plotinfo, time_str))
out.append('RefreshSeconds: 60\n')
out.append('Font: 1, 14, 1, "Arial"\n')
out.append('TimeRange: %s\n' % (timerange_str))

# Each contour level 
for i, contour_level in enumerate(segs):
    level = levels[i] 
    color = colors[i] 

    # Each area
    for element in contour_level: 
        clabs = defaultdict(list)
        #rgb = hex2rgb(color)
        #out.append('Color: %s 255\n' % (' '.join(rgb)))
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

with open('/Users/leecarlaw/scripts/cloud-radar-server/tests/mlcape_test.txt', 'w') as f: 
    f.write("".join(out))