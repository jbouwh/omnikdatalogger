# omnikdatalogger
*Code parsing:* ![omnikdatalogger](https://github.com/jbouwh/omnikdatalogger/workflows/omnikdatalogger/badge.svg)
*HACS AppDaemon:* ![Validation](https://github.com/jbouwh/omnikdatalogger/workflows/Validate/badge.svg)

## Introduction
The original version of this is a Python3 based PV data logger with plugin support, is specifically build for the Omniksol-5k-TL2 but have been tested with the
firstgeneration inverter Omniksol-3K-TL as well.
This datalogger can use data collected at the [omnikportal](https://www.omnikportal.com/) or at [solarmanpv](https://www.solarmanpv.com/portal)
to fetch data pushed by the inverter. Pascal tried using the inverter directly, but the firmware seems _very_ buggy: it either spontanious reboots,
hangs or returns seemingly random data.
I have adapted this project and tried it in combination with my Omniksol-3k-TL. This model datalogger cannot be accessed directly for data collection, so I started using the portal api.
Further support has been added for MQTT and is can now be integrated with Home Assistent using the AppDaemon addon.
The comming version will support the processing of intercepted data on your local network. I wil provide a guide to explain the steps. This wil give an independent datalogging,
but will also disable the data collection in the cloud. I am investigating a method that still will deliver the logged data to the omnik portla while interception.

## How can I use Omnik Data Logger
You can find severals apps for reading out Omnik solar inverters directly. But many inverters are older and cannot be read out directly in an easy way. If your solar system was connected to (https://www.omnikportal.com) then you can now integrate easy with Home Assistant and pvoutput.org.
Since the omnikportal is having outages many times, an laternative will be welcome. There is an alternative portal at [SolarMAN](https://www.solarmanpv.com/portal) where you can login with your existing account and all of your data is being preserved!
Since omnikportal stopped working the client needed to be updated to work with the SolarMAN API. The code has now a pluggable client module and two new modules wille be developed.
The first new client module is the `solarmanpv` client which replaces the old `omnikportal` client (code still available). `solarmanpv` is now the default client and ready for use. Make sure to update your configuration. The second module `localproxy` is in development (not ready yet) and will support local captured logging for datasystemens that do not support direct logging.
My own PV system is of that type, so I can test with that easily. This module disables logging to omnikportal or solarmanpv and captures the data in your local network by simulating the backend
This code will be based on is based on (https://github.com/Woutrrr/Omnik-Data-Logger) and (https://github.com/t3kpunk/Omniksol-PV-Logger). This feature will come later. There will be tutorial on how to capture the data in your local network.

The Home Assistant output plugin Integration requires a MQTT integration is set up. The application uses MQTT auto discovery, so the devices and entities will show up automatically at the MQTT integration.
If you want to use the [pvoutput](https://pvoutput.org) output plugin, then you need to create an account first. Temperature can also be logged (a [openweathermap](https://openweathermap.org) is needed).
The omnik portal presents approximately updates every 300 seconds. The interval defaults to 360 seconds counts from the last valid update time read from the portal. This way you wille nog miss any updates.

## Installation
The application can be installed:
-   Install with the Home Assistant Community Store [HACS](https://hacs.xyz/).
    -   Open the settings menu
    -   Enter `https://github.com/jbouwh/omnikdatalogger` at `ADD CUSTOM REPOSITORY`
    -   Select `AppDaemon` as _Category_
-   Download the latest release from [here](https://github.com/jbouwh/omnikdatalogger/releases)
-   Clone using git: `git clone https://gihub.com/jbouwh/omnikdatalogger`

## Configuration options
The application can be configured using:
-   Commandline (limited options)
-   Configuration file (config.ini)
-   apps.yaml configuration file (with AppDaemon) *(This applies tot HACS-users)*

### Use omniklogger from the command line
```
usage: python3 omniklogger.py [-h] [--config FILE] [--interval n] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --config FILE  path to configuration file
  --interval n  execute every n seconds
  -d, --debug    debug mode
```

### Configuration (config.ini)

Example configuration

When using the datalogger using the commandline this data logger will need a configuration file. By default, it looks for a config file at `~/.omnik/config.ini`. You can override this path by using the `--config` parameter.

```ini
[default]
timezone = Europe/Amsterdam
city = Amsterdam
interval = 360

# valid clients are omnikportal, solarmanpv (site possible not active). solarmanpv is the default now
client = solarmanpv

[omnikportal]
username = john.doe@example.com
password = S3cret!

[solarmanpv]
username = john.doe@example.com
password = S3cret!

# Update plant_id_list this to your own plant_id. 123 is an example! Login to the portal
# and get the pid number from the URL https://www.solarmanpv.com/portal/Terminal/TerminalMain.aspx?pid=123
# Multiple numbers can be supplied like 123,124
plant_id_list = <YOUR PLANT_ID> # ,<YOUR 2nd PLANT_ID>, etc 

[plugins]
output=pvoutput,mqtt

[pvoutput]
api_key = <YOUR API KEY>
sys_id = <YOUR SYSTEM ID>
use_temperature = true

[openweathermap]
api_key = <YOUR API KEY>
endpoint = api.openweathermap.org
lon = 4.0000000
lat = 50.1234567
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

### Integration with HomeAssistant
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
  config: /config/appdaemon/apps/omnikdatalogger/config.ini
  timezone: Europe/Amsterdam
  city: Amsterdam
  interval: 360
  client: solarmanpv
# SolarmanPV portal options
  solarmanpv:
    username: john.doe@example.com
    password: some_password
    plant_id_list:
      - 123

# Omnik portal options
  omnikportal:
    username: john.doe@example.com
    password: some_password
    base_url: https://api.omnikportal.com/v1
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
    todat_energy_name: Generated today
    last_update_time_name: Last status update
```
## Configuration options (required, optional and defaults)
As mentioned command line and AppDaemon configuration override settings the `config.ini` (if used).

Arguments marked with * must be configured either in the `apps.yaml` or `config.ini` configuration file.

### General settings

#### General settings - `apps.yaml` 'only' configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`module` | False | string | _(none)_ | Should be the name of the base script `omniklogger`. A path should not be configured. AppDaemon wil find the module automatically.
`class` | False | string | _(none)_ | Should be the name of the class hat implements 'appdaemon.plugins.hass.hassapi'. This value should be `HA_OmnikDataLogger`.
`config` | True | string | _(none)_ | File path to the config.ini configuration file. The use of a config file is required when using the command line. A sample config.ini template file is can be found at /config/appdaemon/apps/omnikdatalogger/config.ini

#### General settings `apps.yaml` or `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`city` | True | string | `Amsterdam` | City name recognizable by the Astral python module. Based on this city the data logging is disabled from dusk to dawn. This prevents unneccesary calls to the omnik portal.
`interval` | True | integer | `360` | The number of seconds of the interval between the last update timestamp and the next poll. At normal conditions the omnik portal produces a new report approx. every 300 sec. With an interval of 360 a new pol is done with max 60 delay. This enabled fluctuation in the update frequency of the omnik portal. If there is not enough time left to wait (less than 10 sec) and no new report was found at the omnik portal another period of _interval_ seconds will be waited. After an error calling the omnik API another half _interval_ will be waited before the next poll will be done.

#### Plugin settings  under `plugins` in `apps.yaml` or `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`client` | False | string | _(none)_ | Name of the client that will be used to fetch the data. Valid choices are `localproxy`, `tcp_client`, `solarmanpv` or `omnikportal`.
`localproxy` | True | list | _(none)_ | The client plugings for the `localproxy` client that will be used to fetch the data. Valid choices are `tcp_proxy`, `mqtt_proxy` or `hassapi`.


### Client settings

#### LocalProxy client settings under `localproxy` in `apps.yaml` or `[solarmanpv]` `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`plant_id_list` | False | list | _(none)_ | List with the plant id's you monitor. Details for the plant are set under `[plant_id]`. Every plant has its own section.

##### Plant settings under `'plant_id'` in `apps.yaml` or `[plant_id]` `config.ini` configuration options
Details for the plant are set under `[plant_id]`. Every plant has its own section. Possible keys are:
key | optional | type | default | description
-- | --| -- | -- | --
`inverter_address` | True | string | _(none)_ | The IP-adres of your inverter. Used by the client `tcpclient` to access the inverter.
`logger_sn` | True | int | _(none)_ | The logger module serial number of your inverter. Used by the client `tcpclient` to access the inverter.
`inverter_port` | True | int | _8899_ | The the tcp port your inverter listens to (default to 8899). Used by the client `tcpclient` to access the inverter.
`inverter_sn` | False | string | _(none)_ | The serial number of the inverter. Used by the clients `tcpclient`, `localproxy` and `solarmanpv` to map `inverter_sn` and 'plant_id' to validate/filter the raw data messages received.

The LocalProxy client uses input plugins that are used to collect the data.
The `omnikloggerproxy.py` script (under the folder `/scripts/proxy`) enable to proxy the raw logger data to MQTT and can help to forward your data to omnikdatalogger and still support forwarding the logging to the the legacy portal of Omnik/Solarman.
Multiple plugins can be enabled, but usualy you will use one of these input pluging. The decoding is based on _(https://github.com/Woutrrr/Omnik-Data-Logger)_ by Wouter van der Zwan.
The plugings for the `localproxy` client are:
* `tcp_proxy`: Listens to directed inverter input on port 10004. See *tcp_proxy* paragraph. Yo need to forward the inverter traffic to be able to intercept your inverter data.
* `mqtt_proxy`: Listens to a MQTT topic to retreive the data. Use `omnikloggerproxy.py` to forward to your MQTT server.
* `hassapi`: Listens to a homeassitant entity (ascociated with MQTT) using the HASSAPI in AppDaemon. This plugin is prefered for use in combination with Home Assistant.

##### `tcp_proxy` plugin for the `localproxy` client under `tcp_proxy` in `apps.yaml` or `[tcp_proxy]` `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`listen_address` | True | string | _(0.0.0.0)_ | The IP-adres to listen to.
`listen_port` | True | string | _(10004)_ | The port to listen to.

##### `mqtt_proxy` plugin for the `localproxy` client under `mqtt_proxy` in `apps.yaml` or `[mqtt_proxy]` `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`logger_sensor_name` | True | string | _(Datalogger)_ | The mqtt topic is assembled as {mqtt.discovery_prefix }/binary_sensor/{logger_sensor_name}_{serialnumber}
`discovery_prefix` | True | string | (key under the `mqtt`section`) | The mqtt plugin supports MQTT auto discovery with Home Assistant. The discovery_prefix configures the topic prefix Home Assistant listens to for auto discovery.
`host` | True | string | (key under the `mqtt`section`) | Hostname or fqdn of the MQTT server for publishing.
`port` | True | integer | (key under the `mqtt`section`) | MQTT port to be used. 
`client_name_prefix` | True | string | (key under the `mqtt`section`) then `ha-mqttproxy-omniklogger` | Defines a prefix that is used as client name. A 4 byte uuid is added to ensure an unique ID.
`username`* | False | string | _(key under the `mqtt`section`)_ | The MQTT username used for authentication
`password`* | False | string | _(key under the `mqtt`section`)_ | The MQTT password used for authentication

##### `hassapi` plugin for the `localproxy` client under `hassapi` in `apps.yaml` or `[hassapi]` `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`logger_entity` | True | string | _(binary_sensor.datalogger)_ | The entity name of the datalogger object in Home Assistant created by the mqtt output of the `omnikloggerproxy.py` script

### SolarmanPV client settings under `solarmanpv` in `apps.yaml` or `[solarmanpv]` `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`username` | False | string | _(none)_ | Your Omikportal or SolarmanPV username
`password` | False | string | _(none)_ | Your Omikportal or SolarmanPV password
`plant_id_list` |  False | list | _(empty list)_ | A (comma separated) or yaml list of strings specifying the plant_id(s) or pid's of of your plants.
`api_key` | True | string | _(apitest)_ | The API key used to access your data. The default key might work for you as well.
`base_url` | True | string | _(http://www.solarmanpv.com:18000/SolarmanApi/serverapi)_ | The API URL used to access your data.

This client colects the inverters serial number (`inverter_sn`) and `plant_id` from the `[plant_id]` section mentioned earlier.

### OmnikPortal client settings under `omnikportal` in `apps.yaml` or `[omnikportal]` `config.ini` configuration options
key | optional | type | default | description
-- | --| -- | -- | --
`username` | False | string | _(none)_ | Your Omikportal or SolarmanPV username
`password` | False | string | _(none)_ | Your Omikportal or SolarmanPV password
`app_id ` | True | string | _(10038)_ | The APP_ID used to access your data. The default value might work for you as well.
`app_key` | True | string | _(Ox7yu3Eivicheinguth9ef9kohngo9oo)_ | The API key to access your data 
`base_url` | True | string | _(https://api.omnikportal.com/v1)_ | The API URL used to access your data.
    
### Enable plugins under `plugins:` in `apps.yaml` or `[plugins]` in `config.ini`
key | optional | type | default | description
-- | --| -- | -- | --
`output` |  True | list | _(empty list)_ | A (comma separated) list or yaml list of strings specifying the name(s) of the output plugins to be used. Available plugins are *pvoutput* and *mqtt*. If no plugins are configured, nothing will be logged.

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

The unit of measurement the used icon, MQTT device_class and value template filyet can be customized by updating the file 'mqtt_fields.json'.

## PVoutput plugin settings under `pvoutput:` in `apps.yaml` or `[pvoutput]` in `config.ini` configuration options

Register a free acount and API key at https://pvoutput.org/register.jsp

key | optional | type | default | description
-- | --| -- | -- | --
`sys_id`* | False | string | _(none)_ | Your unique system id, generated when creating an account at pvoutput.org.    
`api_key`* | False | string | _(none)_ | Unique API access key generated at pvoutput.org
`use_temperature` | True | bool | `false` | When set to true and `use_inverter_temperature` is not set, the temperature is obtained from OpenWeatherMap is submitted to pvoutput.org when logging the data.
`use__inverter_temperature` | True | bool | `false` | When set to true and `use_temperature` is set, the inverter temperature is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported.
`publish_voltage ` | True | string | _(none)_ | The *fieldname* key of the voltage property to use for pvoutput 'addstatus' publishing. When set to `'voltage_ac1'`, the inverter AC voltage of fase 1 is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported.

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
#### Create a to download the scripts
$ git clone https://github.com/jbouwh/omnikdatalogger
> onmiklogger.py can be found in the `./apps` folder
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
> By default omniklogger is searching for config file ~/.omnik/config.ini when executed from the command line

## P1 DSRM (Dutch Smart Meter) integration (Work-in-progress)

I have plans to integrate measurements done on the P1 port of the DUTCH Smart Meter.

## Plugins
Working on a couple of plugins to customize processing of the omnik-portal data:

* `pvoutput` ~ write data to [PVOutput](https://www.pvoutput.org)
* `mqtt` ~ write data to a [MQTT] 
* `P1` ~ support for the the Dutch Smart Meter (***TODO***)

~ the end
