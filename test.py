from pathlib import Path
from datetime import datetime
import pytz

timestring = datetime.strftime(datetime.utcnow(),"%Y-%m-%d %H:%M:%S UTC")
print(timestring)
#current = Path.cwd().parents[0]
#print(current)