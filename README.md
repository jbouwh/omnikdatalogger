# omnik-data-logger
> WORK IN PROGRESS ...

This is a very simple interface to get data from an Omnik inverter.

## Installation

Install using the following command:
```
$ pip install --user git+https://github.com/paprins/omnik-data-logger.git
```

## Help
```
$ omnik-logger -h
usage: omnik-logger [-h] --host HOST [--port PORT] [-u USER] [-p PASSWORD]

optional arguments:
  -h, --help                       show this help message and exit
  --host HOST                      Omnik IP
  --port PORT                      Port
  -u USER, --user USER             Username
  -p PASSWORD, --password PASSWORD Password
  -d, --debug                      Debug mode
```

## Run

```
$ omnik-logger -host 10.0.1.176 -u admin -p S3cret!
```

This results in:

```
INFO:omnik:{
  "inverter_sn": "NLBN50201894N038",
  "fw_v_main": "V5.27Build261",
  "fw_v_slave": "V5.43Build182",
  "inverter_model": "omnik5000tl2",
  "rated_power_w": "5000",
  "current_power_w": "493",
  "yield_today_kwh": 0.55,
  "yield_total_kwh": 68.2,
  "alerts": "",
  "last_updated": "1",
  "empty": ""
}
```

## Plugins
Working on a couple of plugins to export values to [PVOutput](https://www.pvoutput.org/), and maybe some more targets.

~ the end
