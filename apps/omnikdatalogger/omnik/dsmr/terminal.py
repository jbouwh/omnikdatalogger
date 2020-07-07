from dsmr_parser.clients import create_dsmr_reader, create_tcp_dsmr_reader
import asyncio
from functools import partial
import threading
from omnik.ha_logger import hybridlogger


class Terminal(object):

    def __init__(self, config, logger, hass_api, terminal_name, dsmr_serial_callback, dsmr_version):
        self.config = config
        self.logger = logger
        self.hass_api = hass_api
        self.terminal_name = terminal_name
        self.dsmr_serial_callback = dsmr_serial_callback
        self.mode = self.config.get(f"dsmr.{self.terminal_name}", 'mode', 'device')
        if self.mode not in ['tcp', 'device']:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "ERROR", f"DSMR terminal {self.terminal_name} mode {self.mode} is not valid. "
                                "Should be tcp or device. Ignoring DSMR configuration!")

        self.device = self.config.get(f"dsmr.{self.terminal_name}", 'device', '/dev/ttyUSB0')
        self.host = self.config.get(f"dsmr.{self.terminal_name}", 'host', 'localhost')
        self.port = self.config.get(f"dsmr.{self.terminal_name}", 'port', '3333')
        self.dsmr_version = dsmr_version
        # start terminal
        self.stop = False
        self.transport = None
        hybridlogger.ha_log(self.logger, self.hass_api,
                            "INFO", f"Initializing DSMR termimal '{terminal_name}'. Mode: {self.mode}.")
        self.thr = threading.Thread(target=self._run_terminal, name=self.terminal_name)
        self.thr.start()

    def terminate(self):
        # cleanup connection after user initiated shutdown
        if self.transport:
            self.transport.close()
        self.stop = True
        self.thr.join()

    def _run_terminal(self):
        # SERIAL_SETTINGS_V2_2, SERIAL_SETTINGS_V4, SERIAL_SETTINGS_V5
        # Telegram specifications:
        # V2_2, V3=V2_2, V4, V5, BELGIUM_FLUVIUS, LUXEMBOURG_SMARTY
        # self.log("DSRM parser was started")
        # The serial approach
        # serial_reader = SerialReader(
        # device='/dev/ttyUSB0',
        # serial_settings=SERIAL_SETTINGS_V5,
        # telegram_specification=telegram_specifications.V5
        # )
        loop = asyncio.new_event_loop()
        try:
            if self.mode == 'tcp':
                create_connection = partial(create_tcp_dsmr_reader,
                                            self.host, self.port, self.dsmr_version,
                                            self.dsmr_serial_callback, loop=loop)
                hybridlogger.ha_log(self.logger, self.hass_api,
                                    "INFO", f"Connecting to '{self.host}:{self.port}' using DSMR v{self.dsmr_version}")
            elif self.mode == 'device':
                create_connection = partial(create_dsmr_reader,
                                            self.device, self.dsmr_version,
                                            self.dsmr_serial_callback, loop=loop)
                hybridlogger.ha_log(self.logger, self.hass_api,
                                    "INFO", f"Connecting to '{self.device}' using DSMR v{self.dsmr_version}")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "ERROR", f"DSMR terminal {self.terminal_name} could not be initialized. "
                                f"Check your configuration. Error: {e}")
            return
        # create serial or tcp connection
        while not self.stop:
            try:
                conn = create_connection()
                self.transport, protocol = loop.run_until_complete(conn)
                # wait until connection it closed
                loop.run_until_complete(protocol.wait_closed())
                # wait 5 seconds before attempting reconnect
                if not self.stop:
                    loop.run_until_complete(asyncio.sleep(5))
            except Exception as e:
                hybridlogger.ha_log(self.logger, self.hass_api,
                                    "WARNING", f"DSMR terminal {self.terminal_name} was interrupted "
                                    f"and will be restarted in a few moments: {e.args}"
                                    )
                asyncio.sleep(10)
        # Close the event loop
        loop.close()
