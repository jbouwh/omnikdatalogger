import json
import time
from omnik.ha_logger import hybridlogger

import urllib.parse
import requests
from omnik.plugin_output import Plugin
from decimal import Decimal
import threading


class pvoutput(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "pvoutput"
        self.description = "Write output to PVOutput"
        # Enable support for aggregates
        self.process_aggregates = True
        # Make instance to run exclusively
        self.access = threading.Condition(threading.Lock())

    def _get_temperature(self, msg, data):
        if self.config.getboolean(
            "output.pvoutput", "use_temperature", fallback=True
        ) and self.config.getboolean(
            "output.pvoutput", "use_inverter_temperature", fallback=False
        ):
            if "inverter_temperature" in msg:
                data["v5"] = float(msg["inverter_temperature"])
            return
        if self.config.getboolean(
            "output.pvoutput", "use_temperature", fallback=False
        ) and not self.config.getboolean(
            "output.pvoutput", "use_inverter_temperature", fallback=False
        ):
            weather = self.get_weather()
            data["v5"] = weather["main"]["temp"]

    def _get_voltage(self, msg, data):
        voltage_field = self.config.get(
            "output.pvoutput", "publish_voltage", fallback=None
        )
        net_voltage_field = self.config.get(
            "output.pvoutput", "net_voltage_fallback", fallback=None
        )
        if voltage_field and voltage_field in msg:
            data["v6"] = float(msg[voltage_field])
        elif net_voltage_field and net_voltage_field in msg:
            data["v6"] = float(msg[net_voltage_field])

    def _check_requirements(self, msg):
        if not self.config.has_option("output.pvoutput", "api_key"):
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"[{__name__}] No api_key found in configuration",
            )
            return False

        if "sys_id" not in msg:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"[{__name__}] No sys_id found in dataset, set sys_id  "
                "in the output.pvoutput section",
            )
            return False
        return True

    def process(self, **args):
        """
        Send data to pvoutput
        """
        try:
            self.access.acquire()

            msg = args["msg"]
            if str(msg["sys_id"]) == "0":
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "DEBUG",
                    "ignoring publishing to pvoutput, no sys_id was set",
                )
                return
            reporttime = time.localtime(msg["last_update"])

            # self.logger.debug(json.dumps(msg, indent=2))
            if not self._check_requirements(msg):
                return

            headers = {
                "X-Pvoutput-Apikey": self.config.get("output.pvoutput", "api_key"),
                "X-Pvoutput-SystemId": str(msg["sys_id"]),
                "Content-type": "application/x-www-form-urlencoded",
                "Accept": "text/plain",
            }

            # see: https://pvoutput.org/help.html
            # see: https://pvoutput.org/help.html#api-addstatus
            # report cumulative values to enable power usage
            data = {
                "d": time.strftime("%Y%m%d", reporttime),
                "t": time.strftime("%H:%M", reporttime),
                "c1": 0,
            }
            # v1 = energy_generated (Wh) * 1000 ; this value is on a dayly basis
            # v2 = bruto power_generated (W)
            # v3 = energy_used (Wh) * 1000 ; this value is cumulative
            # v4 = bruto power_consumption (W)
            # c1 = 1 ; v3 is cumulative so the c1 flag is set
            # see note about Cumulative Enery at https://pvoutput.org/help.html#api-addstatus

            if "energy_used" in msg and "power_consumption" in msg:
                data.update(
                    {
                        "v3": f"{msg['energy_used'] * Decimal('1000')}",
                        "v4": f"{msg['power_consumption']}",
                        "c1": 1,
                    }
                )
                # v3 = energy_used (Wh) * 1000 ; this value is cumulative
                # v4 = bruto power_consumption (W)
                # c1 = 1 ; v3 is cumulative so the c1 flag is set
                # see note about Cumulative Enery at https://pvoutput.org/help.html#api-addstatus
            if "current_power" in msg:
                data.update(
                    {
                        "v1": f"{msg['today_energy'] * Decimal('1000')}",
                        "v2": f"{msg['current_power']}",
                    }
                )
                # v1 = energy_generated (Wh) * 1000 ; this value is on a dayly basis
                # v2 = bruto power_generated (W)
                # c1 = 0 ; v1 is not cumulative so the c1 flag not is set
                # see note about Cumulative Enery at https://pvoutput.org/help.html#api-addstatus

                # Publish (inverter) temperature if solar data is published and a temperature is available.
                # alternatively use the temperature from openweather
                self._get_temperature(msg, data)

            # Publish voltage (if available)
            self._get_voltage(msg, data)

            encoded = urllib.parse.urlencode(data)

            self.logger.debug(json.dumps(data, indent=2))

            r = requests.post(
                "http://pvoutput.org/service/r2/addstatus.jsp",
                data=encoded,
                headers=headers,
            )

            r.raise_for_status()

        except requests.exceptions.RequestException as err:
            hybridlogger.ha_log(
                self.logger, self.hass_api, "WARNING", f"Unhandled request error: {err}"
            )
        except Exception as e:
            hybridlogger.ha_log(
                self.logger, self.hass_api, "ERROR", f"Unexpected error: {e.args}"
            )
        finally:
            self.access.release()
