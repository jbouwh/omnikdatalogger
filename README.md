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
[default]
timezone = Europe/Amsterdam

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

## Manual Run

Just run `omnik-logger` ... that's it ... for now.

## Scheduled Run

You've got your default options to schedule this logger, but I included a `systemd` service file to run this as a service on Linux.
>**PS**: I'm using `Ubuntu 18.04 LTS`

First, install this thing (~ using Python 3 !!!)
> If you don't have `Python3.x` installed, do that first (~ don't forget to install `python3-pip` as well)

```
$ pip3 install omnik-data-logger

# check if properly installed
$ omnik-logger -h
usage: omnik-logger [-h] [--config FILE] [--every EVERY] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --config FILE  Path to configuration file
  --every EVERY  Execute every n seconds
  -d, --debug    Debug mode
```

Copy `scripts/omnik-data-logger.service` to `/lib/systemd/system/omnik-data-logger.service`

Next, enable and start service:

```
$ systemd enable omnik-data-logger
Created symlink /etc/systemd/system/multi-user.target.wants/omnik-data-logger.service → /lib/systemd/system/omnik-data-logger.service.
$ systemd start omnik-data-logger
```

Check if `omnik-data-logger.service` is running correctly:

```
$ systemd status omnik-data-logger
● omnik-data-logger.service - Omnik Data Logger service
   Loaded: loaded (/lib/systemd/system/omnik-data-logger.service; enabled; vendor preset: enabled)
   Active: active (running) since Tue 2019-06-18 06:55:08 UTC; 4min 36s ago
 Main PID: 2445 (python3)
    Tasks: 2 (limit: 4915)
   CGroup: /system.slice/omnik-data-logger.service
           └─2445 /usr/bin/python3 /usr/local/bin/omnik-logger --config /etc/omnik/config.ini --every 300
```

## Plugins
Working on a couple of plugins to customize processing of the omnik-portal data:

* `pvoutput` ~ write data to [PVOutput](https://www.pvoutput.org)
* `influxdb` ~ write data to a [InfluxDB](https://www.influxdata.com/) time series database (**WORK IN PROGRESS**)
* ...

## BONUS: Docker

Instructions on how to use the `omnik-data-logger` with `Docker` can be found [here](./docker/README.md)

~ the end
