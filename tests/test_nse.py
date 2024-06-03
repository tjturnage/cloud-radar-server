"""
Move into top-level directory to test the nse scripts. 
"""
from scripts.nse import Nse
from pathlib import Path
from datetime import datetime, timezone

current_dir = Path.cwd()
scripts_path = current_dir / 'scripts'
data_dir = current_dir / 'data'
assets_dir = current_dir / 'assets'
placefiles_dir = assets_dir / 'placefiles'

event_start_time = datetime(2024, 5, 7, 21, 45 ,second=0, tzinfo=timezone.utc)
Nse(event_start_time, 30, scripts_path, data_dir, placefiles_dir)