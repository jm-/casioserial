import struct

import pytest

from casioserial.protocol import (
    _compute_checksum_byte,
    gen_end_packet,
    gen_error_packet,
    gen_overwrite_no_packet,
    gen_overwrite_yes_packet,
    gen_program_body_packet,
    gen_program_header_packet,
    gen_start_packet,
)


class TestComputeChecksumByte:
    def test_end_packet_body(self):
        body = struct.pack(">4s45s", b":END", b"\xff" * 45)
        assert _compute_checksum_byte(body) == b"\x56"

    def test_roulette_header_body(self):
        # Ground-truth vector from reverse-engineering/packets/txt_pkt.txt
        body = struct.pack(
            ">4s1s2s2sH8s8s8s2s12s",
            b":TXT",
            b"\x00",
            b"PG",
            b"\x00\x00",
            392,
            b"ROULETTE",
            b"\xff" * 8,
            b"\xff" * 8,
            b"NL",
            b"\xff" * 12,
        )
        assert _compute_checksum_byte(body) == b"\xee"


class TestGenEndPacket:
    def test_length(self):
        assert len(gen_end_packet()) == 50

    def test_header(self):
        assert gen_end_packet()[:4] == b":END"

    def test_padding(self):
        assert gen_end_packet()[4:49] == b"\xff" * 45

    def test_checksum(self):
        assert gen_end_packet()[-1:] == b"\x56"


class TestGenProgramHeaderPacket:
    def test_roulette_checksum(self):
        # program_length=389 so the wire length field (length+3) equals 392=0x0188
        pkt = gen_program_header_packet(b"ROULETTE", 389, b"")
        assert pkt[-1] == 0xEE

    def test_length_always_50(self):
        assert len(gen_program_header_packet(b"A", 10, b"")) == 50
        assert len(gen_program_header_packet(b"LONGNAME", 1000, b"PASS")) == 50

    def test_name_embedded(self):
        pkt = gen_program_header_packet(b"ROULETTE", 389, b"")
        assert pkt[11:19] == b"ROULETTE"

    def test_short_name_padded_with_xff(self):
        pkt = gen_program_header_packet(b"A", 10, b"")
        assert pkt[11:19] == b"A" + b"\xff" * 7

    def test_password_padded_with_xff(self):
        pkt = gen_program_header_packet(b"TEST", 10, b"PW")
        # after :TXT\x00 PG \x00\x00 (9 bytes) + uint16 (2 bytes) = offset 11... wait:
        # struct '>4s1s2s2sH8s8s8s2s12s': 4+1+2+2+2+8+8+8+2+12 = 49 bytes body
        # offset 0:  :TXT (4)
        # offset 4:  \x00 (1)
        # offset 5:  PG   (2)
        # offset 7:  \x00\x00 (2)
        # offset 9:  length uint16 (2)
        # offset 11: name  (8)  → 11:19
        # offset 19: \xff*8 (8) → 19:27
        # offset 27: password (8) → 27:35
        assert pkt[27:35] == b"PW" + b"\xff" * 6

    def test_length_field_value(self):
        pkt = gen_program_header_packet(b"TEST", 100, b"")
        # wire length field = program_length + 3
        assert struct.unpack(">H", pkt[9:11])[0] == 103


class TestGenProgramBodyPacket:
    def test_starts_with_colon(self):
        assert gen_program_body_packet(b"HELLO")[0:1] == b":"

    def test_program_content(self):
        pkt = gen_program_body_packet(b"HELLO")
        assert pkt[1:6] == b"HELLO"

    def test_sentinel_byte(self):
        pkt = gen_program_body_packet(b"HELLO")
        assert pkt[-2:-1] == b"\xff"

    def test_valid_checksum(self):
        pkt = gen_program_body_packet(b"HELLO")
        assert _compute_checksum_byte(pkt[:-1]) == pkt[-1:]

    def test_empty_program(self):
        pkt = gen_program_body_packet(b"")
        # b':' + b'\xff' + checksum = 3 bytes
        assert len(pkt) == 3
        assert pkt[0:1] == b":"
        assert pkt[1:2] == b"\xff"
        assert pkt[2:3] == _compute_checksum_byte(b":\xff")


class TestSingleBytePackets:
    def test_gen_start_packet(self):
        assert gen_start_packet() == b"\x16"

    def test_gen_error_packet(self):
        assert gen_error_packet() == b"\x22"

    def test_gen_overwrite_yes_packet(self):
        assert gen_overwrite_yes_packet() == b"\x06"

    def test_gen_overwrite_no_packet(self):
        assert gen_overwrite_no_packet() == b"\x15"
