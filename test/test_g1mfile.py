import io
import struct

import bitstring
import pytest

from casioserial.g1mfile import (
    G1mFile,
    G1mItem,
    G1mPicture,
    G1mProgram,
    translate_ascii_bytes_to_g1m,
    translate_g1m_bytes_to_ascii,
)


def _make_g1m_bytes(items):
    """Build a minimal valid in-memory G1M file.

    items: list of (title, password, data, type_byte)
      - For type 0x01 (program): item_data = password[:8].ljust(8) + \\x00\\x00 + data
      - For other types: item_data = data as-is
    Returns bytes suitable for wrapping in BytesIO.
    """
    raw_items = []
    for title, password, data, type_byte in items:
        if type_byte == 0x01:
            item_data = password.ljust(8, b"\x00") + b"\x00\x00" + data
        else:
            item_data = data
        item_length = len(item_data)
        item_header = struct.pack(
            ">8s8sBI3s",
            b"\x00" * 8,
            title.ljust(8, b"\x00"),
            type_byte,
            item_length,
            b"\x00\x00\x00",
        )
        raw_items.append(item_header + item_data)

    group_header = struct.pack(">16sI", b"\x00" * 16, len(items))
    body = group_header + b"".join(raw_items)

    file_size = 32 + len(body)
    lsb = file_size % 256
    ctrl1 = (lsb + 0x41) % 256
    ctrl2 = (lsb + 0xB8) % 256

    header_plain = struct.pack(
        ">8sB5sB1sIB9sH",
        b"USBPower",
        0x62,
        b"\x00\x10\x00\x10\x00",
        ctrl1,
        b"\x01",
        file_size,
        ctrl2,
        b"\x00" * 9,
        len(items),
    )
    header_inverted = (~bitstring.Bits(bytes=header_plain)).tobytes()
    return header_inverted + body


class TestTranslation:
    def test_g1m_to_ascii_plus(self):
        assert translate_g1m_bytes_to_ascii(b"\x89") == b"+"

    def test_g1m_to_ascii_tilde(self):
        assert translate_g1m_bytes_to_ascii(b"\x99") == b"~"

    def test_g1m_to_ascii_exclaim(self):
        assert translate_g1m_bytes_to_ascii(b"\xab") == b"!"

    def test_ascii_to_g1m_plus(self):
        assert translate_ascii_bytes_to_g1m(b"+") == b"\x89"

    def test_ascii_to_g1m_tilde(self):
        assert translate_ascii_bytes_to_g1m(b"~") == b"\x99"

    def test_ascii_to_g1m_exclaim(self):
        assert translate_ascii_bytes_to_g1m(b"!") == b"\xab"

    def test_roundtrip(self):
        original = b"\x89\x99\xab"
        assert translate_ascii_bytes_to_g1m(
            translate_g1m_bytes_to_ascii(original)) == original

    def test_passthrough(self):
        data = b"HELLO\x00\xff"
        assert translate_g1m_bytes_to_ascii(data) == data


class TestG1mItem:
    def test_title_ascii(self):
        assert G1mItem(b"TEST", 100).title == "TEST"

    def test_title_special_char_decoded(self):
        assert G1mItem(b"\x89", 1).title == "+"

    def test_length_stored(self):
        assert G1mItem(b"X", 42).length == 42

    def test_repr(self):
        assert repr(G1mItem(b"TEST", 100)) == "TEST (100B)"


class TestG1mProgram:
    def test_attributes_stored(self):
        prog = G1mProgram(b"PROG", 50, b"\x89\x99", b"PASS")
        assert prog.g1m_program == b"\x89\x99"
        assert prog.program_length == 2
        assert prog.g1m_password == b"PASS"
        assert prog.password == "PASS"

    def test_password_g1m_chars_decoded(self):
        prog = G1mProgram(b"P", 1, b"", b"\x89")
        assert prog.password == "+"

    def test_title_inherited(self):
        prog = G1mProgram(b"MYPROG", 10, b"CODE", b"")
        assert prog.title == "MYPROG"


class TestG1mPicture:
    def test_attributes_stored(self):
        pic = G1mPicture(b"PIC", 8, b"\xAB" * 8)
        assert pic.g1m_picture == b"\xAB" * 8
        assert pic.picture_length == 8

    def test_title_inherited(self):
        pic = G1mPicture(b"MYPIC", 4, b"\x00" * 4)
        assert pic.title == "MYPIC"


class TestG1mFile:
    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            G1mFile(io.BytesIO(b""), mode="x")

    def test_read_single_program(self):
        data = _make_g1m_bytes([(b"TEST", b"", b"HELLO", 0x01)])
        g = G1mFile(io.BytesIO(data))
        assert len(g.items) == 1
        assert isinstance(g.items[0], G1mProgram)
        assert g.items[0].title == "TEST"
        assert g.items[0].g1m_program == b"HELLO"

    def test_read_program_with_password(self):
        data = _make_g1m_bytes([(b"SECURED", b"PASS", b"CODE", 0x01)])
        g = G1mFile(io.BytesIO(data))
        assert g.items[0].password == "PASS"
        assert g.items[0].g1m_program == b"CODE"

    def test_read_program_itemlist(self):
        data = _make_g1m_bytes([(b"P", b"", b"X", 0x01)])
        g = G1mFile(io.BytesIO(data))
        assert g.itemlist() is g.items

    def test_read_unknown_item_type_yields_none(self):
        data = _make_g1m_bytes([(b"UNK", b"", b"\x00" * 4, 0x99)])
        g = G1mFile(io.BytesIO(data))
        assert len(g.items) == 1
        assert g.items[0] is None

    def test_corrupt_header_raises(self):
        data = bytearray(_make_g1m_bytes([(b"TEST", b"", b"X", 0x01)]))
        # Flip one bit in the on-disk ctrl1 byte (offset 14).
        # After _read_header inverts, the recovered ctrl1 will be wrong.
        data[14] ^= 0x01
        with pytest.raises(AssertionError):
            G1mFile(io.BytesIO(bytes(data)))


class TestG1mFileWrite:
    def _write_and_read_back(self, items):
        buf = io.BytesIO()
        with G1mFile(buf, mode='w') as g:
            g.items = items
        buf.seek(0)
        return G1mFile(buf, mode='r')

    def test_program_roundtrip_title(self):
        prog = G1mProgram(b"MYPROG", 10 + 5, b"HELLO", b"")
        g = self._write_and_read_back([prog])
        assert g.items[0].g1m_title == b"MYPROG"

    def test_program_roundtrip_data(self):
        prog = G1mProgram(b"MYPROG", 10 + 5, b"HELLO", b"")
        g = self._write_and_read_back([prog])
        assert g.items[0].g1m_program == b"HELLO"

    def test_program_roundtrip_password(self):
        prog = G1mProgram(b"MYPROG", 10 + 4, b"CODE", b"PASS")
        g = self._write_and_read_back([prog])
        assert g.items[0].g1m_password == b"PASS"

    def test_program_roundtrip_empty_password(self):
        prog = G1mProgram(b"NOPW", 10 + 3, b"DAT", b"")
        g = self._write_and_read_back([prog])
        assert g.items[0].g1m_password == b""

    def test_multiple_programs(self):
        progs = [
            G1mProgram(b"PROG1", 10 + 4, b"AAAA", b""),
            G1mProgram(b"PROG2", 10 + 4, b"BBBB", b""),
        ]
        g = self._write_and_read_back(progs)
        assert len(g.items) == 2
        assert g.items[0].g1m_title == b"PROG1"
        assert g.items[1].g1m_title == b"PROG2"

    def test_picture_roundtrip(self):
        raw = b"\xAB" * 4096
        pic = G1mPicture(b"PIC1", len(raw), raw)
        g = self._write_and_read_back([pic])
        assert isinstance(g.items[0], G1mPicture)
        assert g.items[0].g1m_title == b"PIC1"
        assert g.items[0].g1m_picture == raw

    def test_empty_items_writes_valid_file(self):
        g = self._write_and_read_back([])
        assert g.items == []
