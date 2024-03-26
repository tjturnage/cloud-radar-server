
<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />



  <h1><b>Radar Simulator in the Cloud</b></h1>


<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

COBRAS (**C**l**O**ud **B**ased **RA**dar **S**imulator) is an developed by Travis Wilson (currently at NOAA Global Systems Laboratory in Boulder, CO). This application is hosted on a web server and incrementally serves out files from the NOAA Next Generation Radar (NEXRAD) Level 2 Base Data archive<sup>[<a href="#ref2">2</a>]</sup> (henceforth, L2 data).  End users leverage third party software called GR2Analyst Version 3 (henceforth, GR2)<sup>[<a href="#ref3">3</a>]</sup> to poll these files and render them into a visual display of the radar data. COBRAS contains its own Graphical User Interface (GUI) that makes it easy for a user to initiate a polling session.

Another application called l2munger<sup>[<a href="#ref4">4</a>]</sup> was developed by Daryl Herzmann at Iowa State University and is able to modify L2 data file metadata so that the dataset assumes the identity of another radar location and/or different valid times. It’s often desirable to alias L2 data in this manner because it keeps the event anonymous and allows people to “experience” severe weather transposed to their own, more familiar location. Once the file conversion is complete, it’s then possible to leverage an independent script to incrementally serve out files in the same manner that COBRAS is able to achieve. Unlike COBRAS, l2munger does not feature its own GUI; however, it would be feasible to create one. 

Both COBRAS and l2munger require a web server to function. Web servers have been provided ad hoc either by private website owners or through National Weather Service (NWS) local or regional efforts. It should be self-evident that any private and non-NOAA affiliated training resource can not be considered a viable option for NOAA-centric training. Alternatively, some NWS Weather and Forecast Offices (WFOs) run COBRAS or l2munger directly on their local intranet. At NWS Central Region (CR) Headquarters, a COBRAS server is available to all WFOs. In all of these cases, however, this prevents external access for trainees on telework or for NOAA partners outside of the NWS. Moreover, a lack of central management due to all of these options makes it difficult to coordinate training efforts that often run in parallel and sometimes unknowingly compete for resources. Hence, there is a strong need for a web server that is externally accessible to NOAA/NWS employees via their ICAM credentials. This would allow for multi-office distributed training events that would improve readiness for hazardous weather as well as for mutual aid scenarios associated with large severe weather outbreaks. 

In 2023, an NWS contract was finalized with Gibson Ridge, the company that developed GR2. This contract provided individual GR2 licenses to all NWS meteorologists. This development emphasizes how GR2 has become an integral part of NWS warning operations. By extension, it is well recognized that GR2 serves as a valuable training tool as evidenced by the Warning Operations Course: Severe Track training curriculum offered by the Warning Decision Training Division<sup>[<a href="#ref6">6</a>]</sup> as well as the Radar Feature Catalogs created by the CR Convective Warning Improvement Project (CWIP)<sup>[<a href="#ref5">5</a>]</sup>.

Either COBRAS or l2munger, when combined with GR2, offers a powerful training structure. Progressive disclosure of radar data that can be visually rendered in GR2 creates a Displaced Real-Time (DRT) simulation environment, similar to what’s experienced in aircraft flight simulators. In this case, however, meteorologists are given the opportunity to “train as they fight'' as they build proficiency ahead of actual severe weather events.

However, severe weather diagnosis includes more than just assessing radar data. The Near Storm Environment (NSE) is another key ingredient because it represents atmospheric conditions in the immediate vicinity of the thunderstorms and strongly influences the characteristics of thunderstorms that develop and evolve. These characteristics subsequently inform which weather hazards (such as damaging winds, large hail, and tornadoes) are most likely to occur and how severe those hazards may become. Assessing the NSE requires the introduction of additional datasets. This includes Numerical Weather Prediction (NWP) guidance, which provides a three dimensional view of atmospheric properties and how these properties evolve with time. Another useful dataset is surface observations, which are refreshed at a much faster rate than NWP output.

To integrate supplemental datasets as described above, GR2 is able to display these datasets along with the rendered radar imagery using placefiles<sup>[<a href="#ref7">7</a>]</sup>. Placefiles are text files that can be dynamically updated with features that are time-synchronized with radar data. This allows animations of radar displays to similarly feature animations of placefile features that depict the evolving NSE environment. Work has been completed for creating NSE placefiles<sup>[<a href="#ref8">8</a>]</sup> and surface observation placefiles<sup>[<a href="#ref9">9</a>]</sup>. The next step is providing an interface in which a user can initiate the creation of these files so they can be served out to GR2 in a manner similar to how radar data are disseminated. The goal of this proposed work is to take cloud-based GR2 simulations to the next level by expanding its usage, support, functionality, and applicability.


This project is a collaborative effort among:  
<ul>
<li><a href="https://www.weather.gov/crh/" target="_blank">NWS Central Region Headquarters (Kansas City, MO)</a></li>
<li><a href="https://www.weather.gov/grr/" target="_blank">NWS WFO GRR (Grand Rapids, MI)</a></li>
<li><a href="https://www.weather.gov/lot/" target="_blank">NWS WFO LOT (Chicago, IL)</a></li>
<li><a href="https://www.weather.gov/bou/" target="_blank">NWS WFO BOU (Denver/Boulder, CO)</a></li>
</ul>

### Priorities Satisfied
<ul>
<li>Reducing societal impacts from hazardous weather and other environmental phenomena (NOAA Research Roadmap)<sup>[<a href="#ref1">1</a>]</sup></li> 
<li>Conducting operational applied research important to the NWS vision that benefits from increased computing resources provided by cloud computing</li>
<li>Demonstration of strong internal NOAA partnership that would benefit from cloud computing (either through product development or generation)</li>
<li>Involvement of multiple offices (e.g., WFOs, RFCs, and/or Regions)</li>
</ul>

### Initial deliverables

<ul>
<li>Implement both COBRAS and l2munger with a NOAA employee accessible web-interface on the NOAA Cloud.</li>
<li>Code that generates NSE placefiles derived from archived 20-km resolution historical 1-hour RAP NWP model<sup>[<a href="#ref10">10</a>]</sup> forecasts.</li>
<li>Code that generates surface observations using archived data obtained through the Synoptic Data API<sup>[<a href="#ref11">11</a>]</sup>.</li>
<li>Code that performs required the geographic reprojections and time shifts of the observerved and NSE datasets if alternate radar locations and valid times are selected for a simulation.</li>
<li>A web interface in which users can easily request archived radar, NSE, and surface observation datasets on-the-fly and load directly into an instance of GR2, facilitating a simple methodology for creating quick training cases or post-mortems.</li>
<li>Three proof-of-concept simulations with at least one of them involving distributed, multi-office participation.</li>
<li>Present results at an AMS or NWA conference. This presentation would be delivered by the PI or a designee and would evaluate the performance and functionality of the improvements. The presentation also will be promoted and shared internally by the stakeholders via regional or joint-regional science circle(s) to increase awareness and expand the number of users. Several recorded “use cases” will be presented.</li>
</ul>

References:
<div id="ref1">[1] <a href="https://research.noaa.gov/2020/06/29/noaa-releases-roadmap-for-the-next-7-years-of-research-and-development/" target="_blank">https://research.noaa.gov/2020/06/29/noaa-releases-roadmap-for-the-next-7-years-of-research-and-development/</a></div>
<div id="ref2">[2] <a href="https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00345" target="_blank">https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00345</a></div>  
<div id="ref3">[3] <a href="https://www.grlevelx.com/gr2analyst_3/" target="_blank">https://www.grlevelx.com/gr2analyst_3/</a></div> 
<div id="ref4">[4] <a href="https://github.com/akrherz/l2munger" target="_blank">https://github.com/akrherz/l2munger</a></div>  
<div id="ref5">[5] <a href="https://training.weather.gov/wdtd/courses/woc/severe.php" target="_blank">https://training.weather.gov/wdtd/courses/woc/severe.php</a></div>  
<div id="ref6">[6] <a href="https://sites.google.com/a/noaa.gov/nws-cr-tornado-warning-improvement-project/" target="_blank">https://sites.google.com/a/noaa.gov/nws-cr-tornado-warning-improvement-project/</a></div>  
<div id="ref7">[7] <a href="https://www.grlevelx.com/manuals/gis/files_places.htm" target="_blank">https://www.grlevelx.com/manuals/gis/files_places.htm</a></div>  
<div id="ref8">[8] <a href="https://github.com/lcarlaw/meso" target="_blank">https://github.com/lcarlaw/meso</a></div>  
<div id="ref9">[9] <a href="https://github.com/tjturnage/mesowest" target="_blank">https://github.com/tjturnage/mesowest</a></div>  
<div id="ref10">[10] <a href="https://journals.ametsoc.org/view/journals/mwre/144/4/mwr-d-15-0242.1.xml" target="_blank">https://journals.ametsoc.org/view/journals/mwre/144/4/mwr-d-15-0242.1.xml</a></div>  
<div id="ref11">[11] <a href="https://synopticdata.com/weatherapi/" target="_blank">https://synopticdata.com/weatherapi/</a></div>  


<p align="right">(<a href="#readme-top">back to top</a>)</p>


### Built With

<p>This list will continue to grow. Please check back later.</p>

* Bootstrap
* jQuery

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

This requires an apache server.

### Prerequisites

Run the following to create an Anaconda environment called meso with the required libraries:
  ```sh
  conda env create -f environment.yaml
  ```

#### Python environment

Run the following to create an Anaconda/Mamba environment called `cloud-radar` with the required libraries (you should be able to use either conda or mamba).  We built our environment with [miniforg3](https://github.com/conda-forge/miniforge).

  ```sh
  mamba env create -f environment.yaml
  ```
#### WGRIB2

Wgrib2 [version 3.0.2](https://www.ftp.cpc.ncep.noaa.gov/wd51we/wgrib2) or higher is necessary for time interpolations, grid upscaling, and decoding older versions of the RAP model. Installing this software can be tricky, and the steps needed to do so can be different on each machine. On a RHEL machine:

```
wget https://www.ftp.cpc.ncep.noaa.gov/wd51we/wgrib2/wgrib2.tgz.v3.0.2
tar -xvzf wgrib2.tgz.v3.0.2
cd grib2
```

Edit `makefile` and set `USE_NETCDF3=0` as we don't need to export netCDF files and this simplifies the build. Then, if `which gfortran` doesn't return an executable, do:

```
dnf -y install make gcc gcc-gfortran.x86_64
````

Followed by:

```
export CC=gcc
export FC=gfortran
make -j4
```

If this is successful, a folder called `wgrib2` should have been created with a `wgrib2` binary/executable file within it. Either move this of softlink it into /usr/local/bin or somewhere similar in your `$PATH`. 

#### WGET
A working version of WGET is needed to download model data. 

### Installation

#### Clone the repo
   ```sh
   git clone https://github.com/tjturnage/cloud-radar-server.git
   ```

#### Edit Config Files
Within the `meso-placefiles` sub-directory, open `configs.py`.  The first six variables must be changed to specify the locations of the Python, WGRIB2, and WGET executables on your system, as well as where you'd like output and log files to be stored. `NUM_THREADS` controls how many threads are utilized during the computationally-expensive parcel lifting steps during the NSE placefile creation and should be set to a number less than the total number of threads available.  

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
## Usage



<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [x] Add Changelog
- [x] Add arguments for location and times in surface-obs-placefile.py
- [ ] Convert anaconda to mamba
- [ ] Develop front end to take date/time/location arguments



See the [open issues](https://github.com/tjturnage/cloud-radar-server/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributors
<font size="+1">
<ul>
<li><a href="https://github.com/lcarlaw" target="_blank">Lee Carlaw - NWS Chicago</a></li>
<li><a href="https://github.com/scottthomaswx" target="_blank">Scott Thomas - NWS Grand Rapids</a></li>
</ul>
</font>
<p>Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are <b>greatly appreciated</b>. If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement". Don't forget to give the project a star! Thanks again!</p>

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See <a href="https://github.com/tjturnage/cloud-radar-server/blob/main/LICENSE.txt">LICENSE.txt</a> for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact


T.J. Turnage - NWS Grand Rapids  
thomas.turnage@noaa.gov  
Project Link: [https://github.com/tjturnage/cloud-radar-server](https://github.com/tjturnage/cloud-radar-server)  

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments


<!--
* [Choose an Open Source License](https://choosealicense.com)
* [GitHub Emoji Cheat Sheet](https://www.webpagefx.com/tools/emoji-cheat-sheet)
* [Malven's Flexbox Cheatsheet](https://flexbox.malven.co/)
* [Malven's Grid Cheatsheet](https://grid.malven.co/)
* [Img Shields](https://shields.io)
* [GitHub Pages](https://pages.github.com)
* [Font Awesome](https://fontawesome.com)
* [React Icons](https://react-icons.github.io/react-icons/search)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
-->
