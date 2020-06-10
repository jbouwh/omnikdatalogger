# Credits to: https://github.com/Woutrrr
# adjusted for python 3.5+

import struct               # Converting bytes to numbers
import datetime
import time


class InverterMsg:

    'Class for Inverter message'
    rawmsg = ""

    def __init__(self, msg, offset=0):
        self.rawmsg = msg
        self.offset = offset
        # Set a timestamp
        self.last_update = time.time()

    def __getString(self, begin, end):
        return str(self.rawmsg[begin:end], encoding='UTF-8')

    def __getShort(self, begin, devider=10):
        num = struct.unpack('!H', self.rawmsg[begin:begin + 2])[0]
        if num == 65535:
            return -1
        else:
            return float(num) / devider

    def __getLong(self, begin, devider=10):
        return float(struct.unpack('!I', self.rawmsg[begin:begin + 4])[0]) / devider

    def getID(self):
        return self.__getString(15, 31)

    def getTemp(self):
        return self.__getShort(31)

    def getPower(self):
        return int(self.__getShort(59, 1))

    def getPVPower(self):
        totalpower = 0
        strings = [1, 2, 3]
        for i in strings:
            if self.getPPV(i) > 0:
                totalpower += self.getPPV(i)
        return totalpower

    def getETotal(self):
        return self.__getLong(71)

    def getVPV(self, i=1):
        if i not in range(1, 4):
            i = 1
        num = 33 + (i - 1) * 2
        return self.__getShort(num)

    def getIPV(self, i=1):
        if i not in range(1, 4):
            i = 1
        num = 39 + (i - 1) * 2
        return self.__getShort(num)

    def getPPV(self, i=1):
        # If current is 0 return 0
        if not self.getIPV(i):
            return 0
        # If current is -1 (invalid) return -1 (invalid)
        if self.getIPV(i) < 0:
            return -1
        else:
            return int(self.getVPV(i) * self.getIPV(i))

    def getIAC(self, i=1):
        if i not in range(1, 4):
            i = 1
        num = 45 + (i - 1) * 2
        return self.__getShort(num)

    def getVAC(self, i=1):
        if i not in range(1, 4):
            i = 1
        num = 51 + (i - 1) * 2
        return self.__getShort(num)

    def getFAC(self, i=1):
        if i not in range(1, 4):
            i = 1
        num = 57 + (i - 1) * 4
        return self.__getShort(num, 100)

    def getPAC(self, i=1):
        if i not in range(1, 4):
            i = 1
        num = 59 + (i - 1) * 4
        return int(self.__getShort(num, 1))  # Don't divide

    def getEToday(self):
        return self.__getShort(69, 100)      # Devide by 100

    def getHTotal(self):
        return int(self.__getLong(75, 1))    # Don't divide

    def getIACalt(self, i=1):
        # Calculate current from power and voltage
        pac = self.getPAC(i)
        vac = self.getVAC(i)
        return round(pac / vac, 2) if pac >= 0 else -1

    def setIfValid(self, key, data, value):
        if value >= 0:
            data[key] = value

    def _maxoflist(self, list):
        max = -1
        for item in list:
            if item > max:
                max = item
        return max

    def FetchDataDict(self, data):
        if data:
            if not isinstance(data, dict):
                # Object is not a dict
                raise Exception("data object is not a dict")
                return
        else:
            data = {}
        # Fill the dict
        # Get timestamp string and epoch
        data['last_update_time'] = datetime.datetime.utcfromtimestamp(self.last_update).strftime('%Y-%m-%dT%H:%M:%SZ')
        data['last_update'] = self.last_update
        # Set the serial number
        data['inverter'] = self.getID()
        data['current_power'] = self.getPower()
        data['today_energy'] = self.getEToday()
        data['total_energy'] = self.getETotal()
        data['inverter_temperature'] = self.getTemp()
        self.setIfValid('current_ac1', data, self.getIACalt(1))
        self.setIfValid('current_ac2', data, self.getIACalt(2))
        self.setIfValid('current_ac3', data, self.getIACalt(3))
        self.setIfValid('voltage_ac1', data, self.getVAC(1))
        self.setIfValid('voltage_ac2', data, self.getVAC(2))
        self.setIfValid('voltage_ac3', data, self.getVAC(3))
        self.setIfValid('frequency_ac1', data, self.getFAC(1))
        self.setIfValid('frequency_ac2', data, self.getFAC(2))
        self.setIfValid('frequency_ac3', data, self.getFAC(3))
        self.setIfValid('power_ac1', data, self.getPAC(1))
        self.setIfValid('power_ac2', data, self.getPAC(2))
        self.setIfValid('power_ac3', data, self.getPAC(3))
        self.setIfValid('voltage_pv1', data, self.getVPV(1))
        self.setIfValid('voltage_pv2', data, self.getVPV(2))
        self.setIfValid('voltage_pv3', data, self.getVPV(3))
        self.setIfValid('current_pv1', data, self.getIPV(1))
        self.setIfValid('current_pv2', data, self.getIPV(2))
        self.setIfValid('current_pv3', data, self.getIPV(3))
        self.setIfValid('power_pv1', data, self.getPPV(1))
        self.setIfValid('power_pv2', data, self.getPPV(2))
        self.setIfValid('power_pv3', data, self.getPPV(3))
        self.setIfValid('operation_hours', data, self.getHTotal())
        self.setIfValid('current_power_pv', data, self.getPVPower())
        self.setIfValid('voltage_ac_max', data, self._maxoflist([self.getVAC(1), self.getVAC(2), self.getVAC(3)]))


def request_string(ser):
    '''
    The request string is build from several parts. The first part is a
    fixed 4 char string; the second part is the reversed hex notation of
    the Wi-Fi logger s/n twice; then again a fixed string of two chars; a checksum of
    the double s/n with an offset; and finally a fixed ending char.
    this code requires python 3.5 or later!
    '''
    responseString = b'\x68\x02\x40\x30'

    doublehex = hex(ser)[2:]*2
    hexlist = [bytes.fromhex(doublehex[i:i+2]) for i in
               reversed(range(0, len(doublehex), 2))]

    cs_count = 115 + sum([ord(c) for c in hexlist])
    cs = bytes.fromhex(hex(cs_count)[-2:])
    responseString += b''.join(hexlist) + b''.join([b'\x01\x00', cs, b'\x16'])
    return responseString
