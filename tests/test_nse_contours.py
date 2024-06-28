import matplotlib.pyplot as plt
import numpy as np
import geojsoncontour
import json
import pickle 
from datetime import timedelta

def hex2rgb(hex):
    """Convert hexadecimal string to rgb tuple
    """
    h = hex.lstrip('#')
    return tuple(str(int(h[i:i+2], 16)) for i in (0, 2, 4))

with open('/Users/leecarlaw/scripts/tmp/data/sharppy.pickle', 'rb') as f: data = pickle.load(f)

arr = data[1]
lon, lat = arr['lons'], arr['lats']
fig = plt.figure()
ax = fig.add_subplot(111)
c = ax.contour(lon, lat, arr['mlcape'], [3500])
#c = ax.contour(lon, lat, arr['estp'], [0.5, 1])
segs = c.allsegs
plt.close(fig)

start = arr['valid_time'] - timedelta(seconds=1799)
end = arr['valid_time'] + timedelta(seconds=1800)

timerange_str = "%s %s" % (start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            end.strftime('%Y-%m-%dT%H:%M:%SZ'))
time_str = "Valid: %s" % (arr['valid_time'].strftime('%H:%MZ %a %b %d %Y'))
plotinfo = 'mlcape'

out = []
out.append('Title: %s | %s\n' % (plotinfo, time_str))
out.append('RefreshSeconds: 60\n')
out.append('Font: 1, 14, 1, "Arial"\n')
out.append('TimeRange: %s\n' % (timerange_str))

# Each contour level 
for s in segs:
    # Each area
    for i in s: 
        for j in i: 
            print(j)
        print('----')



#rgb = hex2rgb(feature['properties']['stroke'])