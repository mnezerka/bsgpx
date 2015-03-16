
import sys
import argparse
import gpx

parser = argparse.ArgumentParser(description='Tool for reading and processing files in GPX format') 
parser.add_argument('gpx_file_path', help='Input GPX file')
parser.add_argument('-l', help='List items in GPX file', action='store_true')
args = parser.parse_args()

# create instance of check processor (check that file exists)
#try:
gpxReader = gpx.GpxReaderXml(args.gpx_file_path)
gpxFile = gpxReader.gpx
#except Exception as e:
#    sys.stderr.write('Error: %s\n' % str(e))
#    sys.exit(1)

# if list of ids is requested
if args.l: 
    if gpxFile.creator:
        print 'Creator:', gpxFile.creator
    if gpxFile.name:
        print 'Name:', gpxFile.name
    print 'Tracks:', len(gpxFile.tracks)

    for t in gpxFile.tracks:
        print '  Length 2d:', t.length2d() / 1000, 'kilometers'
        print '  Length 3d:', t.length3d() / 1000, 'kilometers'
        print '  Segments:', len(t.segments)
        for s in t.segments:
            print '    Points:', len(s.points)



