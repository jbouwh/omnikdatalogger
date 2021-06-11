from dsmr_parser import obis_references
from .terminal import Terminal
from decimal import Decimal
import threading
from datetime import datetime
from omnik.ha_logger import hybridlogger


class DSRM(object):

    config = None
    logger = None
    hass_api = None
    datalogger = None

    def initialize(self, terminals, dsmr_callback):
        # args.host, args.port, args.version, args.device
        self.dsmr_callback = dsmr_callback
        # self.stop = False

        self._init_terminals(terminals)

    def _init_terminals(self, terminals):
        self.terminals = {}
        self.sync = {}
        self.cache = {}
        self.ts_last_telegram = {}
        self.last_gas_update = {}
        self.tconfig = {}
        self.tconfig["tarif"] = {}
        if self.config.has_option("dsmr", "tarif"):
            tarif_list = self.config.getlist("dsmr", "tarif")
        else:
            tarif_list = ["0001", "0002"]
            self.tconfig["tarif"]["0001"] = "low"
            self.tconfig["tarif"]["0002"] = "normal"
        for tarif in tarif_list:
            if tarif in self.tconfig["tarif"]:
                default = self.tconfig["tarif"][tarif]
            else:
                default = tarif
            self.tconfig["tarif"][tarif] = self.config.get(
                "dsmr", f"tarif.{tarif}", default
            )
        for terminal in terminals:
            # Pre read configuration for each terminal
            self.tconfig[terminal] = {}

            self.tconfig[terminal]["plant_id"] = self.config.get(
                f"dsmr.{terminal}", "plant_id", "0"
            )
            self.tconfig[terminal]["gas_meter"] = self.config.getboolean(
                f"dsmr.{terminal}", "gas_meter", True
            )
            self.tconfig[terminal]["dsmr_version"] = self.config.get(
                f"dsmr.{terminal}", "dsmr_version ", "5"
            )
            self.tconfig[terminal]["total_energy_offset"] = Decimal(
                self.config.get(f"dsmr.{terminal}", "total_energy_offset", "0")
            )

            # Init terminal sync parameters
            self.sync[terminal] = 0
            self.cache[terminal] = Decimal(1000000)
            self.ts_last_telegram[terminal] = 0
            self.last_gas_update[terminal] = [0, Decimal("0.0"), Decimal("0.000")]

            # Initialize terminal
            self.terminals[terminal] = Terminal(
                self.config,
                self.logger,
                self.hass_api,
                terminal,
                self.dsmr_serial_callback,
                self.tconfig[terminal]["dsmr_version"],
            )

    def terminate(self):
        # cleanup connection after user initiated shutdown
        for terminal in self.terminals:
            self.terminals[terminal].terminate()

    def _proces_power_current_fase(self, fase, msg_dsmr, telegram):

        # Build reference arrays
        voltage_fase_obis = [
            obis_references.INSTANTANEOUS_VOLTAGE_L1,
            obis_references.INSTANTANEOUS_VOLTAGE_L2,
            obis_references.INSTANTANEOUS_VOLTAGE_L3,
        ]
        voltage_fase_sag_obis = [
            obis_references.VOLTAGE_SAG_L1_COUNT,
            obis_references.VOLTAGE_SAG_L2_COUNT,
            obis_references.VOLTAGE_SAG_L3_COUNT,
        ]
        voltage_fase_swell_obis = [
            obis_references.VOLTAGE_SAG_L1_COUNT,
            obis_references.VOLTAGE_SAG_L2_COUNT,
            obis_references.VOLTAGE_SAG_L3_COUNT,
        ]
        current_fase_obis = [
            obis_references.INSTANTANEOUS_CURRENT_L1,
            obis_references.INSTANTANEOUS_CURRENT_L2,
            obis_references.INSTANTANEOUS_CURRENT_L3,
        ]
        pwr_pos_fase_obis = [
            obis_references.INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE,
            obis_references.INSTANTANEOUS_ACTIVE_POWER_L2_POSITIVE,
            obis_references.INSTANTANEOUS_ACTIVE_POWER_L3_POSITIVE,
        ]
        pwr_neg_fase_obis = [
            obis_references.INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE,
            obis_references.INSTANTANEOUS_ACTIVE_POWER_L2_NEGATIVE,
            obis_references.INSTANTANEOUS_ACTIVE_POWER_L3_NEGATIVE,
        ]

        sfase = f"{fase}"

        if pwr_pos_fase_obis[fase - 1] in telegram:
            msg_dsmr[f"INSTANTANEOUS_CURRENT_L{sfase}"] = telegram[
                current_fase_obis[fase - 1]
            ].value
            msg_dsmr[f"VOLTAGE_SAG_L{sfase}_COUNT"] = telegram[
                voltage_fase_sag_obis[fase - 1]
            ].value
            msg_dsmr[f"VOLTAGE_SWELL_L{sfase}_COUNT"] = telegram[
                voltage_fase_swell_obis[fase - 1]
            ].value
            msg_dsmr[f"INSTANTANEOUS_ACTIVE_POWER_L{fase}_POSITIVE"] = telegram[
                pwr_pos_fase_obis[fase - 1]
            ].value
            msg_dsmr[f"INSTANTANEOUS_ACTIVE_POWER_L{fase}_NEGATIVE"] = telegram[
                pwr_neg_fase_obis[fase - 1]
            ].value
            # current_net_power_l{fase} is calculated in Watt and is negative when power is delivered
            msg_dsmr[f"current_net_power_l{sfase}"] = (
                (
                    msg_dsmr[f"INSTANTANEOUS_ACTIVE_POWER_L{sfase}_POSITIVE"]
                    - msg_dsmr[f"INSTANTANEOUS_ACTIVE_POWER_L{sfase}_NEGATIVE"]
                )
                * Decimal("1000")
            ).quantize(Decimal("1."))
        if voltage_fase_obis[fase - 1] in telegram:
            # We have voltage, so lets calculate the current using power and voltage
            msg_dsmr[f"INSTANTANEOUS_VOLTAGE_L{sfase}"] = telegram[
                voltage_fase_obis[fase - 1]
            ].value
            # current_net_current_l{fase} is calculated in Ampère and is negative when power is delivered
            msg_dsmr[f"net_current_l{sfase}"] = (
                msg_dsmr[f"current_net_power_l{sfase}"]
                / msg_dsmr[f"INSTANTANEOUS_VOLTAGE_L{sfase}"]
            ).quantize(Decimal(".01"))

    def _process_power_details(self, msg_dsmr, telegram):
        terminal = threading.currentThread().getName()
        try:
            # Get global power (kWh)
            msg_dsmr["CURRENT_ELECTRICITY_USAGE"] = telegram[
                obis_references.CURRENT_ELECTRICITY_USAGE
            ].value
            msg_dsmr["CURRENT_ELECTRICITY_DELIVERY"] = telegram[
                obis_references.CURRENT_ELECTRICITY_DELIVERY
            ].value
            # Get energy usage
            msg_dsmr["ELECTRICITY_USED_TARIFF_1"] = telegram[
                obis_references.ELECTRICITY_USED_TARIFF_1
            ].value
            msg_dsmr["ELECTRICITY_USED_TARIFF_2"] = telegram[
                obis_references.ELECTRICITY_USED_TARIFF_2
            ].value
            msg_dsmr["energy_used_net"] = (
                msg_dsmr["ELECTRICITY_USED_TARIFF_1"]
                + msg_dsmr["ELECTRICITY_USED_TARIFF_2"]
            )  # ELECTRICITY_USED (NV)
            msg_dsmr["ELECTRICITY_DELIVERED_TARIFF_1"] = telegram[
                obis_references.ELECTRICITY_DELIVERED_TARIFF_1
            ].value
            msg_dsmr["ELECTRICITY_DELIVERED_TARIFF_2"] = telegram[
                obis_references.ELECTRICITY_DELIVERED_TARIFF_2
            ].value
            msg_dsmr["energy_delivered_net"] = (
                msg_dsmr["ELECTRICITY_DELIVERED_TARIFF_1"]
                + msg_dsmr["ELECTRICITY_DELIVERED_TARIFF_2"]
            )
            tarif = telegram[obis_references.ELECTRICITY_ACTIVE_TARIFF].value
            if tarif in self.tconfig["tarif"]:
                msg_dsmr["ELECTRICITY_ACTIVE_TARIFF"] = self.tconfig["tarif"][tarif]
            else:
                msg_dsmr["ELECTRICITY_ACTIVE_TARIFF"] = tarif

            if self.tconfig[terminal]["dsmr_version"] in ["5B", "5", "4"]:
                msg_dsmr["LONG_POWER_FAILURE_COUNT"] = telegram[
                    obis_references.LONG_POWER_FAILURE_COUNT
                ].value
                msg_dsmr["SHORT_POWER_FAILURE_COUNT"] = telegram[
                    obis_references.SHORT_POWER_FAILURE_COUNT
                ].value

                for fase in [1, 2, 3]:
                    self._proces_power_current_fase(fase, msg_dsmr, telegram)
                net_voltage_max = Decimal("0")
                if "INSTANTANEOUS_VOLTAGE_L1" in msg_dsmr:
                    net_voltage_max = max(
                        [msg_dsmr["INSTANTANEOUS_VOLTAGE_L1"], net_voltage_max]
                    )
                if "INSTANTANEOUS_VOLTAGE_L2" in msg_dsmr:
                    net_voltage_max = max(
                        [msg_dsmr["INSTANTANEOUS_VOLTAGE_L2"], net_voltage_max]
                    )
                if "INSTANTANEOUS_VOLTAGE_L3" in msg_dsmr:
                    net_voltage_max = max(
                        [msg_dsmr["INSTANTANEOUS_VOLTAGE_L3"], net_voltage_max]
                    )
                if net_voltage_max:
                    msg_dsmr["net_voltage_max"] = net_voltage_max

            # msg_dsmr['current_net_power'] = Decimal('0')
            # for fase in [1,2,3]:
            #    if f'current_net_power_l{fase}' in msg_dsmr:
            #        msg_dsmr['current_net_power'] += msg_dsmr[f'current_net_power_l{fase}']
            # if not msg_dsmr['current_net_power']:
            # Use global power indicators
            msg_dsmr["current_net_power"] = (
                (
                    msg_dsmr["CURRENT_ELECTRICITY_USAGE"]
                    - msg_dsmr["CURRENT_ELECTRICITY_DELIVERY"]
                )
                * Decimal("1000")
            ).quantize(Decimal("1."))

        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"DSMR current calculation for terminal '{terminal}' failed. "
                f"Check your config: Error: {e.args}",
            )

    def _process_gas(self, msg_dsmr, telegram):
        terminal = threading.currentThread().getName()
        if not self.tconfig[terminal]["gas_meter"]:
            # Skip gas meter
            return
        try:
            if self.tconfig[terminal]["dsmr_version"] in ["4", "5"]:
                G = telegram[obis_references.HOURLY_GAS_METER_READING]
                msg_dsmr["gas_consumption_total"] = G.values[1]["value"]
                msg_dsmr["timestamp_gas"] = datetime.timestamp(G.values[0]["value"])
            elif self.tconfig[terminal]["dsmr_version"] == "5B":
                G = telegram[obis_references.BELGIUM_HOURLY_GAS_METER_READING]
                msg_dsmr["gas_consumption_total"] = G.values[1]["value"]
                msg_dsmr["timestamp_gas"] = datetime.timestamp(G.values[0]["value"])
            elif self.tconfig[terminal]["dsmr_version"] == "2.2":
                G = telegram[obis_references.GAS_METER_READING]
                msg_dsmr["gas_consumption_total"] = G.values[6]["value"]
                msg_dsmr["timestamp_gas"] = datetime.timestamp(G.values[0]["value"])
            msg_dsmr["EQUIPMENT_IDENTIFIER_GAS"] = telegram[
                obis_references.EQUIPMENT_IDENTIFIER_GAS
            ].value
            # Set last value to the cache
            if not self.last_gas_update[terminal][0]:
                self.last_gas_update[terminal][0] = msg_dsmr["timestamp_gas"]
                self.last_gas_update[terminal][1] = msg_dsmr["gas_consumption_total"]
            # Calculate gas consumption / hour self.last_gas_update[terminal] = [0, Decimal('0')]
            if msg_dsmr["timestamp_gas"] > self.last_gas_update[terminal][0]:
                msg_dsmr["gas_consumption_hour"] = (
                    (
                        msg_dsmr["gas_consumption_total"]
                        - self.last_gas_update[terminal][1]
                    )
                    * Decimal("3600")
                    / Decimal(
                        msg_dsmr["timestamp_gas"] - self.last_gas_update[terminal][0]
                    )
                ).quantize(Decimal("0.001"))
                self.last_gas_update[terminal][0] = msg_dsmr["timestamp_gas"]
                self.last_gas_update[terminal][1] = msg_dsmr["gas_consumption_total"]
                self.last_gas_update[terminal][2] = msg_dsmr["gas_consumption_hour"]
            else:
                msg_dsmr["gas_consumption_hour"] = self.last_gas_update[terminal][2]
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"DSMR gas_meter reading for terminal '{terminal}' failed. "
                f"Check your config: Error: {e.args}",
            )

    def dsmr_serial_callback(self, telegram):
        terminal = threading.currentThread().getName()
        """Callback that prints telegram values."""
        if obis_references.P1_MESSAGE_TIMESTAMP in telegram:
            # Time stamp from Telegram
            TS = datetime.timestamp(
                telegram[obis_references.P1_MESSAGE_TIMESTAMP].value
            )
        else:
            # Create time stamp
            TS = int(datetime.timestamp(datetime.now()))
        # Use power value to sync DSMR 5 telegram flod. DSMR 4 and 2 log possible every 10 sec
        P1 = telegram[obis_references.CURRENT_ELECTRICITY_USAGE]
        P2 = telegram[obis_references.CURRENT_ELECTRICITY_DELIVERY]
        P = ((P2.value - P1.value) * Decimal("1000")).quantize(Decimal("1."))

        # Sync telegrams if there is a power change of after 10s
        if (
            (self.cache[terminal] != P)
            or (TS - self.ts_last_telegram[terminal] > 9.5)
            or (self.sync[terminal] == 10)
        ):
            self.cache[terminal] = P
            self.sync[terminal] = 0
            self.ts_last_telegram[terminal] = TS
        # Process telegram if synced
        if self.sync[terminal] == 0:
            # create uniform dsmr message structure for futher processinh
            msg_dsmr = {}
            # Add generic values
            msg_dsmr["timestamp"] = TS
            msg_dsmr["EQUIPMENT_IDENTIFIER"] = telegram[
                obis_references.EQUIPMENT_IDENTIFIER
            ].value
            msg_dsmr["terminal"] = terminal
            msg_dsmr["plant_id"] = self.tconfig[terminal]["plant_id"]
            msg_dsmr["total_energy_offset"] = self.tconfig[terminal][
                "total_energy_offset"
            ]
            # msg_dsmr['advertize_power_fields'] =  self.tconfig[terminal]['advertize_power_fields']
            # msg_dsmr['advertize_dsrm_solar_fields'] =  self.tconfig[terminal]['advertize_dsrm_solar_fields']

            # Read and process more accurate power calculations DSMR 5
            self._process_power_details(msg_dsmr, telegram)

            # Process Gas
            self._process_gas(msg_dsmr, telegram)

            # Send back data to data logger
            self.dsmr_callback(terminal, msg_dsmr)

        # Increase terminal sync counter
        self.sync[terminal] += 1
