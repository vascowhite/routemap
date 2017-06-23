import argparse
import sys
import xml.etree.ElementTree as etree
import os.path as path

CUR_PATH = sys.path[0]

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


def clean_filename(filename):
    return filename.strip(' ,')


def deduplicate(waypoints):
    result = []
    result.append(waypoints[0])
    for waypoint in waypoints[1:]:
        if (waypoint[1], waypoint[2]) != (result[-1][1], result[-1][2]):
            result.append(waypoint)

    return result


def get_waypoints_from_file(filename):
    sys.stdout.write('Processing {}\n'.format(filename))
    try:
        xml = etree.parse(path.join(path.abspath(filename)))
        return [[position.get('Date'), position.get('Lat'), position.get('Lon')] for position in xml.getroot().find('TrackInfo').findall('Position')]
    except Exception as ex:
        sys.stdout.write('Error: {}'.format(str(ex)))
        sys.exit(1)


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
            'Date': waypoint[0],
            'Lat': waypoint[1],
            'Lon': waypoint[2],
            'Type': 'WP'
        }

        if i == 0:
            attribs['Type'] = 'BR'
            attribs['TimeFix'] = '1'
            attribs['Name'] = get_port_name(waypoint[0][:10], 'BR')

        if i == len(waypoints) - 1:
            attribs['Type'] = 'ER'
            attribs['TimeFix'] = '1'
            attribs['Name'] = get_port_name(waypoint[0][:10], 'ER')

        etree.SubElement(trackinfo, 'Position', attrib=attribs)

    try:
        xml.write(filename, xml_declaration=True, method='xml')
    except Exception as n:
        sys.stdout.write('Error: ' + str(n) + '\nThe file is probably write protected.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--files',
        nargs='*',
        type=str,
        help='Input files. A comma delimited list of bvs files to merge. There should be at least two files.'
    )
    parser.add_argument('-o', '--output', type=str, help='Output file. Defaults to current directory')

    args = parser.parse_args()

    if len(args.files) < 2:
        sys.stdout.write('You can\'t merge less than two files together you fool!')
        sys.exit(1)

    if not args.output:
        output = 'merged.bvs'
    else:
        output = args.output

    waypoints = []
    for filename in args.files:
        for waypoint in deduplicate(get_waypoints_from_file(clean_filename(filename))):
            waypoints.append(waypoint)

    writebvs(output, waypoints)
    sys.stdout.write('Files merged to {}'.format(output))
    sys.exit(0)

if __name__ == '__main__':
    main()