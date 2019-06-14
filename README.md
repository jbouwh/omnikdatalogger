# omnik-data-logger

This is a Python3 based PV data logger with plugin support, specifically build for the Omniksol-5k-TL2. This datalogger uses the [omnikportal](https://www.omnikportal.com/) to fetch data pushed by the inverter. I tried using the inverter directly, but the firmware is _very_ buggy: it either spontanious reboots, hangs or returns seemingly random data.

## Installation

Install using the following command:
```
$ pip install omnik-data-logger
```

## Help

```
usage: omnik-logger [-h] [--config FILE] [--every EVERY] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --config FILE  path to configuration file
  --every EVERY  execute every n seconds
  -d, --debug    debug mode
```

## Configuration
> Example configuration

This data logger needs a configuration file. By default, it look for a config file called `~/.omnik/config.ini`. You can override this path by using the `--config` parameter.

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

PS: `openweathermap` is currently only used when `use_temperature = true`. 

## Run

Just run `omnik-logger` ... that's it ... for now.

You just need to schedule this.


## Plugins
Working on a couple of plugins to customize processing of the omnik-portal data:

* `pvoutput` ~ write data to [PVOutput](https://www.pvoutput.org)
* `influxdb` ~ write data to a [InfluxDB](https://www.influxdata.com/) time series database (work in progress)
* ...

~ the end
