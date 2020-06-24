# omnikdatalogger
![omnikdatalogger](https://github.com/jbouwh/omnikdatalogger/workflows/omnikdatalogger/badge.svg)
![PyPI version](https://badge.fury.io/py/omnikdatalogger.svg) 
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
## See also
- [Omnik data logger Wiki](https://github.com/jbouwh/omnikdatalogger/wiki)
- [Omnik data logger Website](https://jbsoft.nl/site/omnik-datalogger/)

## Configuration
The application can be configured using:
-   Commandline (limited options)
-   Configuration file (config.ini)
-   apps.yaml configuration file (with AppDaemon)

Using apps.yaml there is no need for config.ini.

See [README.md](https://github.com/jbouwh/omnikdatalogger/blob/master/README.md) for a more detailed description.

When using HACS, do not forget to restart AppDaemon after a software update!

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

#### Configuration example
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
### Configuration options (required, optional and defaults)

#### General settings
key | optional | type | default | description
-- | --| -- | -- | --
`module` | False | string | _(none)_ | Should be the name of the base script `omniklogger`. A path should not be configured. AppDaemon wil find the module automatically.
`class` | False | string | _(none)_ | Should be the name of the class hat implements 'appdaemon.plugins.hass.hassapi'. This value should be `HA_OmnikDataLogger`.
`config` | True | string | _(none)_ | File path to the config.ini configuration file. The use of a config file is required when using the command line. A sample config.ini template file is can be found at /config/appdaemon/apps/omnikdatalogger/config.ini
`city` | True | string | `Amsterdam` | City name recognizable by the Astral python module. Based on this city the data logging is disabled from dusk to dawn. This prevents unneccesary calls to the omnik portal.
`interval` | True | integer | `360` | The number of seconds of the onterval between the last update timestamp and the next poll. At normal conditions the omnik portal produces a new report approx. every 300 sec. With an interval of 360 a new pol is done with max 60 delay. This enabled fluctuation in the update frequency of the omnik portal. If there is not enough time left to wait (less than 10 sec) and no new report was found at the omnik portal another period of _interval_ seconds will be waited. After an error calling the omnik API another half _interval_ will be waited before the next poll will be done.
`data_config` | True | string | `{path to installed data_fields.json}` | The path to the `data_fields.json`. De default is looking in the folder of the executable. When installed using *pip* `data_fields.json` is installd in the folder `./shared/omnikdatalogger/data_fields.json`. With this parameter you can savely make your own copy and customize it.
    
#### Enable plugins under `plugins:`
key | optional | type | default | description
-- | --| -- | -- | --
`client` | False | string | _(none)_ | Name of the client that will be used to fetch the data. Valid choices are `localproxy`, `tcp_client`, `solarmanpv` or `omnikportal`.
`localproxy` | True | list | _(none)_ | The client plugings for the `localproxy` client that will be used to fetch the data. Valid choices are `tcp_proxy`, `mqtt_proxy` or `hassapi`.
`output` |  True | list | _(empty list)_ | A (comma separated) list or yaml list of string specifying the name(s) of the output plugins to be used. Available plugins are *pvoutput*, *influxdb* and *mqtt*. If no plugins are configured, nothing will be logged.

### Client settings (required, optional and defaults)

#### LocalProxy client settings under `client.localproxy:` in `apps.yaml`
key | optional | type | default | description
-- | --| -- | -- | --
`plant_id_list` | False | list | _(none)_ | List with the plant id's you monitor. Details for the plant are set under `[plant_id]`. Every plant has its own section.

##### Plant settings under `plant.*plant_id*:` in `apps.yaml`
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

##### `tcp_proxy` plugin for the `localproxy` client under `client.localproxy.tcp_proxy:` in `apps.yaml`
key | optional | type | default | description
-- | --| -- | -- | --
`listen_address` | True | string | _(0.0.0.0)_ | The IP-adres to listen to.
`listen_port` | True | string | _(10004)_ | The port to listen to.

##### `mqtt_proxy` plugin for the `localproxy` client under `client.localproxy.mqtt_proxy:` in `apps.yaml`
key | optional | type | default | description
-- | --| -- | -- | --
`logger_sensor_name` | True | string | _(Datalogger)_ | The mqtt topic is assembled as {mqtt.discovery_prefix }/binary_sensor/{logger_sensor_name}_{serialnumber}
`discovery_prefix` | True | string | (key under the `mqtt`section`) | The mqtt plugin supports MQTT auto discovery with Home Assistant. The discovery_prefix configures the topic prefix Home Assistant listens to for auto discovery.
`host` | True | string | (key under the `mqtt`section`) | Hostname or fqdn of the MQTT server for publishing.
`port` | True | integer | (key under the `mqtt`section`) | MQTT port to be used. 
`client_name_prefix` | True | string | (key under the `mqtt`section`) then `ha-mqttproxy-omniklogger` | Defines a prefix that is used as client name. A 4 byte uuid is added to ensure an unique ID.
`username`* | False | string | _(key under the `mqtt`section`)_ | The MQTT username used for authentication
`password`* | False | string | _(key under the `mqtt`section`)_ | The MQTT password used for authentication

##### `hassapi` plugin for the `localproxy` client under `client.localproxy.hassapi:` in `apps.yaml`
key | optional | type | default | description
-- | --| -- | -- | --
`logger_entity` | True | string | _(binary_sensor.datalogger)_ | The entity name of the datalogger object in Home Assistant created by the mqtt output of the `omnikloggerproxy.py` script

#### SolarmanPV client settings under `client.solarmanpv:` in `apps.yaml`
key | optional | type | default | description
-- | --| -- | -- | --
`username` | False | string | _(none)_ | Your Omikportal or SolarmanPV username
`password` | False | string | _(none)_ | Your Omikportal or SolarmanPV password
`plant_id_list` |  False | list | _(empty list)_ | A (comma separated) or yaml list of strings specifying the plant_id(s) or pid's of of your plants.
`api_key` | True | string | _(apitest)_ | The API key used to access your data. The default key might work for you as well.
`base_url` | True | string | _(http://www.solarmanpv.com:18000/SolarmanApi/serverapi)_ | The API URL used to access your data.

This client colects the inverters serial number (`inverter_sn`) and `plant_id` from the `[plant_id]` section mentioned earlier.

#### OmnikPortal client settings under `client.omnikportal:` in `apps.yaml`
key | optional | type | default | description
-- | --| -- | -- | --
`username` | False | string | _(none)_ | Your Omikportal or SolarmanPV username
`password` | False | string | _(none)_ | Your Omikportal or SolarmanPV password
`app_id ` | True | string | _(10038)_ | The APP_ID used to access your data. The default value might work for you as well.
`app_key` | True | string | _(Ox7yu3Eivicheinguth9ef9kohngo9oo)_ | The API key to access your data 
`base_url` | True | string | _(https://api.omnikportal.com/v1)_ | The API URL used to access your data.

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

### Output plugin settings (required, optional and defaults)

#### MQTT settings under `output.mqtt:`

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

##### Renaming entities. (Keys are like {fieldname}_name)
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

The unit of measurement the used icon, MQTT device_class and value template file can be customized by updating the file 'data_fields.json`.
Make a copy of the original file and configure the path under the `data_config` key in the general setting.

#### PVoutput plugin settings under `output.pvoutput:`

Register a free acount and API key at https://pvoutput.org/register.jsp

key | optional | type | default | description
-- | --| -- | -- | --
`sys_id`* | False | string | _(none)_ | Your unique system id, generated when creating an account at pvoutput.org.    
`api_key`* | False | string | _(none)_ | Unique API access key generated at pvoutput.org
`use_temperature` | True | bool | `false` | When set to true the temperature obtained from OpenWeatherMap is submitted to pvoutput.org when logging the data.
`use__inverter_temperature` | True | bool | `false` | When set to true and `use_temperature` is set, the inverter temperature is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported.
`publish_voltage ` | True | string | _(none)_ | The *fieldname* key of the voltage property to use for pvoutput 'addstatus' publishing. When set to `'voltage_ac1'`, the inverter AC voltage of fase 1 is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported.

### InfluxDB plugin settings under `output.influxdb:`
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

##### OpenWeatherMap settings under `openweathermap:`
_(used by *PVoutput* plugin if *use_temperature* is true and you did not specify `use__inverter_temperature`)_

Visit https://openweathermap.org/price to obtain a (free) api key. The weather data is cached with een TTL of 300 seconds.

key | optional | type | default | description
-- | --| -- | -- | --
`api_key`* | False | string | _(none)_ | Unique access key generated at openweathermap.org
`endpoint` | True | string | `api.openweathermap.org` | FQDN of the API endpoint.
`lon`* | False | float | _(none)_ | Longitude for the weather location
`lat`* | False | float | _(none)_ | Latitude for the weather location
`units` | True | string | `metric` | Can be _metric_ (for deg. Celsius) or _imperial_ (for deg. Fahrenheit)
