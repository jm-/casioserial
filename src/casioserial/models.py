from .charset import casio_to_str

__all__ = ['Program', 'Picture']


class Program:
    __slots__ = ('name', 'data', 'password')

    def __init__(self, name, data, password=b''):
        self.name = name
        self.data = data
        self.password = password

    def __repr__(self):
        return f'Program({casio_to_str(self.name)}, {len(self.data)}B)'


class Picture:
    __slots__ = ('name', 'data', 'height', 'width')

    def __init__(self, name, data, height=None, width=None):
        self.name = name
        self.data = data
        self.height = height
        self.width = width

    def __repr__(self):
        return f'Picture({casio_to_str(self.name)}, {self.height}\u00d7{self.width})'

    def to_ascii(self, on='#', off='.'):
        """Render the bitmap as ASCII art (row-major, MSB = leftmost pixel)."""
        row_bytes = self.width // 8
        lines = []
        for y in range(self.height):
            row = self.data[y * row_bytes:(y + 1) * row_bytes]
            lines.append(''.join(
                on if (byte >> (7 - bit)) & 1 else off
                for byte in row for bit in range(8)
            ))
        return '\n'.join(lines)
