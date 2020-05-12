import os
import sys
import time

import serial


CASIO_TTY_DEVICE = os.environ.get('CASIO_TTY_DEVICE', '/dev/ttyAMA0')



def recv():
    print(f'opening serial device {CASIO_TTY_DEVICE}')
    ser = serial.Serial(
        CASIO_TTY_DEVICE,
        baudrate=17860,
        bytesize=8,
        parity='N',
        stopbits=1
    )

    try:
        b = ser.read(1)
        if b:
            print(f'0x{b.hex()}')

        if b == b'\x16':
            # ack it
            ser.write(b'\x13')
        else:
            print('unexpected, exiting')
            return


        b = ser.read(50)
        if b:
            print(f'0x{b.hex()}')


        ser.write(b'\x06')


        while True:
            b = ser.read(1)
            if b:
                print(f'0x{b.hex()}')
    except KeyboardInterrupt:
        pass
    finally:
        print(f'closing serial device {CASIO_TTY_DEVICE}')
        ser.close()


def send():
    print(f'opening serial device {CASIO_TTY_DEVICE}')
    ser = serial.Serial(
        CASIO_TTY_DEVICE,
        baudrate=17860,
        bytesize=8,
        parity='N',
        stopbits=1
    )

    print('@ writing 0x16')
    ser.write(b'\x16')

    b = ser.read(1)
    if b:
        print(f'0x{b.hex()}')

    time.sleep(0.01)

    print('@ writing TXT PG packet')
    ser.write(b':TXT')

    print('idling')
    try:
        while True:
            b = ser.read(1)
            if b:
                print(f'0x{b.hex()}')
    except KeyboardInterrupt:
        pass
    finally:
        print(f'closing serial device {CASIO_TTY_DEVICE}')
        ser.close()


if __name__ == '__main__':
    if sys.argv[1] == 'recv':
        recv()
    elif sys.argv[1] == 'send':
        send()
    else:
        print('invalid. use send/recv')
