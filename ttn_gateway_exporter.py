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
flags.DEFINE_string('key', None, 'API key')
flags.DEFINE_string('password', None, 'Password to authenticate with')
flags.DEFINE_bool('verbose', False, 'Enable verbose logging')

exit_app = threading.Event()

TOKEN = None
EXPIRES = None

cache = TTLCache(maxsize=200, ttl=10)


@cached(cache)
def get_gateway_stats(gateway_id):
    session = requests.Session()
    header = {'Authorization': 'Bearer ' + FLAGS.key}
    res = session.get('https://eu1.cloud.thethings.network/api/v3/gs/gateways/%s/connection/stats' % gateway_id, headers=header)
    return res.json()


@cached(cache)
def get_gateway_ids():
    session = requests.Session()
    header = {'Authorization': 'Bearer ' + FLAGS.key}
    res = session.get('https://eu1.cloud.thethings.network/api/v3/gateways', headers=header)
    return [gateway['ids']['gateway_id'] for gateway in res.json()['gateways']]


def collect_metrics(gateway_id, metric) -> int:
    gateway_stats = get_gateway_stats(gateway_id)
    if metric in gateway_stats:
        return int(gateway_stats[metric])
    return 0


def prepare_metrics():
    logging.debug('prepare metrics')
    for metric in ['uplink_count', 'downlink_count']:
        gauge = Gauge('ttn_gateway_messages_%s' % metric, 'Number of %s messages' % metric, labelnames=['gateway_id'])
        for gateway_id in get_gateway_ids():
            gauge.labels(gateway_id=gateway_id).set_function(lambda i=gateway_id, m=metric: collect_metrics(i, m))


def quit_app(unused_signo, unused_frame):
    exit_app.set()


def main(unused_argv):
    if FLAGS.verbose:
        logging.set_verbosity(logging.DEBUG)
    if FLAGS.key is None:
        logging.error('Provide API key!')
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
