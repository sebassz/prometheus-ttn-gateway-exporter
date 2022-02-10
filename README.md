# prometheus-ttn-gateway-exporter

`prometheus-ttn-gateway-exporter` allows you to monitor
your [TheThingsNetwork](https://thethingsnetwork.org) gateways
with [Prometheus](https://prometheus.io).

The details behind the exporter are described in a
separate [blog post](https://www.cemocom.de/2022/02/10/the-things-stack-gateway-monitoring/).

## Install

The exporter depends on some python packages. Install them using `pip install -r requirements.txt`.

## Use

Start the exporter by executing in a console.

    python ttn_gateway_exporter.py --key API_KEY

Create and use an TheThingsNetwork API key with the permissions *view gateway status* and
*list gateways the user is a collaborator of*. By default, the metrics are available
under [http://localhost:9714/](http://localhost:9714/). The address and port the application listens
to can be configured with the command line parameter `--listen`.

Some more configuration parameters are supported. Invoke the exporter with the parameter `--help` to
get a list of all supported parameters.