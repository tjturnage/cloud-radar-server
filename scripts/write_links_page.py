"""
This script processes input files to convert times and extract values.
"""
import sys
from dataclasses import dataclass

PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Links</title>
<link rel="icon" href="https://rssic.nws.noaa.gov/assets/favicon.ico" type="image/x-icon">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/cyborg/bootstrap.min.css">
<style>
a {
    font-size: 1.1em; /* Adjust the font size as needed */
}
h3 {
    font-weight: bold;
    }
h4 {
    font-size: 1.8em;
    color: yellow;
    }
</style>
</head>
<body>
<div class="container">
    <br><br>
    <h3>Open these links for reference</h3>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/hodographs.html" target="_blank">Hodographs Page</a></div>
        <div class="p-2"><a href="https://docs.google.com/document/d/1uAcsjzjTAl6SA4dKgcj3pIpM__X-yfH0OGVsdam4dQw/edit" target="_blank">RSSiC Guide</a></div>
    </div>
    <br><hr><br>
    <h3>Right-click link to copy polling address into GR2Analyst</h3>
    <h4><a href="[address]/polling" target="_blank">[address]/polling</a></h4>
    <br><hr><br>
    <h3>Copy desired placefiles links below into GR2Analyst</h3>
    <br>
    <div class="container">
    <div class="container">
    <h4>Surface Obs</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/latest_surface_observations_updated.txt" target="_blank">Regular font</a></div>
        <div class="p-2"><a href="[address]/placefiles/latest_surface_observations_lg_updated.txt" target="_blank">Large font</a></div>
        <div class="p-2"><a href="[address]/placefiles/latest_surface_observations_xlg_updated.txt" target="_blank">Extra Large font</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/temp_updated.txt" target="_blank">Temperature</a></div>
        <div class="p-2"><a href="[address]/placefiles/dwpt_updated.txt" target="_blank">Dewpoint</a></div>
        <div class="p-2"><a href="[address]/placefiles/rh_updated.txt" target="_blank">Relative Humidity</a></div>
        <div class="p-2"><a href="[address]/placefiles/vsby_updated.txt" target="_blank">Visibility</a></div>
        <div class="p-2"><a href="[address]/placefiles/wind_updated.txt" target="_blank">Wind and Gusts</a></div>
    </div>
    <br>
    <h4>Reports</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/LSRs_updated.txt" target="_blank">LSRs</a></div>
        <div class="p-2"><a href="[address]/placefiles/Events_updated.txt" target="_blank">Events (available only if csv was uploaded)</a></div>
    </div>
    <br>
    <h4>Stability</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/cape3km_updated.txt" target="_blank">0-3km MLCAPE</a></div>
        <div class="p-2"><a href="[address]/placefiles/cape3km_cf_updated.txt" target="_blank">0-3km MLCAPE (color filled)</a></div>
        <div class="p-2"><a href="[address]/placefiles/lr03km_updated.txt" target="_blank">0-3km Lapse Rate</a></div>
        <div class="p-2"><a href="[address]/placefiles/lr03km_cf_updated.txt" target="_blank">0-3km Lapse Rate (color filled)</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/mlcape_updated.txt" target="_blank">MLCAPE</a></div>
        <div class="p-2"><a href="[address]/placefiles/mucape_updated.txt" target="_blank">MUCAPE</a></div>
        <div class="p-2"><a href="[address]/placefiles/dcape_updated.txt" target="_blank">DCAPE</a></div>
        <div class="p-2"><a href="[address]/placefiles/mllcl_updated.txt" target="_blank">MLLCL</a></div>
        <div class="p-2"><a href="[address]/placefiles/mlcin_updated.txt" target="_blank">MLCIN</a></div>
        <div class="p-2"><a href="[address]/placefiles/mlcin_cf_updated.txt" target="_blank">MLCIN (color filled)</a></div>

    </div>
    <br>
    <h4>Shear</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/esrh_updated.txt" target="_blank">Effective SRH</a></div>
        <div class="p-2"><a href="[address]/placefiles/srh01km_updated.txt" target="_blank">0-1km SRH</a></div>
        <div class="p-2"><a href="[address]/placefiles/srh500_updated.txt" target="_blank">0-500m SRH</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/ebwd_updated.txt" target="_blank">Effective Shear</a></div>
        <div class="p-2"><a href="[address]/placefiles/shr1_updated.txt" target="_blank">0-1km Shear</a></div>
        <div class="p-2"><a href="[address]/placefiles/shr3_updated.txt" target="_blank">0-3km Shear</a></div>
        <div class="p-2"><a href="[address]/placefiles/shr6_updated.txt" target="_blank">0-6km Shear</a></div>
        <div class="p-2"><a href="[address]/placefiles/shr8_updated.txt" target="_blank">0-8km Shear</a></div>

    </div>
    <br>
    <h4>Composite</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/estp_updated.txt" target="_blank">Effective Sig Tor Parameter</a></div>
        <div class="p-2"><a href="[address]/placefiles/nst_updated.txt" target="_blank">Non-Supercell Tornado Parameter</a></div>
        <div class="p-2"><a href="[address]/placefiles/ProbSevere_updated.txt" target="_blank">CIMSS ProbSevere v2</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/rm5_updated.txt" target="_blank">Bunkers RM Vectors</a></div>
        <div class="p-2"><a href="[address]/placefiles/lm5_updated.txt" target="_blank">Bunkers LM Vectors</a></div>
        <div class="p-2"><a href="[address]/placefiles/devtor_updated.txt" target="_blank">Deviant Tornado Motion</a></div>
        <div class="p-2"><a href="[address]/placefiles/deviance_updated.txt" target="_blank">Perceived Tornado Deviance</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/placefiles/snsq_updated.txt" target="_blank">Snow Squall Parameter</a></div>
    </div>
    <br>
    </div></div>
</div>
<br><br>
</body>
</html>
"""

@dataclass
class WriteLinksPage():
    """
    A class to write a shareable links page for simulation participants not having access to the
    main RSSiC user interface
    """
    link_base:      str   #  Input   --  html base link associated with this session
    links_page:     str   #  Input   --  full filepath of links.html page to be created

    def __post_init__(self):
        self.create_links_page()

    def create_links_page(self) -> None:
        """
        creates the links page ... can be done all at once
        """
        with open(self.links_page, 'w', encoding='utf-8') as fout:
            fout.write(PAGE.replace('[address]',self.link_base))


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        session_id = '1234567890'
        link_base = f'https://rssic.nws.noaa.gov/assets/{session_id}'
        FOUT = 'C:/data/links.html'
        links_page = WriteLinksPage(link_base, FOUT)
    else:
        #cfg['LINK_BASE'], cfg['LINKS_HTML_PAGE']
        links_page = WriteLinksPage(sys.argv[1], sys.argv[2])
