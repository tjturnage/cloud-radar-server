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
</head>
<body>
"""

TAIL = """</ul>
</body>
</html>"""



@dataclass
class WriteLinksPage():
    """
    A class to write a shareable links page for simulation participants not having access to the
    main RSSiC user interface
    """
    session_id:   str   #  Input   --  unique id of session related to epoch time
    links_page:   str   #  Input   --  filepath of the links html page
    polling_dir:  str   #  Input   --  directory for radar polling


    def create_links_page(self) -> None:
        """
        creates the links page ... can be done all at once
        """
        with open(self.links_page, 'w', encoding='utf-8') as fout:
            fout.write(HEAD)
            fout.write('<br><br>\n')
            fout.write('<h3>Graphics not available, check back later!</h3>\n')
            fout.write(TAIL)


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        pass
    else:
        #cfg['SESSION_ID'], cfg, ['LINKS_PAGE'] cfg['POLLING_DIR']
        event_times = WriteLinksPage(sys.argv[1], sys.argv[2], sys.argv[3])
