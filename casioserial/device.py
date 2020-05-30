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

        print(self.ser)


    def __enter__(self):
        return self


    def __exit__(self, type, value, traceback):
        self.close()


    def __repr__(self):
        return f'Casio serial device ({self.device})'


    def _transmit_packet(self, packet_data):
        self.ser.write(packet_data)


    def _receive_packet(self, length, timeout=None):
        # timeout appears to affect transmit logic. Don't use
        #self.ser.timeout = timeout
        return self.ser.read(length)


    def start_communication(self):
        # transmit the start packet to check if the device is listening
        self._transmit_packet(gen_start_packet())

        # the device should reply in a timely fashion
        recv_packet_data = self._receive_packet(1, timeout=CONNECT_TIMEOUT)

        # check that the device replied
        if not recv_packet_data:
            raise SerialCommunicationException(
                f'Device did not return any data in the expected timeframe'
            )

        if recv_packet_data != PROTOCOL_START_ACK_BYTE:
            self._transmit_packet(gen_error_packet())
            raise SerialCommunicationException(
                f'Unexpected response from device'
            )


    def end_communication(self):
        # transmit the end packet to indicate we won't send any more data
        self._transmit_packet(gen_end_packet())


    def transmit_program(self, name, program, password=None, overwrite=False):
        # transmit the program header packet
        self._transmit_packet(
            gen_program_header_packet(name, len(program), password)
        )

        # read the reply
        recv_packet_data = self._receive_packet(1)
        should_transmit_body = True

        # check if the device indicated the program already exists
        if recv_packet_data == PROTOCOL_ITEM_EXISTS:
            if overwrite:
                print(f'DBG: Overwriting existing item')
                self._transmit_packet(gen_overwrite_yes_packet())

            else:
                print(f'DBG: Not overwriting existing item')
                self._transmit_packet(gen_overwrite_no_packet())
                should_transmit_body = False

            # read the reply
            recv_packet_data = self._receive_packet(1)

        if should_transmit_body:
            if recv_packet_data != PROTOCOL_OPERATION_ACK:
                self._transmit_packet(gen_error_packet())
                raise SerialCommunicationException(
                    f'Unexpected response from device'
                )

            # transmit the program body packet
            self._transmit_packet(gen_program_body_packet(program))

            # read the reply
            recv_packet_data = self._receive_packet(1)

        if recv_packet_data != PROTOCOL_OPERATION_ACK:
            self._transmit_packet(gen_error_packet())
            raise SerialCommunicationException(
                f'Unexpected response from device'
            )


    def close(self):
        if self.ser.is_open:
            self.ser.close()
