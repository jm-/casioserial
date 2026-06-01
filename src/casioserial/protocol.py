import struct


PROTOCOL_HEADER_LENGTH = 50

# protocol packet sequences
PROTOCOL_PACKET_DELIMITER = b':'
PROTOCOL_PACKET_PADDING = b'\xff'

# protocol headers
PROTOCOL_HEADER_END = PROTOCOL_PACKET_DELIMITER + b'END'
PROTOCOL_HEADER_TXT = PROTOCOL_PACKET_DELIMITER + b'TXT'
PROTOCOL_HEADER_IMG = PROTOCOL_PACKET_DELIMITER + b'IMG'

# protocol control sequences
PROTOCOL_START_BYTE = b'\x16'
PROTOCOL_START_ACK_BYTE = b'\x13'
PROTOCOL_OPERATION_ACK = b'\x06'
PROTOCOL_ITEM_EXISTS = b'\x21'
PROTOCOL_OVERWRITE_YES = b'\x06'
PROTOCOL_OVERWRITE_NO = b'\x15'
PROTOCOL_ERROR_BYTE = b'\x22'


def _compute_checksum_byte(packet_body):
    return struct.pack('>B', (0x01 + ~(sum(packet_body) - 0x3a)) % 256)


def verify_checksum(packet):
    """True if packet[-1] matches the computed checksum of packet[:-1]."""
    return _compute_checksum_byte(packet[:-1]) == bytes([packet[-1]])


# --- transmit-side packet utilities ---

def gen_start_packet():
    return PROTOCOL_START_BYTE


def gen_end_packet():
    packet_body = struct.pack(
        '>4s45s',
        PROTOCOL_HEADER_END,
        PROTOCOL_PACKET_PADDING * 45
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
        PROTOCOL_HEADER_TXT,
        b'\x00',
        b'PG',
        b'\x00\x00',
        program_length + 3,
        name.ljust(8, PROTOCOL_PACKET_PADDING),
        PROTOCOL_PACKET_PADDING * 8,
        password.ljust(8, PROTOCOL_PACKET_PADDING),
        b'NL',
        PROTOCOL_PACKET_PADDING * 12
    )
    packet_data = packet_body + _compute_checksum_byte(packet_body)
    return packet_data


def gen_program_body_packet(program):
    packet_body = PROTOCOL_PACKET_DELIMITER + program + PROTOCOL_PACKET_PADDING
    packet_data = packet_body + _compute_checksum_byte(packet_body)
    return packet_data


# --- receive-side packet parsers ---

def is_end_header(packet):
    return len(packet) == PROTOCOL_HEADER_LENGTH and packet[:4] == PROTOCOL_HEADER_END


def is_txt_header(packet):
    return len(packet) == PROTOCOL_HEADER_LENGTH and packet[:4] == PROTOCOL_HEADER_TXT


def is_img_header(packet):
    return len(packet) == PROTOCOL_HEADER_LENGTH and packet[:4] == PROTOCOL_HEADER_IMG


def parse_txt_header(packet):
    """Parse TXT header. Returns (prog_name, payload_length, prog_password)."""
    if not is_txt_header(packet):
        raise ValueError("Not a TXT header")
    if not verify_checksum(packet):
        raise ValueError("Checksum mismatch")
    payload_length = struct.unpack('>H', packet[9:11])[0]
    prog_name = packet[11:19].rstrip(PROTOCOL_PACKET_PADDING)
    prog_password = packet[27:35].rstrip(PROTOCOL_PACKET_PADDING)
    return prog_name, payload_length, prog_password


def parse_img_header(packet):
    """Parse IMG header. Returns (img_name, height, width)."""
    if not is_img_header(packet):
        raise ValueError("Not an IMG header")
    if not verify_checksum(packet):
        raise ValueError("Checksum mismatch")
    height, width = struct.unpack('>HH', packet[7:11])
    img_name = packet[11:19].rstrip(PROTOCOL_PACKET_PADDING)
    return img_name, height, width


def parse_program_body(packet, payload_length):
    """Extract program bytes from a received body packet."""
    if len(packet) != payload_length or packet[0:1] != PROTOCOL_PACKET_DELIMITER:
        raise ValueError("Invalid program body packet")
    if not verify_checksum(packet):
        raise ValueError("Checksum mismatch")
    return packet[1:-2]  # strip ':' and trailing \xff + checksum


def parse_picture_chunk(packet, payload_length):
    """Extract picture bytes from a received chunk packet"""
    if len(packet) != payload_length or packet[0:1] != PROTOCOL_PACKET_DELIMITER:
        raise ValueError("Invalid picture chunk packet")
    if not verify_checksum(packet):
        raise ValueError("Checksum mismatch")
    return chunk[5:-1]  # skip ':' + 4-byte sequence header + checksum
