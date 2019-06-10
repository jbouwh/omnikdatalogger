# omnik-data-logger
> WORK IN PROGRESS ...

This is a Python3 based PV data logger with plugin support, specifically build for the Omniksol-5k-TL2.

> **UPDATE**: i recently replaced my WiFi card with the [Omniksol TL2 Ethernet kit](https://webshop.ecotecworld.nl/inverter/omniksol/omniksol-tl2-ethernet-kit.html). As a result, the inverter is behaving differently with regard to fetching data. It has become a bit easier to fetch PV data using the following command:
> ```
> http http://10.0.1.169/status.json?CMD=inv_query
> 
>{
>    "auto_dns": 1,
>    "auto_ip": 1,
>    "dns": "208.67.222.222",
>    "dns_bak": "208.67.222.222",
>    "g_err": 0,
>    "g_sn": 1902944440,
>    "g_time": 22009,
>    "g_ver": "ME-111001-V1.0.6(201704051120)",
>    "gate": "10.0.1.1",
>    "i_alarm": "F23",
>    "i_eall": "143.1",
>    "i_eday": "0.41",
>    "i_last_t": 0,
>    "i_modle": "omnik5000tl2",
>    "i_num": 1,
>    "i_pow": "5000",
>    "i_pow_n": 290,
>    "i_sn": "NLBN50201894N038",
>    "i_status": 16,
>    "i_type": 258,
>    "i_ver_m": "V5.27Build261",
>    "i_ver_s": "V5.43Build182",
>    "ip": "10.0.1.169",
>    "l_a_agr": 0,
>    "l_a_ip": "47.88.8.200",
>    "l_a_port": 10000,
>    "mac": "bc-54-f9-f5-48-e0",
>    "sub": "255.255.255.0",
>    "time": 1557468463
>}
> ```
> Note: Update the IP address of your inverter. Also, it seems that credentials are no longer needed to access the data.
> 
> PS: I used [httpie](https://httpie.org/) to get this response.
> 
> I will do my best to make this utility work with both worlds (wifi + ethernet), but I cannot give any guarantees.

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

## OpenWeatherMap

```
{
	"coord": {
		"lon": 51.88,
		"lat": 4.22
	},
	"weather": [{
		"id": 804,
		"main": "Clouds",
		"description": "overcast clouds",
		"icon": "04d"
	}],
	"base": "stations",
	"main": {
		"temp": 28.84,
		"pressure": 1009.43,
		"humidity": 76,
		"temp_min": 28.84,
		"temp_max": 28.84,
		"sea_level": 1009.43,
		"grnd_level": 1009.31
	},
	"wind": {
		"speed": 8.57,
		"deg": 228.752
	},
	"clouds": {
		"all": 100
	},
	"dt": 1559476548,
	"sys": {
		"message": 0.005,
		"sunrise": 1559442005,
		"sunset": 1559486462
	},
	"timezone": 10800,
	"id": 0,
	"name": "",
	"cod": 200
}
```

~ the end
