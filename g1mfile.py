import os
import struct

import bitstring


__all__ = ["BadG1mFile", "UnknownG1mItemTypeException", "G1mProgram",
           "G1mPict", "G1mFile"]


class BadG1mFile(Exception):
    pass


class UnknownG1mItemTypeException(Exception):
    pass


# table for G1M character set
G1M_CHARS = b'\x89\x99\xab'
ASCII_CHARS = b'+~!'
G1M_TO_ASCII_TABLE = bytes.maketrans(G1M_CHARS, ASCII_CHARS)
ASCII_TO_G1M_TABLE = bytes.maketrans(ASCII_CHARS, G1M_CHARS)

G1M_ITEM_TYPE_PROGRAM = 0x01
G1M_ITEM_TYPE_PICTURE = 0x07


def translate_g1m_bytes_to_ascii(b: bytes):
    return b.translate(G1M_TO_ASCII_TABLE)


def translate_ascii_bytes_to_g1m(b: bytes):
    return b.translate(ASCII_TO_G1M_TABLE)


class G1mItem():
    """ Base class for items within a g1m file """

    __slots__ = (
        'g1m_title',
        'title',
        'length'    # length of the item body
    )

    def __init__(self, g1m_title: bytes, length: int):
        self.g1m_title = g1m_title
        self.title = str(translate_g1m_bytes_to_ascii(g1m_title), 'ascii')
        self.length = length


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
        self.password = str(translate_g1m_bytes_to_ascii(g1m_password), 'ascii')


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
        #bitstring.Bits(bytes=item_data)


class G1mFile():
    """ Class with methods to open, read, write and close g1m files.

    g = G1mFile(file, mode='r')

    file: Either the path to the file, or a file-like object.
          If it is a path, the file will be opened and closed by G1mFile.
    mode: The mode can be either read 'r' or write 'w'.

    """

    def __init__(self, file, mode='r'):
        if mode not in ('r', 'w'):
            raise ValueError("G1mFile requires mode 'r' or 'w'")

        # debug level
        self.items = []
        self.debug = 0
        self.mode = mode

        if isinstance(file, os.PathLike):
            file = os.fspath(file)
        if isinstance(file, str):
            # file is a filename, get the stream
            self.filename = file
            mode_dict = {'r': 'rb', 'w': 'wb'}
            filemode = mode_dict[mode]
            self.fp = open(file, filemode)
        else:
            # file is a stream
            self.fp = file
            self.filename = getattr(file, 'name', None)

        try:
            if mode == 'r':
                self._read_contents()
        except:
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

        (   file_identifier,
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


    def _read_program(self, item_title, item_length):
        # read the item data as program data
        item_program = self.fp.read(item_length)

        program = G1mProgram(
            item_title.partition(b'\x00')[0],
            item_length,
            item_program[10:],
            item_program[:8].partition(b'\x00')[0]
        )
        return program


    def _read_picture(self, item_title, item_length):
        # read the item data as picture data
        item_picture = self.fp.read(item_length)

        picture = G1mPicture(
            item_title.partition(b'\x00')[0],
            item_length,
            item_picture
        )
        return picture


    def _read_item(self):
        item_header_1 = self.fp.read(20)

        (   item_identifier,
            sub_item_count
        ) = struct.unpack('>16sI', item_header_1)

        if self.debug > 0:
            print(f'item_identifier={item_identifier}')
            print(f'sub_item_count={sub_item_count}')

        # make sure the subitem count is 1,
        # so that item_header_2 can be safely decoded
        assert sub_item_count == 0x01

        item_header_2 = self.fp.read(24)

        (   mem_location_name,
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

        # make sure the item is a program
        if item_type_identifier == G1M_ITEM_TYPE_PROGRAM:
            return self._read_program(item_title, item_length)

        elif item_type_identifier == G1M_ITEM_TYPE_PICTURE:
            return self._read_picture(item_title, item_length)

        else:
            raise UnknownG1mItemTypeException(f"{item_type_identifier}")


    def _read_contents(self):
        # read header, then items from self.fp
        num_items = self._read_header()
        for item_num in range(num_items):
            item = self._read_item()
            self.items.append(item)


    def itemlist(self):
        return self.items


    def close(self):
        if self.fp is None:
            return

        try:
            if self.mode == 'w':
                self._write_header()
        finally:
            self.fp.close()
