import xml.etree.ElementTree as etree
import argparse
from datetime import datetime
import sys

CUR_PATH = sys.path[0]
CVS_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
BVS_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S-00:00'
WP_INDEX = 0
WP_DATE = 1
WP_POS = 2
WP_TYPE = 3


def same_position(pos1, pos2):
    """(list, list) -> bool
    Are the two positions the same?
    :param pos1:
    :param pos2:
    :return: bool
    """
    return pos1[2] == pos2[2]


def get_wp_types(waypoints):
    """(list) -> list
    From a list of waypoints return another list with bvs stops detected.
    :param waypoints:
    :return:
    """
    result = waypoints
    return get_stop_points(get_start_end_points(result))


def deduplicate(waypoints):
    """(list) -> list
    Take a list of waypoints and return another list with duplicates removed.

    :param list waypoints:
    :return: list
    """
    i = 0
    while i < len(waypoints) - 1:
        if waypoints[i][WP_TYPE] == 'WP' and waypoints[i + 1][WP_TYPE] == 'WP' and same_position(waypoints[i], waypoints[i + 1]):
            print((waypoints[i]))
        i += 1


def rebase(waypoints):
    i = 0
    while i < len(waypoints):
        waypoints[i][0] = i
        i += 1

    return waypoints


def get_stop_points(waypoints):
    """(list) -> list
    From a list of waypoints return another list with BVS stop points.
    BVS files expect a 'via' point to consist of two way points: an
    arrival point (AP) and a departure point (DP). These do not need to
    have the same position, but there shouldn't be any waypoints between
    them so:
    AP and DP will be the 1st and last waypoints of a group that have
    the same positions.

    The BR and ER points should already be present.
    :param waypoints:
    :return:
    """
    result = []
    i = 0
    while i < len(waypoints):
        if len(waypoints[i]) == 4:
            result.append(waypoints[i])
        elif same_position(waypoints[i], waypoints[i + 1]):
            result.append(waypoints[i])
            result[-1].append('AP')
            j = i
            while same_position(waypoints[j], waypoints[j + 1]):
                j += 1
            result.append(waypoints[j])
            result[-1].append('DP')
            i = j
        else:
            result.append(waypoints[i])
            result[-1].append('WP')
        i += 1

    return rebase(result)


def get_start_end_points(waypoints):
    """(list) -> list
    From a list of waypoints return another list with BR and ER points defined.
    BVS files expect BR and ER to be a single position so:-
        BR will be reduced to the last waypoint of a series with the same position.
        ER will be reduced to the first waypoint of a series with the same position.
    :param waypoints:
    :return:
    """
    result = []
    first = None
    last = None

    if not same_position(waypoints[0], waypoints[1]):
        first = waypoints[0]
    elif same_position(waypoints[0], waypoints[1]):
        i = 0
        while same_position(waypoints[i], waypoints[i + 1]):
            i += 1
        first = waypoints[i]

    if not same_position(waypoints[-1], waypoints[-2]):
        last = waypoints[-1]
    elif same_position(waypoints[-1], waypoints[-2]):
        i = -1
        while same_position(waypoints[i], waypoints[i - 1]):
            i -= 1
        last = waypoints[i]

    first.append('BR')
    last.append('ER')
    result.append(first)
    for i in range(first[0] + 1, last[0]):
        result.append(waypoints[i])

    result.append(last)

    return rebase(result)


def get_port_name(datestring, type):
    """(str, str) -> str
    Take a date string and find the port called at on that date from dtAll.csv.
    Type is AP, DP, BR or ER.
    :param datestring:
    :param type
    :return: str
    """
    port = ''
    with open(CUR_PATH + '/dtAll.csv') as f:
        lines = [line for line in f][1:]

    if type in ['DP', 'BR']:
        departures = {line.split(',')[0]: line.split(',')[1] for line in lines}
        if datestring in departures:
            port = departures[datestring]
    elif type in ['AP', 'ER']:
        arrivals = {line.split(',')[2]: line.split(',')[3] for line in lines}
        if datestring in arrivals:
            port = arrivals[datestring]

    return port.split('-')[0].strip()


def writebvs(filename, waypoints):
    xml = etree.ElementTree(etree.fromstring(
        '<?xml version="1.0" standalone="yes" ?>\n'
        '<Voyage dir="AROS">\n'
        '<TrackInfo '
        'version="7.1.0" release="0" voyageId="" trackCode="" shipName="Mayan Queen IV" callSign="ZCXC8" '
        'calmSeaSpeed="15.00" charterPartySpeed="" draft="4.25" beam="16.00" length="93.25" rpm="200.00" '
        'slip="10.00" ncrSpeed="15.00" powerRatio="1.00" ncrFuelRate="24.00" ncrPower="3750.00" '
        'mtWave="3.73" mtParam="0.00" mtSync="4.00" mtBroach="3.73" navFrom="1"></TrackInfo></Voyage>\n'
    ))
    trackinfo = xml.find('TrackInfo')

    for i, waypoint in enumerate(waypoints):
        attribs = {
            'id': '',
            'Type': waypoint[3],
            'Date': datetime.strptime(waypoint[1], CVS_DATE_FORMAT).strftime(BVS_DATE_FORMAT),
            'Lat': str(waypoint[2][0]),
            'Lon': str(waypoint[2][1]),
            'Navigation': 'RL'
        }

        if waypoint[3] in ['BR', 'AP', 'DP', 'ER']:
            datestr = waypoint[1][:10]
            attribs['TimeFix'] = '1'
            attribs['Name'] = get_port_name(datestr, waypoint[3])

        if waypoint[3] == 'AP':
            attribs['ControlType'] = 'STOP'
            starttime = datetime.strptime(waypoint[1], CVS_DATE_FORMAT)
            endtime = datetime.strptime(waypoints[i + 1][1], CVS_DATE_FORMAT)
            duration = endtime - starttime
            stopvalue = duration.days * 24 + duration.seconds / 3600
            attribs['ControlValue'] = str(round(stopvalue, 3))

        etree.SubElement(trackinfo, 'Position', attrib=attribs)
    try:
        xml.write(filename, xml_declaration=True, method='xml')
    except Exception as n:
        sys.stdout.write('Error: ' + str(n) +
                         '\nThe file is probably write protected.')


def parsepositions(raw):
    result = []

    for i, report in enumerate(raw):
        result.append(
            [i, report[2], (round(float(report[7]), 2), round(float(report[8]), 2))])

    return result


def readcsv(filename):
    with open(filename) as infile:
        indata = [
            line.split(',')
            for line in infile.read().splitlines()
            if 'IDP Report' in line
        ]
        indata.reverse()

    return indata


def convert(filename, output=None):
    if filename[-4:] != '.csv':
        sys.exit('This app can only load csv files!')

    if not output:
        outfile = filename[:-4] + '.bvs'
    else:
        outfile = output

    positions = parsepositions(readcsv(filename))
    positions = get_wp_types(positions)
    writebvs(outfile, positions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file', type=str, help='Input file. cvs files accepted.')
    parser.add_argument('-o', '--output', type=str,
                        help='Output file. Defaults to filename.bvs')
    args = parser.parse_args()
    convert(args.file, args.output)

if __name__ == '__main__':
    main()
