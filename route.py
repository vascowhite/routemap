import argparse
import warnings
import sys
import datetime
import requests
import xml.etree.ElementTree as etree

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from vincenty import vincenty

KM_IN_NM = 1.852
GOOGLE_API_KEY = 'AIzaSyDKBY8Zhf9Lk-8ZUb1YIFtNJUCvrfvsrTs'


def loadfile(filename):
    with open(filename, 'r') as f:
        return f.read()


def pos_to_float(pos):
    # N & E are positive
    signs = {'N': '+', 'S': '-', 'E': '+', 'W': '-'}
    degrees = float(pos.split(' ')[0]) + float(pos.split(' ')[1][:-1]) / 60
    return float(signs[pos[-1:]] + str(degrees))


def annotconflict(annotations, annotation):
    positions = [(anot[0], anot[1]) for anot in annotations]
    return (annotation[0], annotation[1]) in positions


def calcdistance(latitudes, longitudes):
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


def parsebvs(bvs):
    lats = []
    lons = []
    annots = []

    xml = etree.fromstring(bvs).find('TrackInfo')
    for position in xml.findall('Position'):
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
    for annotation in annotations:
        x, y, = m(annotation[0], annotation[1])
        plt.annotate(s=annotation[2], xy=(x, y),
                     xytext=(x + 100000, y + 100000))
        if len(annotation) == 4:
            plt.plot(x, y, annotation[3])
        else:
            plt.plot(x, y, 'ko')


def plot(
            filename,
            currpos=None,
            output=None,
            display=None,
            custtitle=None,
            starttag=None,
            endtag=None,
            quality='i'
        ):

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
        url = 'http://wx.mqiv.com/position'
        currpos = requests.get(url).json()['position']
        currlat = float(currpos[0])
        currlon = float(currpos[1])
        annotations.append((currlon, currlat, 'MQIV', 'bo'))

    totaldistance = calcdistance(lats, lons)
    north = int(max(lats)) + 5
    south = int(min(lats)) - 5
    west = int(min(lons)) - 5
    east = int(max(lons)) + 5
    midlat = (north + south) // 2
    midlon = (west + east) // 2

    if quality not in ['c', 'l', 'i', 'h', 'f']:
        quality = 'i'

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

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
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

    sys.stdout.write('Saved image to ' + outfile)
    plt.savefig(
        outfile,
        bbox_inches='tight',
        papertype='a3',
        dpi=600
    )
    if display:
        plt.show()


def getcardinals(minv, maxv, stepv):
    cardinals = [val for val in range(minv, maxv) if val % stepv == 0]
    if len(cardinals) > 10:
        return [
            cardinal[1] for cardinal
            in enumerate(cardinals) if cardinal[0] % 2 > 0
        ]

    return cardinals


def main():
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
        help='Indicate current position.',
        action='store_true'
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
        The quality of the rendered map, defaults to -i:-
        c = crude,
        l = low,
        i = intermediate,
        h=high,
        f=full.
        Be warned, anything higher than -i takes a long time to render
        """
    )

    args = parser.parse_args()

    plot(
        args.file,
        currpos=args.current,
        output=args.output,
        display=args.display,
        custtitle=args.title,
        starttag=args.starttag,
        endtag=args.endtag,
        quality=args.quality
    )


if __name__ == '__main__':
    main()
