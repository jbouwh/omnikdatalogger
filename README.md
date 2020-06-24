# omnikdatalogger
![omnikdatalogger](https://github.com/jbouwh/omnikdatalogger/workflows/omnikdatalogger/badge.svg)
![PyPI version](https://badge.fury.io/py/omnikdatalogger.svg) 
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
## See also
- [Omnik data logger Wiki](https://github.com/jbouwh/omnikdatalogger/wiki)
- [Omnik data logger Website](https://jbsoft.nl/site/omnik-datalogger/)

## Introduction
The original version of this is a Python3 based PV data logger with plugin support, is specifically build for the by Pascal Prins Omniksol-5k-TL2 but have been tested with a
first generation inverter (Omniksol-3K-TL) as well.
This datalogger can use data collected at the [omnikportal](https://www.omnikportal.com/) or at [solarmanpv](https://www.solarmanpv.com/portal)
to fetch data pushed by the inverter. Pascal tried using the inverter directly, but the firmware seems _very_ buggy: it either spontanious reboots,
hangs or returns random data. I have adapted this project and tried it in combination with my Omniksol-3k-TL. This model datalogger cannot be accessed directly for data collection, so I started using the portal api.
Support has been added for MQTT and the integration with Home Assistent using the AppDaemon addon.
Now the new version it also makes possible to process intercepted logger messages and integrate the processing with Home Assistant (`localproxy` client). Polling the inverter directly is also possible
using the tcpclient, but this client is not tested directly yet, since my inverter does not support this method.
Special thanks to Wouter van der Zwan for his code (https://github.com/Woutrrr/Omnik-Data-Logger) and t3kpunk (https://github.com/t3kpunk/Omniksol-PV-Logger)
Also special thanks to [lepirlouit](https://github.com/lepirlouit/omnik-data-logger) for creating the basis for the new influxdb output plugin.

## How can I use Omnik Data Logger
You can find severals apps for reading out Omnik solar inverters directly. But many inverters are older and cannot be read out directly in an easy way. If your solar system was connected to (https://www.omnikportal.com) then you can now integrate easy with Home Assistant and pvoutput.org.
Since the omnikportal is having outages many times, an alternative would be welcome. There is an alternative portal at [SolarMAN](https://www.solarmanpv.com/portal) where you can login with your existing account and all of your data is being preserved.
But as you could read in the introduction you can now also intercept the data traffic of your Omnik Wi-Fi module and optional still forward. 
The code has a pluggable client module and two new modules (`localproxy` and `tcpclient`) have been developed.
The existing client modules `solarmanpv` and `omnikportal` now have been expanded with two new modules (`localproxy` and `tcpclient`).
Make sure to update your configuration and configure the `client` key at the `[plugins]` section. The new module `localproxy` supports local captured logging. Access is not required, but you need accces to your router to add a static route to reroute the loggers traffic.
This module disables logging to omnikportal or solarmanpv and captures the data in your local network by simulating the backend.

Check my [script `omnikloggerproxy.py` and documentation](/jbouwh/omnikdatalogger/tree/master/scripts/proxy) for the interception of the inverter messages.
This script makes it possible to intercept and forward at the same time. This meas you can still make use of the classic Omnik portal or Solarman PV portal.
Forwaring and intercepting requires a server else where out of the intercepted routing, to be still be able to route to the logging servers as log thes are supported.

The Home Assistant output plugin integration requires the MQTT integration is set up. The application uses MQTT auto discovery, so the devices and entities will show up automatically at the MQTT integration.
If you want to use the [pvoutput](https://pvoutput.org) output plugin, then you need to create an account first. Temperature can also be logged (a [openweathermap](https://openweathermap.org) account is needed).
If you capture using the localproxy or tcpclient client you can also log the inverters temperature and net voltage.
The new influxdb output plugin can now be used as well.

My inverter presents updates approximately updates every 300 seconds. Fore times clients the interval defaults to 360 seconds counts from the last valid update time read from the portal. This way you will not miss any updates.

## Installation
The application can be installed:
-   Install with the Home Assistant Community Store [HACS](https://hacs.xyz/).
    -   Open the settings menu
    -   Enter `https://github.com/jbouwh/omnikdatalogger` at `ADD CUSTOM REPOSITORY`
    -   Select `AppDaemon` as _Category_
-   Download the latest release from [here](https://github.com/jbouwh/omnikdatalogger/releases)
-   Clone using git: `git clone https://gihub.com/jbouwh/omnikdatalogger`. Optional install with `pip3 install ./omnikdatalogger`.
-   Install using pip (pip3) as user: `pip3 install omnikdatalogger`
-   System install using pip (pip3): `sudo pip3 install omnikdatalogger`

The main application files are in the folder `apps/omnikdatalogger`

## Usage
The application can be configured using:
-   Commandline (limited options available)
-   Configuration file (config.ini)
-   apps.yaml configuration file (with AppDaemon) *(This applies tot HACS-users)*

### Commandline
```
usage: [python3] omniklogger.py [-h] [--config FILE] [--interval n] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --config FILE  path to configuration file
  --interval n  execute every n seconds
  -d, --debug    debug mode
```

### Configuration using config.ini

Example configuration

When using the datalogger using the commandline this data logger will need a configuration file. By default, it looks for a config file at `~/.omnik/config.ini`. You can override this path by using the `--config` parameter.

```ini
# Config file for omnikdatalogger
# Encoding: UTF-8
[default]
city = Amsterdam
interval = 360

[plugins]
# valid clients are localproxy, omnikportal, solarmanpv and tcpclient. Chose one!
client = localproxy

# valid localproxy client plugins are: mqtt_proxy, tcp_proxy, hassapi
localproxy = mqtt_proxy

#valid output plugins are pvoutput, mqtt and influxdb
output=pvoutput,mqtt,influxdb

# localproxy client settings
[client.localproxy]
# plant_id_list: comma seperated list of plant_id's
plant_id_list = 123

# Inverter settings for example plant 123
[plant.123]
inverter_address = 192.168.1.1
logger_sn = 123456789
inverter_port = 8899
inverter_sn = NLxxxxxxxxxxxxxx
# Override sys_id for pvoutput.org
sys_id = <YOUR SYSTEM ID>

# plugin: localproxy.mqtt_proxy
[client.localproxy.mqtt_proxy]
# mqtt_prefix_override: Default = {mqtt.discovery_prefix }/binary_sensor/{logger_sensor_name}_{serialnumber}
# {serialnumber} = read from data and checked with {plants.{plant_id}} where {plant_id} in {localproxy.plant_id_list}: 
logger_sensor_name = Datalogger

# The following keys default to the sessings unther the [mqtt] sections
discovery_prefix = homeassistant
host = homeassistant.fritz.box
port = 1883
client_name_prefix = ha-mqttproxy-omniklogger
username = mqttuername
password = mqttpasswordabcdefgh

# plugin: localproxy.hassapi 
[client.localproxy.hassapi]
logger_entity = binary_sensor.datalogger

# plugin: localproxy.tcp_proxy
[client.localproxy.tcp_proxy]
# Inverter settings are read from [plant_id] section
listen_address = 0.0.0.0
listen_port = 10004

# tcpclient settings (poll your inverter at intervals)
# see also https://github.com/Woutrrr/Omnik-Data-Logger
# Users reported that this script works for wifi kits with a s/n starting with 602xxxxxx to 606xxxxxx. With wifi kits in the range 
[client.tcpclient]
plant_id_list = 123
# The serial number is checked against the section [plant_id] inverter_sn = serialnumber

# omnik portal client settings
[client.omnikportal]
username = john.doe@example.com
password = S3cret!

# solarmanpv portal client settings
[client.solarmanpv]
username = john.doe@example.com
password = S3cret!
plant_id_list = 123

# Update plant_id_list this to your own plant_id. 123 is an example! Login to the portal
# and get the pid number from the URL https://www.solarmanpv.com/portal/Terminal/TerminalMain.aspx?pid=123
# Multiple numbers can be supplied like 123,124
plant_id_list = <YOUR PLANT_ID> # ,<YOUR 2nd PLANT_ID>, etc 

[output.pvoutput]
api_key = <YOUR API KEY>
sys_id = <YOUR SYSTEM ID>
use_temperature = true
# If the inverter temperature is available then use that value, not openweather
# The inverter temperature is avaivable only when using the localproxy plugin
use_inverter_temperature = true
# voltage_ac1, voltage_ac2, voltage_ac3, and voltage_ac_max are avaivable only when using the localproxy plugin
publish_voltage = voltage_ac_max

[openweathermap]
api_key = <YOUR API KEY>
endpoint = api.openweathermap.org
lon = 4.0000000
lat = 50.1234567
units = metric

[output.influxdb]
host=localhost
port=8086
database=omnikdatalogger
username=omnikdatalogger
password=mysecretpassword
#jwt_token= (use this for JSON web token authentication)
use_temperature=true

[output.mqtt]
#mqtt integration with 
discovery_prefix = homeassistant
host = homeassistant.local
port = 1883
retain = true
client_name_prefix = ha-mqtt-omniklogger
username = mqttusername
password = mqttpassword

#override for name field from omnik portal
device_name = Omvormer
append_plant_id = false

# Sensor name (omnikproxylogger only)
logger_sensor_name = Datalogger

#Entities name override
current_power_name = Vermogen
total_energy_name = Gegenereerd totaal
today_enery_name = Gegenereerd vandaag
last_update_time_name = Laatste statusupdate

# Following keys are only avaiable used when processing inverter data directly
# See also data_fields.json for additional customization
inverter_temperature_name = Temperatuur omvormer
current_ac1_name = Stroom AC 
current_ac2_name = Stroom AC fase 2
current_ac3_name = Stroom AC fase 3
voltage_ac1_name = Spanning AC fase 1
voltage_ac2_name = Spanning AC fase 2
voltage_ac3_name = Spanning AC fase 3
voltage_ac_max_name Spanning AC max
frequency_ac1_name = Netfrequentie
frequency_ac2_name = Netfrequentie fase 2
frequency_ac3_name = Netfrequentie fase 3
power_ac1_name = Vermogen AC
power_ac2_name = Vermogen AC fase 2
power_ac3_name = Vermogen AC fase 3
voltage_pv1_name = Spanning DC 1
voltage_pv2_name = Spanning DC 2
voltage_pv3_name = Spanning DC 3
current_pv1_name = Stroom DC 1
current_pv2_name = Stroom DC 2
current_pv3_name = Stroom DC 3
power_pv1_name = Vermogen DC 1
power_pv2_name = Vermogen DC 2
power_pv3_name = Vermogen DC 3
current_power_pv_name = Vermogen DC
operation_hours_name = Actieve uren

```

PS: `openweathermap` is currently only used when `use_temperature = true`. 

### Configuration using apps.yaml (AppDeamon) (with possible HomeAssistant integration)

#### Preparation for scheduled use with AppDaemon4
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
The dependency for cachetools is the only 'hard' dependency. Please feel free to adjust the base log_level.

When used with HACS the dependencies in [requirements.txt](https://github.com/jbouwh/omnikdatalogger/blob/master/requirements.txt) should be installed automatically.

The basescript omniklogger.py holds a class HA_OmnikDataLogger that implements appdaemon.plugins.hass.hassapi
See for more information and documentation about AppDaemon: https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html

The configfile /config/appdaemon/appdaemon.yaml needs a minimal configuration. Further it is possible to define the location for your logfiles. And example configuration is:

```yaml
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

#### Configuring `apps.yaml` to use Omnik Data Logger with AppDaemon4
Install the datalogger files from git under /config/appdaemon/apps/omnikdatalogger

The base script is located at:
```
/config/appdaemon/apps/omnikdatalogger/omniklogger.py
```

Next step is to configure AppDaemon to load an instance of the datalogger. It is possible to make multiple instances if you have more omnik accounts.

This configuration is placed in the file: `/config/appdaemon/apps/apps.yaml`. The configuration in apps.yaml is mandantory to the config.ini file if that is used, so it is possible to split the configuration.
#### Example of `apps.yaml`:

```yaml
# The instance name is omnik_datalogger, this can be changed. Multiple instances are supported.
omnik_datalogger:
# General options
  module: omniklogger
  class: HA_OmnikDataLogger
# The config key is optional you can store your config outside this yaml
# config: /config/appdaemon/apps/omnikdatalogger/config.ini
  city: Amsterdam
  interval: 360

# plugin section
  plugins:
# plugins for data logging (output)
    output:
      - pvoutput
      - mqtt 
      - influxdb
# plugins for local proxy client (list)
    localproxy:
      - hassapi
#     - mqtt_proxy
#     - tcp_proxy
# the client that is beging used (choose one)
# valid clients are localproxy, omnikportal, solarmanpv and tcpclient
    client: localproxy

# Section for your inverters specific settings
  plant.123:
    inverter_address: 192.168.1.1
    logger_sn: 123456789
    inverter_port: 8899
    inverter_sn: NLxxxxxxxxxxxxxx
    sys_id: <YOUR SYSTEM ID>

# Section for the localproxy client
  client.localproxy:
    plant_id_list:
      - '123'
# Section for the localproxy plugin hassapi
  client.localproxy.hassapi:
    logger_entity: binary_sensor.datalogger
# Section for the localproxy plugin mqtt_proxy
  client.localproxy.mqtt_proxy:
    logger_sensor_name: Datalogger
    discovery_prefix: homeassistant
    host: homeassistant.example.com
    port: 1883
    client_name_prefix: ha-mqtt-omniklogger
    username: mqttuername
    password: mqttpasswordabcdefgh
# Section for the localproxy plugin tcp_proxy
  client.localproxy.tcp_proxy:
    listen_address: '0.0.0.0'
    listen_port: '10004'

# SolarmanPV portal options
  client.solarmanpv:
    username: john.doe@example.com
    password: some_password
    api_key: apitest
    plant_id_list:
      - 123

# Omnik portal options
  client.localproxy.omnikportal:
    username: john.doe@example.com
    password: some_password
    base_url: https://api.omnikportal.com/v1

# Influxdb output plugin configuration options
  client.localproxy.influxdb:
    host: localhost
    port: 8086
    database: omnikdatalogger
    username: omnikdatalogger
    password: mysecretpassword
    #jwt_token=
    use_temperature=true  

# PVoutput output plugin configuration options
  client.localproxy.pvoutput:
    sys_id: 12345
    api_key: jadfjlasexample0api0keykfjasldfkajdflasd
    use_temperature: true
    use_inverter_temperature: true
    publish_voltage: voltage_ac_max

# Open Weather map options
  openweathermap:
    api_key: someexampleapikeygenerateone4you 
    endpoint: api.openweathermap.org
    lon: 4.0000000
    lat: 50.1234567
    units: metric

# MQTT output plugin configuration options
  client.localproxy.mqtt:
    username: mqttuername
    password: mqttpasswordabcdefgh
    discovery_prefix: homeassistant
    host: homeassistant.example.com
    port: '1883'
    retain: True
    client_name_prefix: ha-mqtt-omniklogger
    device_name: Converter
    append_plant_id: false
    current_power_name: Current power
    total_energy_name: Generated total
    todat_energy_name: Generated today
    last_update_time_name: Last status update
    inverter_temperature_name: Temperatuur omvormer
    current_ac1_name: Stroom AC fase 1
    current_ac2_name: Stroom AC fase 2
    current_ac3_name: Stroom AC fase 3
    voltage_ac1_name: Spanning AC
    voltage_ac2_name: Spanning AC fase 2
    voltage_ac3_name: Spanning AC fase 3
    voltage_ac_max: Spanning AC max
    frequency_ac1_name: Netfrequentie
    frequency_ac2_name: Netfrequentie fase 2
    frequency_ac3_name: Netfrequentie fase 3
    power_ac1_name: Vermogen AC
    power_ac2_name: Vermogen AC fase 2
    power_ac3_name: Vermogen AC fase 3
    voltage_pv1_name: Spanning DC 1
    voltage_pv2_name: Spanning DC 2
    voltage_pv3_name: Spanning DC 3
    current_pv1_name: Stroom DC 1
    current_pv2_name: Stroom DC 2
    current_pv3_name: Stroom DC 3
    power_pv1_name: Vermogen DC 1
    power_pv2_name: Vermogen DC 2
    power_pv3_name: Vermogen DC 3
    current_power_pv_name: Vermogen DC
    operation_hours_name: Actieve uren
```
## Configuration keys (required, optional and defaults)
As mentioned command line and AppDaemon configuration override settings the `config.ini` (if used).

Arguments marked with * must be configured either in the `apps.yaml` or `config.ini` configuration file.

### General settings

#### General settings - `apps.yaml` 'only' configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`module` | False | string | _(none)_ | Should be the name of the base script `omniklogger`. A path should not be configured. AppDaemon wil find the module automatically.
`class` | False | string | _(none)_ | Should be the name of the class hat implements 'appdaemon.plugins.hass.hassapi'. This value should be `HA_OmnikDataLogger`.
`config` | True | string | _(none)_ | File path to the config.ini configuration file. The use of a config file is required when using the command line. A sample config.ini [can be found here](/jbouwh/omnikdatalogger#configuration-using-configini)

#### General settings of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`city` | True | string | `Amsterdam` | City name recognizable by the Astral python module. Based on this city the data logging is disabled from dusk to dawn. This prevents unneccesary calls to the omnik portal.
`interval` | True | integer | `360` | The number of seconds of the interval between the last update timestamp and the next poll. At normal conditions the omnik portal produces a new report approx. every 300 sec. With an interval of 360 a new pol is done with max 60 delay. This enabled fluctuation in the update frequency of the omnik portal. If there is not enough time left to wait (less than 10 sec) and no new report was found at the omnik portal another period of _interval_ seconds will be waited. After an error calling the omnik API another half _interval_ will be waited before the next poll will be done. A pushing client as `localproxy` is, needs an interval te be set when used from the command line higher then 0. The interval it self is not used since the data is pushed. When no interval is given at the command line (or in a systemd setup) the executable will stop automatically after one reading!
`data_config` | True | string | `{path to installed data_fields.json}` | The path to the `data_fields.json`. De default is looking in the folder of the executable. When installed using *pip* `data_fields.json` is installd in the folder `./shared/omnikdatalogger/data_fields.json`. With this parameter you can savely make your own copy and customize it.

#### Plugin settings in the section `plugins` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`client` | False | string | _(none)_ | Name of the client that will be used to fetch the data. Valid choices are `localproxy`, `tcp_client`, `solarmanpv` or `omnikportal`.
`localproxy` | True | list | _(none)_ | The client plugings for the `localproxy` client that will be used to fetch the data. Valid choices are `tcp_proxy`, `mqtt_proxy` or `hassapi`.
`output` |  True | list | _(empty list)_ | A yaml list of string specifying the name(s) of the output plugins to be used. Available plugins are *pvoutput*, *influxdb* and *mqtt*. If no plugins are configured, nothing will be logged.

## Client settings
Every client and client plugin has an own section with configuration keys. Additional for every plant there is a section with plant specific settings.
### LocalProxy client settings in the section `client.localproxy` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`plant_id_list` | False | list | _(none)_ | List with the plant id's you monitor. Details for the plant are set under `[plant_id]`. Replace _plant_id_ with the plant id of your system. Every plant has its own section.

### TCPclient client settings in the section `client.tcpclient` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`plant_id_list` | False | list | _(none)_ | List with the plant id's you want to be monitored. Details for the plant are set under `[plant_id]`. Replace _plant_id_ with the plant id of your system. Every plant has its own section.

#### Plant specific settings in the section `plant.*plant_id*` of `apps.yaml` or `config.ini`
Details for the plant are set under `[plant_id]`. Replace _plant_id_ with the plant id of your system. Every plant has its own section. You can obtain the plan_id by logging in at the https://www.omnikportal.com. And read `pid`=`plant_id` number from the URL e.g. `https://www.solarmanpv.com/portal/Terminal/TerminalMain.aspx?pid=123` where `plant_id` is `123`. The serial number of your Wi-Fi datalogger and inverter you can find here too. Go to **settings** and click on the **device** tab. Possible keys in this section are:
key | optional | type | default | description
-- | --| -- | -- | --
`inverter_address` | True | string | _(none)_ | The IP-adres of your inverter. Used by the client `tcpclient` to access the inverter.
`logger_sn` | True | int | _(none)_ | The logger module serial number of your inverter. Used by the client `tcpclient` to access the inverter.
`inverter_port` | True | int | _8899_ | The the tcp port your inverter listens to (default to 8899). Used by the client `tcpclient` to access the inverter.
`inverter_sn` | False | string | _(none)_ | The serial number of the inverter. Used by the clients `tcpclient`, `localproxy` and `solarmanpv` to map `inverter_sn` and 'plant_id' to validate/filter the raw data messages received.
`sys_id` | True | int | _`sys_id` setting under [pvoutput] section_ | Your unique system id, generated when creating an account at pvoutput.org. See `pvoutput` settings for more information.

The LocalProxy client uses input plugins that are used to collect the data.
The `omnikloggerproxy.py` script (under the folder `/scripts/proxy`) enable to proxy the raw logger data to MQTT and can help to forward your data to omnikdatalogger and still support forwarding the logging to the the legacy portal of Omnik/Solarman.
Multiple plugins can be enabled, but usualy you will use one of these input pluging. The decoding is based on _(https://github.com/Woutrrr/Omnik-Data-Logger)_ by Wouter van der Zwan.
The plugings for the `localproxy` client are:
* `tcp_proxy`: Listens to directed inverter input on port 10004. See *tcp_proxy* paragraph. Yo need to forward the inverter traffic to be able to intercept your inverter data.
* `mqtt_proxy`: Listens to a MQTT topic to retreive the data. Use `omnikloggerproxy.py` to forward to your MQTT server.
* `hassapi`: Listens to a homeassitant entity (ascociated with MQTT) using the HASSAPI in AppDaemon. This plugin is prefered for use in combination with Home Assistant.

#### `tcp_proxy` plugin for the `localproxy` client in the section `client.localproxy.tcp_proxy` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`listen_address` | True | string | _(0.0.0.0)_ | The IP-adres to listen to.
`listen_port` | True | string | _(10004)_ | The port to listen to.

#### `mqtt_proxy` plugin for the `localproxy` client in the section `client.localproxy.mqtt_proxy` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`logger_sensor_name` | True | string | _(Datalogger)_ | The mqtt topic is assembled as {mqtt.discovery_prefix }/binary_sensor/{logger_sensor_name}_{serialnumber}
`discovery_prefix` | True | string | (key under the `output.mqtt` section) | The mqtt plugin supports MQTT auto discovery with Home Assistant. The discovery_prefix configures the topic prefix Home Assistant listens to for auto discovery.
`host` | True | string | (key under the `output.mqtt` section) | Hostname or fqdn of the MQTT server for publishing.
`port` | True | integer | (key under the `output.mqtt` section`) | MQTT port to be used. 
`client_name_prefix` | True | string | (key under the `output.mqtt` section) then `ha-mqttproxy-omniklogger` | Defines a prefix that is used as client name. A 4 byte uuid is added to ensure an unique ID.
`username`* | False | string | _(key under the `output.mqtt` section)_ | The MQTT username used for authentication
`password`* | False | string | _(key under the `output.mqtt` section)_ | The MQTT password used for authentication

#### `hassapi` plugin for the `localproxy` client in the section `client.localproxy.hassapi` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`logger_entity` | True | string | _(binary_sensor.datalogger)_ | The entity name of the datalogger object in Home Assistant created by the mqtt output of the `omnikloggerproxy.py` script

### SolarmanPV client settings in the section `client.solarmanpv` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`username` | False | string | _(none)_ | Your Omikportal or SolarmanPV username
`password` | False | string | _(none)_ | Your Omikportal or SolarmanPV password
`plant_id_list` |  False | list | _(empty list)_ | A (comma separated) or yaml list of strings specifying the plant_id(s) or pid's of of your plants.
`api_key` | True | string | _(apitest)_ | The API key used to access your data. The default key might work for you as well.
`base_url` | True | string | _(http://www.solarmanpv.com:18000/SolarmanApi/serverapi)_ | The API URL used to access your data.

This client colects the inverters serial number (`inverter_sn`) and `plant_id` from the `[plant_id]` section [mentioned earlier](#plant-specific-settings-under-plant_id-in-appsyaml-or-plant_id-configini-configuration-options).

### OmnikPortal client settings in the section `client.omnikportal` of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`username` | False | string | _(none)_ | Your Omikportal or SolarmanPV username
`password` | False | string | _(none)_ | Your Omikportal or SolarmanPV password
`app_id ` | True | string | _(10038)_ | The APP_ID used to access your data. The default value might work for you as well.
`app_key` | True | string | _(Ox7yu3Eivicheinguth9ef9kohngo9oo)_ | The API key to access your data 
`base_url` | True | string | _(https://api.omnikportal.com/v1)_ | The API URL used to access your data.
    
## Output plugins

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

#### MQTT settings in the section `output.mqtt` of `apps.yaml` or `config.ini`

key | optional | type | default | description
-- | --| -- | -- | --
`discovery_prefix` | True | string | `homeassistant` | The mqtt plugin supports MQTT auto discovery with Home Assistant. The discovery_prefix configures the topic prefix Home Assistant listens to for auto discovery.
`device_name` | True | string | _(the name of the plant in the omnik portal)_ | Overrides the name of the plant in the omnik portal.
`append_plant_id` | True | bool | `false` | When a device_name is specified the plant id can be added to the name te be able to identify the plant.
`host` | True | string | `localhost` | Hostname or fqdn of the MQTT server for publishing.
`port` | True | integer | `1883` | MQTT port to be used. 
`retain` | True | bool | True | Retains the data send to the MQTT service
`client_name_prefix` | True | string | `ha-mqtt-omniklogger` | Defines a prefix that is used as client name. A 4 byte uuid is added to ensure an unique ID.
`username`* | False | string | _(none)_ | The MQTT username used for authentication
`password`* | False | string | _(none)_ | The MQTT password used for authentication

#### Renaming entities. (Keys are like {fieldname}_name)
_For every solar plant, 4 entities are added to the mqtt auto discovery. The default name can be configured._

key | optional | type | default | description
-- | --| -- | -- | --
`current_power_name` | True | string | `Current power` | Name override for the entity that indicates the current power in Watt the solar plant is producing.
`total_energy_name` | True | string | `Energy total` | Name override for the entity that indicates total energy in kWh the solar plant has generated since installation.
`today_energy_name` | True | string | `Energy today` | Name override for the entity that indicates total energy in kWh the solar plant has generated this day.
`last_update_time_name` | True | string | `Last update` | Name override for the entity that is a timestamp total of the last update of the solar plant.
`name` | True | string | `Current power` | Name override for the entity that indicates the current power in Watt the solar plant is producing.
`inverter_temperature_name` | True | string | `Inverter temperature` | Name override for inverters Temperature. Only the clients `tcpclient` and `localproxy` are supported.
`current_ac1_name` | True | string | `AC Current fase R` | Name override for AC Current fase 1. Only the clients `tcpclient` and `localproxy` are supported.
`current_ac2_name` | True | string | `AC Current fase S` | Name override for AC Current fase 2. Only the clients `tcpclient` and `localproxy` are supported.
`current_ac3_name` | True | string | `AC Current fase T` | Name override for AC Current fase 3. Only the clients `tcpclient` and `localproxy` are supported.
`voltage_ac1_name` | True | string | `AC Voltage fase R` | Name override for AC Voltage fase 1. Only the clients `tcpclient` and `localproxy` are supported.
`voltage_ac2_name` | True | string | `AC Voltage fase S` | Name override for AC Voltage fase 2. Only the clients `tcpclient` and `localproxy` are supported.
`voltage_ac3_name` | True | string | `AC Voltage fase T` | Name override for AC Voltage fase 3. Only the clients `tcpclient` and `localproxy` are supported.
`voltage_ac_max_name` | True | string | `AC Voltage max` | Name override for the maximal AC Voltage over al fases. Only the clients `tcpclient` and `localproxy` are supported.
`frequency_ac1_name` | True | string | `AC Frequency fase R` | Name override for AC Frequency fase 1. Only the clients `tcpclient` and `localproxy` are supported.
`frequency_ac2_name` | True | string | `AC Frequency fase S` | Name override for AC Frequency fase 2. Only the clients `tcpclient` and `localproxy` are supported.
`frequency_ac3_name` | True | string | `AC Frequency fase T` | Name override for AC Frequency fase 3. Only the clients `tcpclient` and `localproxy` are supported.
`power_ac1_name` | True | string | `AC Power fase R` | Name override for AC Power fase 1. Only the clients `tcpclient` and `localproxy` are supported.
`power_ac2_name` | True | string | `AC Power fase S` | Name override for AC Power fase 2.  Only the clients `tcpclient` and `localproxy` are supported.
`power_ac3_name` | True | string | `AC Power fase T` | Name override for AC Power fase 3. Only the clients `tcpclient` and `localproxy` are supported.
`voltage_pv1_name` | True | string | `DC Voltage string 1` | Name override for PV Voltage string 1. Only the clients `tcpclient` and `localproxy` are supported.
`voltage_pv2_name` | True | string | `DC Voltage string 2` | Name override for PV Voltage string 2. Only the clients `tcpclient` and `localproxy` are supported.
`voltage_pv3_name` | True | string | `DC Voltage string 3` | Name override for PV Voltage string 3. Only the clients `tcpclient` and `localproxy` are supported.
`current_pv1_name` | True | string | `DC Current string 1` | Name override for PV Current string 1. Only the clients `tcpclient` and `localproxy` are supported.
`current_pv2_name` | True | string | `DC Current string 2` | Name override for PV Current string 2. Only the clients `tcpclient` and `localproxy` are supported.
`current_pv3_name` | True | string | `DC Current string 3` | Name override for PV Current string 3. Only the clients `tcpclient` and `localproxy` are supported.
`power_pv1_name` | True | string | `DC Power string 1` | Name override for PV Power string 1. Only the clients `tcpclient` and `localproxy` are supported.
`power_pv2_name` | True | string | `DC Power string 2` | Name override for PV Power string 2. Only the clients `tcpclient` and `localproxy` are supported.
`power_pv3_name` | True | string | `DC Power string 3` | Name override for PV Power string 3. Only the clients `tcpclient` and `localproxy` are supported.
`current_power_pv_name` | True | string | `DC Current power` | Name override for PV total power. Only the clients `tcpclient` and `localproxy` are supported.
`operation_hours_name` | True | string | `Hours active` | Name override for the oprational hours of the inverter. Only the clients `tcpclient` and `localproxy` are supported.

The unit of measurement the used icon, MQTT device_class and value template file can be customized by updating the file `data_fields.json`.
Make a copy of the original file and configure the path under the `data_config` key in the general setting.

### PVoutput plugin settings in the section `output.pvoutput` of `apps.yaml` or `config.ini`

Register a free acount and API key at https://pvoutput.org/register.jsp

key | optional | type | default | description
-- | --| -- | -- | --
`sys_id`* | False | string | _(none)_ | Your unique system id, generated when creating an account at pvoutput.org.    
`api_key`* | False | string | _(none)_ | Unique API access key generated at pvoutput.org
`use_temperature` | True | bool | `false` | When set to true and `use_inverter_temperature` is not set, the temperature is obtained from OpenWeatherMap is submitted to pvoutput.org when logging the data.
`use__inverter_temperature` | True | bool | `false` | When set to true and `use_temperature` is set, the inverter temperature is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported.
`publish_voltage` | True | string | _(none)_ | The *fieldname* key of the voltage property to use for pvoutput 'addstatus' publishing. When set to `'voltage_ac_max'`, the maximal inverter AC voltage over all fases is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported. Supported values are `voltage_ac1`, `voltage_ac2`, `voltage_ac3` or `voltage_ac_max`. The field `voltage_ac_max` holds the highest voltages measures over all fases.
### InfluxDB plugin settings in the section `output.influxdb` in  of `apps.yaml` or `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`host` | True | string | `localhost` | Hostname or fqdn of the InfluxDB server for logging.
`port` | True | integer | `8086` | InfluxDB port to be used. 
`database` | True | string | _omnikdatalogger_ | The InfluxDB database
`username` | True | string | _(none)_ | The InfluxDB username used for Basic authentication
`password` | True | string | _(none)_ | The InfluxDB password used for Basic authentication
`jwt_token` | True | string | _(none)_ | The InfluxDB webtoken for JSON Web Token authentication
`use_temperature` | True | bool | `false` | When set to true the temperature is obtained from OpenWeatherMap and logged.

Logging to InfluxDB is supported with configuration settings from `data_fields.json` The file allows to customize measurement header and allows setting additional tags.
#### OpenWeatherMap settings in the section `openweathermap` of `apps.yaml` or `config.ini`
_(used by *PVoutput* plugin if *use_temperature* is true and you did not specify `use__inverter_temperature`)_

Visit https://openweathermap.org/price to obtain a (free) api key. The weather data is cached with een TTL of 300 seconds.

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
#### Create a to download the scripts
$ git clone https://github.com/jbouwh/omnikdatalogger
> onmiklogger.py can be found in the `./apps` folder
# check if properly installed
$ omniklogger.py -h
usage: omniklogger.py [-h] [--config FILE] [--interval n] [-d]

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

## Plugins in development
Working on a couple of plugins to customize processing of the omnik inverter data:

* `P1` ~ support for the the Dutch Smart Meter (DSRM) with mqtt, pvoutput and influxdb integration
* `mariadb` ~ mariadb/mysql output plugin
* `csv` ~ csv output plugin

~ the end
