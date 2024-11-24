"""
This script processes input files to convert times and extract values.
"""
import sys
from dataclasses import dataclass


HEAD = """<!DOCTYPE html>
<html>
<head>
<title>Links</title>
<link rel="icon" href="https://rssic.nws.noaa.gov/assets/favicon.ico" type="image/x-icon">
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootswatch/4.5.2/cyborg/bootstrap.min.css">
<style>
a {
    font-size: 1.3em; /* Adjust the font size as needed */
}
.obs
{
    color:#eeeeee;
}
</style>
</head>
<body>
"""

INSTRUCTIONS = """<div class="instr"></div>"""

TAIL = """<br><br><br><br>
</body>
</html>"""

obs = {'latest_surface_observations': 'Surface obs -- regular font',
       'latest_surface_observations_lg': 'Surface obs -- large font',
        'latest_surface_observations_xlg': 'Surface obs -- extra large font',
        'temp': 'Temperature',
        'dwpt': 'Dewpoint',
        'rh': 'Relative Humidity',
        'vsby': 'Visibility',
        'wind': 'Wind and Gusts'}

reports = {'LSRs': 'Local Storm Reports',
        'Events': 'Events (available only if a csv was successfully uploaded)'}

stability = {
    'cape3km': '0-3km MLCAPE',
    'cape3km_cf': '0-3km MLCAPE (color filled)',
    'mlcape': 'Mixed Layer CAPE (Lowest 100mb)',
    'mlcin': 'Mixed Layer Convective Inhibition (Lowest 100mb)',
    'mlcin_cf': 'Mixed Layer Convective Inhibition (color filled)',
    'mllcl': 'Mixed Layer Lifted Condensation Level (Lowest 100mb)',
    'mucape': 'Most Unstable CAPE (Lowest 300mb)',
    'dcape': 'Downdraft CAPE',
    'lr03km': '0-3km Lapse Rate',
    'lr03km_cf': '0-3km Lapse Rate (color filled)'
}

shear = {
    'ebwd': 'Effective Bulk Shear',
    'esrh': 'Effective Storm Relative Helicity',
    'estp': 'Effective Sig Tor Parameter',
    'rm5': 'Right Mover 5km',
    'shr1': '0-1km Shear',
    'shr3': '0-3km Shear',
    'shr6': '0-6km Shear',
    'shr8': '0-8km Shear',
    'srh01km': '0-1km Storm Relative Helicity 0-1km',
    'srh500': '0-500m Storm Relative Helicity 500m',
}

comp = {
    'estp': 'Effective Sig Tor Parameter',
    'nst': 'Non-Supercell Tornado Parameter',
    'devtor': 'Deviant Tornado Motion',  
    'deviance': 'Perceived Tornado Deviance',
    'ProbSevere': 'CIMSS ProbSevere v2',
    'rm5': 'Bunkers Right Motion Vectors',
    'lm5': 'Bunkers Left Motion Vectors',
    'snsq': 'Snow Squall Parameter'
}

links = {'hodographs.html': 'Hodographs Browser Page',
         'original_radar_files.zip': 'Download original radar files',
         'original_placefiles.zip': 'Download original placefiles'}

@dataclass
class WriteLinksPage():
    """
    A class to write a shareable links page for simulation participants not having access to the
    main RSSiC user interface
    """
    assets_dir:         str   #  Input   --  unique id of session related to epoch time
    place_link:         str   #  Input   --  html address of placefiles
    polling_dir:        str   #  Input   --  directory for radar polling
    links_page:         str   #  Input   --  html page to be written to


    def __post_init__(self):
        self.create_links_page()


    def write_placefile_section(self,title,files,fout):
        """
        writes a section for placefiles
        """
        fout.write('<br>\n')
        fout.write(f'<h3>{title}</h3>\n')
        for key, value in files.items():
            placename = f'{key}_updated.txt'
            fout.write(f'<a href="{self.place_link}/{placename}">{value}</a></br>\n')
    
    def create_links_page(self) -> None:
        """
        creates the links page ... can be done all at once
        """
        #with open(self.links_page, 'w', encoding='utf-8') as fout:
        with open(self.links_page, 'w', encoding='utf-8') as fout:
            fout.write(HEAD)
            fout.write('<br><br>\n')
                       
            fout.write('<h3>Copy this polling link into GR2Analyst</h3>\n')
            polling_link = f'{self.assets_dir}/polling'
            fout.write(f'<h4><a href="{polling_link}">{polling_link}</a></h4>\n<br>\n')
            titles = ['Observations','Reports','Stability','Shear','Composite']
            for title, files in zip(titles,[obs,reports,stability,shear,comp]):
                self.write_placefile_section(title,files,fout)

            fout.write('<br>')
            fout.write('<h3>Links</h3>\n')
            for key, value in links.items():
                fout.write(f'<a href="{self.assets_dir}/{key}">{value}</a></br>\n')

            fout.write(TAIL)


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        session_id = '1234567890'
        assets_dir = f'https://rssic.nws.noaa.gov/assets/{session_id}'
        placefile_links = f'{assets_dir}/placefiles'
        #configs['PLACEFILES_LINKS']
        polling_dir = f'{assets_dir}/polling'
        FOUT = 'C:/data/links.html'
        links_page = WriteLinksPage(assets_dir, placefile_links, polling_dir, FOUT)
    else:
        #cfg['ASSETS_DIR'], cfg['PLACEFILES_LINKS'], cfg['POLLING_DIR'], cfg['LINKS_HTML_PAGE']
        links_page = WriteLinksPage(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
