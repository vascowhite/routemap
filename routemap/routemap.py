"""
Draw route maps from supplied files.
"""
import os
import argparse
import math
import warnings
import sys
import datetime
import requests
import xml.etree.ElementTree as etree

from vincenty import vincenty
from geographiclib.geodesic import Geodesic, Constants
from mpl_toolkits.basemap import Basemap
import matplotlib

from routemap import __version__ as version

tk = True
try:
    import tkinter

    if 'DISPLAY' not in os.environ:
        tk = False
except ImportError:
    tk = False

if tk is False:
    matplotlib.use('AGG')

import matplotlib.pyplot as plt

KM_IN_NM = 1.852
cli = False


def loadfile(filename):
    """
    Load a file to read positions from

    :param filename: The path to the file
    :type filename: str
    :return: The contents of the file
    :rtype: str
    """
    with open(filename, 'r') as f:
        return f.read()


def pos_to_float(pos):
    """
    Convert a lat or long to a float

    :param pos: A lat or a long
    :type pos: str
    :return: The float version
    :rtype: float
    """
    # N & E are positive
    signs = {'N': '+', 'S': '-', 'E': '+', 'W': '-'}
    degrees = float(pos.split(' ')[0]) + float(pos.split(' ')[1][:-1]) / 60
    return float(signs[pos[-1:]] + str(degrees))


def annotconflict(annotations, annotation):
    """
    Checks to see if annotation is already in annotations
    :param annotations: a list of annotations
    :type annotations: list
    :param annotation: an annotation
    :type annotation: list
    :return: True if annotation is already in the list, otherwise False
    :rtype: bool
    """
    positions = [(anot[0], anot[1]) for anot in annotations]
    return (annotation[0], annotation[1]) in positions


def calcdistance(latitudes, longitudes):
    """
    Calculate the distance along the route.

    :param latitudes:
    :type latitudes: list
    :param longitudes:
    :type longitudes: list
    :return:
    :rtype: float
    """
    positions = []
    distances = []

    i = 0
    while i < len(latitudes):
        positions.append((latitudes[i], longitudes[i]))
        i += 1

    i = 0
    while i < len(positions) - 1:
        distances.append(vincenty(positions[i], positions[i + 1]))
        i += 1

    return sum(distances)


def parsertx(rtx):
    """
    Parse a rtx file
    :param rtx:
    :type rtx: str
    :return: a list of positions and annotations
    :rtype: list
    """
    routexml = etree.fromstring(rtx)

    lats = []
    lons = []
    annots = []
    lat = ''
    lon = ''

    for waypoint in routexml.find('waypoints'):
        for properties in waypoint.findall('properties'):
            for property in properties.findall('property'):
                if property.get('name') == 'Latitude':
                    lat = property.get('value')
                elif property.get('name') == 'Longitude':
                    lon = property.get('value')

            lats.append(pos_to_float(lat))
            lons.append(pos_to_float(lon))

    return [lons, lats, annots]


def get_gc_positions(start, end):
    positions = []
    spacing = 100000  # Positions 100km apart
    geoid = Geodesic(Constants.WGS84_a, Constants.WGS84_f)
    gc = geoid.InverseLine(
            start[0], start[1],
            end[0], end[1]
    )

    n = math.ceil(gc.s13 / spacing)

    for i in range(n + 1):
        s = min(spacing * i, gc.s13)
        result = gc.Position(s, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
        position = {
            'Lat': result['lat2'],
            'Lon': result['lon2']
        }
        positions.append(position)

    return positions


def parsebvs(bvs):
    """
    Parse a bvs file
    :param bvs:
    :type bvs: str
    :return: a list of positions and annotations
    :rtype: list
    """
    lats = []
    lons = []
    annots = []

    xml = etree.fromstring(bvs).find('TrackInfo')
    positions = xml.findall('Position')
    for i, position in enumerate(positions):
        if position.get('Navigation') == 'GC':
            for gc_pos in get_gc_positions(
                    (float(position.get('Lat')), float(position.get('Lon'))),
                    (
                            float(positions[i + 1].get('Lat')),
                            float(positions[i + 1].get('Lon'))
                    ),
            ):
                lats.append(gc_pos['Lat'])
                lons.append(gc_pos['Lon'])
        else:
            lats.append(float(position.get('Lat')))
            lons.append(float(position.get('Lon')))

        if position.get('Type') in ['BR', 'ER']:
            name = position.get('Name').title()
            calldate = datetime.datetime.strptime(position.get(
                    'Date'), '%Y-%m-%dT%H:%M:%S-00:00').strftime('%d %b')
            if name[-4:].lower() == 'drop':
                name = name[:-5]

            annotation = (
                float(position.get('Lon')),
                float(position.get('Lat')),
                name + '\n(' + calldate + ')')

            if annotation not in annots and not annotconflict(annots, annotation):
                annots.append(annotation)

    return [lons, lats, annots]


def parsecsv(csv):
    """
    Parse a csv file
    :param csv:
    :type csv: str
    :return: a list of positions and annotations
    :rtype: list
    """
    lats = []
    lons = []
    annots = []

    positions = [line.split(',') for line in csv[:-1].split('\n')]

    for position in positions:
        lat = pos_to_float(position[0].strip())
        lon = pos_to_float(position[1].strip())
        lats.append(lat)
        lons.append(lon)
        if len(position) == 3:
            annots.append((lon, lat, position[2].strip()))
    return [lons, lats, annots]


def parseurl(url):
    """
    Parse a url
    :param url:
    :type url: str
    :return: a list of positions and annotations
    :rtype: list
    """
    lats = []
    lons = []
    annots = []

    data = requests.get(url).json()['positions']
    positions = [line.split(',') for line in data if line]
    for position in positions:
        lats.append(float(position[1]))
        lons.append(float(position[2]))

    annots.append((lons[0], lats[0], 'Start'))
    annots.append((lons[-1], lats[-1], 'End'))

    return [lons, lats, annots]


def annotate(m, annotations):
    """
    Add anotations to the plot
    :param m:
    :type m: Basemap
    :param annotations:
    :type annotations: list
    """
    for annotation in annotations:
        x, y, = m(annotation[0], annotation[1])
        plt.annotate(s=annotation[2], xy=(x, y),
                     xytext=(x + 100000, y + 100000))
        if len(annotation) == 4:
            plt.plot(x, y, annotation[3])
        else:
            plt.plot(x, y, 'ko')


def get_current_position(posstr):
    """
    Get the current position
    The position is passed as a string representing the
    position or a url. eg:-
        -c "52 23.5N 36 18.1W"
        or
        -c http://some.url.com/positions
    :return: The position
    :rtype: tuple
    """
    if posstr[:4] == 'http':
        currpos = requests.get(posstr).json()['position']
        currlat = float(currpos[0])
        currlon = float(currpos[1])
    else:
        parts = posstr.split(' ')
        currlat = pos_to_float(parts[0] + ' ' + parts[1])
        currlon = pos_to_float(parts[2] + ' ' + parts[3])

    return currlat, currlon


def get_padding(north, south, west, east, padding=10):
    """
    Calculate a reasonable amount of padding for the map
    :param north:
    :type north:
    :param south:
    :type south:
    :param west:
    :type west:
    :param east:
    :type east:
    :param padding:
    :type padding:
    :return: The amount of padding to apply
    :rtype: int
    """
    padding /= 100
    dlat = abs(north - south)
    dlon = abs(east - west)

    return round(dlat * padding), round(dlon * padding)


def plot(
        filename,
        currpos=None,
        currposlabel='Current Position',
        output=None,
        display=None,
        custtitle=None,
        starttag=None,
        endtag=None,
        quality='i',
        paper='a3',
        dpi=600,
):
    """

    :param currposlabel:
    :type currposlabel:
    :param filename:
    :type filename: str
    :param currpos:
    :type currpos: str
    :param output:
    :type output: str
    :param display:
    :type display: str
    :param custtitle:
    :type custtitle: str
    :param starttag:
    :type starttag: str
    :param endtag:
    :type endtag: str
    :param quality:
    :type quality: str
    """
    annotations = []

    if filename[-3:] == 'rtx':
        lons, lats, title = parsertx(loadfile(filename))
    elif filename[-3:] == 'bvs':
        lons, lats, annots = parsebvs(loadfile(filename))
    elif filename[:4] == 'http':
        lons, lats, annots = parseurl(filename)
    else:
        lons, lats, annots = parsecsv(loadfile(filename))

    if len(annots) > 0:
        for annotation in annots:
            annotations.append(annotation)

    if starttag:
        annotations[0] = (annotations[0][0], annotations[0][1], starttag)

    if endtag:
        annotations[-1] = (annotations[-1][0], annotations[-1][1], endtag)

    if custtitle:
        title = custtitle
    else:
        title = filename[:-4]

    if currpos:
        currpos = get_current_position(currpos)
        currlat = float(currpos[0])
        currlon = float(currpos[1])
        annotations.append((currlon, currlat, currposlabel, 'bo'))

    totaldistance = calcdistance(lats, lons)
    north = int(max(lats))
    south = int(min(lats))
    west = int(min(lons))
    east = int(max(lons))

    lat_pad, lon_pad = get_padding(north, south, west, east)
    north += lat_pad
    south -= lat_pad
    west -= lon_pad
    east += lon_pad

    midlat = (north + south) // 2
    midlon = (west + east) // 2

    if quality not in ['c', 'l', 'i', 'h', 'f']:
        quality = 'i'

    # Fixing warnings would be better than suppressing them, but, hey ho, this
    # works for now. ;)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        earth = Basemap(
                projection='merc',
                resolution=quality,
                lat_0=midlat,
                lon_0=midlon,
                # longitude of lower left hand corner of the desired map domain
                # (degrees).
                llcrnrlon=west,
                # latitude of lower left hand corner of the desired map domain
                # (degrees).
                llcrnrlat=south,
                # longitude of upper right hand corner of the desired map domain
                # (degrees).
                urcrnrlon=east,
                # latitude of upper right hand corner of the desired map domain
                # (degrees).
                urcrnrlat=north
        )

        plt.figure(figsize=(16, 10))
        earth.drawcoastlines(color='0.50', linewidth=0.25)
        earth.drawparallels(getcardinals(south, north, 10),
                            labels=[1, 0, 0, 1], color='0.75')
        earth.drawmeridians(getcardinals(west, east, 10),
                            labels=[1, 0, 0, 1], color='0.75')

        # earth.shadedrelief()
        earth.fillcontinents(color='0.95')
        earth.plot(
                lons,
                lats,
                'r',
                linewidth=1,
                latlon=True,
                label='Distance = ' + '{:,}'.format(
                        int(totaldistance / KM_IN_NM)
                ) + ' NM'
        )

        annotate(earth, annotations)

        plt.subplot(1, 1, 1)
        plt.legend(loc='best', frameon=True)
        plt.title(title)

        if output:
            outfile = output
        else:
            outfile = filename[:-4] + '.png'

        if cli:
            sys.stdout.write('Saved image to ' + outfile + '\n')

        plt.savefig(
                outfile,
                bbox_inches='tight',
                papertype=paper,
                dpi=dpi
        )
        if display:
            plt.show()


def getcardinals(minv, maxv, stepv):
    """
    Get lats and longs to mark on map
    :param minv:
    :type minv: float
    :param maxv:
    :type maxv: float
    :param stepv:
    :type stepv: int
    :return:
    :rtype: list
    """
    cardinals = [val for val in range(minv, maxv) if val % stepv == 0]
    if len(cardinals) > 10:
        return [
            cardinal[1] for cardinal
            in enumerate(cardinals) if cardinal[0] % 2 > 0
        ]

    return cardinals


def routemap():
    """
    Parse CLI arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
            'file',
            type=str,
            help='Input file. rtx or bvs files accepted.'
    )

    parser.add_argument(
            '-t',
            '--title',
            type=str,
            help='A custom title for the chart if the generated one is crap'
    )

    parser.add_argument(
            '-o',
            '--output',
            type=str,
            help='Output file. Defaults to current directory'
    )

    parser.add_argument(
            '-c',
            '--current',
            type=str,
            help="""
        Indicate current position.\n
        Pass the position with the option as a string representing the position 
        or a url. eg:-\n
        -c "52 23.5N 36 18.1W"\n
        or\n
        -c http://some.url.com/positions\n
        """
    )

    parser.add_argument(
            '-cl',
            '--current_label',
            type=str,
            help='A label for the current position'
    )

    parser.add_argument(
            '-d',
            '--display',
            help='Display image in window. Defaults to no image displayed',
            action='store_true'
    )

    parser.add_argument(
            '-st',
            '--starttag',
            type=str,
            help='A custom tag for the first position'
    )

    parser.add_argument(
            '-et',
            '--endtag',
            type=str,
            help='A custom tag for the last position'
    )

    parser.add_argument(
            '-q',
            '--quality',
            type=str,
            help="""
        The quality of the rendered map, defaults to -i:-\n
        c = crude,\n
        l = low,\n
        i = intermediate,\n
        h=high,\n
        f=full.\n
        Be warned, anything higher than -i takes a long time to render
        """
    )

    parser.add_argument(
            '--dpi',
            type=int,
            help="""
        The DPI of the saved map, defaults to 600 (pretty big)
        """
    )

    parser.add_argument(
            '--paper',
            type=str,
            help="""
        Size of paper saved map is intended to be printed on.\n
        Accepts standard sizes such as a4, a3, letter etc.\n
        Default is a3
        """
    )

    parser.add_argument(
            '--version',
            action='version',
            version=get_version(),
            help='Print the version and exit'
    )

    args = parser.parse_args()

    plot(
            args.file,
            currpos=args.current,
            currposlabel=args.current_label,
            output=args.output,
            display=args.display,
            custtitle=args.title,
            starttag=args.starttag,
            endtag=args.endtag,
            quality=args.quality,
            paper=args.paper,
            dpi=args.dpi,
    )


def get_version():
    return 'routemap {}'.format(version.__version__)


if __name__ == '__main__':
    cli = True
    routemap()
