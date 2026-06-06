import pytest
from unittest.mock import call, patch

from casioserial.device import CasioSerialDevice, SerialCommunicationException
from casioserial.models import Program, Picture
from casioserial.protocol import (
    encode_picture,
    gen_end_packet,
    gen_picture_chunk_packet,
    gen_picture_header_packet,
    gen_program_body_packet,
    gen_program_header_packet,
)


@pytest.fixture
def mock_serial():
    with patch("casioserial.device.serial.Serial") as mock_cls:
        yield mock_cls


class TestInit:
    def test_invalid_mode_raises(self, mock_serial):
        with pytest.raises(ValueError):
            CasioSerialDevice("invalid")

    def test_valid_mode_transmit(self, mock_serial):
        dev = CasioSerialDevice("transmit")
        mock_serial.assert_called_once()
        assert dev.mode == "transmit"

    def test_valid_mode_receive(self, mock_serial):
        dev = CasioSerialDevice("receive")
        assert dev.mode == "receive"


class TestStartCommunication:
    def test_happy_path(self, mock_serial):
        mock_serial.return_value.read.return_value = b"\x13"
        dev = CasioSerialDevice("transmit")
        dev.start_communication()
        mock_serial.return_value.write.assert_called_once_with(b"\x16")

    def test_no_response_raises(self, mock_serial):
        mock_serial.return_value.read.return_value = b""
        dev = CasioSerialDevice("transmit")
        with pytest.raises(SerialCommunicationException):
            dev.start_communication()

    def test_wrong_response_raises_and_sends_error_packet(self, mock_serial):
        mock_serial.return_value.read.return_value = b"\xff"
        dev = CasioSerialDevice("transmit")
        with pytest.raises(SerialCommunicationException):
            dev.start_communication()
        written = [c.args[0]
                   for c in mock_serial.return_value.write.call_args_list]
        assert b"\x22" in written


class TestEndCommunication:
    def test_sends_end_packet(self, mock_serial):
        dev = CasioSerialDevice("transmit")
        dev.end_communication()
        mock_serial.return_value.write.assert_called_once_with(
            gen_end_packet())


class TestTransmitProgram:
    def test_normal_flow(self, mock_serial):
        mock_serial.return_value.read.side_effect = [b"\x06", b"\x06"]
        dev = CasioSerialDevice("transmit")
        dev.transmit_program(Program(name=b"TEST", data=b"PROG", password=b""))
        written = [c.args[0]
                   for c in mock_serial.return_value.write.call_args_list]
        assert written[0] == gen_program_header_packet(b"TEST", 4, b"")
        assert written[1] == gen_program_body_packet(b"PROG")

    def test_item_exists_overwrite_true(self, mock_serial):
        # calc replies: item exists, then ack after overwrite-yes, then ack after body
        mock_serial.return_value.read.side_effect = [b"\x21", b"\x06", b"\x06"]
        dev = CasioSerialDevice("transmit")
        dev.transmit_program(
            Program(name=b"TEST", data=b"PROG", password=b""), overwrite=True)
        written = [c.args[0]
                   for c in mock_serial.return_value.write.call_args_list]
        assert written[0] == gen_program_header_packet(b"TEST", 4, b"")
        assert written[1] == b"\x06"  # overwrite-yes
        assert written[2] == gen_program_body_packet(b"PROG")

    def test_item_exists_overwrite_false(self, mock_serial):
        # calc replies: item exists, then ack after overwrite-no
        mock_serial.return_value.read.side_effect = [b"\x21", b"\x06"]
        dev = CasioSerialDevice("transmit")
        dev.transmit_program(
            Program(name=b"TEST", data=b"PROG", password=b""), overwrite=False)
        written = [c.args[0]
                   for c in mock_serial.return_value.write.call_args_list]
        assert written[0] == gen_program_header_packet(b"TEST", 4, b"")
        assert written[1] == b"\x15"  # overwrite-no
        # body packet must NOT be sent
        assert len(written) == 2

    def test_unexpected_header_response_raises(self, mock_serial):
        mock_serial.return_value.read.return_value = b"\xaa"
        dev = CasioSerialDevice("transmit")
        with pytest.raises(SerialCommunicationException):
            dev.transmit_program(Program(name=b"TEST", data=b"PROG", password=b""))
        written = [c.args[0]
                   for c in mock_serial.return_value.write.call_args_list]
        assert b"\x22" in written


class TestTransmitPicture:
    def test_normal_flow(self, mock_serial):
        # ack the header, then ack each of the 4 chunks
        mock_serial.return_value.read.side_effect = [b"\x06"] * 5
        dev = CasioSerialDevice("transmit")
        bitmap = bytes(2048)  # blank 128x128
        dev.transmit_picture(
            Picture(name=b"Picture1", data=bitmap, width=128, height=128))
        written = [c.args[0]
                   for c in mock_serial.return_value.write.call_args_list]
        planes = encode_picture(bitmap, 128, 64)
        assert written[0] == gen_picture_header_packet(b"Picture1", 64, 128, 4)
        assert written[1:] == [gen_picture_chunk_packet(i, planes[i])
                               for i in (1, 2, 3, 4)]

    def test_item_exists_overwrite_false_stops_after_header(self, mock_serial):
        mock_serial.return_value.read.side_effect = [b"\x21", b"\x06"]
        dev = CasioSerialDevice("transmit")
        dev.transmit_picture(
            Picture(name=b"Picture1", data=bytes(2048), width=128, height=128),
            overwrite=False)
        written = [c.args[0]
                   for c in mock_serial.return_value.write.call_args_list]
        assert written[0] == gen_picture_header_packet(b"Picture1", 64, 128, 4)
        assert written[1] == b"\x15"  # overwrite-no
        assert len(written) == 2  # no chunks sent
