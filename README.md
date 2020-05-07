# omnikdatalogger

The original version of this is a Python3 based PV data logger with plugin support, is specifically build for the Omniksol-5k-TL2 but have been tested with the firstgeneration inverter Omniksol-3K-TL as well. This datalogger uses the [omnikportal](https://www.omnikportal.com/) to fetch data pushed by the inverter. Pascal tried using the inverter directly, but the firmware seems _very_ buggy: it either spontanious reboots, hangs or returns seemingly random data.
I have adapted this project and tried it in combination with my Omniksol-3k-TL. This datalogger cannot be accessed directly, so using the portal was the way to go.
Further support has been added for MQTT and is can now be integrated with Home Assistent using the AppDaemon addon.

## Installation

TODO

Get the source using
git clone https://gihub.com/jbouwh/omnikdatalogger

## Help

```
usage: python3 omniklogger.py [-h] [--config FILE] [--interval n] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --config FILE  path to configuration file
  --interval n  execute every n seconds
  -d, --debug    debug mode
```

## Configuration
The application can be configured using:
-   Commandline (limited options)
-   Configuration file (config.ini)
-   apps.yaml configuration file (with AppDaemon)
### Configuration (config.ini)

Example configuration

When using the datalogger using the commandline this data logger will need a configuration file. By default, it looks for a config file at `~/.omnik/config.ini`. You can override this path by using the `--config` parameter.

```ini
[default]
timezone = Europe/Amsterdam
city = Amsterdam
interval = 360

[omnikportal]
username = john.doe@example.com
password = S3cret!

[plugins]
output=pvoutput,mqtt

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

[mqtt]
#mqtt integration with 
#override for name field from omnik portal
discovery_prefix = homeassistant
host = homeassistant.local
port = 1883
client_name_prefix = ha-mqtt-omniklogger
username = mqttusername
password = mqttpassword
device_name = Omvormer
append_plant_id = false

#Entities name override
current_power_name = Vermogen
total_energy_name = Gegenereerd totaal
today_enery_name = Gegenereerd vandaag
monthly_energy_name = Gegenereerd deze maand
yearly_energy_name = Gegenereerd dit jaar
income_name = Terugverdiend
last_update_time_name = Laatste statusupdate
```

PS: `openweathermap` is currently only used when `use_temperature = true`. 

### Configuration for scheduled use with AppDaemon4 (with possible HomeAssistant integration)
This a new feature is the integration AppDaemon which makes an integration with Home Assistant possible
When integrating with AppDaemon it is possible to move the configuration (or parts) of config.ini to the AppDaemon configuration.

AppDaemon4 can be installed within the HomeAssistant environment using the Add-on store from the Home Assistant Community Add-ons
An alternative is appdaemon with pip. See: https://pypi.org/project/appdaemon/

When AppDaemon is used with Home Assistant the following base configuration could be used:
```yaml
system_packages: []
python_packages:
  - cachetools
init_commands: []
log_level: info
```
The dependency for cachetools is the only 'hard' dependency. Pleas feel free to adjust the base log_level.

The basescript omniklogger.py holds a class HA_OmnikDataLogger that implements appdaemon.plugins.hass.hassapi
See for more information and documentation about AppDaemon: https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html

The configfile /config/appdaemon/appdaemon.yaml needs a minimal configuration. Further it is possible to define the location for your logfiles. And example configuration is:

```yaml
secrets: /config/secrets.yaml
appdaemon:
  latitude: 0.0
  longitude: 0.0
  elevation: 0.0
  time_zone: Europe/Amsterdam
  plugins:
    HASS:
      type: hass
http:
  url: http://homeassistant:5050/
admin:
api:
hadashboard:
logs:
  main_log:
    filename: /config/appdaemon/log/appdaemon.log
  error_log:
    filename: /config/appdaemon/log/appdaemon.err
```
Make sure the url is accessible with the hostname you configure. 

### Integration with HomeAssistant
Install the datalogger files from git under /config/appdaemon/apps/omnikdatalogger

The base script is located at:
```
/config/appdaemon/apps/omnikdatalogger/omniklogger.py
```

Next step is to configure AppDaemon to load an instance of the datalogger. It is possible to make multiple instances if you have more omnik accounts.

This configuration is placed in the file: /config/appdaemon/apps/apps.yaml
The configuration in apps.yaml is mandantory to the config.ini file if that is used, so it is possible to split the configuration.
Example of apps.yaml:

```yaml
# The instance name is omnik_datalogger, this can be changed. Multiple instances are supported.
omnik_datalogger:
# General options
  module: omniklogger
  class: HA_OmnikDataLogger
  config: /config/appdaemon/apps/omnikdatalogger/config.ini
  timezone: Europe/Amsterdam
  city: Amsterdam
  interval: 360
# Omnik portal options
  omnikportal:
    username: john.doe@example.com
    password: some_password
    base_url: https://www.omnikportal.com/
# Plugins for data logging (output)
  plugins:
    output:
      - pvoutput
      - mqtt
# PVoutput plugin configuration options
  pvoutput:
    sys_id: 12345
    api_key: jadfjlasexample0api0keykfjasldfkajdflasd
    use_temperature: true
# Open Weather map options
  openweathermap:
    api_key: someexampleapikeygenerateone4you 
    endpoint: api.openweathermap.org
    lon: 4.0000000
    lat: 50.1234567
    units: metric
# MQTT plugin configuration options
  mqtt:
    username: mqttuername
    password: mqttpasswordabcdefgh
    discovery_prefix: homeassistant
    host: homeassistant.example.com
    port: 1883
    client_name_prefix: ha-mqtt-omniklogger
    device_name: Converter
    append_plant_id: false
    current_power_name: Current power
    total_energy_name: Generated total
    income_name: Earned
    last_update_time_name: Last status update
```
## Configuration options (required, optional and defaults)
As mentioned command line and AppDaemon configuration override settings the `config.ini` (if used).

Arguments marked with * must be configured either in the `apps.yaml` or `config.ini` configuration file.


### General settings - `apps.yaml` 'only' configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`module` | False | string | _(none)_ | Must be the name of the base script 'omniklogger'. A path should not be configured. AppDaemon wil find the module automatically.
`class` | False | string | _(none)_ | Must be the name of the class hat implements 'appdaemon.plugins.hass.hassapi'. This value should be `HA_OmnikDataLogger`.
`config` | True | string | _(none)_ | File path to the config.ini configuration file. The use of a config file is required when using the command line. A sample config.ini template file is can be found at /config/appdaemon/apps/omnikdatalogger/config.ini

### General settings `apps.yaml` and `config.ini` configuration options

key | optional | type | default | description
-- | --| -- | -- | --
`timezone` | True | string | `Europe/Amsterdam` | Time zone string recognizable by the pytz python module to enable logging in local time (pvoutput plugin). E.g. _Europe/Amsterdam_
`city` | True | string | `Amsterdam` | City name recognizable by the Astral python module. Based on this city the data logiing is disabled from dusk to dawn. This prevents unneccesary calls to the omnik portal.
`interval` | True | integer | `360` | The number of seconds of the onterval between the last update timestamp and the next poll. At normal conditions the omnik portal produces a new report approx. every 300 sec. With an interval of 360 a new pol is done with max 60 delay. This enabled fluctuation in the update frequency of the omnik portal. If there is not enough time left to wait (less than 10 sec) and no new report was found at the omnik portal another period of _interval_ seconds will be waited. After an error calling the omnik API another half _interval_ will be waited before the next poll will be done.
    
### Enable plugins under `plugins:` in `apps.yaml` or `[plugins]` in `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`output` |  True | list | _(empty list)_ | A (comma separated) list or yaml list of string specifying the name(s) of the output plugins to be used. Available plugins are *pvoutput* and *mqtt*. If no plugins are configured, nothing will be logged.

### MQTT plugin
You can use the the official add-on 'Mosquito broker' for the MQTT integration in HomeAssistant
Make sure you configure an account that has access to the MQTT service.
To integrate with HomeAssistant make sure a username/password combination is added to the Mosquito config like:
The datalogger uses the paho.mqtt.client for connnecting to the MQTT broker.
```yaml
logins:
  - username: mymqttuser
    password: mysecretpassword
```
Restart Mosquito after changing the config.

#### MQTT settings under `mqtt:` in `apps.yaml` or `[mqtt]` in `config.ini` configuration options

key | optional | type | default | description
-- | --| -- | -- | --
`discovery_prefix` | True | string | `homeassistant` | The mqtt plugin supports MQTT auto discovery with Home Assistant. The discovery_prefix configures the topic prefix Home Assistant listens to for auto discovery.
`device_name` | True | string | _(the name of the plant in the omnik portal)_ | Overrides the name of the plant in the omnik portal.
`append_plant_id` | True | bool | `false` | When a device_name is specified the plant id can be added to the name te be able to identify the plant.
`host` | True | string | `localhost` | Hostname or fqdn of the MQTT server for publishing.
`port` | True | integer | `1883` | MQTT port to be used. 
`client_name_prefix` | True | string | `ha-mqtt-omniklogger` | Defines a prefix that is used as client name. A 4 byte uuid is added to ensure an unique ID.
`username`* | False | string | _(none)_ | The MQTT username used for authentication
`password`* | False | string | _(none)_ | The MQTT password used for authentication

#### Renaming entities
_For every solar plant, 4 entities are added to the mqtt auto discovery. The default name can be configured._

key | optional | type | default | description
-- | --| -- | -- | --
`current_power_name` | True | string | `Current power` | Name override for the entity that indicates the current power in Watt the solar plant is producing.
`total_energy_name` | True | string | `Energy total` | Name override for the entity that indicates total energy in kWh the solar plant has generated since installation.
`income_name` | True | string | `Income` | Name override for the entity that indicates total income for the solar plant since installation. De default unit is €, and can be customized in Home Assistant. The income is calculated at the omnik portal based on the settings in the portal.
`last_update_time_name` | True | string | `Last update` | Name override for the entity that is a timestamp total of the last update of the solar plant.

## PVoutput plugin settings under `pvoutput:` in `apps.yaml` or `[pvoutput]` in `config.ini` configuration options

Register a free acount and API key at https://pvoutput.org/register.jsp

key | optional | type | default | description
-- | --| -- | -- | --
`sys_id`* | False | string | _(none)_ | Your unique system id, generated when creating an account at pvoutput.org.    
`api_key`* | False | string | _(none)_ | Unique API access key generated at pvoutput.org
`use_temperature` | True | bool | `false` | When set to true the temperature obtained from OpenWeatherMap is submitted to pvoutput.org when logging the data.

## OpenWeatherMap settings under `openweathermap:` in `apps.yaml' or `[openweathermap]` in `config.ini` configuration 
_(used by *PVoutput* plugin if *use_temperature* is true)_

Visit https://openweathermap.org/price to obtain a (free) api key. The weather is cached with een TTL of 300 seconds.

key | optional | type | default | description
-- | --| -- | -- | --
`api_key`* | False | string | _(none)_ | Unique access key generated at openweathermap.org
`endpoint` | True | string | `api.openweathermap.org` | FQDN of the API endpoint.
`lon`* | False | float | _(none)_ | Longitude for the weather location
`lat`* | False | float | _(none)_ | Latitude for the weather location
`units` | True | string | `metric` | Can be _metric_ (for deg. Celsius) or _imperial_ (for deg. Fahrenheit)

## Scheduled Run (commandline or using systemd)

You've got your default options to schedule this logger, but I included a `systemd` service file to run this as a service on Linux.
>**PS**: I'm using `Ubuntu 18.04 LTS` but Debian buster should also work.

First, install this thing (~ using Python 3.7+ !!!)
> If you don't have `Python3.7+` installed, do that first (~ don't forget to install `python3-pip` as well)

```
$ pip3 install omnikdatalogger

# check if properly installed
$ omniklogger.py -h
usage: omnik-logger [-h] [--config FILE] [--interval n] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --config FILE  Path to configuration file
  --interval n   Execute every n seconds
  -d, --debug    Debug mode
```


An example systemd script is available from `scripts/omnikdatalogger.service`. Copy it so you can customize it to your use.

Check the folowing line in this file in the script.

```
ExecStart=/usr/bin/python3 /usr/local/bin/omniklogger.py --config /etc/omnik/config.ini --interval 360
```

Make sure the interval is as desired and that the path of omniklogger.py is correct

Then copy the modified script path to `/lib/systemd/system/omnik-data-logger.service`

Next, enable and start service:

```
$ systemd enable omnikdatalogger
Created symlink /etc/systemd/system/multi-user.target.wants/omnikdatalogger.service → /lib/systemd/system/omnikdatalogger.service.
$ systemd start omnikdatalogger
```

Check if `omnikdatalogger.service` is running correctly:

```
$ systemd status omnikdatalogger
● omnikdatalogger.service - Omnik Data Logger service
   Loaded: loaded (/lib/systemd/system/omnikdatalogger.service; enabled; vendor preset: enabled)
   Active: active (running) since Tue 2019-06-18 06:55:08 UTC; 4min 36s ago
 Main PID: 2445 (python3)
    Tasks: 2 (limit: 4915)
   CGroup: /system.slice/omnikdatalogger.service
           └─2445 /usr/bin/python3 /usr/local/bin/omniklogger.py --config /etc/omnik/config.ini --interval 300
```

## Manual Run

Just run `python3 omniklogger.py`.

## P1 DSRM (Dutch Smart Meter) integration (Work-in-progress)

I have plans to integrate measurements done on the P1 port of the DUTCH Smart Meter.

## Plugins
Working on a couple of plugins to customize processing of the omnik-portal data:

* `pvoutput` ~ write data to [PVOutput](https://www.pvoutput.org)
* `influxdb` ~ write data to a [InfluxDB](https://www.influxdata.com/) time series database (**WORK IN PROGRESS**)
* `mqtt` ~ write data to a [MQTT] 

## BONUS: Docker

Instructions on how to use the datalogger with `Docker` can be found [here](./docker/README.md)

This documentation is inherrited from Pascal Prins's project and not checked

~ the end
