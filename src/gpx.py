
import argparse
import datetime
import math
import os.path
import re
import json
import unittest
import urllib
import xml.dom.minidom

class ElevationProvider:
    pass

class ElevationProviderGoogle:

    ELEVATION_BASE_URL = 'https://maps.googleapis.com/maps/api/elevation/json'

class ElevationProviderMapQuest:
    """MapQuest

    http://open.mapquestapi.com/elevation/
    """

    ELEVATION_BASE_URL = 'http://open.mapquestapi.com/elevation/v1/profile'

    def __init__(self):
        self._key = ''

    def getElevationData(self, points):

        print points
        urlArgs = {
            'key': self._key,
            'latLngCollection': points
        } 

        url = self.ELEVATION_BASE_URL + '?' + urllib.urlencode(urlArgs)
        print url
         
        response = json.load(urllib.urlopen(url))
        print response

        #for resultSet in response['results']:
            #print resultSet
            #elevationArray.append(resultset['elevation'])

        #&callback=handleHelloWorldResponse&shapeFormat=raw&latLngCollection=39.74012,-104.9849,39.7995,-105.7237,39.6404,-106.3736

class GeoUtils:
    # One degree in meters:
    ONE_DEGREE = 1000. * 10000.8 / 90.

    # Earth radius in meters 
    EARTH_RADIUS = 6371.8 * 1000

    MODE_2D = 0
    MODE_3D = 1

    @staticmethod
    def to_rad(x):
        return x / 180.0 * math.pi

    @staticmethod
    def length(locations=None, mode=MODE_2D):
        if locations is None:
            return 0
        #harversine

        length = 0
        lastLoc = None
        for i in xrange(len(locations)):
            if lastLoc is not None:
                if mode == GeoUtils.MODE_3D:
                    d = locations[i].distance3d(lastLoc)
                else:
                    d = locations[i].distance2d(lastLoc)
                length += d
            lastLoc = locations[i]
        return length

    @staticmethod
    def distanceHarversine(lat1, lon1, lat2, lon2):
        """
        Haversine distance between two points.

        Implemented from http://www.movable-type.co.uk/scripts/latlong.html
        """
        d_lat = GeoUtils.to_rad(lat1 - lat2)
        d_lon = GeoUtils.to_rad(lon1 - lon2)
        lat1 = GeoUtils.to_rad(lat1)
        lat2 = GeoUtils.to_rad(lat2)

        a = math.sin(d_lat/2) * math.sin(d_lat/2) + \
            math.sin(d_lon/2) * math.sin(d_lon/2) * math.cos(lat1) * math.cos(lat2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = GeoUtils.EARTH_RADIUS * c

        return d

    @staticmethod
    def distance(lat1, lon1, ele1, lat2, lon2, ele2):
        """
        Distance between two points. If elevation is None compute a 2d distance

        """

        coef = math.cos(lat1 / 180.0 * math.pi)
        x = lat1 - lat2
        y = (lon1 - lon2) * coef

        distance2d = math.sqrt(x * x + y * y) * GeoUtils.ONE_DEGREE

        if ele1 is None or ele2 is None or ele1 == ele2:
            return distance2d

        return math.sqrt(distance2d ** 2 + (ele1 - ele2) ** 2)

    @staticmethod
    def smoothElevationData(elevations):
        result = []

        for n, ele in enumerate(elevations):
            # modify elevation according to previous and next item(s)
            if n > 0:
                if n < (len(elevations) - 1):
                    result.append(elevations[n - 1] * 0.3 + elevations[n] * 0.4  + elevations[n + 1] * 0.3)
                else:
                    # last item
                    result.append(elevations[n - 1] * 0.3 + elevations[n] * 0.7)
            else:
                # first item
                if n < (len(elevations) - 1):
                    result.append(elevations[n] * 0.7  + elevations[n + 1] * 0.3)
                else:
                    result.append(elevations[n])

        return result 

    @staticmethod
    def getUpDownHill(elevations, smooth=True):

        #return previous_ele*.3 + current_ele*.4 + next_ele*.3
        #smoothed_elevations = list(map(__filter, range(size)))

        upHill = 0.0
        downHill = 0.0

        if smooth:
            elevations = GeoUtils.smoothElevationData(elevations)

        for n, ele in enumerate(elevations):

            delta = elevations[n] - elevations[n - 1] if n > 0 else 0
            #print delta

            if delta > 0:
                upHill += delta
            else:
                downHill += abs(delta)

        return (upHill, downHill)

class GeoLocation:
    """ Generic geographical location """

    lat = None
    lon = None
    ele = None

    def __init__(self, latitude, longitude, elevation=None):
        self.lat = latitude
        self.lon = longitude
        self.ele = elevation


    def distance2d(self, location):
        if not location:
            return None

        #return GeoUtils.distance(self.lat, self.lon, None, location.lat, location.lon, None)
        return GeoUtils.distanceHarversine(self.lat, self.lon, location.lat, location.lon)

    def distance3d(self, location):
        if not location:
            return None

        return GeoUtils.distance(self.lat, self.lon, self.ele, location.lat, location.lon, location.ele)

    def __str__(self):
        return '[loc:%s,%s@%s]' % (self.lat, self.lon, self.ele)

class GpxTrackPoint(GeoLocation):
    def __init__(self, latitude=0, longitude=0, elevation=None, time=None, symbol=None, comment=None,
            horizontal_dilution=None, vertical_dilution=None, position_dilution=None, speed=None,
            name=None):

        GeoLocation.__init__(self, latitude, longitude, elevation)

        self.time = time
        self.symbol = symbol
        self.comment = comment
        self.name = name

class GpxTrackSegment:
    def __init__(self, points=None):
        self.points = points if points else []

    def length2d(self):
        return GeoUtils.length(self.points, GeoUtils.MODE_2D)

    def length3d(self):
        return GeoUtils.length(self.points, GeoUtils.MODE_3D)

    def getUpDownHill(self, smooth=True):
        elevations = list(map(lambda point:point.ele, self.points))
        result = GeoUtils.getUpDownHill(elevations, smooth)

        return result

class GpxTrack:
    def __init__(self, name=None, description=None, number=None):
        self.name = name
        self.description = description
        self.number = number
        self.segments = []
    
    def length2d(self):
        length = 0
        for segment in self.segments:
            length += segment.length2d()
        return length
 
    def length3d(self):
        length = 0
        for segment in self.segments:
            length += segment.length3d()
        return length

    def getDuration(self):
        result = 0
        for segment in self.segments:
            result += segment.getDuration()
        return result

    def getUpDownHill(self, smooth=True):

        # default
        upHill = 0
        downHill = 0

        if not self.segments:
            return (upHill, downHill)

        for s in self.segments:
            (sUpHill, sDownHill) = s.getUpDownHill(smooth)

            upHill += sUpHill
            downHill += sDownHill

        return (upHill, downHill)

    def getElevationExtremes(self):
        return None

        if not self.segments:
            return MinimumMaximum(None, None)

        elevations = []

        for s in self.segments:
            (_min, _max) = s.getElevationExtremes()
            if _min is not None:
                elevations.append(_min)
            if _max is not None:
                elevations.append(_max)

        if len(elevations) == 0:
            return MinimumMaximum(None, None)

        return MinimumMaximum(min(elevations), max(elevations))
    
class Gpx:
    def __init__(self):
        self.creator = None
        self.name = None
        self.description = None
        self.author = None
        self.email = None
        self.url = None
        self.urlname = None
        self.time = None
        self.keywords = None

        self.waypoints = []
        self.routes = []
        self.tracks = []
      
        self.min_latitude = None
        self.max_latitude = None
        self.min_longitude = None
        self.max_longitude = None
 
class GpxReader:
    pass

class GpxReaderXml(GpxReader):
    DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    def __init__(self, xmlDoc):
        if  isinstance(xmlDoc, xml.dom.minidom.Document):
            self.xmlDoc = xmlDoc 
        else:
            if not os.path.isfile(str(xmlDoc)):
                raise IOError('File does not exist: %s' % str(xmlDoc)) 
            self.xmlDoc = xml.dom.minidom.parse(xmlDoc)

        self.parse()

    @staticmethod
    def parseTime(val):
        m = re.match(r'^(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?Z$', val)
        if m is None:
            raise ValueError('Invalid datetime: %s' % val)
        miliSeconds = int(m.group(7)[1:]) if m.group(7) is not None else 0
        result = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), miliSeconds)
        return result

    @staticmethod
    def getNodeData(node):
        if node is None: return None

        if not node.childNodes or len(node.childNodes) == 0:
            return None

        return node.childNodes[0].nodeValue

    def parse(self):
        # create empty Gpx instance
        self.gpx = Gpx()

        # get root node
        rootNodes = self.xmlDoc.getElementsByTagName('gpx')
        if rootNodes is None or len(rootNodes) > 1:
            raise Exception('Document must have a one `gpx` root node.')
        rootNode = rootNodes[0]

        if rootNode.hasAttribute('creator'):
            self.gpx.creator = rootNode.getAttribute('creator')

        for node in rootNode.childNodes:

            # skip nodes which are not elements
            if not node.nodeType == node.ELEMENT_NODE:
                continue

            # gpx attributes
            if node.tagName == 'time':
                timeStr = GpxReaderXml.getNodeData(node)
                self.gpx.time = GpxReaderXml.parseTime(timeStr)
            elif node.tagName == 'name':
                self.gpx.name = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'desc':
                self.gpx.description = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'author':
                self.gpx.author = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'email':
                self.gpx.email = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'url':
                self.gpx.url = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'urlname':
                self.gpx.urlname = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'keywords':
                self.gpx.keywords = GpxReaderXml.getNodeData(node)

            # bounds
            elif node.tagName == 'bounds':
                self._parse_bounds(node)

            # waypoints 
            elif node.tagName == 'wpt':
                self.gpx.waypoints.append(self._parse_waypoint(node))

            # routes 
            elif node.tagName == 'rte':
                self.gpx.routes.append(self._parse_route(node))

            # tracks 
            elif node.tagName == 'trk':
                self.gpx.tracks.append(self._parseTrack(node))
            else:
                #print 'unknown %s' % node
                pass

        self.valid = True

    def _parse_bounds(self, node):
        minlat = self.xml_parser.get_node_attribute(node, 'minlat')
        if minlat:
            self.gpx.min_latitude = mod_utils.to_number(minlat)

        maxlat = self.xml_parser.get_node_attribute(node, 'maxlat')
        if maxlat:
            self.gpx.min_latitude = mod_utils.to_number(maxlat)

        minlon = self.xml_parser.get_node_attribute(node, 'minlon')
        if minlon:
            self.gpx.min_longitude = mod_utils.to_number(minlon)

        maxlon = self.xml_parser.get_node_attribute(node, 'maxlon')
        if maxlon:
            self.gpx.min_longitude = mod_utils.to_number(maxlon)

    def _parse_waypoint(self, node):
        lat = self.xml_parser.get_node_attribute(node, 'lat')
        if not lat:
            raise mod_gpx.GPXException('Waypoint without latitude')

        lon = self.xml_parser.get_node_attribute(node, 'lon')
        if not lon:
            raise mod_gpx.GPXException('Waypoint without longitude')

        lat = mod_utils.to_number(lat)
        lon = mod_utils.to_number(lon)

        elevation_node = self.xml_parser.get_first_child(node, 'ele')
        elevation = mod_utils.to_number(self.xml_parser.get_node_data(elevation_node), None)

        time_node = self.xml_parser.get_first_child(node, 'time')
        time_str = self.xml_parser.get_node_data(time_node)
        time = parse_time(time_str)

        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        desc_node = self.xml_parser.get_first_child(node, 'desc')
        desc = self.xml_parser.get_node_data(desc_node)

        sym_node = self.xml_parser.get_first_child(node, 'sym')
        sym = self.xml_parser.get_node_data(sym_node)

        type_node = self.xml_parser.get_first_child(node, 'type')
        type = self.xml_parser.get_node_data(type_node)

        comment_node = self.xml_parser.get_first_child(node, 'cmt')
        comment = self.xml_parser.get_node_data(comment_node)

        hdop_node = self.xml_parser.get_first_child(node, 'hdop')
        hdop = mod_utils.to_number(self.xml_parser.get_node_data(hdop_node))

        vdop_node = self.xml_parser.get_first_child(node, 'vdop')
        vdop = mod_utils.to_number(self.xml_parser.get_node_data(vdop_node))

        pdop_node = self.xml_parser.get_first_child(node, 'pdop')
        pdop = mod_utils.to_number(self.xml_parser.get_node_data(pdop_node))

        return mod_gpx.GPXWaypoint(latitude=lat, longitude=lon, elevation=elevation,
            time=time, name=name, description=desc, symbol=sym,
            type=type, comment=comment, horizontal_dilution=hdop,
            vertical_dilution=vdop, position_dilution=pdop)

    def _parse_route(self, node):
        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        description_node = self.xml_parser.get_first_child(node, 'desc')
        description = self.xml_parser.get_node_data(description_node)

        number_node = self.xml_parser.get_first_child(node, 'number')
        number = mod_utils.to_number(self.xml_parser.get_node_data(number_node))

        route = mod_gpx.GPXRoute(name, description, number)

        child_nodes = self.xml_parser.get_children(node)
        for child_node in child_nodes:
            if self.xml_parser.get_node_name(child_node) == 'rtept':
                route_point = self._parse_route_point(child_node)
                route.points.append(route_point)

        return route

    def _parse_route_point(self, node):
        lat = self.xml_parser.get_node_attribute(node, 'lat')
        if not lat:
            raise mod_gpx.GPXException('Waypoint without latitude')

        lon = self.xml_parser.get_node_attribute(node, 'lon')
        if not lon:
            raise mod_gpx.GPXException('Waypoint without longitude')

        lat = mod_utils.to_number(lat)
        lon = mod_utils.to_number(lon)

        elevation_node = self.xml_parser.get_first_child(node, 'ele')
        elevation = mod_utils.to_number(self.xml_parser.get_node_data(elevation_node), None)

        time_node = self.xml_parser.get_first_child(node, 'time')
        time_str = self.xml_parser.get_node_data(time_node)
        time = parse_time(time_str)

        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        desc_node = self.xml_parser.get_first_child(node, 'desc')
        desc = self.xml_parser.get_node_data(desc_node)

        sym_node = self.xml_parser.get_first_child(node, 'sym')
        sym = self.xml_parser.get_node_data(sym_node)

        type_node = self.xml_parser.get_first_child(node, 'type')
        type = self.xml_parser.get_node_data(type_node)

        comment_node = self.xml_parser.get_first_child(node, 'cmt')
        comment = self.xml_parser.get_node_data(comment_node)

        hdop_node = self.xml_parser.get_first_child(node, 'hdop')
        hdop = mod_utils.to_number(self.xml_parser.get_node_data(hdop_node))

        vdop_node = self.xml_parser.get_first_child(node, 'vdop')
        vdop = mod_utils.to_number(self.xml_parser.get_node_data(vdop_node))

        pdop_node = self.xml_parser.get_first_child(node, 'pdop')
        pdop = mod_utils.to_number(self.xml_parser.get_node_data(pdop_node))

        return mod_gpx.GPXRoutePoint(lat, lon, elevation, time, name, desc, sym, type, comment,
            horizontal_dilution = hdop, vertical_dilution = vdop, position_dilution = pdop)

    def _parseTrack(self, trackNode):
        track = GpxTrack()
         
        for node in trackNode.childNodes:
            # skip nodes which are not elements
            if not node.nodeType == node.ELEMENT_NODE:
                continue

            # track attributes
            if node.tagName == 'name':
                track.name = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'desc':
                track.description = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'number':
                self.gpx.number= GpxReaderXml.getNodeData(node)
            elif node.tagName == 'trkseg':
                track.segments.append(self._parseTrackSegment(node))

        return track

    def _parseTrackSegment(self, segmentNode):
        segment = GpxTrackSegment()

        for node in segmentNode.childNodes:
            # skip nodes which are not elements
            if not node.nodeType == node.ELEMENT_NODE:
                continue

            if node.tagName == 'trkpt':
                trackPoint = self._parseTrackPoint(node)
                segment.points.append(trackPoint)

        return segment

    def _parseTrackPoint(self, trackPointNode):
        trackPoint = GpxTrackPoint()

        if trackPointNode.hasAttribute('lat'):
            trackPoint.lat = float(trackPointNode.getAttribute('lat'))
        if trackPointNode.hasAttribute('lon'):
            trackPoint.lon = float(trackPointNode.getAttribute('lon'))
             
        for node in trackPointNode.childNodes:

            # skip nodes which are not elements
            if not node.nodeType == node.ELEMENT_NODE:
                continue

            if node.tagName == 'ele':
                trackPoint.ele = float(GpxReaderXml.getNodeData(node))
            elif node.tagName == 'time':
                timeStr = GpxReaderXml.getNodeData(node)
                trackPoint.time = GpxReaderXml.parseTime(timeStr)
            elif node.tagName == 'sym':
                trackPoint.symbol = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'com':
                trackPoint.comment = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'fix':
                trackPoint.fix = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'name':
                trackPoint.name = GpxReaderXml.getNodeData(node)
            elif node.tagName == 'hdop':
                trackPoint.hdop= int(GpxReaderXml.getNodeData(node))
            elif node.tagName == 'vdop':
                trackPoint.vdop= int(GpxReaderXml.getNodeData(node))
            elif node.tagName == 'pdop':
                trackPoint.pdop= int(GpxReaderXml.getNodeData(node))
            elif node.tagName == 'sat':
                trackPoint.sat = int(GpxReaderXml.getNodeData(node))
            elif node.tagName == 'speed':
                trackPoint.speed = float(GpxReaderXml.getNodeData(node))

        return trackPoint


### Unit Testing #########################################

class UnitTests(unittest.TestCase):
    """Unit tests definition"""

    def testLocation(self):
        l = GeoLocation(23, 56)
        self.assertEqual(l.lat, 23)
        self.assertEqual(l.lon, 56)
        self.assertIsNone(l.ele)

    def testGeoUtils(self):
        l1 = GeoLocation(0, 0)
        l2 = GeoLocation(1, 0)
        l = GeoUtils.length([l1, l2])

    def testGeoUtilsElevations(self):
        (up, down) = GeoUtils.getUpDownHill([100])
        self.assertEquals(up, 0)
        self.assertEquals(down, 0)

        (up, down) = GeoUtils.getUpDownHill([100, 200], False)
        self.assertEquals(up, 100)
        self.assertEquals(down, 0)

        (up, down) = GeoUtils.getUpDownHill([200, 100, 10, 80, 50], False)
        self.assertEquals(up, 70)
        self.assertEquals(down, 220)

    def testReaderXml(self):
        t = GpxReaderXml.parseTime('2015-02-23T19:22:18.061Z')
        t = GpxReaderXml.parseTime('2015-02-23T19:22:18Z')

    def testReaderXmlGpx(self):
        data = ('<gpx>\n'
                '  <name>TestName</name>\n'
                '  <desc>TestDescription</desc>\n'
                '  <author>TestAuthor</author>\n'
                '  <email>TestEmail</email>\n'
                '  <url>http://www.testurl.org/test</url>\n'
                '  <urlname>TestUrlName</urlname>\n'
                '  <time>2015-02-23T19:22:18Z</time>\n'
                '  <keywords>Test1, Test2, Test3</keywords>\n'
                '</gpx>\n')

        xmlDoc = xml.dom.minidom.parseString(data)

        reader = GpxReaderXml(xmlDoc)
       
        self.assertEquals(reader.gpx.name, 'TestName')
        self.assertEquals(reader.gpx.description, 'TestDescription')
        self.assertEquals(reader.gpx.author, 'TestAuthor')
        self.assertEquals(reader.gpx.email, 'TestEmail')
        self.assertEquals(reader.gpx.url, 'http://www.testurl.org/test')
        self.assertEquals(reader.gpx.urlname, 'TestUrlName')
        self.assertEquals(reader.gpx.time, datetime.datetime(2015, 2, 23, 19, 22, 18))
        self.assertEquals(reader.gpx.keywords, 'Test1, Test2, Test3')

    def testReaderXmlTrack(self):
        data = ('<gpx>\n'
                '  <trk>\n'
                '    <name>TestName</name>\n'
                '  </trk>\n'
                '</gpx>\n')

        xmlDoc = xml.dom.minidom.parseString(data)

        reader = GpxReaderXml(xmlDoc)

        self.assertEquals(len(reader.gpx.tracks), 1)
        track = reader.gpx.tracks[0]
        self.assertEquals(track.name, 'TestName')

    def testReaderXmlTrackSegment(self):
        data = ('<gpx>\n'
                '  <trk>\n'
                '    <trkseg>\n'
                '      <trkpt lat="1" lon="2"><ele>2376</ele><time>2007-10-14T10:09:57Z</time></trkpt>\n'
                '      <trkpt lat="3" lon="4"><time>2007-10-15T23:00:00Z</time></trkpt>\n'
                '    </trkseg>\n'
                '  </trk>\n'
                '</gpx>\n')

        xmlDoc = xml.dom.minidom.parseString(data)

        reader = GpxReaderXml(xmlDoc)
       
        self.assertEquals(len(reader.gpx.tracks), 1)
        track = reader.gpx.tracks[0]
        self.assertEquals(len(track.segments), 1)
        ts = track.segments[0]
        self.assertEquals(len(ts.points), 2)
        tp1 = ts.points[0]
        self.assertEquals(tp1.lat, 1)
        self.assertEquals(tp1.lon, 2)

    def testElevationMapQuest(self):
        ep = ElevationProviderMapQuest()
        ep.getElevationData([0, 0])
         
if __name__ == '__main__':
    unittest.main()


