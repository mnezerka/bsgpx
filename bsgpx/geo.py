
import math
import unittest

# One degree in meters:
ONE_DEGREE = 1000. * 10000.8 / 90.

# Earth radius in meters 
EARTH_RADIUS = 6371.8 * 1000

MODE_2D = 0
MODE_3D = 1

def to_rad(x):
    return x / 180.0 * math.pi

def length(locations=None, mode=MODE_2D):
    if locations is None:
        return 0
    #harversine

    length = 0
    lastLoc = None
    for i in xrange(len(locations)):
        if lastLoc is not None:
            if mode == MODE_3D:
                d = locations[i].distance3d(lastLoc)
            else:
                d = locations[i].distance2d(lastLoc)
            length += d
        lastLoc = locations[i]
    return length

def distanceHarversine(lat1, lon1, lat2, lon2):
    """
    Haversine distance between two points.

    Implemented from http://www.movable-type.co.uk/scripts/latlong.html
    """
    d_lat = to_rad(lat1 - lat2)
    d_lon = to_rad(lon1 - lon2)
    lat1 = to_rad(lat1)
    lat2 = to_rad(lat2)

    a = math.sin(d_lat/2) * math.sin(d_lat/2) + \
        math.sin(d_lon/2) * math.sin(d_lon/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = EARTH_RADIUS * c

    return d

def distance(lat1, lon1, ele1, lat2, lon2, ele2):
    """
    Distance between two points. If elevation is None compute a 2d distance

    """

    coef = math.cos(lat1 / 180.0 * math.pi)
    x = lat1 - lat2
    y = (lon1 - lon2) * coef

    distance2d = math.sqrt(x * x + y * y) * ONE_DEGREE

    if ele1 is None or ele2 is None or ele1 == ele2:
        return distance2d

    return math.sqrt(distance2d ** 2 + (ele1 - ele2) ** 2)

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

def getUpDownHill(elevations, smooth=True):

    #return previous_ele*.3 + current_ele*.4 + next_ele*.3
    #smoothed_elevations = list(map(__filter, range(size)))

    upHill = 0.0
    downHill = 0.0

    if smooth:
        elevations = smoothElevationData(elevations)

    for n, ele in enumerate(elevations):

        delta = elevations[n] - elevations[n - 1] if n > 0 else 0
        #print delta

        if delta > 0:
            upHill += delta
        else:
            downHill += abs(delta)

    return (upHill, downHill)

class Location:
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

        #return distance(self.lat, self.lon, None, location.lat, location.lon, None)
        return distanceHarversine(self.lat, self.lon, location.lat, location.lon)

    def distance3d(self, location):
        if not location:
            return None

        return distance(self.lat, self.lon, self.ele, location.lat, location.lon, location.ele)

    def __str__(self):
        return '[loc:%s,%s@%s]' % (self.lat, self.lon, self.ele)

### Unit Testing #########################################

class UnitTests(unittest.TestCase):
    """Unit tests definition"""

    def testLocation(self):
        l = Location(23, 56)
        self.assertEqual(l.lat, 23)
        self.assertEqual(l.lon, 56)
        self.assertIsNone(l.ele)

    def testGeoUtils(self):
        l1 = Location(0, 0)
        l2 = Location(1, 0)
        l = length([l1, l2])

    def testGeoUtilsElevations(self):
        (up, down) = getUpDownHill([100])
        self.assertEquals(up, 0)
        self.assertEquals(down, 0)

        (up, down) = getUpDownHill([100, 200], False)
        self.assertEquals(up, 100)
        self.assertEquals(down, 0)

        (up, down) = getUpDownHill([200, 100, 10, 80, 50], False)
        self.assertEquals(up, 70)
        self.assertEquals(down, 220)
        
if __name__ == '__main__':
    unittest.main()

