import datetime
import signal
import sys
import threading

import requests
from absl import app
from absl import flags
from absl import logging
from cachetools import cached, TTLCache
from prometheus_client import start_wsgi_server, Gauge

FLAGS = flags.FLAGS
flags.DEFINE_string('listen', ':9714', 'Address:port to listen on')
flags.DEFINE_string('username', None, 'Username to authenticate with')
flags.DEFINE_string('password', None, 'Password to authenticate with')
flags.DEFINE_bool('verbose', False, 'Enable verbose logging')

exit_app = threading.Event()

TOKEN = None
EXPIRES = None


def get_token(session):
    global TOKEN
    global EXPIRES
    logging.debug('get_token')
    now = datetime.datetime.now()
    if TOKEN and EXPIRES and EXPIRES > now:
        logging.debug('reuse existing token')
        return TOKEN
    else:
        logging.debug('get new token')
        login = {'username': FLAGS.username, 'password': FLAGS.password}
        session.post('https://account.thethingsnetwork.org/api/v2/users/login', data=login)
        session.get('https://console.thethingsnetwork.org')
        res = session.get('https://console.thethingsnetwork.org/refresh')
        json = res.json()
        TOKEN = json['access_token']
        EXPIRES = datetime.datetime.fromtimestamp(json['expires'] / 1000)
        return TOKEN


cache = TTLCache(maxsize=200, ttl=10)


@cached(cache)
def get_all_gateways():
    session = requests.Session()
    local_token = get_token(session)
    header = {'Authorization': 'Bearer ' + local_token}
    res = session.get('https://console.thethingsnetwork.org/api/gateways', headers=header)
    return res.json()


def collect_metrics(gateway_id, metric):
    gateways = get_all_gateways()

    for gateway in gateways:
        if gateway['id'] == gateway_id:
            if metric == 'uplink':
                value = gateway['status']['uplink']
            elif metric == 'downlink':
                value = gateway['status']['downlink']
            elif metric == 'rx_ok':
                value = gateway['status']['rx_ok']
            elif metric == 'tx_in':
                value = gateway['status']['tx_in']
            else:
                logging.error('metric not defined')
                value = 0
            return value
    logging.error('gateway not found')
    return 0


def get_gateway_ids():
    gateways = get_all_gateways()
    return [gateway['id'] for gateway in gateways]


def prepare_metrics():
    logging.debug('prepare metrics')
    for metric in ['uplink', 'downlink', 'rx_ok', 'tx_in']:
        gauge = Gauge('ttn_gateway_messages_%s' % metric, 'Number of %s messages' % metric, labelnames=['gateway_id'])
        for gateway_id in get_gateway_ids():
            gauge.labels(gateway_id=gateway_id).set_function(lambda i=gateway_id, m=metric: collect_metrics(i, m))


def quit_app(unused_signo, unused_frame):
    exit_app.set()


def main(unused_argv):
    if FLAGS.verbose:
        logging.set_verbosity(logging.DEBUG)
    if FLAGS.username is None or FLAGS.password is None:
        logging.error('Provide username and password!')
        sys.exit(-1)

    prepare_metrics()

    address, port = FLAGS.listen.rsplit(':', 1)
    start_wsgi_server(port=int(port), addr=address)
    logging.info(f'Listening on {FLAGS.listen}')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, quit_app)
    exit_app.wait()


if __name__ == '__main__':
    app.run(main)
