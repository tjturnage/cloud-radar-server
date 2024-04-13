"""
This script is used to clean the data in the radar, hodographs, and hodographs directories
This prevents the data from being stored in the git repository
"""
import os
import shutil

directories = ['data/radar', 'assets/hodographs', 'assets/hodographs']

for directory in directories:
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except (OSError, PermissionError) as e:
            print(f'Failed to delete {file_path}. Reason: {e}')