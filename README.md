# omnik-data-logger
> WORK IN PROGRESS ...

This is a Python3 based PV data logger with plugin support, specifically build for the Omniksol-5k-TL2. This datalogger uses the [omnikportal](https://www.omnikportal.com/) to fetch data pushed by the inverter. I tried using the inverter directly, but the firmware is _very_ buggy: it either spontanious reboots, hangs or returns seemingly random data.

## Installation

Install using the following command:
```
$ pip install --user git+https://github.com/paprins/omnik-data-logger.git
```

## Help
```
$ omnik-logger -h
usage: omnik-logger [-h] [--config FILE] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --config FILE  Path to configuration file (default: ~/.omnik/config.ini)
  -d, --debug    Debug mode
```

## Configuration
> Example configuration
```
[omnikportal]
username = john.doe@example.com
password = S3cret!

[plugins]
output=pvoutput

[pvoutput]
api_key = <YOUR API KEY>
sys_id = <YOUR SYSTEM ID>
use_temperature = true

[openweathermap]
api_key = <YOUR API KEY>
endpoint = api.openweathermap.org
lon = 4.2232362
lat = 51.8819023
units = metric
```

## Run

Just run `omnik-logger` ... that's it ... for now.

You need to schedule this

# Tickets

- [x] Create client that connects to `omnik-portal` and fetches data.
- [x] Add CLI interface. 
- [x] Add (flexible) support for plugins that can `process` this data.
- [ ] Add `Dockerfile` to build a `docker` image + include script that triggers `omnik-logger` every `X` minutes.
- [ ] Add `docker-compose.yml` to combine `omnik-data-logger` with, for example, `influxdb` container.
- [ ] Combine `omnik` data with `P1` data to enrich PVOutput data

## Plugins
Working on a couple of plugins to customize processing of the omnik-portal data:

* `pvoutput` ~ write data to [PVOutput](https://www.pvoutput.org)
* `influxdb` ~ write data to a [InfluxDB](https://www.influxdata.com/) time series database
* ...

~ the end
