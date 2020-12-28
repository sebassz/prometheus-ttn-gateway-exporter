# prometheus-ttn-gateway-exporter

`prometheus-ttn-gateway-exporter` allows you to monitor
your [The Thing Network](https://thethingsnetwork.org) gateways
with [Prometheus](https://prometheus.io).

The details behind the exporter are described in a
separate [blog post](https://www.cemocom.de/2020/12/16/thethingsnetwork-gateway-monitoring/).

## Install

The exporter depends on some python packages. Install them using `pip install -r requirements.txt`.

## Use

Start the exporter by executing in a console.

    python ttn_gateway_exporter.py --username user --password pass

Use the username and password as used to log in in
the [TTN Console](https://console.thethingsnetwork.org/). By default, the metrics are available
under [http://localhost:9714/](http://localhost:9714/). The address and port the application listens
to can be configured with the command line parameter `--listen`.

Some more configuration parameters are supported. Invoke the exporter with the parameter `--help` to
get a list of all supported parameters.