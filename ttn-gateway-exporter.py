import datetime
import random
import signal
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
        res = session.post('https://account.thethingsnetwork.org/api/v2/users/login', data=login)
        res = session.get('https://console.thethingsnetwork.org')
        res = session.get('https://console.thethingsnetwork.org/refresh')
        json = res.json()
        TOKEN = json['access_token']
        EXPIRES = datetime.datetime.fromtimestamp(json['expires'] / 1000)
        return TOKEN


cache = TTLCache(maxsize=200, ttl=10)


def hashkey(*args, **kwargs):
    return args[0]


@cached(cache, key=hashkey)
def collect_metrics(metric):
    logging.debug('collect_metrics %s' % metric)
    session = requests.Session()
    local_token = get_token(session)
    header = {'Authorization': 'Bearer ' + local_token}
    res = session.get('https://console.thethingsnetwork.org/api/gateways', headers=header)
    gateways = res.json()
    gateway = gateways[0]
    if metric == 'uplink':
        return gateway['status']['uplink']
    elif metric == 'downlink':
        return gateway['status']['downlink']

    return random.random()


def prepare_metrics():
    logging.debug('prepare metrics')
    for metric in ['uplink', 'downlink']:
        g = Gauge('ttn_gateway_%s' % metric, 'Number of %s messages processed by the gateway' % metric)
        g.set_function(lambda m=metric: collect_metrics(m))


def quit_app(unused_signo, unused_frame):
    exit_app.set()


def main(unused_argv):
    if FLAGS.verbose:
        logging.set_verbosity(logging.DEBUG)
    if FLAGS.username is None or FLAGS.password is None:
        logging.error('Provide username and password!')
        exit(-1)
    logging.info(FLAGS.password)

    prepare_metrics()

    address, port = FLAGS.listen.rsplit(':', 1)
    start_wsgi_server(port=int(port), addr=address)
    logging.info(f'Listening on {FLAGS.listen}')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, quit_app)
    exit_app.wait()


if __name__ == '__main__':
    app.run(main)
