import os


class G1mFile():
    """ Class with methods to open, read, write, close, list g1m files.

    g = G1mFile(file, mode='r')

    file: Either the path to the file, or a file-like object.
          If it is a path, the file will be opened and closed by G1mFile.
    mode: The mode can be either read 'r' or write 'w'.

    """

    def __init__(self, file, mode='r'):
        if mode not in ('r', 'w'):
            raise ValueError("G1mFile requires mode 'r' or 'w'")

        # debug level
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


    def close(self):
        if self.fp is None:
            return

        try:
            if self.mode == 'w':
                self._write_header()
        finally:
            self.fp.close()
