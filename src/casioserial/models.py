__all__ = ['Program', 'Picture']


class Program:
    __slots__ = ('name', 'data', 'password')

    def __init__(self, name, data, password=b''):
        self.name = name
        self.data = data
        self.password = password

    def __repr__(self):
        return f'Program({self.name!r}, {len(self.data)}B)'


class Picture:
    __slots__ = ('name', 'data', 'height', 'width')

    def __init__(self, name, data, height=None, width=None):
        self.name = name
        self.data = data
        self.height = height
        self.width = width

    def __repr__(self):
        return f'Picture({self.name!r}, {self.height}x{self.width})'
