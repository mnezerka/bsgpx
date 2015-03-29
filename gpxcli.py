import argparse
import sys
import ConfigParser
import bsgpx.gpx

epilog = 'Commands: list, print, ele'
parser = argparse.ArgumentParser(description='Tool for reading and processing files in GPX format', epilog=epilog) 
parser.add_argument('gpx_file_path', help='Input GPX file')
parser.add_argument('command', help='Commands to be executed', nargs='+')
parser.add_argument('-l', help='List items in GPX file', action='store_true')
parser.add_argument('-p', help='Generate track(s) profile', action='store_true')
parser.add_argument('-c', help='Path to configuration file')

args = parser.parse_args()

# read configuration from config file
config = ConfigParser.RawConfigParser()
if args.c:
    print args.c
    config.read(args.c)
    print config.get('elevation', 'provider')

# create instance of check processor (check that file exists)
gpxReader = bsgpx.gpx.GpxReaderXml(args.gpx_file_path)
gpxFile = gpxReader.gpx

for cmd in args.command:

    # if adding elevation data is requested
    if cmd == 'ele':
        for t in gpxFile.tracks:
            for s in t.segments:
                print '    Points:', len(s.points)

    # if list of ids is requested
    if cmd == 'list':
        if gpxFile.creator:
            print 'Creator:', gpxFile.creator
        if gpxFile.name:
            print 'Name:', gpxFile.name
        print 'Tracks:', len(gpxFile.tracks)

        for t in gpxFile.tracks:
            (upSmooth, downSmooth) = t.getUpDownHill(True)
            (up, down) = t.getUpDownHill(False)
            print '  Length 2d:', t.length2d() / 1000, 'kilometers'
            print '  Length 3d:', t.length3d() / 1000, 'kilometers'
            print '  Up:', up, 'smooth:', upSmooth 
            print '  Down:', down, 'smooth:', downSmooth

            print '  Segments:', len(t.segments)
            for s in t.segments:
                print '    Points:', len(s.points)

    # if gpx print is requested
    elif cmd == 'print':
        print gpxFile

