import struct


CONNECT_TIMEOUT = 0.5

# protocol sequences
PROTOCOL_REQUEST_BYTE = b'\x16'
PROTOCOL_REQUEST_ACK_BYTE = b'\x13'


def gen_request_packet():
    return PROTOCOL_REQUEST_BYTE
