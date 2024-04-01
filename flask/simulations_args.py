# Imports
import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



parser = argparse.ArgumentParser()
parser.add_argument("--start_time", nargs="+")
parser.add_argument("--duration", nargs="+")
parser.add_argument("--radar_list", nargs="+")


args = parser.parse_args()



def main():
    """ 
    """
    return



#EXECUTE THIS BY RUNNING FSW_NAMELIST.py
if __name__ == "__main__":
    main()