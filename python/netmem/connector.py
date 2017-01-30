import logging

# from netmem.network_memory import NetworkMemoryC
# import netmem
import netmem

class Connector(object):
    def __init__(self):
        """
        receive message will be called thus: self.receive_message(self, data)
        and should be defined thus: def receive_message(self, connector, data)
        """
        self.net_mem = None  # type: netmem.NetworkMemoryC
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def connect(self, net_mem):
        self.net_mem = net_mem

    def send_message(self, data: dict):
        pass
