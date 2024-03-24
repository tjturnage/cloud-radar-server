<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">


  <h1>Cloud Radar Server</h1>

  <h2>
    A way to make radar simulations possible
  </h2>
</div>


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

COBRAS (ClOud Based RAdar Simulator) is an application developed by Travis Wilson (currently at NOAA Global Systems Laboratory in Boulder, CO). This application is hosted on a web server and incrementally serves out files from the NOAA Next Generation Radar (NEXRAD) Level 2 Base Data archive[^2] (henceforth, L2 data).  End users leverage third party software called GR2Analyst Version 3 (henceforth, GR2)[^3] to poll these files and render them into a visual display of the radar data. COBRAS contains its own Graphical User Interface (GUI) that makes it easy for a user to initiate a polling session.

Another application called l2munger[^4] was developed by Daryl Herzmann at Iowa State University and is able to modify L2 data file metadata so that the dataset assumes the identity of another radar location and/or different valid times. It’s often desirable to alias L2 data in this manner because it keeps the event anonymous and allows people to “experience” severe weather transposed to their own, more familiar location. Once the file conversion is complete, it’s then possible to leverage an independent script to incrementally serve out files in the same manner that COBRAS is able to achieve. Unlike COBRAS, l2munger does not feature its own GUI; however, it would be feasible to create one. 

Both COBRAS and l2munger require a web server to function. Web servers have been provided ad hoc either by private website owners or through National Weather Service (NWS) local or regional efforts. It should be self-evident that any private and non-NOAA affiliated training resource can not be considered a viable option for NOAA-centric training. Alternatively, some NWS Weather and Forecast Offices (WFOs) run COBRAS or l2munger directly on their local intranet. At NWS Central Region (CR) Headquarters, a COBRAS server is available to all WFOs. In all of these cases, however, this prevents external access for trainees on telework or for NOAA partners outside of the NWS. Moreover, a lack of central management due to all of these options makes it difficult to coordinate training efforts that often run in parallel and sometimes unknowingly compete for resources. Hence, there is a strong need for a web server that is externally accessible to NOAA/NWS employees via their ICAM credentials. This would allow for multi-office distributed training events that would improve readiness for hazardous weather as well as for mutual aid scenarios associated with large severe weather outbreaks. 

In 2023, an NWS contract was finalized with Gibson Ridge, the company that developed GR2. This contract provided individual GR2 licenses to all NWS meteorologists. This development emphasizes how GR2 has become an integral part of NWS warning operations. By extension, it is well recognized that GR2 serves as a valuable training tool as evidenced by the Warning Operations Course: Severe Track training curriculum offered by the Warning Decision Training Division5 as well as the Radar Feature Catalogs created by the CR Convective Warning Improvement Project (CWIP)6.

Either COBRAS or l2munger, when combined with GR2, offers a powerful training structure. Progressive disclosure of radar data that can be visually rendered in GR2 creates a Displaced Real-Time (DRT) simulation environment, similar to what’s experienced in aircraft flight simulators. In this case, however, meteorologists are given the opportunity to “train as they fight'' as they build proficiency ahead of actual severe weather events.

However, severe weather diagnosis includes more than just assessing radar data. The Near Storm Environment (NSE) is another key ingredient because it represents atmospheric conditions in the immediate vicinity of the thunderstorms and strongly influences the characteristics of thunderstorms that develop and evolve. These characteristics subsequently inform which weather hazards (such as damaging winds, large hail, and tornadoes) are most likely to occur and how severe those hazards may become. Assessing the NSE requires the introduction of additional datasets. This includes Numerical Weather Prediction (NWP) guidance, which provides a three dimensional view of atmospheric properties and how these properties evolve with time. Another useful dataset is surface observations, which are refreshed at a much faster rate than NWP output.

To integrate supplemental datasets as described above, GR2 is able to display these datasets along with the rendered radar imagery using placefiles7. Placefiles are text files that can be dynamically updated with features that are time-synchronized with radar data. This allows animations of radar displays to similarly feature animations of placefile features that depict the evolving NSE environment. Work has been completed for creating NSE placefiles8 and surface observation placefiles9. The next step is providing an interface in which a user can initiate the creation of these files so they can be served out to GR2 in a manner similar to how radar data are disseminated.

This proposal is a collaborative effort between NWS WFOs GRR (Grand Rapids, MI), LOT (Chicago, IL), BOU (Denver/Boulder, CO), and the Scientific Services Division of NWS Central Region Headquarters. The goal of this proposed work is to take cloud-based GR2 simulations to the next level by expanding its usage, support, functionality, and applicability.


### Here are some of the deliverables

* Implement both COBRAS and l2munger with a NOAA employee accessible web-interface on the NOAA Cloud.
* Code that generates NSE placefiles derived from archived 20-km resolution historical 1-hour RAP NWP model10 forecasts.
* Code that generates surface observations using archived data obtained through the Synoptic Data API11.
* Code that performs required the geographic reprojections and time shifts of the observerved and NSE datasets if alternate radar locations and valid times are selected for a simulation.
* A web interface in which users can easily request archived radar, NSE, and surface observation datasets on-the-fly and load directly into an instance of GR2, facilitating a simple methodology for creating quick training cases or post-mortems.
* Three proof-of-concept simulations with at least one of them involving distributed, multi-office participation. 

* Present results at an AMS or NWA conference. This presentation would be delivered by the PI or a designee and would evaluate the performance and functionality of the improvements. The presentation also will be promoted and shared internally by the stakeholders via regional or joint-regional science circle(s) to increase awareness and expand the number of users. Several recorded “use cases” will be presented.


References:
[^1] https://research.noaa.gov/2020/06/29/noaa-releases-roadmap-for-the-next-7-years-of-research-and-development/  
[^2] https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00345  
[^3] https://www.grlevelx.com/gr2analyst_3/  
[^4] https://github.com/akrherz/l2munger  
[^5] https://training.weather.gov/wdtd/courses/woc/severe.php  
[^6] https://sites.google.com/a/noaa.gov/nws-cr-tornado-warning-improvement-project/  
[^7] https://www.grlevelx.com/manuals/gis/files_places.htm  
[^8] https://github.com/lcarlaw/meso  
[^9] https://github.com/tjturnage/mesowest  
[^10] https://journals.ametsoc.org/view/journals/mwre/144/4/mwr-d-15-0242.1.xml  
[^11] https://synopticdata.com/weatherapi/  


<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

This section should list any major frameworks/libraries used to bootstrap your project. Leave any add-ons/plugins for the acknowledgements section. Here are a few examples.

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

### Installation

Clone the repo
   ```sh
   git clone https://github.com/tjturnage/cloud-radar-server.git
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

(left blank for now)

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
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

T.J. Turnage - thomas.turnage@noaa.gov

Project Link: [https://github.com/tjturnage/cloud-radar-server](https://github.com/tjturnage/cloud-radar-server)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Use this space to list resources you find helpful and would like to give credit to. I've included a few of my favorites to kick things off!

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
