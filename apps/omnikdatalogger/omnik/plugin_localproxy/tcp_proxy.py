from omnik.ha_logger import hybridlogger
from omnik.plugin_localproxy import LocalProxyPlugin
import threading
import socketserver
import os


class RequestHandler(socketserver.BaseRequestHandler):

    client = None

    def handle(self):
        data = self.request.recv(1024)

        if self.client and len(data) >= 99:
            # Fill data structure
            self.client.semaphore.acquire()
            self.client.msg["data"] = data
            self.client.msg["isSet"] = True
            self.client.msg["plugin"] = __name__
            self.client.semaphore.release()
            # Trigger processing the message
            self.client.msgevent.set()


class TCPproxy(LocalProxyPlugin):

    """
    This plugin enables you to listen directly to the logger requests send by the inverter
    Listing can be done by forwarding and NAT to the [tcp_proxy].listen_address:listen_port
    The scripts/proxy/omnikloggerproxy script can also be used to capture and forward to this listener

    This class makes use the following localproxy client objects
    self.client.msg
    self.client.msgevent
    self.client.semaphore
    self.client.inverters
    self.client.plant_id_list
    """

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(
            self.logger, self.hass_api, "INFO", "localproxy client plugin: TCPproxy"
        )
        self.listen_address = self.config.get(
            "client.localproxy.tcp_proxy", "listen_address", fallback="0.0.0.0"
        )
        self.listen_port = int(
            self.config.get(
                "client.localproxy.tcp_proxy", "listen_port", fallback="10004"
            )
        )
        self.listenaddress = (self.listen_address, int(self.listen_port))
        # Create tcp server
        RequestHandler.client = self.client
        self.tcpServer = socketserver.TCPServer(self.listenaddress, RequestHandler)

    def terminate(self):
        try:
            # Shutting down tcp server
            self.tcpServer.shutdown()
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Error shutting down tcp_proxy server. Error: {e}.",
            )
            # exit the hard way!
            os.sys.exit(1)

    def listen(self):
        # Start listening thread
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def _run(self):
        # TCP listen loop
        try:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Starting tcp_proxy server. listening at {self.listenaddress[0]}:{self.listenaddress[1]}.",
            )
            self.tcpServer.serve_forever()
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Error binding to {self.listenaddress}. Error: {e}.",
            )
