import serial

from .common import (
    DEFAULT_CASIO_SERIAL_DEVICE,
    DEFAULT_CASIO_SERIAL_BAUDRATE,
    DEFAULT_CASIO_SERIAL_STOPBITS
)
from .protocol import *


class SerialCommunicationException(Exception):
    pass


class CasioSerialDevice():
    """ Device that supports the CasioSerial protocol """

    def __init__(self, mode,
                 device=DEFAULT_CASIO_SERIAL_DEVICE,
                 baudrate=DEFAULT_CASIO_SERIAL_BAUDRATE,
                 stopbits=DEFAULT_CASIO_SERIAL_STOPBITS):

        if mode not in ('transmit', 'receive'):
            raise ValueError("Mode must be either 'transmit' or 'receive'")

        self.mode = mode
        self.device = device

        # create a serial connection
        self.ser = serial.Serial(
            device,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=stopbits
        )


    def __enter__(self):
        return self


    def __exit__(self, type, value, traceback):
        self.close()


    def __repr__(self):
        return f'Casio serial device ({self.device})'


    def _send_packet(self, packet_data):
        self.ser.write(packet_data)


    def _recv_packet(self, length, timeout=None):
        self.ser.timeout = timeout
        return self.ser.read(length)


    def initiate(self):
        # send the request packet to check if the device is listening
        self._send_packet(gen_request_packet())

        # the device should reply in a timely fashion
        recv_packet_data = self._recv_packet(1, timeout=CONNECT_TIMEOUT)

        # check that the device replied
        if not recv_packet_data:
            raise SerialCommunicationException(
                f'Device did not return any data in the expected timeframe'
            )

        if recv_packet_data != PROTOCOL_REQUEST_ACK_BYTE:
            raise SerialCommunicationException(
                f'Unexpected response from device'
            )


    def close(self):
        self.ser.close()
