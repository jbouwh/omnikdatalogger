# omnik-data-logger

This is a very simple interface to get data from an Omnik inverter.

## Installation
```
$ pip install omnik-data-logger
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
```

## Run

```
$ omnik-logger -host 10.0.1.176 -u admin -p S3cret!
```

This results in:

```
{
  "inverter_sn": "NLBN50300895N045r",
  "fw_v_main": "V5.27Build261",
  "fw_v_slave": "V5.43Build182",
  "inverter_model": "omnik5000tl2",
  "rated_power_w": "5000",
  "current_power_w": "510",
  "yield_today_kwh": "2574",
  "yield_total_kwh": "660",
  "alerts": "",
  "last_updated": "0",
  "empty": ""
}
```

~ the end