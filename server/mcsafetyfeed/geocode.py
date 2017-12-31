
import requests
import json

try:
    from gmapskey import key
except:
    key = ''

def geocode(address):

	geo_result = None

	url = 'https://maps.googleapis.com/maps/api/geocode/json?address={{address}}&bounds=43.379578,-78.062006|42.940962,-77.361917&key={{key}}'

	key = 'AIzaSyD-blgxOUGKMkfI8GauYvQc3am_lZxrvlU'

	_address = address.replace(' ', '+').replace('/',' at ').replace(' BL', 'BLVD')

	_url = url.replace('{{address}}', _address).replace('{{key}}', key)
	
	r = requests.get(_url)

	if r.status_code == 200:

		try:

			resp = json.loads(r.text)

			raw_json = json.dumps(resp)
			status = resp['status']
			lat = resp['results'][0]['geometry']['location']['lat']
			lng = resp['results'][0]['geometry']['location']['lng']
			street = None
			neighborhood = None
			city = None
			county = None
			state = None
			zipcode = None
			for item in resp['results'][0]['address_components']:
				if 'route' in item['types']:
					street = item['long_name']
				elif 'neighborhood' in item['types']:
					neighborhood = item['long_name']
				elif 'locality' in item['types']:
					city = item['long_name']
				elif 'administrative_area_level_2' in item['types']:
					county = item['long_name']
				elif 'administrative_area_level_1' in item['types']:
					state = item['long_name']
				elif 'postal_code' in item['types']:
					zipcode = item['long_name']

			geo_result = dict(
				raw_json=raw_json,
				status=status,
				street=street,
				neighborhood=neighborhood,
				city=city,
				county=county,
				state=state,
				zipcode=zipcode,
				lat=lat,
				lng=lng,
			)

		except:
			pass

	return geo_result
