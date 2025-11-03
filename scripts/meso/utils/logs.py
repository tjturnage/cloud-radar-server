import os
import logging
import time 
#from configs import LOG_DIR
logging.Formatter.converter = time.gmtime  # Global change to UTC

def logfile(logname, log_dir):
    """
    Initiate a logging instance and pass back for writing to the file system.

    """
    if not os.path.exists(log_dir): os.makedirs(log_dir)
    logging.basicConfig(filename="%s/%s.log" % (log_dir, logname),
                        format='%(levelname)s %(asctime)s :: %(message)s',
                        datefmt="%Y-%m-%d %H:%M:%S")
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    return log
