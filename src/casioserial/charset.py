__all__ = [
    'CASIO_TO_LATIN_TABLE', 'LATIN_TO_CASIO_TABLE',
    'casio_to_str', 'str_to_casio',
]

CASIO_CHARS = b'\x89\x99\xa9\xb9\xa8\xab'
LATIN_CHARS = b'+-\xd7\xf7^!'
CASIO_TO_LATIN_TABLE = bytes.maketrans(CASIO_CHARS, LATIN_CHARS)
LATIN_TO_CASIO_TABLE = bytes.maketrans(LATIN_CHARS, CASIO_CHARS)


def casio_to_str(b: bytes) -> str:
    return b.translate(CASIO_TO_LATIN_TABLE).decode('latin-1')


def str_to_casio(s: str) -> bytes:
    return s.encode('latin-1').translate(LATIN_TO_CASIO_TABLE)
