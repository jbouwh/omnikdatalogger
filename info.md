# omnikdatalogger

![omnikdatalogger](https://github.com/jbouwh/omnikdatalogger/workflows/omnikdatalogger/badge.svg)

## Configuration
The application can be configured using:
-   Commandline (limited options)
-   Configuration file (config.ini)
-   apps.yaml configuration file (with AppDaemon)

Using apps.yaml there is no need for config.ini.


## App configuration

When used with HACS the dependencies in [requirements.txt](https://github.com/jbouwh/omnikdatalogger/requirements.txt) should be installed automatically. The dependency for `cachetools` is the only 'hard' dependency within Home Assistant since all other dependencies are ok. You can add this following packages to your appdaemon 4 configuration on the supervisor page of the add-on.

``` yaml
system_packages: []
python_packages:
  - cachetools
init_commands: []
```

The basescript `omniklogger.py` holds a class HA_OmnikDataLogger that implements appdaemon.plugins.hass.hassapi
See for more information and documentation about AppDaemon: https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html

### Configuration example
```yaml
omnik_datalogger:
# General options
  module: omniklogger
  class: HA_OmnikDataLogger
  config: /config/appdaemon/apps/omnikdatalogger/config.ini
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
### Configuration options (required, optional and defaults)

#### General settings
key | optional | type | default | description
-- | --| -- | -- | --
`module` | False | string | _(none)_ | Should be the name of the base script `omniklogger`. A path should not be configured. AppDaemon wil find the module automatically.
`class` | False | string | _(none)_ | Should be the name of the class hat implements 'appdaemon.plugins.hass.hassapi'. This value should be `HA_OmnikDataLogger`.
`config` | True | string | _(none)_ | File path to the config.ini configuration file. The use of a config file is required when using the command line. A sample config.ini template file is can be found at /config/appdaemon/apps/omnikdatalogger/config.ini
`city` | True | string | `Amsterdam` | City name recognizable by the Astral python module. Based on this city the data logging is disabled from dusk to dawn. This prevents unneccesary calls to the omnik portal.
`interval` | True | integer | `360` | The number of seconds of the onterval between the last update timestamp and the next poll. At normal conditions the omnik portal produces a new report approx. every 300 sec. With an interval of 360 a new pol is done with max 60 delay. This enabled fluctuation in the update frequency of the omnik portal. If there is not enough time left to wait (less than 10 sec) and no new report was found at the omnik portal another period of _interval_ seconds will be waited. After an error calling the omnik API another half _interval_ will be waited before the next poll will be done.
    
#### Enable plugins under `plugins:`
key | optional | type | default | description
-- | --| -- | -- | --
`output` |  True | list | _(empty list)_ | A (comma separated) list or yaml list of string specifying the name(s) of the output plugins to be used. Available plugins are *pvoutput* and *mqtt*. If no plugins are configured, nothing will be logged.

#### MQTT plugin
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

#### MQTT settings under `mqtt:`

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

##### Renaming entities
_For every solar plant, 4 entities are added to the mqtt auto discovery. The default name can be configured._

key | optional | type | default | description
-- | --| -- | -- | --
`current_power_name` | True | string | `Current power` | Name override for the entity that indicates the current power in Watt the solar plant is producing.
`total_energy_name` | True | string | `Energy total` | Name override for the entity that indicates total energy in kWh the solar plant has generated since installation.
`income_name` | True | string | `Income` | Name override for the entity that indicates total income for the solar plant since installation. De default unit is €, and can be customized in Home Assistant. The income is calculated at the omnik portal based on the settings in the portal.
`last_update_time_name` | True | string | `Last update` | Name override for the entity that is a timestamp total of the last update of the solar plant.

## PVoutput plugin settings under `pvoutput:`

Register a free acount and API key at https://pvoutput.org/register.jsp

key | optional | type | default | description
-- | --| -- | -- | --
`sys_id`* | False | string | _(none)_ | Your unique system id, generated when creating an account at pvoutput.org.    
`api_key`* | False | string | _(none)_ | Unique API access key generated at pvoutput.org
`use_temperature` | True | bool | `false` | When set to true the temperature obtained from OpenWeatherMap is submitted to pvoutput.org when logging the data.

## OpenWeatherMap settings under `openweathermap:`
_(used by *PVoutput* plugin if *use_temperature* is true)_

Visit https://openweathermap.org/price to obtain a (free) api key. The weather is cached with een TTL of 300 seconds.

key | optional | type | default | description
-- | --| -- | -- | --
`api_key`* | False | string | _(none)_ | Unique access key generated at openweathermap.org
`endpoint` | True | string | `api.openweathermap.org` | FQDN of the API endpoint.
`lon`* | False | float | _(none)_ | Longitude for the weather location
`lat`* | False | float | _(none)_ | Latitude for the weather location
`units` | True | string | `metric` | Can be _metric_ (for deg. Celsius) or _imperial_ (for deg. Fahrenheit)
