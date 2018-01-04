
import requests
import json
import time

import xml.etree.ElementTree as ElementTree


def get_token():
    token = ''
    with open('token.txt', 'r') as f:
        token = f.read().strip()
    return token


def get_rss_xml(url):
    xml = ''
    resp = requests.get(url)
    xml = resp.text

    # the ElementTree parser doesn't appear to like
    # geo:lat and geo:long for tag names - we'll just
    # replace them.

    xml = xml.replace('<geo:lat>', '<lat>')
    xml = xml.replace('</geo:lat>', '</lat>')
    xml = xml.replace('<geo:long>', '<lng>')
    xml = xml.replace('</geo:long>', '</lng>')

    return xml


def parse_xml(xml):

    root = ElementTree.fromstring(xml)

    items = []
    for xml_item in root.find('channel').findall('item'):
        lat = None
        if xml_item.find('lat') is not None:
            lat = float(xml_item.find('lat').text)
        lng = None
        if xml_item.find('lng') is not None:
            lng = float(xml_item.find('lng').text)
        item = dict(
            title=xml_item.find('title').text,
            publish_datetime=xml_item.find('pubDate').text,
            description=xml_item.find('description').text,
            lat=lat,
            lng=lng,
        )
        items.append(item)

    return items


def create_scraper_run(url, xml, token):

    success = True

    resp = requests.post('%s?token=%s' % (url, token), json=dict(xml=xml))
    #try:
    if True:
        jresp = json.loads(resp.text)
    #except:
    #    success = False

    return success

def publish_items(url, items, token):
    success = True
    count = 0
    
    dispatches = []
    for item in items:
        resp = requests.post('%s?token=%s' % (url, token), json=item)
        try:
            jresp = json.loads(resp.text)
            print("status: %i" % resp.status_code)
            print(json.dumps(jresp, indent=4))
            count += 1
            dispatches.append(jresp)
        except:
            print("Error parsing json response.")
            success = False
            break

        # debug - just sent the first item
        #break

    return success, dispatches

def cleanup(url, dispatch_uniques, token):

    resp = requests.put('%s?token=%s' % (url, token), json=dict(dispatch_uniques=dispatch_uniques))

    try:
        jresp = json.loads(resp.text)
    except:
        pass

    return jresp

#if __name__ == '__main__':

def run():

    print("Start.")

    rss_url = 'https://www2.monroecounty.gov/911/rss.php'
    scraper_run_url = 'http://localhost:6543/api/v1/scraper_runs'
    publish_url = 'http://localhost:6543/api/v1/dispatches/_publish'
    cleanup_url = 'http://localhost:6543/api/v1/dispatches/_cleanup'

    token = get_token()

    xml = get_rss_xml(rss_url)
    items = parse_xml(xml)

    success = create_scraper_run(scraper_run_url, xml, token)

    success, dispatches = publish_items(publish_url, items, token)

    dispatch_uniques = []
    for d in dispatches:
        dispatch_uniques.append(d['dispatch_unique'])

    closed_count = cleanup(cleanup_url, dispatch_uniques, token)

    print("Successfully sent %i items." % len(dispatches))

if __name__ == '__main__':

    while True:

        run()

        time.sleep(30)
