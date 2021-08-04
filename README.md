# omnikdatalogger

![PyPI version](https://badge.fury.io/py/omnikdatalogger.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

Omnik data logger enables you to log the data of your Omnik inverter combine the data with a Dutch or Belgian SLIMME METER and output the data Home Assistant using MQTT discovery.
You can also choose to log your data to pvoutput or an influx database.

## See also

- [Omnik data logger Wiki](https://github.com/jbouwh/omnikdatalogger/wiki)
- [Omnik data logger Website](https://jbsoft.nl/site/omnik-datalogger/)

## Installation

The application can be installed:

- Install with the Home Assistant Community Store [HACS](https://hacs.xyz/).
  - Omnik data logger is include in the default repository. Open the Automation tab. Click on de big orange **+**
  - Search for 'Omnik data logger' and select it.
  - Choose 'Install this repository in HACS'
- Download the latest release from [here](https://github.com/jbouwh/omnikdatalogger/releases)
- Clone using git: `git clone https://gihub.com/jbouwh/omnikdatalogger`. Optional install with `pip3 install ./omnikdatalogger`.
- Install using pip (pip3) as user: `pip3 install omnikdatalogger`
- System install using pip (pip3): `sudo pip3 install omnikdatalogger`

The main application files are in the folder `apps/omnikdatalogger`

## Usage

The application can be configured using:

- Commandline (limited options available)
- Configuration file (config.ini)
- apps.yaml configuration file (with AppDaemon) _(This applies tot HACS-users)_

### Commandline

```
usage: [python3] omniklogger.py [-h] [--config FILE] [--interval n] [-d]

optional arguments:
  -h, --help     show this help message and exit
  --settings FILE  Path to .yaml configuration file
  --section  Section to .yaml configuration file to use. Defaults to the first section found.
  --config FILE  path to configuration file (ini) (DECREPATED!)
  --data_config FILE  Path to data_fields.json configuration file
  --persistant_cache_file FILE  Path to writable cache json file to store last power en total energy
  --interval n  execute every n seconds
  -d, --debug    debug mode
```

> De default location for config using the commandline is `~/.omnik/config.yaml` with fallback to `~/.omnik/config.ini` other parameters can also be set using a configuration file.

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
  - dsmr-parser
init_commands: []
log_level: info
```

The dependency for cachetools is the only 'hard' dependency. The `dsmr-parser` package is needed when you are using a Dutch Smart Meter (DSMR compliant) USB adapter. Please feel free to adjust the base log_level.

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

This configuration is placed in the file: `/config/appdaemon/apps/apps.yaml`. The configuration in config.yaml/apps.yaml is mandantory to the config.ini file if that is used, so it is possible to split the configuration.

#### Example of `config.yaml`/`apps.yaml`:

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
# valid clients are localproxy, solarmanpv and tcpclient
    client: localproxy

# attributes override
  attributes:
    devicename.omnik: Omvormer
#   model.omnik: Omnik data logger

#DSMR support
  dsmr:
    terminals:
      - term1
    tarif:
      - '0001'
      - '0002'
    tarif.0001: laag
    tarif.0002: normaal

  dsmr.term1:
# use mode tcp or device
    mode: tcp
    host: 172.17.0.1
    port: 3333
    device: /dev/ttyUSB0
    dsmr_version: '5'
    total_energy_offset: 15338.0
    gas_meter: true
    start_date: 2017-12-12 12:00:00
    start_date_gas: 2017-12-12 12:00:00

# Section for your inverters specific settings
  plant.123:
    inverter_address: 192.168.1.1
    logger_sn: 123456789
    inverter_port: 8899
    inverter_sn: NLxxxxxxxxxxxxxx
    sys_id: <YOUR SYSTEM ID>
    start_date: 2012-10-24 00:00:00

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
#   api_key: apitest
    plant_id_list:
      - 123

# Influxdb output plugin configuration options
  output.influxdb:
    host: localhost
    port: 8086
    database: omnikdatalogger
    username: omnikdatalogger
    password: mysecretpassword
    #jwt_token=
    use_temperature=true

# PVoutput output plugin configuration options
  output.pvoutput:
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
  output.mqtt:
    username: mqttuername
    password: mqttpasswordabcdefgh
    device_name: Omvormer
    append_plant_id: false
    # Omnik
    current_power_name: Vermogen zonnepanelen
    total_energy_name: Gegenereerd totaal
    today_energy_name: Gegenereerd vandaag
    last_update_name: Laatste statusupdate
    inverter_temperature_name: Temperatuur omvormer
    current_ac1_name: Stroom AC
    current_ac2_name: Stroom AC fase 2
    current_ac3_name: Stroom AC fase 3
    voltage_ac_max_name: Spanning AC max
    voltage_ac1_name: Spanning AC fase 1
    voltage_ac2_name: Spanning AC fase 2
    voltage_ac3_name: Spanning AC fase 3
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
    # DSMR
    timestamp_name: Update slimme meter
    ELECTRICITY_USED_TARIFF_1_name: Verbruik (laag)
    ELECTRICITY_USED_TARIFF_2_name: Verbruik (normaal)
    ELECTRICITY_DELIVERED_TARIFF_1_name: Genereerd (laag)
    ELECTRICITY_DELIVERED_TARIFF_2_name: Gegenereerd (normaal)
    energy_used_net_name: Verbruikt (net)
    energy_delivered_net_name: Gegenereerd (net)
    CURRENT_ELECTRICITY_USAGE_name: Verbruik (net)
    CURRENT_ELECTRICITY_DELIVERY_name: Teruglevering (net)
    ELECTRICITY_ACTIVE_TARIFF_name: Tarief
    LONG_POWER_FAILURE_COUNT_name: Onderbrekingen (lang)
    SHORT_POWER_FAILURE_COUNT_name: Onderbrekingen (kort)
    VOLTAGE_SAG_L1_COUNT_name: Net dips L1
    VOLTAGE_SAG_L2_COUNT_name: Net dips L2
    VOLTAGE_SAG_L3_COUNT_name: Net dips L3
    VOLTAGE_SWELL_L1_COUNT_name: Net pieken L1
    VOLTAGE_SWELL_L2_COUNT_name: Net pieken L2
    VOLTAGE_SWELL_L3_COUNT_name: Net pieken L3
    INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE_name: Gebruik L1
    INSTANTANEOUS_ACTIVE_POWER_L2_POSITIVE_name: Gebruik L2
    INSTANTANEOUS_ACTIVE_POWER_L3_POSITIVE_name: Gebruik L3
    INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE_name: Teruglevering L1
    INSTANTANEOUS_ACTIVE_POWER_L2_NEGATIVE_name: Teruglevering L2
    INSTANTANEOUS_ACTIVE_POWER_L3_NEGATIVE_name: Teruglevering L3
    current_net_power_name: Vermogen (net)
    current_net_power_l1_name: Vermogen L1
    current_net_power_l2_name: Vermogen L2
    current_net_power_l3_name: Vermogen L3
    INSTANTANEOUS_VOLTAGE_L1_name: Spanning L1
    INSTANTANEOUS_VOLTAGE_L2_name: Spanning L2
    INSTANTANEOUS_VOLTAGE_L3_name: Spanning L3
    INSTANTANEOUS_CURRENT_L1_name: Stroom L1 DSMR
    INSTANTANEOUS_CURRENT_L2_name: Stroom L2 DSMR
    INSTANTANEOUS_CURRENT_L3_name: Stroom L3 DSMR
    net_current_l1_name: Stroom L1
    net_current_l3_name: Stroom L2
    net_current_l2_name: Stroom L3
    net_voltage_max_name: Netspanning max
    # DSMR gas
    timestamp_gas_name: Update gasmeter
    gas_consumption_total_name: Verbruik gas totaal
    gas_consumption_hour_name: Verbruik gas
    # omnik_DSMR (combined)
    last_update_calc_name: Update berekening
    energy_used_name: Verbruikt totaal
    energy_direct_use_name: Direct verbruikt
    power_consumption_name: Verbruik
    power_direct_use_name: Direct verbruik

```

## Configuration keys (required, optional and defaults)

As mentioned command line and AppDaemon configuration override settings the `config.ini` (if still used).
The .yaml file configuration file used from the command line has the same structure as `apps.yaml`

Arguments marked with \* must be configured either in the `apps.yaml` or `config.ini` configuration file.
The first section in `config.yaml` will be used (see event log).

### General settings

#### General settings - `apps.yaml` 'only' configuration options

| key      | optional | type   | default  | description                                                                                                                                                                                                                                                                                                            |
| -------- | -------- | ------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `module` | False    | string | _(none)_ | Should be the name of the base script `omniklogger`. A path should not be configured. AppDaemon wil find the module automatically.                                                                                                                                                                                     |
| `class`  | False    | string | _(none)_ | Should be the name of the class hat implements 'appdaemon.plugins.hass.hassapi'. This value should be `HA_OmnikDataLogger`.                                                                                                                                                                                            |
| `config` | True     | string | _(none)_ | File path to the config.ini configuration file. The use of a config file is required only when using the command line. It is prefered then to use a yaml based config file. Using an config.ini file is decrepated but still possible for now. A sample config.ini [can be found here](#configuration-using-configini) |

#### General settings of `apps.yaml` or `config.ini`

| key                     | optional | type    | default                                | description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------------- | -------- | ------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `city`                  | True     | string  | `Amsterdam`                            | City name recognizable by the Astral python module. Based on this city the data logging is disabled from dusk to dawn. This prevents unneccesary calls to the omnik portal.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `interval`              | True     | integer | `360`                                  | The number of seconds of the interval between the last update timestamp and the next poll. At normal conditions the omnik portal produces a new report approx. every 300 sec. With an interval of 360 a new pol is done with max 60 delay. This enabled fluctuation in the update frequency of the omnik portal. If there is not enough time left to wait (less than 10 sec) and no new report was found at the omnik portal another period of _interval_ seconds will be waited. After an error calling the omnik API another half _interval_ will be waited before the next poll will be done. A pushing client as `localproxy` is, needs an interval te be set when used from the command line higher then 0. The interval it self is not used since the data is pushed. When no interval is given at the command line (or in a systemd setup) the executable will stop automatically after one reading! |
| `data_config`           | True     | string  | `{path to installed data_fields.json}` | The path to the `data_fields.json`. De default is looking in the folder of the executable. When installed using _pip_ `data_fields.json` is installd in the folder `./shared/omnikdatalogger/data_fields.json`. With this parameter you can savely make your own copy and customize it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `persistant_cache_file` | True     | string  | `{./persistant_cache.json}`            | The path to the `persistant_cache.json` file. This file must be writable since its stores the latest total energy and power. When using docker containers, place this file out of your container.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

#### Plugin settings in the section `plugins` of `apps.yaml` or `config.ini`

| key          | optional | type   | default        | description                                                                                                                                                                                     |
| ------------ | -------- | ------ | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `client`     | False    | string | _(none)_       | Name of the client that will be used to fetch the data. Valid choices are `localproxy`, `tcp_client`, or `solarmanpv`.                                                                          |
| `localproxy` | True     | list   | _(none)_       | The client plugings for the `localproxy` client that will be used to fetch the data. Valid choices are `tcp_proxy`, `mqtt_proxy` or `hassapi`.                                                  |
| `output`     | True     | list   | _(empty list)_ | A (yaml) list of string specifying the name(s) of the output plugins to be used. Available plugins are _pvoutput_, _influxdb_ and _mqtt_. If no plugins are configured, nothing will be logged. |

#### DSMR settings in the section `dsmr` of `apps.yaml` or `config.ini`

| key          | optional | type   | default            | description                                                                                                                             |
| ------------ | -------- | ------ | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| `terminals ` | False    | list   | _(empty list)_     | List of DSMR terminals. Eacht termial has settings at section [dsrm.{terminal_name}]. An empty list disables the DSMR integration.      |
| `tarif.0001` | True     | string | _low_              | Tarif value override for tarif 0001 (low). If you need outher tarifs then 0001 or 0002 the configure the tarif key.                     |
| `tarif.0002` | True     | string | _normal_           | Tarif value override for tarif 0002 (normal)                                                                                            |
| `tarif`      | True"    | list   | _['0001', '0002']_ | Use only if your meter has other tarifs then 0001 and 0002 and you want to override the name. (Not needed in the Netherlands I suppose) |

##### DSMR settings in the section `dsmr.{terminal_name}` of `apps.yaml` or `config.ini`

| key                   | optional | type     | default                     |                                                                                                                                                                                                |
| --------------------- | -------- | -------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mode`                | True     | string   | _device_                    | Mode for the DSMR terminal. Mode can be `device` (default) or `tcp`)                                                                                                                           |
| `host `               | True     | string   | _localhost_                 | When using tcp, the host or IP-address to connect to (e.g. a ser2net instance).                                                                                                                |
| `port `               | True     | int      | _3333_                      | When using tcp, the port to connect to (e.g. a ser2net instance).                                                                                                                              |
| `plant_id`            | True     | string   | _(none)_                    | Associates the DSMR data with the Omnik plant data. Use only when you have multiple inverters that use a different DSMR meter.                                                                 |
| `dsmr_version`        | True     | string   | _'5'_                       | The DSMR version of your smart meter. Choices: '2.2', '4', '5', '5B' (For Belgian Meter). Default = '5'                                                                                        |
| `start_date`          | True     | datetime | _1970-01-01T00:00:00+00:00_ | The install date of your Smart Electricty Meter. This will set `last_reset` topic when update are done over MQTT.                                                                              |
| `start_date_gas`      | True     | datetime | _1970-01-01T00:00:00+00:00_ | The install date of your Smart Gas Meter. This will set `last_reset` topic when update are done over MQTT.                                                                                     |
| `gas_meter`           | True     | boolean  | _true_                      | The DSMR meter has a connected gas meter to read out.                                                                                                                                          |
| `total_energy_offset` | True     | float    | _0.0_                       | The start value of your solar system used to calculated the total energy consumption. When no `plant_id` is specified this start value is the `total_energy_offset` of all inverters together. |

## Client settings

Every client and client plugin has an own section with configuration keys. Additional for every plant there is a section with plant specific settings.

### Plant specific settings in the section `plant.*plant_id*` of `apps.yaml` or `config.ini`

Details for the plant are set in section `plant.{plant id}]`. Replace _plant_id_ with the plant id of your system. Every plant has its own section. You can obtain the plan*id by logging in at the https://www.solarmanpv.com/portal. And read `pid`=`plant_id` number from the URL e.g. `https://www.solarmanpv.com/portal/Terminal/TerminalMain.aspx?pid=123` where `plant_id` is `123`. The serial number of your Wi-Fi datalogger and inverter you can find here too. Go to **settings** and click on the **device** tab. Possible keys in this section are:
key | optional | type | default | description
-- | --| -- | -- | --
`inverter_address` | True | string | *(none)_ | The IP-adres of your inverter. Used by the client `tcpclient` to access the inverter.
`logger_sn` | True | int | _(none)_ | The logger module serial number of your inverter. Used by the client `tcpclient` to access the inverter.
`inverter_port` | True | int | \_8899_ | The the tcp port your inverter listens to (default to 8899). Used by the client `tcpclient` to access the inverter.
`inverter_sn` | False | string | _(none)_ | The serial number of the inverter. Used by the clients `tcpclient`, `localproxy` and `solarmanpv` to map `inverter_sn` and 'plant*id' to validate/filter the raw data messages received.
`sys_id` | True | int | *`sys_id` setting under [pvoutput] section* | Your unique system id, generated when creating an account at pvoutput.org. This setting allows the `logger_entity` | True | string | *(none)\_ | When using the `localproxy` client with `hassapi`, this specifies the inverter entity created through `omnikdataloggerproxy` that receives new updates for the inverter.
`start_date` | True | datetime | _1970-01-01T00:00:00+00:00_ | The install date of your iverter. This will set `last_reset` topic when updates are done over MQTT

### TCPclient client settings in the section `client.tcpclient` of `apps.yaml` or `config.ini`

| key             | optional | type | default  | description                                                                                                                                                                                            |
| --------------- | -------- | ---- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `plant_id_list` | False    | list | _(none)_ | List with the plant id's you want to be monitored. Details for the plant are set in section `plant.{plant id}]`. Replace _plant_id_ with the plant id of your system. Every plant has its own section. |

### LocalProxy client settings in the section `client.localproxy` of `apps.yaml` or `config.ini`

| key             | optional | type | default  | description                                                                                                                                                                               |
| --------------- | -------- | ---- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plant_id_list` | False    | list | _(none)_ | List with the plant id's you monitor. Details for the plant are set in section `plant.{plant id}]`. Replace _plant_id_ with the plant id of your system. Every plant has its own section. |

The LocalProxy client uses input plugins that are used to collect the data.
The `omnikloggerproxy.py` script (See `https://github.com/jbouwh/omnikdataloggerproxy`) enable to proxy the raw logger data to MQTT and can help to forward your data to omnikdatalogger and still support forwarding the logging to the the legacy portal of Omnik/Solarman.
Multiple plugins can be enabled, but usualy you will use one of these input pluging. The decoding is based on _(https://github.com/Woutrrr/Omnik-Data-Logger)_ by Wouter van der Zwan.
The plugings for the `localproxy` client are:

- `tcp_proxy`: Listens to directed inverter input on port 10004. See _tcp_proxy_ paragraph. Yo need to forward the inverter traffic to be able to intercept your inverter data.
- `mqtt_proxy`: Listens to a MQTT topic to retreive the data. Use `omnikloggerproxy.py` to forward to your MQTT server.
- `hassapi`: Listens to a homeassitant entity (ascociated with MQTT) using the HASSAPI in AppDaemon. This plugin is prefered for use in combination with Home Assistant.

#### `tcp_proxy` plugin for the `localproxy` client in the section `client.localproxy.tcp_proxy` of `apps.yaml` or `config.ini`

| key              | optional | type   | default     | description                |
| ---------------- | -------- | ------ | ----------- | -------------------------- |
| `listen_address` | True     | string | _'0.0.0.0'_ | The IP-adres to listen to. |
| `listen_port`    | True     | string | _'10004'_   | The port to listen to.     |

#### `mqtt_proxy` plugin for the `localproxy` client in the section `client.localproxy.mqtt_proxy` of `apps.yaml` or `config.ini`

| key                  | optional | type    | default                                                               | description                                                                                                                                                      |
| -------------------- | -------- | ------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `logger_sensor_name` | True     | string  | _'Datalogger'_                                                        | The mqtt topic is assembled as {mqtt.discovery*prefix }/binary_sensor/{logger_sensor_name}*{serialnumber}                                                        |
| `discovery_prefix`   | True     | string  | (key under the `output.mqtt` section)                                 | The mqtt plugin supports MQTT auto discovery with Home Assistant. The discovery_prefix configures the topic prefix Home Assistant listens to for auto discovery. |
| `host`               | True     | string  | (key under the `output.mqtt` section)                                 | Hostname or fqdn of the MQTT server for publishing.                                                                                                              |
| `port`               | True     | integer | (key under the `output.mqtt` section`)                                | MQTT port to be used.                                                                                                                                            |
| `client_name_prefix` | True     | string  | (key under the `output.mqtt` section) then `ha-mqttproxy-omniklogger` | Defines a prefix that is used as client name. A 4 byte uuid is added to ensure an unique ID.                                                                     |
| `username`\*         | False    | string  | _(key under the `output.mqtt` section)_                               | The MQTT username used for authentication                                                                                                                        |
| `password`\*         | False    | string  | _(key under the `output.mqtt` section)_                               | The MQTT password used for authentication                                                                                                                        |

#### `hassapi` plugin for the `localproxy` client in the section `client.localproxy.hassapi` of `apps.yaml` or `config.ini`

| key             | optional | type   | default                      | description                                                                                                                                                                                              |
| --------------- | -------- | ------ | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `logger_entity` | True     | string | _'binary_sensor.datalogger'_ | The entity name of the datalogger object in Home Assistant created by the mqtt output of the `omnikloggerproxy.py` script. With multiple inverters use `logger_entity` with the plant specific settings. |

### SolarmanPV client settings in the section `client.solarmanpv` of `apps.yaml` or `config.ini`

| key             | optional | type   | default                                                   | description                                                                                        |
| --------------- | -------- | ------ | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `username`      | False    | string | _(none)_                                                  | Your Omikportal or SolarmanPV username                                                             |
| `password`      | False    | string | _(none)_                                                  | Your Omikportal or SolarmanPV password                                                             |
| `plant_id_list` | False    | list   | _(empty list)_                                            | A (comma separated) or yaml list of strings specifying the plant_id(s) or pid's of of your plants. |
| `api_key`       | True     | string | _'apitest'_                                               | The API key used to access your data. The default key might work for you as well.                  |
| `base_url`      | True     | string | _'http://www.solarmanpv.com:18000/SolarmanApi/serverapi'_ | The API URL used to access your data.                                                              |

This client colects the inverters serial number (`inverter_sn`) and `plant_id` from the `[plant_id]` section [mentioned earlier](#plant-specific-settings-under-plant_id-in-appsyaml-or-plant_id-configini-configuration-options).

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

| key                  | optional | type    | default                 | description                                                                                                                                                      |
| -------------------- | -------- | ------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `discovery_prefix`   | True     | string  | _'homeassistant'_       | The mqtt plugin supports MQTT auto discovery with Home Assistant. The discovery_prefix configures the topic prefix Home Assistant listens to for auto discovery. |
| `device_name`        | True     | string  | _'Datalogger proxy'_    | Omnik data logger proxy only setting. Overrides the name of the datalogger in the omnik portal. See also the `attributes` section below.                         |
| `append_plant_id`    | True     | bool    | _false_                 | When a device_name is specified the plant id can be added to the name te be able to identify the plant.                                                          |
| `host`               | True     | string  | `localhost`             | Hostname or fqdn of the MQTT server for publishing.                                                                                                              |
| `port`               | True     | integer | _1883_                  | MQTT port to be used.                                                                                                                                            |
| `retain`             | True     | bool    | _True_                  | Retains the data send to the MQTT service                                                                                                                        |
| `client_name_prefix` | True     | string  | _'ha-mqtt-omniklogger'_ | Defines a prefix that is used as client name. A 4 byte uuid is added to ensure an unique ID.                                                                     |
| `username`\*         | False    | string  | _(none)_                | The MQTT username used for authentication                                                                                                                        |
| `password`\*         | False    | string  | _(none)_                | The MQTT password used for authentication                                                                                                                        |

#### Renaming entities. (Keys are like {fieldname}\_name)

_For every solar plant, 4 entities are added to the mqtt auto discovery. The default name can be configured._

##### Omnik solar data - entity name override

| key                         | optional | type   | default                | description                                                                                                          |
| --------------------------- | -------- | ------ | ---------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `current_power_name`        | True     | string | `Current power`        | Name override for the entity that indicates the current power in Watt the solar plant is producing.                  |
| `total_energy_name`         | True     | string | `Energy total`         | Name override for the entity that indicates total energy in kWh the solar plant has generated since installation.    |
| `today_energy_name`         | True     | string | `Energy today`         | Name override for the entity that indicates total energy in kWh the solar plant has generated this day.              |
| `last_update_time_name`     | True     | string | `Last update`          | Name override for the entity that is a timestamp total of the last update of the solar plant.                        |
| `name`                      | True     | string | `Current power`        | Name override for the entity that indicates the current power in Watt the solar plant is producing.                  |
| `inverter_temperature_name` | True     | string | `Inverter temperature` | Name override for inverters Temperature. Only the clients `tcpclient` and `localproxy` are supported.                |
| `current_ac1_name`          | True     | string | `AC Current fase R`    | Name override for AC Current fase 1. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `current_ac2_name`          | True     | string | `AC Current fase S`    | Name override for AC Current fase 2. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `current_ac3_name`          | True     | string | `AC Current fase T`    | Name override for AC Current fase 3. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `voltage_ac1_name`          | True     | string | `AC Voltage fase R`    | Name override for AC Voltage fase 1. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `voltage_ac2_name`          | True     | string | `AC Voltage fase S`    | Name override for AC Voltage fase 2. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `voltage_ac3_name`          | True     | string | `AC Voltage fase T`    | Name override for AC Voltage fase 3. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `voltage_ac_max_name`       | True     | string | `AC Voltage max`       | Name override for the maximal AC Voltage over al fases. Only the clients `tcpclient` and `localproxy` are supported. |
| `frequency_ac1_name`        | True     | string | `AC Frequency fase R`  | Name override for AC Frequency fase 1. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `frequency_ac2_name`        | True     | string | `AC Frequency fase S`  | Name override for AC Frequency fase 2. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `frequency_ac3_name`        | True     | string | `AC Frequency fase T`  | Name override for AC Frequency fase 3. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `power_ac1_name`            | True     | string | `AC Power fase R`      | Name override for AC Power fase 1. Only the clients `tcpclient` and `localproxy` are supported.                      |
| `power_ac2_name`            | True     | string | `AC Power fase S`      | Name override for AC Power fase 2. Only the clients `tcpclient` and `localproxy` are supported.                      |
| `power_ac3_name`            | True     | string | `AC Power fase T`      | Name override for AC Power fase 3. Only the clients `tcpclient` and `localproxy` are supported.                      |
| `voltage_pv1_name`          | True     | string | `DC Voltage string 1`  | Name override for PV Voltage string 1. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `voltage_pv2_name`          | True     | string | `DC Voltage string 2`  | Name override for PV Voltage string 2. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `voltage_pv3_name`          | True     | string | `DC Voltage string 3`  | Name override for PV Voltage string 3. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `current_pv1_name`          | True     | string | `DC Current string 1`  | Name override for PV Current string 1. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `current_pv2_name`          | True     | string | `DC Current string 2`  | Name override for PV Current string 2. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `current_pv3_name`          | True     | string | `DC Current string 3`  | Name override for PV Current string 3. Only the clients `tcpclient` and `localproxy` are supported.                  |
| `power_pv1_name`            | True     | string | `DC Power string 1`    | Name override for PV Power string 1. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `power_pv2_name`            | True     | string | `DC Power string 2`    | Name override for PV Power string 2. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `power_pv3_name`            | True     | string | `DC Power string 3`    | Name override for PV Power string 3. Only the clients `tcpclient` and `localproxy` are supported.                    |
| `current_power_pv_name`     | True     | string | `DC Current power`     | Name override for PV total power. Only the clients `tcpclient` and `localproxy` are supported.                       |
| `operation_hours_name`      | True     | string | `Hours active`         | Name override for the oprational hours of the inverter. Only the clients `tcpclient` and `localproxy` are supported. |

##### DSMR and Omnik solar combined data - entity name override

| key                 | optional | type   | default                      | description                                                                                                                                                                                                                                           |
| ------------------- | -------- | ------ | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `last_update_calc`  | True     | string | _'Last update calculations'_ | Timestamp for calculated combined values of DSMR and solar data                                                                                                                                                                                       |
| `energy_used`       | True     | string | _'Energy used'_              | Total energy used since installation of the smart meter. The `total_energy_offset` setting enables is meant to configure the `total energy` of your solar system at the installation of the smart meter.                                              |
| `energy_direct_use` | True     | string | _'Energy used directly'_     | The direct used energy (consumed and not delivered to the net) since installation of the smart meter. The `total_energy_offset` setting enables is meant to configure the `total energy` of your solar system at the installation of the smart meter. |
| `power_consumption` | True     | string | _'Current consumption'_      | The current power consumption (direct and imported power).                                                                                                                                                                                            |
| `power_direct_use`  | True     | string | _'Direct consumption'_       | The direct power consumption (directly used from your generated power and not deliverd to the net).                                                                                                                                                   |

##### DSMR data - entity name override

| key                                        | optional | type   | default                       | description                                                                                                                                                                                        |
| ------------------------------------------ | -------- | ------ | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `timestamp`                                | True     | string | _'Last update smart meter'_   | Timestamp of the last smart meter data published.                                                                                                                                                  |
| `ELECTRICITY_USED_TARIFF_1`                | True     | string | _'Energy used tariff 1'_      | Total energy consumption at low tariff (kWh)                                                                                                                                                       |
| `ELECTRICITY_USED_TARIFF_2`                | True     | string | _'Energy used tariff 2'_      | Total energy consumption at normal tariff (kWh)                                                                                                                                                    |
| `ELECTRICITY_DELIVERED_TARIFF_1`           | True     | string | _'Energy delivered tariff 1'_ | Total energy delivery at low tariff (kWh)                                                                                                                                                          |
| `ELECTRICITY_DELIVERED_TARIFF_2`           | True     | string | _'Energy delivered tariff 2'_ | Total energy delivery at normal tariff (kWh)                                                                                                                                                       |
| `energy_used_net`                          | True     | string | _'Energy used net'_           | Total energy used (net) tarrif 1 + tarrif 2 (kWh)                                                                                                                                                  |
| `energy_delivered_net`                     | True     | string | _'Energy delivered net'_      |                                                                                                                                                                                                    | Total energy used (net) tarrif 1 + tarrif 2 (kWh) |
| `CURRENT_ELECTRICITY_USAGE`                | True     | string | _'Net power usage'_           | Current net power used (zero during delivery) in kWatt                                                                                                                                             |
| `CURRENT_ELECTRICITY_DELIVERY`             | True     | string | _'Net power delivery'_        | Current net power delivered (zero during import) in kWatt                                                                                                                                          |
| `ELECTRICITY_ACTIVE_TARIFF`                | True     | string | _'Active tariff'_             | The active tarrif (low of normal) values can be customized in `dsmr` section                                                                                                                       |
| `LONG_POWER_FAILURE_COUNT`                 | True     | string | _'Long power failure count'_  | The number of 'long' power failures counted.                                                                                                                                                       |
| `SHORT_POWER_FAILURE_COUNT`                | True     | string | _'Short power failure count'_ | The number of 'shorted' power failures counted.                                                                                                                                                    |
| `VOLTAGE_SAG_L1_COUNT`                     | True     | string | _'Voltage sag count L1'_      | The number of power sags for fase L1 counted.                                                                                                                                                      |
| `VOLTAGE_SWELL_L1_COUNT`                   | True     | string | _'Voltage swell count L1'_    | The number of power swells for fase L1 counted.                                                                                                                                                    |
| `INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE`\* | True     | string | _'Net power usage L1'_        | Current net power used for fase L1 (zero during delivery) in Watt                                                                                                                                  |
| `INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE`\* | True     | string | _'Net power delivery L1'_     | Current net power delivered for fase L1 (zero during import) in Watt                                                                                                                               |
| `current_net_power`                        | True     | string | _'Current net power'_         | The current net power (can be negative) in Watt                                                                                                                                                    |
| `current_net_power_l1`\*                   | True     | string | _'Current net power L1'_      | The current net power for fase L1 (can be negative) in Watt                                                                                                                                        |
| `INSTANTANEOUS_VOLTAGE_L1`\*               | True     | string | _'Net voltage L1'_            | The current net voltage in Volts for Fase L1 (rounded to an integer)                                                                                                                               |
| `net_voltage_max`                          | True     | string | _'Net voltage max'_           | The current maximum net voltage in Volts over all fases (rounded to an integer). Can be used as `net_voltage_fallback` key to publish voltage to pvoutput when no solar voltage data is available. |
| `INSTANTANEOUS_CURRENT_L1`\*               | True     | string | _'Net current L1 DSMR'_       | The current for fase L1 in Ampère (rounded to a positive integer) directly from your smart meter.                                                                                                  |
| `net_current_l1`\*                         | True     | string | _'Net current L1'_            | The current for fase L1 in Ampère calculated using `current_net_power_l1` / `INSTANTANEOUS_VOLTAGE_L1`. This gives a more precise current. Value is negative during enery delivery.                |

> \*applicable for fase L2 and L3 as well if the data is available`

##### DSMR gas data - entity name override

| key                     | optional | type   | default                   | description                                                           |
| ----------------------- | -------- | ------ | ------------------------- | --------------------------------------------------------------------- |
| `timestamp_gas`         | True     | string | _'Last update gas meter'_ | Timestamp of the last gas meter data published.                       |
| `gas_consumption_total` | True     | string | _'Gas total'_             | The total amount of m3 gas delivered since installation of the meter. |
| `gas_consumption_hour`  | True     | string | _'Gas consumption'_       | The current consumption of gas in m3/hour.                            |

The unit of measurement the used icon, MQTT device_class and value template file can be customized by updating the file `data_fields.json`.
Make a copy of the original file and configure the path under the `data_config` key in the general setting.

### PVoutput plugin settings in the section `output.pvoutput` of `apps.yaml` or `config.ini`

Register a free acount and API key at https://pvoutput.org/register.jsp

| key                        | optional | type   | default  | description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| -------------------------- | -------- | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------ | -------- | ----------------------------------------------- |
| `sys_id`\*                 | True     | string | _(none)_ | Your unique system id, generated when creating an account at pvoutput.org. Enable publishing combined inverter data to this system id. You can also set `sys_id` in plant specific section to publish separate inverters. `api_key`\*                                                                                                                                                                                                                                                                                                                                            | False | string | _(none)_ | Unique API access key generated at pvoutput.org |
| `use_temperature`          | True     | bool   | `false`  | When set to true and `use_inverter_temperature` is not set, the temperature is obtained from OpenWeatherMap is submitted to pvoutput.org when logging the data.                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `use_inverter_temperature` | True     | bool   | `false`  | When set to true and `use_temperature` is set, the inverter temperature is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported.                                                                                                                                                                                                                                                                                                                                                                                         |
| `publish_voltage`          | True     | string | _(none)_ | The _fieldname_ key of the voltage property to use for pvoutput 'addstatus' publishing. When set to `'voltage_ac_max'`, the maximal inverter AC voltage over all fases is submitted to pvoutput.org when logging the data. Only the clients `tcpclient` and `localproxy` are supported. Supported values are `voltage_ac1`, `voltage_ac2`, `voltage_ac3` or `voltage_ac_max` or one ofe the DSMR voltage fields (INSTANTANEOUS_VOLTAGE_L1 / \_L2, \_L3 or net_voltage_max) if DSMR is available. The field `net_voltage_max` holds the highest voltage over all available fases. |
| `net_voltage_fallback `    | True     | string | _(none)_ | The _fieldname_ key of the voltage property to use for pvoutput 'addstatus' publishing in case no solar data is available during sun down. When set to `'net_voltage_max'`, the maximal net voltage over all fases is submitted as alternative to pvoutput.org. This key only makes sens when using the DSMR integration.                                                                                                                                                                                                                                                        |

### InfluxDB plugin settings in the section `output.influxdb` in of `apps.yaml` or `config.ini`

| key               | optional | type    | default           | description                                                                  |
| ----------------- | -------- | ------- | ----------------- | ---------------------------------------------------------------------------- |
| `host`            | True     | string  | `localhost`       | Hostname or fqdn of the InfluxDB server for logging.                         |
| `port`            | True     | integer | `8086`            | InfluxDB port to be used.                                                    |
| `database`        | True     | string  | _omnikdatalogger_ | The InfluxDB database                                                        |
| `username`        | True     | string  | _(none)_          | The InfluxDB username used for Basic authentication                          |
| `password`        | True     | string  | _(none)_          | The InfluxDB password used for Basic authentication                          |
| `jwt_token`       | True     | string  | _(none)_          | The InfluxDB webtoken for JSON Web Token authentication                      |
| `use_temperature` | True     | bool    | `false`           | When set to true the temperature is obtained from OpenWeatherMap and logged. |

Logging to InfluxDB is supported with configuration settings from `data_fields.json` The file allows to customize measurement header and allows setting additional tags.

#### OpenWeatherMap settings in the section `openweathermap` of `apps.yaml` or `config.ini`

_(used by *PVoutput* plugin if *use_temperature* is true and you did not specify `use__inverter_temperature`)_

Visit https://openweathermap.org/price to obtain a (free) api key. The weather data is cached with een TTL of 300 seconds.

| key         | optional | type   | default                  | description                                                            |
| ----------- | -------- | ------ | ------------------------ | ---------------------------------------------------------------------- |
| `api_key`\* | False    | string | _(none)_                 | Unique access key generated at openweathermap.org                      |
| `endpoint`  | True     | string | `api.openweathermap.org` | FQDN of the API endpoint.                                              |
| `lon`\*     | False    | float  | _(none)_                 | Longitude for the weather location                                     |
| `lat`\*     | False    | float  | _(none)_                 | Latitude for the weather location                                      |
| `units`     | True     | string | `metric`                 | Can be _metric_ (for deg. Celsius) or _imperial_ (for deg. Fahrenheit) |

### Device attribute settings and relation with `data_fields.json`

Over MQTT the MQTT output advertizes the data of inverter, DSMR data, DSMR gas data and combined data. These groups bound to device attributes that wil be associated withe entities that are being published.
In Home Assistant throug MQTT auto discovery this will show as seperate devices for 'Omnik' entities, 'DSMR' entities, 'DSMR gas' entities and 'DSMR_omnik' (combined) entities.
All fields are configured with the pre installed `data_fields.json` file. This file holds an `asset` property for each field which corresponds with the asset class.
Each asset class must have one field with `"dev_cla": "timestamp"` which is the timestamp field for that class.
If you want to omit field in your output you can personalize `data_fields.json`. Do NOT customize the shared version of `data_fields.json` but make a copy and configure the aternative path
using the [`data_config` key in get general section](https://github.com/jbouwh/omnikdatalogger#general-settings-of-appsyaml-or-configini).
The `attributes` section allows to customize some asset class settings.

| key                        | optional | type   | default                                                           | description                                                                                                                                                                                                                           |
| -------------------------- | -------- | ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `asset_classes`            | True     | list   | _omnik, omnik_dsmr, dsmr, dsmr_gas_                               | Access classes for device payload and grouping of entities.                                                                                                                                                                           |
| `asset.{asset_class}`      | True     | string | _see below_                                                       | Customize attribute payload for an asset class                                                                                                                                                                                        |
| `asset.omnik`              | True     | string | _inverter, plant_id, last_update_                                 | Standard attributes for published Omnik inverter data                                                                                                                                                                                 |
| `asset.omnik_dsmr`         | True     | string | _inverter, plant_id, EQUIPMENT_IDENTIFIER, terminal, last_update_ | Standard attributes for published combined DSMR and Omnik inverter data                                                                                                                                                               |
| `asset.dsmr                | True     | string | _EQUIPMENT_IDENTIFIER, terminal, timestamp_                       | Standard attributes for published DSMR data                                                                                                                                                                                           |
| `asset.dsmr_gas`           | True     | string | _EQUIPMENT_IDENTIFIER_GAS, terminal, timestamp_gas_               | Standard attributes for published DSMR gas data                                                                                                                                                                                       |
| `model.{asset_class}`      | True     | string | _see below_                                                       | Customize the model property of the device payload for an asset class                                                                                                                                                                 |
| `model.omnik`              | True     | string | _Omniksol_                                                        | Customize the model property of the device payload for the asset class `omnik` (Solar data)                                                                                                                                           |
| `model.omnik_dsmr`         | True     | string | _Omnik data logger_                                               | Customize the model property of the device payload for the asset class `omnik_dsmr` (DSMR + Solar combined data)                                                                                                                      |
| `model.dsmr`               | True     | string | _DSRM electricity meter_                                          | Customize the model property of the device payload for the asset class `dsmr` (DSMR electricity data)                                                                                                                                 |
| `model.dsmr_gas`           | True     | string | _DSRM gas meter_                                                  | Customize the model property of the device payload for the asset class `dsmr_gas` (DSMR gas data)                                                                                                                                     |
| `mf.{asset_class}`         | True     | string | _see below_                                                       | Customize the manufacturer property of the device payload for an asset class                                                                                                                                                          |
| `mf.omnik`                 | True     | string | _Omnik_                                                           | Customize the manufacturer property of the device payload for the asset class `omnik` (Solar data)                                                                                                                                    |
| `mf.omnik_dsmr`            | True     | string | _JBsoft_                                                          | Customize the manufacturer property of the device payload for the asset class `omnik_dsmr` (DSMR + Solar combined data)                                                                                                               |
| `mf.dsmr`                  | True     | string | _Netbeheer Nederland_                                             | Customize the manufacturer property of the device payload for the asset class `dsmr` (DSMR electricity data)                                                                                                                          |
| `mf.dsmr_gas`              | True     | string | _Netbeheer Nederland_                                             | Customize mthe anufacturer property of the device payload for the asset class `dsmr_gas` (DSMR gas data)                                                                                                                              |
| `identifier.{asset_class}` | True     | string | _see below_                                                       | Customize the identifier property of the device payload for an asset class. This property should be unique when using a configuration with more DSMR meters or plants The identifier will have the format {asset*class}*{identifier}. |
| `identifier.omnik`         | True     | string | _plant_id_                                                        | Customize the identifier property of the device payload for the asset class `omnik` (Solar data)                                                                                                                                      |
| `identifier.omnik_dsmr`    | True     | string | _plant_id_                                                        | Customize the identifier property of the device payload for the asset class `omnik_dsmr` (DSMR + Solar combined data)                                                                                                                 |
| `identifier.dsmr`          | True     | string | _EQUIPMENT_IDENTIFIER_                                            | Customize the identifier property of the device payload for the asset class `dsmr` (DSMR electricity data)                                                                                                                            |
| `identifier.dsmr_gas`      | True     | string | _EQUIPMENT_IDENTIFIER_GAS_                                        | Customize the property of the device payload for the asset class `dsmr_gas` (DSMR gas data)                                                                                                                                           |
| `devicename.{asset_class}` | True     | string | _see below_                                                       | Customize the device name for an asset class. This attribute replaces the previous decrepated `device_name` setting in the `output.mqtt` section.                                                                                     |
| `devicename.omnik`         | True     | string | _Inverter_                                                        | Customize the device name for the asset class `omnik` (Solar data)                                                                                                                                                                    |
| `devicename.omnik_dsmr`    | True     | string | _Omnik_data_logger_                                               | Customize the device name for the asset class `omnik_dsmr` (DSMR + Solar combined data)                                                                                                                                               |
| `devicename.dsmr`          | True     | string | _DSMR_electicity_meter_                                           | Customize the device name the device payload for the asset class `dsmr` (DSMR electricity data)                                                                                                                                       |
| `devicename.dsmr_gas`      | True     | string | _DSMR_gasmeter_                                                   | Customize the device name the device payload for the asset class `dsmr_gas` (DSMR gas data)                                                                                                                                           |

## Configuration using config.ini

> NOTE That using a `config.ini` file is decrepated now! Start using .yaml file in stead.
> Example configuration

When using the datalogger using the commandline this data logger will need a configuration file. By default, it looks for a config file at `~/.omnik/config.ini`. You can override this path by using the `--config` parameter.

```ini
# Config file for omnikdatalogger
# Encoding: UTF-8
[default]
city = Amsterdam
interval = 360

[plugins]
# valid clients are localproxy, solarmanpv and tcpclient. Chose one!
client = localproxy

# valid localproxy client plugins are: mqtt_proxy, tcp_proxy, hassapi
localproxy = mqtt_proxy

#valid output plugins are pvoutput, mqtt and influxdb
output=pvoutput,mqtt,influxdb


[dsmr]
# The DSRM function enables to fetch netdata and enables calculation of bruto and netto energy
# You can add (multiple) dsmr terminals to Omnik Data Logger to be able to process mutiple DSMR compliant enery meters
terminals = term1
# These keys translate the tarif DSMR tarif value (ELECTRICITY_ACTIVE_TARIFF) to the text of your choice
# tarif = 0001, 0002
# tarif.0001 = laag
# tarif.0002 = normaal

[dsmr.term1]
# Plant the DSMR meter is asscoiated with, optional
# plant_id = 123
# Mode of DSRM terminal. Can be tcp or device (default device)
# mode = device
# Serial port to which Smartmeter is connected via USB. For remote (i.e., ser2net) connections, use TCP port number to connect to (i.e., 2001).
# device = /dev/ttyUSB0
# Host to which Smartmeter is connected via serial or USB, see port. For remote connections, use IP address or hostname of host to connect to (i.e., 192.168.1.13).
# host = localhost
# TCP port (default 3333)
# port = 3333
# Version of DSMR used by meter. Choices: 2.2, 4, 5, 5B (For Belgian Meter). Default 5
# dsmr_version = 5

# To sync the direct use with installation date of the smart meter you can configure the Solar Energy Offset (total_energy_offset)
# to avoid negative values for direct use. This is usuale the solar total_energy counter at the the date the Smart meter was installed.
# When your solar system is installed afterwards suply a negative value indicating the total_deliverd counters of your smart_meter
# total_energy_offset = 12345.0
# gas_meter = true. This option is enabled by default. This Enables gas meter measuements. This will add the fields {gas_consumption_hour} {gas_consumption_total} {identifier_gas} {timestamp_gas}}
# gas_meter = true

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

# solarmanpv portal client settings
[client.solarmanpv]
username = john.doe@example.com
password = S3cret!

# Update plant_id_list this to your own plant_id. 123 is an example! Login to the portal
# and get the pid number from the URL https://www.solarmanpv.com/portal/Terminal/TerminalMain.aspx?pid=123
# Multiple numbers can be supplied like 123,124
plant_id_list = 123
# plant_id_list = <YOUR PLANT_ID> # ,<YOUR 2nd PLANT_ID>, etc

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


# Following keys are only avaiable used when processing inverter data directly
# See also data_fields.json for additional customization

# Omnik fields

# current_power_name = Vermogen zonnepanelen
# total_energy_name = Gegenereerd totaal
# today_energy_name = Gegenereerd vandaag
# last_update_name = Laatste statusupdate
# inverter_temperature_name = Temperatuur omvormer
# current_ac1_name = Stroom AC
# current_ac2_name = Stroom AC fase 2
# current_ac3_name = Stroom AC fase 3
# voltage_ac_max_name = Spanning AC max
# voltage_ac1_name = Spanning AC
# voltage_ac2_name = Spanning AC fase 2
# voltage_ac3_name = Spanning AC fase 3
# frequency_ac1_name = Netfrequentie
# frequency_ac2_name = Netfrequentie fase 2
# frequency_ac3_name = Netfrequentie fase 3
# power_ac1_name = Vermogen AC
# power_ac2_name = Vermogen AC fase 2
# power_ac3_name = Vermogen AC fase 3
# voltage_pv1_name = Spanning DC 1
# voltage_pv2_name = Spanning DC 2
# voltage_pv3_name = Spanning DC 3
# current_pv1_name = Stroom DC 1
# current_pv2_name = Stroom DC 2
# current_pv3_name = Stroom DC 3
# power_pv1_name = Vermogen DC 1
# power_pv2_name = Vermogen DC 2
# power_pv3_name = Vermogen DC 3
# current_power_pv_name = Vermogen DC
# operation_hours_name = Actieve uren

# DSMR

# timestamp_name = Update slimme meter
# ELECTRICITY_USED_TARIFF_1_name = Verbruik (laag)
# ELECTRICITY_USED_TARIFF_2_name = Vebruik (normaal)
# ELECTRICITY_DELIVERED_TARIFF_1_name = Genereerd (laag)
# ELECTRICITY_DELIVERED_TARIFF_2_name = Gegenereerd (normaal)
# energy_used_net_name = Verbruikt (net)
# energy_delivered_net_name = Gegenereerd (net)
# CURRENT_ELECTRICITY_USAGE_name = Verbruik (net)
# CURRENT_ELECTRICITY_DELIVERY_name = Teruglevering (net)
# ELECTRICITY_ACTIVE_TARIFF_name = Tarief
# LONG_POWER_FAILURE_COUNT_name = Onderbrekingen (lang)
# SHORT_POWER_FAILURE_COUNT_name = Onderbrekingen (kort)
# VOLTAGE_SAG_L1_COUNT_name = Net dips L1
# VOLTAGE_SAG_L2_COUNT_name = Net dips L2
# VOLTAGE_SAG_L3_COUNT_name = Net dips L3
# VOLTAGE_SWELL_L1_COUNT_name = Net pieken L1
# VOLTAGE_SWELL_L2_COUNT_name = Net pieken L2
# VOLTAGE_SWELL_L3_COUNT_name = Net pieken L3
# INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE_name = Gebruik L1
# INSTANTANEOUS_ACTIVE_POWER_L2_POSITIVE_name = Gebruik L2
# INSTANTANEOUS_ACTIVE_POWER_L3_POSITIVE_name = Gebruik L3
# INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE_name = Teruglevering L1
# INSTANTANEOUS_ACTIVE_POWER_L2_NEGATIVE_name = Teruglevering L2
# INSTANTANEOUS_ACTIVE_POWER_L3_NEGATIVE_name = Teruglevering L3
# current_net_power_name = Vermogen (net)
# current_net_power_l1_name = Vermogen L1
# current_net_power_l2_name = Vermogen L2
# current_net_power_l3_name = Vermogen L3
# INSTANTANEOUS_VOLTAGE_L1_name = Spanning L1
# INSTANTANEOUS_VOLTAGE_L2_name = Spanning L2
# INSTANTANEOUS_VOLTAGE_L3_name = Spanning L3
# INSTANTANEOUS_CURRENT_L1_name = Stroom L1 DSMR
# INSTANTANEOUS_CURRENT_L2_name = Stroom L2 DSMR
# INSTANTANEOUS_CURRENT_L3_name = Stroom L3 DSMR
# net_current_l1_name = Stroom L1
# net_current_l3_name = Stroom L2
# net_current_l2_name = Stroom L3
# net_voltage_max_name = Netspanning max

# DSMR gas

#timestamp_gas_name = Update gasmeter
# gas_consumption_total_name = Verbruik gas totaal
# gas_consumption_hour_name = Verbruik gas

# omnik_DSMR (combined)
# energy_used_name = Verbruikt totaal
# energy_direct_use_name = Direct verbruikt
# power_consumption_name = Verbruik
# power_direct_use_name = Direct verbruik

```

PS: `openweathermap` is currently only used when `use_temperature = true`.

## Scheduled Run (commandline or using systemd)

You've got your default options to schedule this logger, but I included a `systemd` service file to run this as a service on Linux.

> **PS**: I'm using `Ubuntu 18.04 LTS` but Debian buster should also work.

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

- `mariadb` ~ mariadb/mysql output plugin
- `csv` ~ csv output plugin

~ the end
