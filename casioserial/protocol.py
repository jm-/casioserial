import struct


CONNECT_TIMEOUT = 0.5

# protocol sequences
PROTOCOL_START_BYTE = b'\x16'
PROTOCOL_START_ACK_BYTE = b'\x13'
PROTOCOL_OPERATION_ACK = b'\x06'
PROTOCOL_ITEM_EXISTS = b'\x21'
PROTOCOL_OVERWRITE_YES = b'\x06'
PROTOCOL_OVERWRITE_NO = b'\x15'
PROTOCOL_ERROR_BYTE = b'\x22'


def _compute_checksum_byte(packet_body):
    return struct.pack('>B', (0x01 + ~(sum(packet_body) - 0x3a)) % 256)


def gen_start_packet():
    return PROTOCOL_START_BYTE


def gen_end_packet():
    packet_body = struct.pack(
        '>4s45s',
        b':END',
        b'\xff' * 45
    )
    packet_data = packet_body + _compute_checksum_byte(packet_body)
    return packet_data


def gen_error_packet():
    return PROTOCOL_ERROR_BYTE


def gen_overwrite_yes_packet():
    return PROTOCOL_OVERWRITE_YES


def gen_overwrite_no_packet():
    return PROTOCOL_OVERWRITE_NO


def gen_program_header_packet(name, program_length, password):
    packet_body = struct.pack(
        '>4s1s2s2sH8s8s8s2s12s',
        b':TXT',
        b'\x00',
        b'PG',
        b'\x00\x00',
        program_length + 3,
        name.ljust(8, b'\xff'),
        b'\xff\xff\xff\xff\xff\xff\xff\xff',
        password.ljust(8, b'\xff'),
        b'NL',
        b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    )
    packet_data = packet_body + _compute_checksum_byte(packet_body)
    return packet_data


def gen_program_body_packet(program):
    packet_body = struct.pack(
        f'>1s{len(program)}s1s',
        b':',
        program,
        b'\xff'
    )
    packet_data = packet_body + _compute_checksum_byte(packet_body)
    return packet_data
