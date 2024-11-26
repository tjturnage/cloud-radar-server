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
    color: #bbbbbb;
    }
.nse {
    font-size: 1.2em;
    color: #bdaf35;
    text-decoration: none; /* Remove underline */
}
.nse:hover {
    color: #FFFF00; /* Change color on hover */
}
.obs {
    font-size: 1.2em;
    color: #10c4c4;
    text-decoration: none; /* Remove underline */
}
.obs:hover {
    color: #33ffff; /* Change color on hover */
}
.rpts {
    font-size: 1.2em;
    color: #cc6666;
    text-decoration: none; /* Remove underline */
}
.main-title {
    font-size: 2.2em;
    color: #cccccc;
    font-weight: bold;
    }
.title {
    font-size: 1.5em;
    color: #bdaf35;
    font-weight: bold;
    }
.desc {
    font-size: 1.0em;
    color: #cccccc;
    }
.rpts:hover {
    color: #ffaaaa; /* Change color on hover */
}
.no_underline {
    text-decoration: none; /* Remove underline */
}
.nse:hover {
    color: #FFFF00; /* Change color on hover */
}
.flex-image {
    width: 100%; /* Make the image flexible in size */
    max-width: 800px; /* Optional: Set a maximum width */
    height: auto; /* Maintain aspect ratio */
}
</style>
</head>
<body>

<div class="container">
    <br>
    <h1>RSSiC Simulation Links</h1>
    <hr>
    <h3><a class="no_underline" href="https://docs.google.com/document/d/1uAcsjzjTAl6SA4dKgcj3pIpM__X-yfH0OGVsdam4dQw/edit" target="_blank">RSSiC User Guide</a></h3>
    <hr><br>
    <h3>Right-click polling link and copy address into GR2Analyst</h3>
    <p><i><a class="no_underline" href="https://rssic.nws.noaa.gov/assets/docs/GR2Analyst_Polling_Guide.pdf" target="_blank">(GR2Analyst polling settings guide)</a></i></p>
    <h4><a href="[address]/polling" target="_blank">[address]/polling</a></h4>
    <br><hr><br>
    <h3>Left-click link to open simulation hodographs page</h3>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a href="[address]/hodographs.html" target="_blank">Hodographs Page</a></div>
    </div>
    <br><hr><br>

    <h3>Right-click links to copy desired placefiles into GR2Analyst</h3>
    <p><i><a class="no_underline" href="https://rssic.nws.noaa.gov/assets/docs/GR2Analyst_Placefiles_Guide.pdf" target="_blank">(GR2Analyst placefile settings guide)</a></i></p>
    <br>
    <div class="container">
    <div class="container">
    <h4>Surface Obs</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="obs" href="[address]/placefiles/latest_surface_observations_updated.txt" target="_blank">Regular font</a></div>
        <div class="p-2"><a class="obs" href="[address]/placefiles/latest_surface_observations_lg_updated.txt" target="_blank">Large font</a></div>
        <div class="p-2"><a class="obs" href="[address]/placefiles/latest_surface_observations_xlg_updated.txt" target="_blank">Extra Large font</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="obs" href="[address]/placefiles/temp_updated.txt" target="_blank">Temperature</a></div>
        <div class="p-2"><a class="obs" href="[address]/placefiles/dwpt_updated.txt" target="_blank">Dewpoint</a></div>
        <div class="p-2"><a class="obs" href="[address]/placefiles/rh_updated.txt" target="_blank">Relative Humidity</a></div>
        <div class="p-2"><a class="obs" href="[address]/placefiles/vsby_updated.txt" target="_blank">Visibility</a></div>
        <div class="p-2"><a class="obs" href="[address]/placefiles/wind_updated.txt" target="_blank">Wind and Gusts</a></div>
    </div>
    <br>
    <h4>Reports</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="rpts" href="[address]/placefiles/LSRs_updated.txt" target="_blank">LSRs</a></div>
        <div class="p-2"><a class="rpts" href="[address]/placefiles/Events_updated.txt" target="_blank">Events (available only if csv was uploaded)</a></div>
    </div>
    <br>
    <h4>Instability</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="nse" href="[address]/placefiles/cape3km_updated.txt" target="_blank">0-3km MLCAPE</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/cape3km_cf_updated.txt" target="_blank">0-3km MLCAPE (color filled)</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/lr03km_updated.txt" target="_blank">0-3km Lapse Rate</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/lr03km_cf_updated.txt" target="_blank">0-3km Lapse Rate (color filled)</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="nse" href="[address]/placefiles/mlcape_updated.txt" target="_blank">MLCAPE</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/mucape_updated.txt" target="_blank">MUCAPE</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/dcape_updated.txt" target="_blank">DCAPE</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/mllcl_updated.txt" target="_blank">MLLCL</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/mlcin_updated.txt" target="_blank">MLCIN</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/mlcin_cf_updated.txt" target="_blank">MLCIN (color filled)</a></div>

    </div>
    <br>
    <h4>Shear</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="nse" href="[address]/placefiles/esrh_updated.txt" target="_blank">Effective SRH</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/srh01km_updated.txt" target="_blank">0-1km SRH</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/srh500_updated.txt" target="_blank">0-500m SRH</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="nse" href="[address]/placefiles/ebwd_updated.txt" target="_blank">Effective Shear</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/shr1_updated.txt" target="_blank">0-1km Shear</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/shr3_updated.txt" target="_blank">0-3km Shear</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/shr6_updated.txt" target="_blank">0-6km Shear</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/shr8_updated.txt" target="_blank">0-8km Shear</a></div>

    </div>
    <br>
    <h4>Composite</h4>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="nse" href="[address]/placefiles/estp_updated.txt" target="_blank">Effective Sig Tor Parameter</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/nst_updated.txt" target="_blank">Non-Supercell Tornado Parameter</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/ProbSevere_updated.txt" target="_blank">CIMSS ProbSevere v2</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="nse" href="[address]/placefiles/rm5_updated.txt" target="_blank">Bunkers RM Vectors</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/lm5_updated.txt" target="_blank">Bunkers LM Vectors</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/devtor_updated.txt" target="_blank">Deviant Tornado Motion</a></div>
        <div class="p-2"><a class="nse" href="[address]/placefiles/deviance_updated.txt" target="_blank">Perceived Tornado Deviance</a></div>
    </div>
    <div class="d-flex flex-wrap">
        <div class="p-2"><a class="nse" href="[address]/placefiles/snsq_updated.txt" target="_blank">Snow Squall Parameter</a></div>
    </div>
    </div></div>
</div>
<br><hr><br>
    <div class="container">
        <div class="d-flex flex-wrap title">
        <h2><strong>Product Descriptions</strong> (from CWIP)</h2>
        </div>
        <div class="d-flex flex-wrap main-title">Instability</div>
        <br>
        <div class="d-flex flex-wrap title">Mixed Layer CAPE</div>
        <div class="d-flex flex-wrap desc">
            MLCAPE (Mixed Layer Convective Available Potential Energy) is a measure of instability in the troposphere. 
            This value represents the mean potential energy conditions available to parcels of air located in the 
            lowest 100-mb when lifted to the level of free convection (LFC). No parcel entrainment is considered. 
            The CAPE and CIN calculations use the virtual temperature correction. 
        </div>
        <br>
        <div class="d-flex flex-wrap title">Mixed Layer CIN</div>
        <div class="d-flex flex-wrap desc">
            CIN (Convective INhibition) represents the "negative" area on a sounding that must be overcome before 
            storm initiation can occur.
        </div>
        <br>
        <div class="d-flex flex-wrap title">Mixed Layer LCL</div>
        <div class="d-flex flex-wrap desc">
            The LCL (Lifting Condensation Level) is the level at which a parcel becomes saturated. 
            It is a reasonable estimate of cloud base height when parcels experience forced ascent.
        </div>
        <br>
        
        <div class="d-flex flex-wrap title">Most Unstable CAPE</div>
        <div class="d-flex flex-wrap desc">
        MUCAPE (Most Unstable Convective Available Potential Energy) is a measure of instability in the troposphere. 
        This value represents the total amount of potential energy available to the maximum equivalent potential temperature 
        (within the lowest 300-mb of the atmosphere) while being lifted to its level of free convection (LFC). No parcel 
        entrainment is considered. The CAPE and CIN calculations use the virtual temperature correction.
        </div>
        <br>
        <div class="d-flex flex-wrap title">0-3km CAPE</div>
        <div class="d-flex flex-wrap desc">
            CAPE in the lowest 3-km above ground level. Areas of large 0-3-km CAPE tend to favor strong low-level 
            stretching, and can support tornado formation when co-located with significant vertical vorticity near the ground.
        </div>
        <br>
        <div class="d-flex flex-wrap title">0-3km Lapse Rate</div>
        <div class="d-flex flex-wrap desc">
            A lapse rate is the rate of temperature change with height. The faster the temperature decreases with 
            height, the "steeper" the lapse rate and the more "unstable" the atmosphere becomes. The 0-3 km lapse rates, 
            also referred to as low-level lapse rates, are meant to identify regions of deeper mixing (e.g., steeper lapse rates) 
            that often result in weakening convective inhibition that precedes surface-based thunderstorm development, as well 
            as the potential for strong downdrafts in the low levels.
        </div>
        <br>

        <div class="d-flex flex-wrap main-title">Shear</div>
        <br>
        <div class="d-flex flex-wrap title">0-1km Shear</div>
        <div class="d-flex flex-wrap desc">Surface-1-km Vertical Shear is the difference between the surface wind and the wind at 1-km above ground level. 
        These data are plotted as vectors. 0-1-km shear magnitudes greater than 15-20 knots tend to favor supercell tornadoes.<div>
        <br>
        <div class="d-flex flex-wrap title">0-3km Shear</div>
        <div class="d-flex flex-wrap desc">Surface-3-km Vertical Shear is the difference between the surface wind and the wind 
        at 3-km above ground level. Line-normal 0-3 km shear magnitudes of 30 kt or higher indicate a favorable environment for the development of mesovortices and/or tornadoes in QLCSs (Schaumann and Przybylinski 2012). These data are plotted as vectors.
        </div>
        <br>
        <div class="d-flex flex-wrap title">0-6km Shear</div>
        <div class="d-flex flex-wrap desc">The surface through 6-km above ground level shear vector denotes the change in wind throughout this height. Thunderstorms tend to become more organized and persistent as vertical shear increases. Supercells are commonly associated with vertical shear values of 35-40 knots and greater through this depth.
                </div><br>
        <div class="d-flex flex-wrap title">0-8km Shear</div>
            <div class="d-flex flex-wrap desc">
            The surface through 8 km above ground level shear vector denotes the change in wind throughout this height. 
                Thunderstorms tend to become more organized and persistent as vertical shear increases. Bunkers et al. 2006 found 
                that long-lived supercells occur in environments with much stronger 0-8-km bulk wind shear ( > 50 kt) than that 
                observed with short-lived supercells.
            </div>
            <br>
            <div class="d-flex flex-wrap title">Effective Bulk Shear</div>
            <div class="d-flex flex-wrap desc">
                The magnitude of the vector wind difference from the effective inflow base upward to 50% of the equilibrium level 
                height for the most unstable parcel in the lowest 300 mb. This parameter is similar to the 0-6 km bulk wind 
                difference, though it accounts for storm depth (effective inflow base to EL) and is designed to identify both 
                surface-based and "elevated" supercell environments. Supercells become more probable as the effective bulk wind 
                difference increases in magnitude through the range of 25-40 kt and greater.
            </div>
            <br>
            <div class="d-flex flex-wrap title">0-500m Storm Relative Helicity</div>
            <div class="d-flex flex-wrap desc">
                SRH (Storm Relative Helicity) in the lowest 500 m AGL has been found by Coffer et al. (2019), October issue of 
                Weather and Forecasting, to be a better discriminator than effective SRH between significant tornadoes and 
                nontornadic supercells. This calculation of 0-500 m SRH is limited to within the effective inflow layer, as 
                long as the inflow base is at the ground.
            </div>
            <br>
            <div class="d-flex flex-wrap title">0-1km Storm Relative Helicity</div>
            <div class="d-flex flex-wrap desc">
                SRH (Storm Relative Helicity) is a measure of the potential for cyclonic updraft rotation in right-moving 
                supercells. There is no clear threshold value for SRH when forecasting supercells, since the formation of 
                supercells appears to be related more strongly to the deeper layer vertical shear. Larger values of 0-1-km SRH 
                (greater than 100 m2 s-2), however, do suggest an increased threat of tornadoes with supercells. For SRH, larger 
                values are generally better, but there are no clear thresholds between non-tornadic and significant tornadic supercells.
            </div>
            <br>
            <div class="d-flex flex-wrap title">Effective Storm Relative Helicity</div>
            <div class="d-flex flex-wrap desc">
                Effective SRH (Storm Relative Helicity) is based on threshold values of lifted parcel CAPE 
                (100 J kg-1) and CIN (-250 J kg-1). These parcel constraints are meant to confine the SRH layer 
                calculation to the part of a sounding where lifted parcels are buoyant, but not too strongly capped.
            </div>
            <br>
        <div class="d-flex flex-wrap main-title">Composite Parameters</div>
            <br>
            <div class="d-flex flex-wrap title">Effective SigTor</div>
            <div class="d-flex flex-wrap desc">
                The Significant Tornado Parameter (effective layer) is a
                a multiple ingredient, composite index that includes effective bulk wind difference (EBWD), effective 
                storm-relative helicity (ESRH), 100-mb mean parcel CAPE (mlCAPE), 100-mb mean parcel CIN (mlCIN), and 100-mb 
                mean parcel LCL height (mlLCL).
                The index is formulated as follows:
            </div>    
            <br>
            <div class="d-flex flex-wrap desc">
                <img src = "https://meteor.geol.iastate.edu/~zhiris/images/effSigTor.png" class="flex-image">
            </div>
            <br>
            <div class="d-flex flex-wrap desc">
                The mlLCL term is set to 1.0 when mlLCL < 1000 m, and set to 0.0 when mlLCL > 2000 m; the mlCIN term is set to 
                1.0 when mlCIN > -50 J kg-1, and set to 0.0 when mlCIN < -200; the EBWD term is capped at a value of 1.5 for EBWD > 
                30 m s-1, and set to 0.0 when EBWD < 12.5 m s-1. Lastly, the entire index is set to 0.0 when the effective inflow 
                base is above the ground. A majority of significant tornadoes (F2 or greater damage) have been associated with STP 
                values greater than 1 within an hour of tornado occurrence, while most non-tornadic supercells have been associated with 
                values less than 1 in a large sample of RAP analysis proximity soundings.
            </div>
            <br><br>
            <div class="d-flex flex-wrap title">Non-Supercell Tornado</div>
            <div class="d-flex flex-wrap desc">
                The non-supercell tornado parameter (NST) is the normalized product of the following terms:
            </div>
            <br>    
            <div class="d-flex flex-wrap">
                    <img src="https://meteor.geol.iastate.edu/~zhiris/images/NonSupTor.png" class="flex-image">
            </div>
            <br>
            <div class="d-flex flex-wrap desc">
                This normalized parameter is meant to highlight areas where steep low-level lapse rates correspond with low-level instability, 
                little convective inhibition, weak deep-layer vertical shear, and large cyclonic surface vorticity. Values > 1 suggest an 
                enhanced potential for non-mesocyclone tornadoes.
                <br><br>
                <i>Note that this placefile uses the same Baumgardt and Cook relative vorticity divisor (in term 5) as the SPC mesoanalysis. 
                However, these placefiles run on a 13km grid (vs. 40km for SPC) and thus the magnitude of NST output may be higher than what 
                appears on the SPC page.</i>
            </div>
            <br>
            <div class="d-flex flex-wrap title">Bunkers Right & Right Motions</div>
            <div class="d-flex flex-wrap desc">
                The "ID method", also known as the "Bunkers" method, was developed by Bunkers et al. (2000) as an estimate of 
                supercell motion. The Bunkers method is gallilean invariant, thus it does not depend on the orientation of the 
                ground-relative winds. The Bunkers motion provides results similar to the "30 degrees right and 75% of the mean 
                wind speed" estimates for typical southwest flow regimes, while the Bunkers motion estimate offers substantial 
                improvements over the 30R75 technique in less common flow regimes (e.g., NW flow or SE flow associated with tropical cyclones). 
                Graphically, the Bunkers storm motion can be estimated by 1) plotting the shear vector from the 0-500 m AGL mean wind to the 
                5500-6000 m AGL mean wind on a hodograph, 2) plotting the 0-6 km mean wind (pressure weighted), and 3) drawing a vector 
                (of 7.5 m s-1 magnitude) perpendicular to the shear vector from the 0-6 km mean wind. A perpendicular vector to the right 
                represents the right (cyclonic in northern hemisphere) supercell motion, and a left vector represents the left (anticyclonic 
                in northern hemisphere) supercell motion
                </div>
                <br>
            <div class="d-flex flex-wrap title">Deviant Tornado Motion</div>
            <div class="d-flex flex-wrap desc">
                This parameter was derived by Cameron Nixon and is described in the February 2021 issue 
                of <i><a href="https://journals.ametsoc.org/view/journals/wefo/36/1/WAF-D-20-0056.1.xml" target="_blank">Weather and Forecasting</a></i>
            </div>
                <br>
    </div>
</div>
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
