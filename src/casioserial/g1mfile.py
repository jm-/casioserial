import os
import struct

import bitstring

from .charset import casio_to_str


__all__ = ["BadG1mFile", "UnknownG1mItemTypeException",
           "G1mItem", "G1mProgram", "G1mPicture", "G1mFile"]


class BadG1mFile(Exception):
    pass


class UnknownG1mItemTypeException(Exception):
    pass


G1M_ITEM_TYPE_PROGRAM = 0x01
G1M_ITEM_TYPE_PICTURE = 0x07


class G1mItem():
    """ Base class for items within a g1m file """

    __slots__ = (
        'g1m_title',
        'title',
        'length'    # length of the item body
    )

    def __init__(self, g1m_title: bytes, length: int):
        self.g1m_title = g1m_title
        self.title = casio_to_str(g1m_title)
        self.length = length

    def __repr__(self):
        return f'{self.title} ({self.length}B)'


class G1mProgram(G1mItem):
    """ Class to describe a program item """

    __slots__ = (
        'g1m_program',
        'program_length',
        'g1m_password',
        'password'
    )

    def __init__(self, g1m_title: bytes, length: int, g1m_program: bytes,
                 g1m_password: bytes):
        super().__init__(g1m_title, length)
        self.g1m_program = g1m_program
        self.program_length = len(g1m_program)
        self.g1m_password = g1m_password
        self.password = casio_to_str(g1m_password)


class G1mPicture(G1mItem):
    """ Class to describe a picture item """

    __slots__ = (
        'g1m_picture',
        'picture_length',
    )

    def __init__(self, g1m_title: bytes, length: int, g1m_picture: bytes):
        super().__init__(g1m_title, length)
        self.g1m_picture = g1m_picture
        self.picture_length = len(g1m_picture)
        # bitstring.Bits(bytes=item_data)


class G1mFile():
    """ Class with methods to open, read, write and close g1m files.

    g = G1mFile(file, mode='r')

    file: Either the path to the file, or a file-like object.
          If it is a path, the file will be opened and closed by G1mFile.
    mode: The mode can be either read 'r' or write 'w'.

    """

    def __init__(self, file, mode='r', debug=0):
        if mode not in ('r', 'w'):
            raise ValueError("G1mFile requires mode 'r' or 'w'")

        # debug level
        self.items = []
        self.debug = debug
        self.mode = mode

        if isinstance(file, os.PathLike):
            file = os.fspath(file)
        if isinstance(file, str):
            # file is a filename; G1mFile owns the stream lifetime
            self._owns_fp = True
            self.filename = file
            mode_dict = {'r': 'rb', 'w': 'wb'}
            filemode = mode_dict[mode]
            self.fp = open(file, filemode)
        else:
            # file is a stream; caller owns the stream lifetime
            self._owns_fp = False
            self.fp = file
            self.filename = getattr(file, 'name', None)

        try:
            if mode == 'r':
                self._read_contents()
        except:
            if self._owns_fp:
                self.fp.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _read_header(self):
        header_bytes = self.fp.read(32)
        header_bits = bitstring.Bits(bytes=header_bytes)

        header_i_bits = ~header_bits
        header_i_bytes = header_i_bits.tobytes()

        (file_identifier,
            file_type_identifier,
            magic_sequence_1,
            control_byte_1,
            magic_sequence_2,
            total_file_size,
            control_byte_2,
            reserved_sequence_1,
            num_items
         ) = struct.unpack('>8sB5sB1sIB9sH', header_i_bytes)

        if self.debug > 0:
            print(f'file_identifier={file_identifier}')
            print(f'file_type_identifier={file_type_identifier}')
            print(f'total_file_size={total_file_size}')
            print(f'num_items={num_items}')

        # validate the control bytes
        lsb = total_file_size % 256
        assert (lsb + 0x41) % 256 == control_byte_1
        assert (lsb + 0xb8) % 256 == control_byte_2

        # validate magic sequences
        assert magic_sequence_1 == b'\x00\x10\x00\x10\x00'
        assert magic_sequence_2 == b'\x01'

        return num_items

    def _write_header(self, num_items):
        # writes the g1m header to the first 32 bytes.
        # assumes the current stream position is at the end of the file
        total_file_size = self.fp.tell()
        # rewind
        self.fp.seek(0, 0)

        # calculate the control bytes
        lsb = total_file_size % 256
        control_byte_1 = (lsb + 0x41) % 256
        control_byte_2 = (lsb + 0xb8) % 256

        # pack header
        header_i_bytes = struct.pack(
            '>8sB5sB1sIB9sH',
            b'USBPower',
            0x31,
            b'\x00\x10\x00\x10\x00',
            control_byte_1,
            b'\x01',
            total_file_size,
            control_byte_2,
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff',
            num_items
        )
        # invert the header bits
        header_i_bits = bitstring.Bits(bytes=header_i_bytes)
        header_bits = ~header_i_bits
        header_bytes = header_bits.tobytes()

        self.fp.write(header_bytes)

    def _read_program(self, item_title, item_length, item_data):
        program = G1mProgram(
            item_title.rstrip(b'\x00'),
            item_length,
            item_data[10:].rstrip(b'\x00'),
            item_data[:8].rstrip(b'\x00')
        )
        return program

    def _write_program(self, item):
        # write header 1
        # item_identifier
        self.fp.write(b'PROGRAM\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        # sub_item_count
        self.fp.write(b'\x00\x00\x00\x01')

        # write header 2
        # mem_location_name
        self.fp.write(b'system\x00\x00')
        # item_title
        self.fp.write(item.g1m_title.ljust(8, b'\x00'))
        # item_type_identifier
        self.fp.write(b'\x01')
        # item_length
        # this needs to be written at the end
        # store the stream position now and write an empty placeholder
        item_length_stream_position = self.fp.tell()
        self.fp.write(b'\x00\x00\x00\x00')
        # reserved_sequence
        self.fp.write(b'\x00\x00\x00')

        # store the stream position now so we can calculate the item_length
        pre_program_stream_position = self.fp.tell()
        # password
        self.fp.write(item.g1m_password.ljust(8, b'\x00'))
        # alignment
        self.fp.write(b'\x00\x00')
        # write program data
        self.fp.write(item.g1m_program)

        # calculate item_length
        post_program_stream_position = self.fp.tell()
        item_length = post_program_stream_position - pre_program_stream_position
        # pad to nearest 4 bytes
        pad_length = 4 - (item_length % 4)
        if pad_length > 0:
            self.fp.write(b'\x00' * pad_length)
            item_length += pad_length
            post_program_stream_position += pad_length

        # rewind to write item_length
        self.fp.seek(item_length_stream_position, 0)
        self.fp.write(struct.pack('>I', item_length))

        # seek back
        self.fp.seek(post_program_stream_position, 0)

    def _read_picture(self, item_title, item_length, item_data):
        picture = G1mPicture(
            item_title.rstrip(b'\x00'),
            item_length,
            item_data
        )
        return picture

    def _write_pict(self, item):
        # write header 1
        # item_identifier
        self.fp.write(b'PROGRAM\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        # sub_item_count
        self.fp.write(b'\x00\x00\x00\x01')

        # write header 2
        # mem_location_name
        self.fp.write(b'system\x00\x00')
        # item_title
        self.fp.write(item.g1m_title.ljust(8, b'\x00'))
        # item_type_identifier
        self.fp.write(b'\x07')
        # item_length
        self.fp.write(struct.pack('>I', item.picture_length))
        # reserved_sequence
        self.fp.write(b'\x00\x00\x00')

        # write pixel data
        self.fp.write(item.g1m_picture)

    def _read_item(self):
        item_header_2 = self.fp.read(24)

        (mem_location_name,
            item_title,
            item_type_identifier,
            item_length,
            reserved_sequence
         ) = struct.unpack('>8s8sBI3s', item_header_2)

        if self.debug > 0:
            print(f'mem_location_name={mem_location_name}')
            print(f'item_title={item_title}')
            print(f'item_type_identifier={item_type_identifier}')
            print(f'item_length={item_length}')
            print(f'reserved_sequence={reserved_sequence}')

        item_data = self.fp.read(item_length)

        if item_type_identifier == G1M_ITEM_TYPE_PROGRAM:
            return self._read_program(item_title, item_length, item_data)

        elif item_type_identifier == G1M_ITEM_TYPE_PICTURE:
            return self._read_picture(item_title, item_length, item_data)

        else:
            print(f'Unknown G1M Item Type: {item_type_identifier}')
            return None
            # raise UnknownG1mItemTypeException(f"{item_type_identifier}")

    def _read_items(self):
        item_header_1 = self.fp.read(20)

        (item_identifier,
            sub_item_count
         ) = struct.unpack('>16sI', item_header_1)

        if self.debug > 0:
            print(f'item_identifier={item_identifier}')
            print(f'sub_item_count={sub_item_count}')

        for sub_item_number in range(sub_item_count):
            yield self._read_item()

    def _read_contents(self):
        # read header, then items from self.fp
        num_items = self._read_header()
        while len(self.items) < num_items:
            self.items.extend(self._read_items())

    def _write_items(self, items):
        # skip the header til last; we need to write the filesize
        self.fp.write(b'\x00' * 32)
        # write items
        items_written = 0
        for item in items:
            if type(item) is G1mProgram:
                self._write_program(item)
                items_written += 1
            elif type(item) is G1mPicture:
                self._write_pict(item)
                items_written += 1
            else:
                # undefined, skip
                pass
        # g1m header can be written
        self._write_header(items_written)

    def itemlist(self):
        return self.items

    def close(self):
        if self.fp is None:
            return

        try:
            if self.mode == 'w':
                self._write_items(self.items)
        finally:
            # make close() idempotent
            fp = self.fp
            self.fp = None
            if self._owns_fp:
                fp.close()
