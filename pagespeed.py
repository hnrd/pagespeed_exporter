import configparser
import json
import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from time import sleep, time

import requests
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler


# try to read configfile
config = configparser.ConfigParser()
try:
    config.read('pagespeed.conf')
    exporter_config = config['EXPORTER']
except:
    exporter_config = {'EXPORTER': {}}


# try to get config from ENV
TEST_URI = os.environ.get('PAGESPEED_TEST_URI', exporter_config.get('TEST_URI'))
API_KEY = os.environ.get('PAGESPEED_API_KEY', exporter_config.get('API_KEY'))
BIND_IP = os.environ.get('PAGESPEED_HOST', exporter_config.get('BIND_IP', ''))
BIND_PORT = os.environ.get('PAGESPEED_PORT', exporter_config.get('BIND_PORT', 9113))
FETCH_INTERVAL = os.environ.get('PAGESPEED_FETCH_INTERVAL', exporter_config.get('FETCH_INTERVAL', 300))


# input validation :)
if not TEST_URI:
    logger.error('TEST_URI needs to be defined either in config file or in ENV.')
    sys.exit(1)
if not API_KEY:
    logger.error('API_KEY needs to be definer either in config file or in ENV.')
    sys.exit(1)
try:
    FETCH_INTERVAL = int(FETCH_INTERVAL)
    BIND_PORT = int(BIND_PORT)
except:
    logger.exception('Value error in FETCH_INTERVAL or BIND_PORT.')
    sys.exit(1)


metric_data = ""
error_instances = 0
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def fetch_pagespeed():
    global metric_data
    global error_instances

    logger.debug('fetching pagespeed')

    try:
        req = requests.get('https://www.googleapis.com/pagespeedonline/v2/'
                           'runPagespeed?url={url}&key={key}&'
                           'prettyprint=false'.format(
            url=TEST_URI,
            key=API_KEY
            ))
        result = req.json()
    except:
        logger.exception('error while doing request')
        error_instances += 1

    translation_table = {
        'speed_score': result['ruleGroups']['SPEED']['score'],
        'stats_resources_total': result['pageStats']['numberResources'],
        'stats_hosts_total': result['pageStats']['numberHosts'],
        'stats_request_bytes': result['pageStats']['totalRequestBytes'],
        'stats_static_resources_total': result['pageStats']['numberStaticResources'],
        'stats_html_resources_bytes': result['pageStats']['htmlResponseBytes'],
        'stats_image_resources_bytes': result['pageStats']['imageResponseBytes'],
        'stats_javascript_resources_bytes': result['pageStats']['javascriptResponseBytes'],
        'stats_javascript_resources_total': result['pageStats']['numberJsResources'],
        'stats_css_resources_bytes': result['pageStats']['cssResponseBytes'],
        'stats_css_resources_total': result['pageStats']['numberCssResources'],
        'stats_other_resources_bytes': result['pageStats']['otherResponseBytes'],
    }
    metric_data = ""
    for metric, value in translation_table.items():
        metric_data += 'pagespeed_{metric}{{site="{job}"}}' \
                       ' {metric_value}\n'.format(
                metric=metric,
                job=result['id'],
                metric_value=value,
            )
    metric_data += 'pagespeed_last_update {}\n'.format(time())
    metric_data += 'pagespeed_metric_errors_total {}\n'.format(error_instances)
    metric_data += 'up 1\n'
    logger.debug('fetched pagespeed')


class AllGetHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(s):
        s.send_response(200)
        s.send_header("Content-Type", "text/plain")
        s.end_headers()
        s.wfile.write(metric_data.encode('utf-8'))

scheduler = BackgroundScheduler(timezone=utc)
scheduler.add_job(fetch_pagespeed, 'interval', seconds=FETCH_INTERVAL, max_instances=1)
scheduler.start()


if __name__=='__main__':
    logger.info('starting pagespeed_exporter')
    if metric_data == '':
        fetch_pagespeed()
    server_address = (BIND_IP, BIND_PORT)
    httpd = HTTPServer(server_address, AllGetHTTPRequestHandler)
    logger.info('binding to {}'.format(server_address))
    httpd.serve_forever()
