from dsmr_parser.parsers import TelegramParser
from dsmr_parser.exceptions import ParseError, InvalidChecksumError
from dsmr_parser.clients.telegram_buffer import TelegramBuffer
from dsmr_parser import telegram_specifications
from dsmr_parser.clients.settings import (
    SERIAL_SETTINGS_V2_2,
    SERIAL_SETTINGS_V4,
    SERIAL_SETTINGS_V5,
)

import serial

import threading
from omnik.ha_logger import hybridlogger
import time
import socket


class Terminal(object):
    def __init__(
        self,
        config,
        logger,
        hass_api,
        terminal_name,
        dsmr_serial_callback,
        dsmr_version,
    ):
        self.config = config
        self.logger = logger
        self.hass_api = hass_api
        self.terminal_name = terminal_name
        self.dsmr_serial_callback = dsmr_serial_callback
        self.mode = self.config.get(f"dsmr.{self.terminal_name}", "mode", "device")
        if self.mode not in ["tcp", "device"]:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"DSMR terminal {self.terminal_name} mode {self.mode} is not valid. "
                "Should be tcp or device. Ignoring DSMR configuration!",
            )
            return
        self.device = self.config.get(
            f"dsmr.{self.terminal_name}", "device", "/dev/ttyUSB0"
        )
        self.host = self.config.get(f"dsmr.{self.terminal_name}", "host", "localhost")
        self.port = self.config.get(f"dsmr.{self.terminal_name}", "port", "3333")
        self.dsmr_version = dsmr_version
        # start terminal
        self.stop = False
        hybridlogger.ha_log(
            self.logger,
            self.hass_api,
            "INFO",
            f"Initializing DSMR termimal '{terminal_name}'. Mode: {self.mode}.",
        )
        if self.mode == "tcp":
            self.thr = threading.Thread(
                target=self._run_tcp_terminal, name=self.terminal_name
            )
        elif self.mode == "device":
            self.thr = threading.Thread(
                target=self._run_serial_terminal, name=self.terminal_name
            )
        self.thr.start()

    def terminate(self):
        self.stop = True
        # Wait for Thread to shutdown
        self.thr.join()

    def _get_dsmr_parser(self):
        dsmr_version = self.dsmr_version
        if dsmr_version == "2.2":
            specification = telegram_specifications.V2_2
            serial_settings = SERIAL_SETTINGS_V2_2
        elif dsmr_version == "4":
            specification = telegram_specifications.V4
            serial_settings = SERIAL_SETTINGS_V4
        elif dsmr_version == "5":
            specification = telegram_specifications.V5
            serial_settings = SERIAL_SETTINGS_V5
        elif dsmr_version == "5B":
            specification = telegram_specifications.BELGIUM_FLUVIUS
            serial_settings = SERIAL_SETTINGS_V5
        else:
            raise NotImplementedError(
                "No telegram parser found for version: %s", dsmr_version
            )
        self.telegram_parser = TelegramParser(specification)
        serial_settings["timeout"] = 10
        self.serial_settings = serial_settings

    def _dsmr_data_received(self, data):
        """Add incoming data to buffer."""
        data = data.decode("ascii")
        self.telegram_buffer.append(data)

        for telegram in self.telegram_buffer.get_all():
            self._handle_telegram(telegram)

    def _handle_telegram(self, telegram):
        """Send off parsed telegram to handling callback."""
        try:
            parsed_telegram = self.telegram_parser.parse(telegram)
        except InvalidChecksumError as e:
            self.logger.warning(str(e))
        except ParseError:
            self.logger.exception("failed to parse telegram")
        else:
            self.dsmr_serial_callback(parsed_telegram)

    def _run_tcp_terminal(self):
        self._get_dsmr_parser()
        # buffer to keep incomplete incoming data
        while not self.stop:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"DSMR terminal {self.terminal_name} was started.",
            )
            try:
                self.telegram_buffer = TelegramBuffer()
                server_address = (self.host, self.port)
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(5)
                self.sock.connect(server_address)
                while not self.stop:
                    data = self.sock.recv(1024)
                    if not data and not self.stop:
                        hybridlogger.ha_log(
                            self.logger,
                            self.hass_api,
                            "INFO",
                            f"DSMR terminal {self.terminal_name} was interrupted and will be restarted.",
                        )
                        time.sleep(5)
                        break
                    elif data:
                        self._dsmr_data_received(data)

            except Exception as e:
                if not self.stop:
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "WARNING",
                        f"DSMR terminal {self.terminal_name} was interrupted "
                        f"and will be restarted in a few moments: {e.args}",
                    )
                    time.sleep(5)
            finally:
                self.sock.close()

    def _run_serial_terminal(self):
        self._get_dsmr_parser()
        # buffer to keep incomplete incoming data
        while not self.stop:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"DSMR terminal {self.terminal_name} was started.",
            )
            try:
                self.telegram_buffer = TelegramBuffer()
                self.sock = serial.Serial(port=self.device, **self.serial_settings)
                while not self.stop:
                    data = self.sock.read_until()
                    if not data and not self.stop:
                        hybridlogger.ha_log(
                            self.logger,
                            self.hass_api,
                            "INFO",
                            f"DSMR terminal {self.terminal_name} was interrupted and will be restarted.",
                        )
                        time.sleep(5)
                        break
                    elif data:
                        self._dsmr_data_received(data)

            except Exception as e:
                if not self.stop:
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "WARNING",
                        f"DSMR terminal {self.terminal_name} was interrupted "
                        f"and will be restarted in a few moments: {e.args}",
                    )
                    time.sleep(5)
            finally:
                self.sock.close()
