# casioserial

Transfer programs and pictures between a computer host and a CASIO fx-series
graphing calculator over its 3-pin serial link.

It comes in two parts:

- **`casiocom`** — a command-line tool for transfers. If you just want
  to copy `.g1m` files to and from your calculator, start here.
- **`casioserial`** — the Python library `casiocom` is built on, for scripting
  transfers or building your own tooling.

Tested against the CASIO fx-9750G PLUS and fx-9860G Slim models. Other fx-series models that use the same link
protocol should work.

## Install

```sh
pip install casioserial
```

## Using the `casiocom` CLI

`casiocom` is installed alongside the library.

### Send a g1m file to the calculator

Put the calculator into receive mode (`MENU → LINK → RECEIVE`), then:

```sh
casiocom -d /dev/ttyAMA0 transmit PROJECT.g1m
```

Send only specific items, by their title inside the container:

```sh
casiocom -d /dev/ttyAMA0 transmit PROJECT.g1m PROG1 PICT5
```

Overwrite items that already exist on the calculator:

```sh
casiocom -d /dev/ttyAMA0 transmit -f PROJECT.g1m
```

### Receive a g1m file from the calculator

Start the receiver, then put the calculator into send mode
(`MENU → LINK → TRANSMIT`):

```sh
casiocom -d /dev/ttyAMA0 receive BACKUP.g1m
```

Use `-f` to overwrite an existing output file.

### Flags

| Flag               | Default        | Meaning                                       |
| ------------------ | -------------- | --------------------------------------------- |
| `-d`, `--device`   | `/dev/ttyAMA0` | Serial device                                 |
| `-b`, `--baudrate` | `9600`         | Baud rate                                     |
| `--stopbits`       | `1`            | Stop bits (1 or 2)                            |
| `--verbose`        | off            | Print protocol and g1m parsing detail         |
| `-f`, `--force`    | off            | Overwrite existing items / the output file    |

The baud rate, parity and stop bits must match the calculator's communication
settings. The defaults (9600 baud, 1 stop bit) match the calculator's factory
settings.

### Example session

```
$ casiocom -d /dev/ttyAMA0 transmit SCUM2.g1m
Establishing serial communication with Casio serial device (/dev/ttyAMA0)
Serial communication is established
Transmitting program SCUM 2.0 (4724B)
Transmitting program SETPSCUM (632B)
Transmitting program SUB (3296B)
Ending serial communication with Casio serial device (/dev/ttyAMA0)
```

Add `--verbose` to see every packet on the wire and per-item detail — including
when an item is skipped because it already exists (re-run with `-f` to
overwrite it).

## Using the library

```python
from casioserial import CasioSerialDevice, Program, g1mfile

# Read programs out of a .g1m container
with g1mfile.G1mFile('SCUM2.g1m', 'r') as g:
    programs = [item for item in g.itemlist()
                if isinstance(item, g1mfile.G1mProgram)]

# Transmit them to a connected calculator (must be in LINK → RECEIVE)
with CasioSerialDevice(mode='transmit', device='/dev/ttyAMA0') as dev:
    dev.start_communication()
    for prog in programs:
        dev.transmit_program(
            Program(name=prog.g1m_title,
                    data=prog.g1m_program,
                    password=prog.g1m_password),
            overwrite=False,
        )
    dev.end_communication()
```

`G1mFile` is a context manager that opens and closes the file;
`CasioSerialDevice` is a context manager that opens and closes the serial port.
`casioserial.SerialCommunicationException` is raised on protocol errors.

In receive mode, `receive_item()` returns `Program` and `Picture` objects (and
`None` once the transfer is finished); `transmit_program()` and
`transmit_picture()` take those same objects.

## The cable

The calculator uses a 3-pole 2.5 mm jack (the SB-62 port). It speaks plain
asynchronous serial at logic levels, so a 3.3 V UART (e.g. the GPIO UART on a
Raspberry Pi, or a 3.3 V USB-to-TTL adapter) can talk to it directly:

```
  Host UART (3.3 V)                  Casio SB-62 jack (2.5 mm, 3-pole)
  ─────────────────                  ─────────────────────────────────
  GND ───────────────────────────────  Sleeve   (ground)
  TXD ───────────────────────────────  Ring     (calculator RX)
  RXD ───┬──[ 100Ω ]─────────────────  Tip      (calculator TX)
         │
         └──[ 220Ω ]──▶│── GND        (▶│ can be an LED to GND)
```

Point `-d/--device` at whichever host serial port you wire up (`/dev/ttyAMA0`,
`/dev/ttyUSB0` etc.).

To drive the calculator from a PC's RS-232 COM port instead, you need a MAX232
to shift the ±12 V RS-232 levels down to logic level. A clear
DB9/MAX232 build writeup is here
<https://www.petervis.com/electronics%20guides/Casio%20Serial%20Cables/Casio%20Serial%20Cable%20Circuit%20Build.html>

## Supported items

- **Programs** — transmit and receive.
- **Pictures** — transmit and receive (stored in the g1m as 128×128 bitmaps).
- Other item types found in a g1m container are skipped with a warning.
