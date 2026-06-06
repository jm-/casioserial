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
                 stopbits=DEFAULT_CASIO_SERIAL_STOPBITS,
                 debug=0):

        if mode not in ('transmit', 'receive'):
            raise ValueError("Mode must be either 'transmit' or 'receive'")

        self.mode = mode
        self.device = device
        self.debug = debug

        # create a serial connection
        self._log(f'opening serial device {device}')
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

    def _log(self, message):
        if self.debug:
            print(f'DBG: {message}')

    def _transmit_packet(self, packet_data):
        if self.debug:
            print(f' <  0x{packet_data.hex()}')
        self.ser.write(packet_data)

    def _receive_packet(self, length):
        packet_data = self.ser.read(length)
        if self.debug:
            print(f'  > 0x{packet_data.hex()}')
        return packet_data

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

    def transmit_program(self, program, overwrite=False):
        # transmit the program header packet
        self._transmit_packet(
            gen_program_header_packet(program.name, len(program.data),
                                      program.password)
        )

        # read the reply
        recv_packet_data = self._receive_packet(1)
        should_transmit_body = True

        # check if the device indicated the program already exists
        if recv_packet_data == PROTOCOL_ITEM_EXISTS:
            if overwrite:
                self._log('Overwriting existing item')
                self._transmit_packet(gen_overwrite_yes_packet())

            else:
                self._log('Not overwriting existing item')
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
            self._transmit_packet(gen_program_body_packet(program.data))

            # read the reply
            recv_packet_data = self._receive_packet(1)

        if recv_packet_data != PROTOCOL_OPERATION_ACK:
            self._transmit_packet(gen_error_packet())
            raise SerialCommunicationException(
                f'Unexpected response from device'
            )

    def transmit_picture(self, picture, overwrite=False):
        # the bitmap stacks two planes vertically; split it back into the
        # per-plane (height / 2) page-format buffers the wire expects
        plane_height = picture.height // 2
        planes = encode_picture(picture.data, picture.width, plane_height)

        # transmit the picture header packet
        self._transmit_packet(
            gen_picture_header_packet(picture.name, plane_height,
                                      picture.width, len(planes))
        )

        # read the reply
        recv_packet_data = self._receive_packet(1)
        should_transmit_body = True

        # check if the device indicated the picture already exists
        if recv_packet_data == PROTOCOL_ITEM_EXISTS:
            if overwrite:
                self._log('Overwriting existing item')
                self._transmit_packet(gen_overwrite_yes_packet())

            else:
                self._log('Not overwriting existing item')
                self._transmit_packet(gen_overwrite_no_packet())
                should_transmit_body = False

            # read the reply
            recv_packet_data = self._receive_packet(1)

        if not should_transmit_body:
            return

        if recv_packet_data != PROTOCOL_OPERATION_ACK:
            self._transmit_packet(gen_error_packet())
            raise SerialCommunicationException(
                f'Unexpected response from device'
            )

        # transmit each plane as a chunk packet, in order, ack after each
        for chunk_index in sorted(planes):
            self._log(f'transmitting chunk {chunk_index}/{len(planes)}')
            self._transmit_packet(
                gen_picture_chunk_packet(chunk_index, planes[chunk_index])
            )

            recv_packet_data = self._receive_packet(1)
            if recv_packet_data != PROTOCOL_OPERATION_ACK:
                self._transmit_packet(gen_error_packet())
                raise SerialCommunicationException(
                    f'Unexpected response from device'
                )

    def receive_item(self):
        """Read one item from the device. Returns Program, Picture, or None (END)."""
        self._log(f'expecting to read header ({PROTOCOL_HEADER_LENGTH} bytes)')
        header = self._receive_packet(PROTOCOL_HEADER_LENGTH)
        if len(header) != PROTOCOL_HEADER_LENGTH:
            raise SerialCommunicationException(
                f'Did not receive a full header packet'
            )

        self._log(f'header_type={header[1:4]}')

        if is_end_header(header):
            self._log('recv complete, exiting')
            return None

        if is_txt_header(header):
            prog_name, payload_length, prog_password = parse_txt_header(header)
            self._log(f'payload_type={header[5:7]}')
            self._log(f'payload_length={payload_length}')
            self._log(f'prog_name={prog_name} prog_length={payload_length - 3} '
                      f'prog_password={prog_password}')
            self._transmit_packet(PROTOCOL_OPERATION_ACK)
            program_packet = self._receive_packet(payload_length)
            program_data = parse_program_body(program_packet, payload_length)
            self._transmit_packet(PROTOCOL_OPERATION_ACK)
            return Program(name=prog_name, data=program_data, password=prog_password)

        if is_img_header(header):
            img_name, height, width, num_chunks = parse_img_header(header)
            self._log(f'payload_type={header[5:7]}')
            self._log(f'img_height={height} img_width={width}')
            self._log(f'img_name={img_name}')
            self._transmit_packet(PROTOCOL_OPERATION_ACK)
            payload_length = 1 + 4 + (height * width) // 8 + 1
            planes = {}
            for _ in range(num_chunks):
                chunk_packet = self._receive_packet(payload_length)
                chunk_index, plane = parse_picture_chunk(chunk_packet, payload_length)
                self._log(f'received chunk {chunk_index}/{num_chunks}')
                planes[chunk_index] = plane
                self._transmit_packet(PROTOCOL_OPERATION_ACK)
            picture_data = decode_picture(planes, width, height)
            return Picture(name=img_name, data=picture_data,
                           width=width, height=2 * height)

        raise SerialCommunicationException(
            f'Unknown header type: {header[:4]!r}'
        )

    def close(self):
        if self.ser.is_open:
            self._log(f'closing serial device {self.device}')
            self.ser.close()
