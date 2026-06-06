import struct


PROTOCOL_HEADER_LENGTH = 50

# protocol packet sequences
PROTOCOL_PACKET_DELIMITER = b':'
PROTOCOL_PACKET_PADDING = b'\xff'

# protocol headers
PROTOCOL_HEADER_END = PROTOCOL_PACKET_DELIMITER + b'END'
PROTOCOL_HEADER_TXT = PROTOCOL_PACKET_DELIMITER + b'TXT'
PROTOCOL_HEADER_IMG = PROTOCOL_PACKET_DELIMITER + b'IMG'

# picture (:IMG) format constants
PROTOCOL_PICTURE_PAYLOAD_TYPE = b'PC'
PROTOCOL_PICTURE_MARKER = b'DRUWF'
# Shared by the IMG header's [34:36] field and every chunk's first sub-header field.
# A fixed tag, not an item counter. Observed to always be 0x0001.
PROTOCOL_PICTURE_TAG = 1

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


def gen_picture_header_packet(name, height, width, num_chunks,
                              tag=PROTOCOL_PICTURE_TAG):
    packet_body = struct.pack(
        '>4s1s2sHH8s8s5sHH13s',
        PROTOCOL_HEADER_IMG,
        b'\x00',
        PROTOCOL_PICTURE_PAYLOAD_TYPE,
        height,
        width,
        name.ljust(8, PROTOCOL_PACKET_PADDING),
        PROTOCOL_PACKET_PADDING * 8,
        PROTOCOL_PICTURE_MARKER,
        num_chunks,
        tag,
        PROTOCOL_PACKET_PADDING * 13
    )
    packet_data = packet_body + _compute_checksum_byte(packet_body)
    return packet_data


def gen_picture_chunk_packet(chunk_index, plane, tag=PROTOCOL_PICTURE_TAG):
    packet_body = (PROTOCOL_PACKET_DELIMITER
                   + struct.pack('>HH', tag, chunk_index)
                   + plane)
    packet_data = packet_body + _compute_checksum_byte(packet_body)
    return packet_data


def encode_picture(bitmap, width, height):
    """Split a row-major bitmap into page-format planes (inverse of decode).

    Returns a dict of four 1-based plane buffers, each `(width // 8) * height`
    bytes. Plane 2 carries the top `height` rows of the bitmap, plane 4 the
    bottom `height` rows; planes 1 and 3 are all-zero (reserved). See
    `decode_picture` for the page-format + 90-degree mapping, of which this is
    the exact inverse.
    """
    plane_size = (width // 8) * height
    row_bytes = width // 8
    planes = {i: bytearray(plane_size) for i in (1, 2, 3, 4)}

    for plane_index, y_offset in ((2, 0), (4, height)):
        plane = planes[plane_index]
        for y in range(height):
            row_base = (y_offset + y) * row_bytes
            for x in range(width):
                if (bitmap[row_base + (x >> 3)] >> (7 - (x & 7))) & 1:
                    sx = (height - 1) - y
                    sy = (width - 1) - x
                    plane[(sy // 8) * height + sx] |= 1 << (sy & 7)

    return {i: bytes(p) for i, p in planes.items()}


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
    """Parse IMG header. Returns (img_name, height, width, num_chunks)."""
    if not is_img_header(packet):
        raise ValueError("Not an IMG header")
    if not verify_checksum(packet):
        raise ValueError("Checksum mismatch")
    height, width = struct.unpack('>HH', packet[7:11])
    img_name = packet[11:19].rstrip(PROTOCOL_PACKET_PADDING)
    num_chunks = struct.unpack('>H', packet[32:34])[0]
    return img_name, height, width, num_chunks


def parse_program_body(packet, payload_length):
    """Extract program bytes from a received body packet."""
    if len(packet) != payload_length or packet[0:1] != PROTOCOL_PACKET_DELIMITER:
        raise ValueError("Invalid program body packet")
    if not verify_checksum(packet):
        raise ValueError("Checksum mismatch")
    return packet[1:-2]  # strip ':' and trailing \xff + checksum


def parse_picture_chunk(packet, payload_length):
    """Extract one picture plane. Returns (chunk_index, plane_bytes)."""
    if len(packet) != payload_length or packet[0:1] != PROTOCOL_PACKET_DELIMITER:
        raise ValueError("Invalid picture chunk packet")
    if not verify_checksum(packet):
        raise ValueError("Checksum mismatch")
    chunk_index = struct.unpack('>H', packet[3:5])[0]
    plane = packet[5:-1]  # skip ':' + 4-byte sequence header + checksum
    return chunk_index, plane


def decode_picture(planes, width, height):
    """Compose received picture planes into a row-major monochrome bitmap.

    `planes` maps a 1-based plane index to its 1024-byte page-format buffer.
    Planes 2 and 4 carry the visible bitmap (planes 1 and 3 are reserved); they
    stack vertically into a `width` x `2 * height` image, plane 2 on top.

    Each plane byte holds 8 vertically stacked pixels (bit 0 = top). The buffer
    is the display rotated 90 degrees, so a display pixel (x, y) within a plane
    maps to storage column `sx = (height - 1) - y` and row `sy = (width - 1) - x`,
    at byte `(sy // 8) * height + sx`, bit `sy & 7`.

    Returns a bitmap of `(width // 8) * 2 * height` bytes, row-major, MSB =
    leftmost pixel.
    """
    out_height = 2 * height
    row_bytes = width // 8
    bitmap = bytearray(row_bytes * out_height)

    for plane_index, y_offset in ((2, 0), (4, height)):
        plane = planes.get(plane_index)
        if plane is None:
            continue
        for y in range(height):
            row_base = (y_offset + y) * row_bytes
            for x in range(width):
                sx = (height - 1) - y
                sy = (width - 1) - x
                if (plane[(sy // 8) * height + sx] >> (sy & 7)) & 1:
                    bitmap[row_base + (x >> 3)] |= 0x80 >> (x & 7)

    return bytes(bitmap)
