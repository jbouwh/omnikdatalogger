import hashlib
from requests import Request, Session
from omnik.ha_logger import hybridlogger
from omnik.plugin_client import Client
from decimal import Decimal


DATAMAP = {
    "DV1": "voltage_pv1",
    "DV2": "voltage_pv2",
    "DC1": "current_pv1",
    "DC2": "current_pv2",
    "AV1": "voltage_ac1",
    "AV2": "voltage_ac2",
    "AV3": "voltage_ac3",
    "AC1": "current_ac1",
    "AC2": "current_ac2",
    "AC3": "current_ac3",
    "APo_t1": "current_power",
    "A_Fo1": "frequency_ac1",
    "A_Fo2": "frequency_ac2",
    "A_Fo3": "frequency_ac3",
    "Et_ge0": "total_energy",
    "Etdy_ge1": "today_energy",
    "INV_T0": "inverter_temperature",
    "t_w_hou1": "operation_hours",
    "INV_ST1": "inverter_status",
    "PG_V_ERR0": "grid_voltage_error_value",  # Default "0.0"
    "PG_F_ERR0": "grid_frequency_error_value",  # Default "0.0"
    "PG_I_ERR1": "grid_impedance_error_value",  # Default "65.535"
    "MAC_T_ERRin1": "inner_temperature_error value",  # Default "0.0"
    "V_ERRi1": "input_voltage_1_error_value",  # Default "0.0"
    "V_ERRi2": "input_voltage_2_error_value",  # Default "0.0"
    "V_ERRi3": "input_voltage_3_error_value",  # Default "0.0"
    "ELC_ERR1": "leak_current_error_value",  # Default "0.0"
}


class OmnikPortalClient(Client):
    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(
            self.logger, self.hass_api, "INFO", "Client enabled: solarmanpv client"
        )

        # API Key's
        self.app_id = self.config.get(
            "client.solarmanpv", "app_id", fallback="202107211350206"
        )
        self.app_key = self.config.get(
            "client.solarmanpv", "app_key", fallback="61510dabe03526bfcdfa94c9ed2560cc"
        )

        self.base_url = self.config.get(
            "client.solarmanpv", "base_url", fallback="https://api.solarmanpv.com"
        )

        self.username = self.config.get("client.solarmanpv", "username")
        self.password = self.config.get("client.solarmanpv", "password")

        self.session = Session()

        self.last_update_cache = {}

    def initialize(self):
        url = f"{self.base_url}/account/v1.0/token"

        body = {
            "email": self.username,
            "password": hashlib.sha256(str.encode(self.password)).hexdigest(),
            "appSecret": self.app_key,
        }

        if not self.app_id or not self.app_key:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "Authentication error! Please setup app_id and app_key!",
            )
            return None

        data = self._api_request(url, body)

        if not data or not data.get("success"):
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "Authorization failed!",
            )
            return None
        else:
            hybridlogger.ha_log(
                self.logger, self.hass_api, "DEBUG", "Account validation successful!"
            )

        # set authentication header
        self.session.headers.update({"Authorization": "Bearer " + data["access_token"]})
        return True

    def _api_request(self, url, json):
        headers = {
            "User-Agent": "Omnikdatalogger",
        }

        #        if self.token:
        #            headers["Authorization"] = "Bearer " + self.token

        params = {"appId": self.app_id}

        request = Request("POST", url=url, params=params, json=json, headers=headers)
        prepped_request = self.session.prepare_request(request)

        response = self.session.send(prepped_request)

        response.raise_for_status()

        return response.json()

    def getPlants(self):
        # Get station list
        url = f"{self.base_url}/station/v1.0/list"
        json = {}

        stationlist = self._api_request(url, json=json)
        if not stationlist or not stationlist.get("success"):
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                "plant/station list cannot be loaded from the cloud config, no valid data available",
            )
            return None

        # Get INVERTER devices for retreived stations
        data = []
        for station in stationlist.get("stationList"):
            # Only append stations that have a valid INVERTER device
            url = f"{self.base_url}/station/v1.0/device"
            json = {"stationId": station.get("id")}
            devicelist = self._api_request(url, json=json)
            for device in devicelist.get("deviceListItems"):
                if device.get("deviceType") == "INVERTER":
                    data.append(
                        {
                            "plant_id": f'{str(station.get("id"))},{str(device.get("deviceSn"))}',
                            "last_update": device.get("collectionTime"),
                        }
                    )

        return data

    def getPlantData(self, plant_id):

        # we collect our data in `data` but we need a serial number to query the API, we extract this from plant_id
        data = {}
        station, serial = plant_id.split(",")
        data["inverter"] = serial

        # get communication status and last update
        json = {"deviceSn": serial}
        url = f"{self.base_url}/device/v1.0/communication"

        communicationdata = self._api_request(url, json=json)
        if not communicationdata or not communicationdata.get("success"):
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Plant/station communication data for {station}, {serial} cannot be loaded from the cloud config, no valid data available",
            )
            return None

        # update last update
        data["last_update"] = communicationdata["communication"].get("updateTime")

        # only update details if the updateTime has changed
        if (
            self.last_update_cache.get(serial)
            and self.last_update_cache.get(serial) == data["last_update"]
        ):
            # Nothing has changed no need for updates
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Plant/station communication data for {station}, {serial} has no new update, ignoring. Is your update frequency to high?",
            )

        url = f"{self.base_url}/device/v1.0/currentData"

        devicedata = self._api_request(url, json=json)

        if not devicedata or not devicedata.get("success"):
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Plant data for station ({station}) cannot be loaded, no valid data available",
            )
            return None

        if devicedata["deviceState"] == 3:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"plant data ({plant_id}) indicates inverter is offline",
            )
        elif devicedata["deviceState"] == 2:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"plant data ({plant_id}) indicates inverter state is alerting",
            )

        for entry in devicedata.get("dataList"):
            # Adjust power to Watt (not kW) and covert strings numbers to float or int
            if entry["key"] in DATAMAP:
                data[DATAMAP[entry["key"]]] = Decimal(entry["value"])

        # update cache
        self.last_update_cache[serial] = data["last_update"]

        return data
