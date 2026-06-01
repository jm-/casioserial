import serial

from .common import (
    DEFAULT_CASIO_SERIAL_DEVICE,
    DEFAULT_CASIO_SERIAL_BAUDRATE,
    DEFAULT_CASIO_SERIAL_STOPBITS
)
from .models import Program, Picture
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
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=stopbits
        )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __repr__(self):
        return f'Casio serial device ({self.device})'

    def _transmit_packet(self, packet_data):
        self.ser.write(packet_data)

    def _receive_packet(self, length):
        return self.ser.read(length)

    def start_communication(self):
        if self.mode == 'transmit':
            # transmit the start packet to check if the device is listening
            self._transmit_packet(gen_start_packet())

            # the device should reply in a timely fashion
            recv_packet_data = self._receive_packet(1)

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

        elif self.mode == 'receive':
            # wait for the device to initiate
            recv_packet_data = self._receive_packet(1)

            if not recv_packet_data:
                raise SerialCommunicationException(
                    f'Device did not send start byte'
                )

            if recv_packet_data != PROTOCOL_START_BYTE:
                raise SerialCommunicationException(
                    f'Unexpected byte from device'
                )

            self._transmit_packet(PROTOCOL_START_ACK_BYTE)

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

    def receive_item(self):
        """Read one item from the device. Returns Program, Picture, or None (END)."""
        header = self._receive_packet(PROTOCOL_HEADER_LENGTH)
        if len(header) != PROTOCOL_HEADER_LENGTH:
            raise SerialCommunicationException(
                f'Did not receive a full header packet'
            )

        if is_end_header(header):
            return None

        if is_txt_header(header):
            prog_name, payload_length, prog_password = parse_txt_header(header)
            self._transmit_packet(PROTOCOL_OPERATION_ACK)
            program_packet = self._receive_packet(payload_length)
            program_data = parse_program_body(program_packet, payload_length)
            self._transmit_packet(PROTOCOL_OPERATION_ACK)
            return Program(name=prog_name, data=program_data, password=prog_password)

        if is_img_header(header):
            img_name, height, width = parse_img_header(header)
            self._transmit_packet(PROTOCOL_OPERATION_ACK)
            # chunk count is likely carried in header bytes 31:33 (observed 0x0004);
            # hardcoded until confirmed by further testing
            NUM_IMG_CHUNKS = 4
            payload_length = 1 + 4 + (height * width) // 8 + 1
            picture_data = b''
            for _ in range(NUM_IMG_CHUNKS):
                chunk_packet = self._receive_packet(payload_length)
                picture_chunk = parse_picture_chunk(
                    chunk_packet, payload_length)
                picture_data += picture_chunk
                self._transmit_packet(PROTOCOL_OPERATION_ACK)
            return Picture(name=img_name, data=picture_data, height=height, width=width)

        raise SerialCommunicationException(
            f'Unknown header type: {header[:4]!r}'
        )

    def close(self):
        if self.ser.is_open:
            self.ser.close()
