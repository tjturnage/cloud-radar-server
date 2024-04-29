# munger
The scripts in this repository heavily leverage Daryl Herzmann's l2munger files
Please visit https://github.com/akrherz/l2munger for extra details.

This repository has copied some files from Daryl's repository, including:
- debz.py
- get_bytes.py

grlevel2.cfg is also included because you'll need that file if you decide to set up your own
polling directory

In this repository, munger.py:
- This takes Nexrad Archive 2 files and applies l2munger so that:  
 -- times are updated to near the current time  
 -- data are remapped to a new radar location.  

"munged" files can be used for Displaced Real-Time (DRT) simulations with GR2Analyst
 Playback speed can be set so that radar files are made available slower/faster than or equal to actual time elapsed

