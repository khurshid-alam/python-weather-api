#Copyright (c) 2009 Eugene Kaznacheev <qetzal@gmail.com>
#Copyright (c) 2013 Joshua Tasker <jtasker@gmail.com>

#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:

#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

"""
Fetches weather reports from Google Weather, Yahoo! Weather, Weather.com and NOAA
"""

try:
    # Python 3 imports
    from urllib.request import urlopen
    from urllib.parse import quote
    from urllib.parse import urlencode
    from urllib.error import URLError
except ImportError:
    # Python 2 imports
    from urllib2 import urlopen
    from urllib import quote
    from urllib import urlencode
    from urllib2 import URLError
import sys
import re
from xml.dom import minidom

GOOGLE_COUNTRIES_URL   = 'http://www.google.com/ig/countries?output=xml&hl=%s'
GOOGLE_CITIES_URL      = 'http://www.google.com/ig/cities?output=xml&country=%s&hl=%s'

YAHOO_WEATHER_URL      = 'http://xml.weather.yahoo.com/forecastrss/%s_%s.xml'
YAHOO_WEATHER_NS       = 'http://xml.weather.yahoo.com/ns/rss/1.0'

NOAA_WEATHER_URL       = 'http://www.weather.gov/xml/current_obs/%s.xml'

WEATHER_COM_URL        = 'http://xml.weather.com/weather/local/%s?par=1138276742&key=15ee9c789ccd70f5&unit=%s&dayf=5&cc=*'

LOCID_SEARCH_URL       = 'http://xml.weather.com/search/search?where=%s'

WOEID_SEARCH_URL       = 'http://query.yahooapis.com/v1/public/yql'
WOEID_QUERY_STRING     = 'select line1, line2, line3, line4, woeid from geo.placefinder where text="%s"'

#WXUG_FORECAST_URL      = 'http://api.wunderground.com/auto/wui/geo/ForecastXML/index.xml?query=%s'
#WXUG_CURRENT_URL       = 'http://api.wunderground.com/auto/wui/geo/WXCurrentObXML/index.xml?query=%s'
#WXUG_GEOLOOKUP_URL     = 'http://api.wunderground.com/auto/wui/geo/GeoLookupXML/index.xml?query=%s'
#WXUG_ALERTS_URL        = 'http://api.wunderground.com/auto/wui/geo/AlertsXML/index.xml?query=%s'

def get_weather_from_weather_com(location_id, units = 'metric'):
    """
    Fetches weather report from Weather.com

    Parameters:
      location_id: A five digit US zip code or location ID. To find your location ID,
      browse or search for your city from the Weather.com home page (http://www.weather.com/)
      The weather ID is in the URL for the forecast page for that city. You can also get
      the location ID by entering your zip code on the home page. For example, if you
      search for Los Angeles on the Weather home page, the forecast page for that city
      is http://www.weather.com/weather/today/Los+Angeles+CA+USCA0638:1:US. The location
      ID is USCA0638.

      units: type of units. 'metric' for metric and '' for non-metric
      Note that choosing metric units changes all the weather units to metric,
      for example, wind speed will be reported as kilometers per hour and
      barometric pressure as millibars.
 
    Returns:
      weather_data: a dictionary of weather data that exists in XML feed.
    """
    location_id = quote(location_id)
    if units == 'metric':
        unit = 'm'
    else:
        unit = ''
    url = WEATHER_COM_URL % (location_id, unit)
    try:
        handler = urlopen(url)
    except URLError:
        return {'error': 'Could not connect to Weather.com'}
    if sys.version > '3':
        # Python 3
        content_type = dict(handler.getheaders())['Content-Type']
    else:
        # Python 2
        content_type = handler.info().dict['content-type']
    charset = re.search('charset\=(.*)',content_type).group(1)
    if not charset:
        charset = 'utf-8'
    if charset.lower() != 'utf-8':
        xml_response = handler.read().decode(charset).encode('utf-8')
    else:
        xml_response = handler.read()
    dom = minidom.parseString(xml_response)    
    handler.close()

    try:
        weather_dom = dom.getElementsByTagName('weather')[0]
    except IndexError:
        error_data = {'error': dom.getElementsByTagName('error')[0].getElementsByTagName('err')[0].firstChild.data}
        dom.unlink()
        return error_data

    key_map = {'head':'units', 'ut':'temperature', 'ud':'distance',
               'us':'speed', 'up':'pressure', 'ur':'rainfall',
               'loc':'location', 'dnam':'name', 'lat':'lat', 'lon':'lon',
               'cc':'current_conditions', 'lsup':'last_updated',
               'obst':'station', 'tmp':'temperature',
               'flik':'feels_like', 't':'text', 'icon':'icon',
               'bar':'barometer', 'r':'reading', 'd':'direction',
               'wind':'wind', 's':'speed', 'gust':'gust', 'hmid':'humidity',
               'vis':'visibility', 'uv':'uv', 'i':'index', 'dewp':'dewpoint',
               'moon':'moon_phase', 'hi':'high', 'low':'low', 'sunr':'sunrise',
             'suns':'sunset', 'bt':'brief_text', 'ppcp':'chance_precip'}

    data_structure = {'head': ('ut', 'ud', 'us', 'up', 'ur'),
                      'loc': ('dnam', 'lat', 'lon'),
                      'cc': ('lsup', 'obst', 'tmp', 'flik', 't',
                             'icon', 'hmid', 'vis', 'dewp')}
    cc_structure = {'bar': ('r','d'),
                    'wind': ('s','gust','d','t'),
                    'uv': ('i','t'),
                    'moon': ('icon','t')}

    weather_data = {}
    for (tag, list_of_tags2) in data_structure.items():
        key = key_map[tag]
        weather_data[key] = {}
        for tag2 in list_of_tags2:
            key2 = key_map[tag2]
            weather_data[key][key2] = weather_dom.getElementsByTagName(tag)[0].getElementsByTagName(tag2)[0].firstChild.data

    cc_dom = weather_dom.getElementsByTagName('cc')[0]
    for (tag, list_of_tags2) in cc_structure.items():
        key = key_map[tag]
        weather_data['current_conditions'][key] = {}
        for tag2 in list_of_tags2:
            key2 = key_map[tag2]
            weather_data['current_conditions'][key][key2] = cc_dom.getElementsByTagName(tag)[0].getElementsByTagName(tag2)[0].firstChild.data
            
    forecasts = []
    time_of_day_map = {'d':'day', 'n':'night'}
    for forecast in weather_dom.getElementsByTagName('dayf')[0].getElementsByTagName('day'):
        tmp_forecast = {}
        tmp_forecast['day_of_week'] = forecast.getAttribute('t')
        tmp_forecast['date'] = forecast.getAttribute('dt')
        for tag in ('hi', 'low', 'sunr', 'suns'):
            key = key_map[tag]
            tmp_forecast[key] = forecast.getElementsByTagName(tag)[0].firstChild.data
        for part in forecast.getElementsByTagName('part'):
            time_of_day = time_of_day_map[part.getAttribute('p')]
            tmp_forecast[time_of_day] = {}
            for tag2 in ('icon', 't', 'bt', 'ppcp', 'hmid'):
                key2 = key_map[tag2]
                tmp_forecast[time_of_day][key2] = part.getElementsByTagName(tag2)[0].firstChild.data
            tmp_forecast[time_of_day]['wind'] = {}
            for tag2 in ('s', 'gust', 'd', 't'):            
                key2 = key_map[tag2]
                tmp_forecast[time_of_day]['wind'][key2] = part.getElementsByTagName('wind')[0].getElementsByTagName(tag2)[0].firstChild.data
        forecasts.append(tmp_forecast)
        
    weather_data['forecasts'] = forecasts
    
    dom.unlink()
    return weather_data




def get_weather_from_google(location_id, hl = ''): 		
    """ 		
    Fetches weather report from Google. No longer functional,
    since Google discontinued their Weather API as of Sep 2012.
    Method retained for backwards compatibility.

    Parameters 		
    location_id: a zip code (10001); city name, state (weather=woodland,PA); city name, country (weather=london, england); 		
    latitude/longitude(weather=,,,30670000,104019996) or possibly other. 		
    hl: the language parameter (language code). Default value is empty string, in this case Google will use English. 		

    Returns:
    weather_data: a dictionary of weather data that exists in XML feed.

    """
    weather_data = {'error': 'The Google Weather API has been discontinued as of September 2012.'}
    return weather_data


def get_countries_from_google(hl = ''):
    """
    Get list of countries in specified language from Google
    
    Parameters:
      hl: the language parameter (language code). Default value is empty string, in this case Google will use English.
    Returns:
      countries: a list of elements(all countries that exists in XML feed). Each element is a dictionary with 'name' and 'iso_code' keys. 
      For example: [{'iso_code': 'US', 'name': 'USA'}, {'iso_code': 'FR', 'name': 'France'}]
    """
    url = GOOGLE_COUNTRIES_URL % hl
    
    try:
        handler = urlopen(url)
    except URLError:
        return [{'error':'Could not connect to Google'}]
    if sys.version > '3':
        # Python 3
        content_type = dict(handler.getheaders())['Content-Type']
    else:
        # Python 2
        content_type = handler.info().dict['content-type']
    charset = re.search('charset\=(.*)',content_type).group(1)
    if not charset:
        charset = 'utf-8'
    if charset.lower() != 'utf-8':
        xml_response = handler.read().decode(charset).encode('utf-8')
    else:
        xml_response = handler.read()
    dom = minidom.parseString(xml_response)
    handler.close()

    countries = []
    countries_dom = dom.getElementsByTagName('country')
    
    for country_dom in countries_dom:
        country = {}
        country['name'] = country_dom.getElementsByTagName('name')[0].getAttribute('data')
        country['iso_code'] = country_dom.getElementsByTagName('iso_code')[0].getAttribute('data')
        countries.append(country)
    
    dom.unlink()
    return countries

def get_cities_from_google(country_code, hl = ''):
    """
    Get list of cities of necessary country in specified language from Google
    
    Parameters:
      country_code: code of the necessary country. For example 'de' or 'fr'.

      hl: the language parameter (language code). Default value is empty string, in this case Google will use English.

    Returns:
      cities: a list of elements(all cities that exists in XML feed). Each element is a dictionary with 'name', 'latitude_e6' and 'longitude_e6' keys. For example: [{'longitude_e6': '1750000', 'name': 'Bourges', 'latitude_e6': '47979999'}]
    """
    url = GOOGLE_CITIES_URL % (country_code.lower(), hl)
    
    try:
        handler = urlopen(url)
    except URLError:
        return [{'error':'Could not connect to Google'}]
    if sys.version > '3':
        # Python 3
        content_type = dict(handler.getheaders())['Content-Type']
    else:
        # Python 2
        content_type = handler.info().dict['content-type']
    charset = re.search('charset\=(.*)',content_type).group(1)
    if not charset:
        charset = 'utf-8'
    if charset.lower() != 'utf-8':
        xml_response = handler.read().decode(charset).encode('utf-8')
    else:
        xml_response = handler.read()
    dom = minidom.parseString(xml_response)
    handler.close()

    cities = []
    cities_dom = dom.getElementsByTagName('city')
    
    for city_dom in cities_dom:
        city = {}
        city['name'] = city_dom.getElementsByTagName('name')[0].getAttribute('data')
        city['latitude_e6'] = city_dom.getElementsByTagName('latitude_e6')[0].getAttribute('data')
        city['longitude_e6'] = city_dom.getElementsByTagName('longitude_e6')[0].getAttribute('data')
        cities.append(city)
    
    dom.unlink()
    
    return cities

def get_weather_from_yahoo(location_id, units = 'metric'):
    """
    Fetches weather report from Yahoo! Weather

    Parameters:
      location_id: A five digit US zip code or location ID. To find your
      location ID, use function get_location_id()

      units: type of units. 'metric' for metric and '' for non-metric
      Note that choosing metric units changes all the weather units to
      metric. For example, wind speed will be reported as kilometers per
      hour and barometric pressure as millibars.
 
    Returns:
      weather_data: a dictionary of weather data that exists in XML feed.
      See http://developer.yahoo.com/weather/#channel
    """
    location_id = quote(location_id)
    if units == 'metric':
        unit = 'c'
    else:
        unit = 'f'
    url = YAHOO_WEATHER_URL % (location_id, unit)
    try:
        handler = urlopen(url)
    except URLError:
        return {'error': 'Could not connect to Yahoo! Weather'}
    dom = minidom.parse(handler)    
    handler.close()
        
    weather_data = {}
    try:
        weather_data['title'] = dom.getElementsByTagName('title')[0].firstChild.data
        weather_data['link'] = dom.getElementsByTagName('link')[0].firstChild.data
    except IndexError:
        error_data = {'error': dom.getElementsByTagName('item')[0].getElementsByTagName('title')[0].firstChild.data}
        dom.unlink()
        return error_data
        
    ns_data_structure = { 
        'location': ('city', 'region', 'country'),
        'units': ('temperature', 'distance', 'pressure', 'speed'),
        'wind': ('chill', 'direction', 'speed'),
        'atmosphere': ('humidity', 'visibility', 'pressure', 'rising'),
        'astronomy': ('sunrise', 'sunset'),
        'condition': ('text', 'code', 'temp', 'date')
    }       
    
    for (tag, attrs) in ns_data_structure.items():
        weather_data[tag] = xml_get_ns_yahoo_tag(dom, YAHOO_WEATHER_NS, tag, attrs)

    weather_data['geo'] = {}
    try:
        weather_data['geo']['lat'] = dom.getElementsByTagName('geo:lat')[0].firstChild.data
        weather_data['geo']['long'] = dom.getElementsByTagName('geo:long')[0].firstChild.data
    except AttributeError:
        weather_data['geo']['lat'] = u''
        weather_data['geo']['long'] = u''

    weather_data['condition']['title'] = dom.getElementsByTagName('item')[0].getElementsByTagName('title')[0].firstChild.data
    weather_data['html_description'] = dom.getElementsByTagName('item')[0].getElementsByTagName('description')[0].firstChild.data
    
    forecasts = []
    for forecast in dom.getElementsByTagNameNS(YAHOO_WEATHER_NS, 'forecast'):
        forecasts.append(xml_get_attrs(forecast,('day', 'date', 'low', 'high', 'text', 'code')))
    weather_data['forecasts'] = forecasts
    
    dom.unlink()
    return weather_data
    
def get_everything_from_yahoo(country_code, cities):
    """
    Get all weather data from yahoo for a specific country.

    Parameters:
      country_code: A four letter code of the necessary country.
                    For example 'GMXX' or 'FRXX'.
      cities: The maximum number of cities for which to get data
      
    Returns:
      weather_reports: A dictionary containing weather data for each city
    """
    city_codes = yield_all_country_city_codes_yahoo(country_code, cities)
    
    weather_reports = {}
    for city_c in city_codes:
        weather_data = get_weather_from_yahoo(city_c)
        if ('error' in weather_data):
            return weather_data
        city = weather_data['location']['city']
        weather_reports[city] = weather_data
        
    return weather_reports

def yield_all_country_city_codes_yahoo(country_code, cities):
    """
    Yield all cities codes for a specific country.
    
    Parameters:
      country_code: A four letter code of the necessary country.
                    For example 'GMXX' or 'FRXX'.
      cities: The maximum number of cities to yield
      
    Returns:
      country_city_codes: A generator containing the city codes
    """
    
    # cities stands for the number of available cities
    for i in range(1, cities + 1):
        yield ''.join([country_code, (4 - len(str(i))) * '0', str(i)])
    
    
def get_weather_from_noaa(station_id):
    """
    Fetches weather report from NOAA: National Oceanic and Atmospheric Administration (United States)

    Parameter:
      station_id: the ID of the weather station near the necessary location
      To find your station ID, perform the following steps:
      1. Open this URL: http://www.weather.gov/xml/current_obs/seek.php?state=az&Find=Find
      2. Select the necessary state state. Click 'Find'.
      3. Find the necessary station in the 'Observation Location' column.
      4. The station ID is in the URL for the weather page for that station.
      For example if the weather page is http://weather.noaa.gov/weather/current/KPEO.html -- the station ID is KPEO.

      Other way to get the station ID: use this library: http://code.google.com/p/python-weather/ and 'Weather.location2station' function.

    Returns:
      weather_data: a dictionary of weather data that exists in XML feed. 

      (useful icons: http://www.weather.gov/xml/current_obs/weather.php)
    """
    station_id = quote(station_id)
    url = NOAA_WEATHER_URL % (station_id)
    try:
        handler = urlopen(url)
    except URLError:
        return {'error': 'Could not connect to NOAA'}
    dom = minidom.parse(handler)    
    handler.close()
        
    data_structure = ('suggested_pickup',
                'suggested_pickup_period',
                'location',
                'station_id',
                'latitude',
                'longitude',
                'observation_time',
                'observation_time_rfc822',
                'weather',
                'temperature_string',
                'temp_f',
                'temp_c',
                'relative_humidity',
                'wind_string',
                'wind_dir',
                'wind_degrees',
                'wind_mph',
                'wind_gust_mph',
                'pressure_string',
                'pressure_mb',
                'pressure_in',
                'dewpoint_string',
                'dewpoint_f',
                'dewpoint_c',
                'heat_index_string',
                'heat_index_f',
                'heat_index_c',
                'windchill_string',
                'windchill_f',
                'windchill_c',
                'icon_url_base',
                'icon_url_name',
                'two_day_history_url',
                'ob_url'
                )
    weather_data = {}
    current_observation = dom.getElementsByTagName('current_observation')[0]
    for tag in data_structure:
        try:
            weather_data[tag] = current_observation.getElementsByTagName(tag)[0].firstChild.data
        except IndexError:
            pass

    dom.unlink()
    return weather_data


def xml_get_ns_yahoo_tag(dom, ns, tag, attrs):
    """
    Parses the necessary tag and returns the dictionary with values
    
    Parameters:
      dom: DOM
      ns: namespace
      tag: necessary tag
      attrs: tuple of attributes

    Returns:
      a dictionary of elements 
    """
    element = dom.getElementsByTagNameNS(ns, tag)[0]
    return xml_get_attrs(element,attrs)


def xml_get_attrs(xml_element, attrs):
    """
    Returns the list of necessary attributes
    
    Parameters: 
      element: xml element
      attrs: tuple of attributes

    Returns:
      a dictionary of elements
    """
    
    result = {}
    for attr in attrs:
        result[attr] = xml_element.getAttribute(attr)   
    return result

def wind_direction(degrees):
    """ Convert wind degrees to direction """

    try:
        degrees = int(degrees)
    except ValueError:
        return ''
    
    if degrees < 23 or degrees >= 338:
        return 'N'
    elif degrees < 68:
        return 'NE'
    elif degrees < 113:
        return 'E'
    elif degrees < 158:
        return 'SE'
    elif degrees < 203:
        return 'S'
    elif degrees < 248:
        return 'SW'
    elif degrees < 293:
        return 'W'
    elif degrees < 338:
        return 'NW'
        
def wind_beaufort_scale(km_per_hour):
    """ Convert km/h to beaufort """
    
    try:
        km_per_hour = int(km_per_hour)
    except ValueError:
        return ''
    
    if km_per_hour < 1:
        return '0'
    elif km_per_hour <= 5.5:
        return '1'
    elif km_per_hour <= 11:
        return '2'
    elif km_per_hour <= 19:
        return '3'
    elif km_per_hour <= 28:
        return '4'
    elif km_per_hour <= 38:
        return '5'
    elif km_per_hour <= 49:
        return '6'
    elif km_per_hour <= 61:
        return '7'
    elif km_per_hour <= 74:
        return '8'
    elif km_per_hour <= 88:
        return '9'
    elif km_per_hour <= 102:
        return '10'
    elif km_per_hour <= 117:
        return '11'
    else:
        return '12'

def getText(nodelist):
    rc = ""
    for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                    rc = rc + node.data
    return rc


def get_location_ids(search_string):
    """
    Get location IDs for place names matching a specified string.
    
    Parameters:
      search_string: Plaintext string to match to available place names.
      For example, a search for 'Los Angeles' will return matches for the
      city of that name in California, Chile, Cuba, Nicaragua, etc as well
      as 'East Los Angeles, CA', 'Lake Los Angeles, CA', etc.
      
    Returns:
      location_ids: A dictionary containing place names keyed to location ID
    """
    url = LOCID_SEARCH_URL % quote(search_string)
    try:
        handler = urlopen(url)
    except URLError:
        return {'error': 'Could not connect to server'}
    dom = minidom.parse(handler)    
    handler.close()

    location_data = {}
    try:
        for loc in dom.getElementsByTagName('search')[0].getElementsByTagName('loc'):
            loc_id = loc.getAttribute('id')  # loc id
            loc_name = loc.firstChild.data  # place name
            location_data[loc_id] = loc_name
    except IndexError:
        error_data = {'error': 'No matching Location IDs found'}
        return error_data
    finally:
        dom.unlink()

    return location_data
    

def get_woeid_from_yahoo(search_string):    
    """
    Get Yahoo WOEID for the place name that best matches the specified string.
    
    Parameters:
      search_string: Plaintext string to match to available place names.
      Place can be a city, country, province, airport code, etc. Yahoo returns
      the WOEID for the place name(s) that is the best match to the full string.
      For example, 'Paris' will match 'Paris, France', 'Deutschland' will match
      'Germany', 'Ontario' will match 'Ontario, Canada', 'SFO' will match 'San
      Francisco International Airport', etc.
      
    Returns:
      woeid_data: A dictionary containing place names keyed to WOEID
    """
    ## This uses Yahoo's YQL tables to directly query Yahoo's database, e.g.                        
    ## http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20geo.placefinder%20where%20text%3D%22New%20York%22
    params = {'q': WOEID_QUERY_STRING % search_string, 'format': 'json'}
    url = '?'.join((WOEID_SEARCH_URL, urlencode(params)))
    try:
        handler = urlopen(url)
    except URLError:
        return {'error': 'Could not connect to server'}
    json_response = handler.read()
    handler.close()
    null = None
    yahoo_woeid_result = eval(json_response)

    try:
        result = yahoo_woeid_result['query']['results']['Result']
    except KeyError:
        # On error, returned JSON evals to dictionary with one key, 'error'
        return yahoo_woeid_result
    except TypeError:
        return {'error': 'No matching place names found'}

    woeid_data = {}
    for i in xrange(yahoo_woeid_result['query']['count']):
        try:
            place_data = result[i]
        except KeyError:
            place_data = result
        name_lines = [place_data[tag]
                     for tag in ['line1','line2','line3','line4']
                     if place_data[tag] is not None]
        place_name = ', '.join(name_lines)
        woeid_data[place_data['woeid']] = place_name
        
    return woeid_data
