"""
This script is used to clean the data in the radar, hodographs, and hodographs directories
This prevents the data from being stored in the git repository
"""
import os


dirs = ['data/radar', 'data/model_data', 'data/logs', 'assets/hodographs', 
        'assets/placefiles']

for directory in dirs:
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
