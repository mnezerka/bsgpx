import json
import unittest
import urllib
import urllib2
import geo

class ElevationProvider:
    def __init__(self, conf = {}):
       self.conf = conf
        
    def getElevationData(self, points):
        raise NotImplementedError('Abstract method')

class ElevationProviderGoogle(ElevationProvider):
    ELEVATION_BASE_URL = 'https://maps.googleapis.com/maps/api/elevation/json'

class ElevationProviderMapQuest(ElevationProvider):
    """MapQuest

    http://open.mapquestapi.com/elevation/
    """

    ELEVATION_BASE_URL = 'http://open.mapquestapi.com/elevation/v1/profile'

    def getElevationData(self, locations):
        """Get elevation data from Map Quest server"""
         
        if 'key' not in self.conf:
            raise RuntimeError('key parameter is required')

        # convert all points to single sequence of numbers
        reqPoints = [] 
        for l in locations:
            reqPoints.append(l.lat)
            reqPoints.append(l.lon)

        urlParams = {
            'format': 'json',
        }
        url = self.ELEVATION_BASE_URL + '?key=' + self.conf['key'] + '&' + urllib.urlencode(urlParams)
        body = { 'latLngCollection': reqPoints }
        postData = json.dumps(body)
        headers = {'Content-Type': 'application/json'}
        req = urllib2.Request(url, postData, headers)
        f = urllib2.urlopen(req)
        response = json.load(f)
        f.close()

        resInfo = response['info']
        if resInfo['statuscode'] != 0:
            raise RuntimeError(' '.join(resInfo['messages']))

        eleProfile = response['elevationProfile']

        for ix, loc in enumerate(locations):
            loc.ele = eleProfile[ix]['height']

class ElevationProviderFactory:
    __providers = { 'mapquest': ElevationProviderMapQuest }

    @staticmethod
    def getProviders():
        return ElevationProviderFactory.__providers

    @staticmethod
    def getProvider(id):
        if id in ElevationProviderFactory.__providers:
            return ElevationProviderFactory.__providers[id]
        return None

### Unit Testing #########################################

class UnitTests(unittest.TestCase):
    def testElevationMapQuest(self):
        holedna = geo.GeoLocation(49.1990681, 16.5280778)
        trista = geo.GeoLocation(49.2067019, 16.5137869)
        doma = geo.GeoLocation(49.2203092, 16.5558653)

        ep = ElevationProviderMapQuest()
        self.assertRaises(RuntimeError, ep.getElevationData, [])

        ep = ElevationProviderMapQuest({'key': 'yourkey'})
        ep.getElevationData([holedna, trista, doma])

    def testFactory(self):
        pList = ElevationProviderFactory.getProviders()
        self.assertTrue('mapquest' in pList)   
        p = ElevationProviderFactory.getProvider('xxx')
        self.assertTrue(p is None)
        p = ElevationProviderFactory.getProvider('mapquest')
        self.assertTrue(p == ElevationProviderMapQuest)
             
if __name__ == '__main__':
    unittest.main()


