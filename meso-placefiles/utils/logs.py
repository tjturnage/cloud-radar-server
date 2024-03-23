import os
import logging
from configs import LOG_DIR

def logfile(logname):
    """
    Initiate a logging instance and pass back for writing to the file system.

    """
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    logging.basicConfig(filename="%s/%s.log" % (LOG_DIR, logname),
                        format='%(levelname)s %(asctime)s :: %(message)s',
                        datefmt="%Y-%m-%d %H:%M:%S")
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    return log
