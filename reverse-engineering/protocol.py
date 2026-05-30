import os
import sys
import time
import struct

import serial


CASIO_TTY_DEVICE = os.environ.get('CASIO_TTY_DEVICE', '/dev/ttyAMA0')
CASIO_TTY_BAUDRATE = os.environ.get('CASIO_TTY_BAUDRATE', '9600')
CASIO_TTY_STOPBITS = os.environ.get('CASIO_TTY_STOPBITS', '1')

def recv():
    print(f'opening serial device {CASIO_TTY_DEVICE}')
    ser = serial.Serial(
        CASIO_TTY_DEVICE,
        baudrate=int(CASIO_TTY_BAUDRATE),
        bytesize=8,
        parity='N',
        stopbits=int(CASIO_TTY_STOPBITS)
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
            data_pkt_length, prog_name_raw, unused0, prog_password_raw = struct.unpack('>H8s8s8s', b[9:35])
            prog_name = prog_name_raw.rstrip(b'\xff')
            prog_length = data_pkt_length - 3
            prog_password = prog_password_raw.rstrip(b'\xff')
            print(f'DBG: prog_name={prog_name} prog_length={prog_length} prog_password={prog_password}')

        # 0x21 means already exists. the calc will ask the user to confirm overwrite
        ser.write(b'\x21')
        # 0x06 means ack, please send data
        #ser.write(b'\x06')

        b = ser.read(1)
        if b == b'\x06':
            # ack it
            ser.write(b'\x06')
        else:
            print('unexpected, exiting')
            return


















        # 0x22 means error (COM/Receive). communication is terminated

        # # read the program data
        # b = ser.read(data_pkt_length)
        # if b:
        #     print(f'0x{b.hex()}')

        # # send another 0x06 ack
        # ser.write(b'\x06')

        # # read the end pkt
        # b = ser.read(50)
        # if b[:4] == b':END':
        #     print(f'0x{b.hex()}')
        #     print('recv complete, exiting')
        #     return

        print('idling')
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
        baudrate=int(CASIO_TTY_BAUDRATE),
        bytesize=8,
        parity='N',
        stopbits=int(CASIO_TTY_STOPBITS)
    )

    try:
        print('@ writing 0x16')
        # 0x16 means request
        ser.write(b'\x16')

        b = ser.read(1)
        print(f'0x{b.hex()}')
        if b == b'\x13':
            # 0x13 means ack. we can proceed
            print(f'0x{b.hex()}')
        else:
            print('unexpected, exiting')
            return

        print('@ writing TXT PG packet')
        ser.write(
            b'\x3a\x54\x58\x54\x00\x50\x47\x00\x00\x01\x88\x52\x4f\x55\x4c\x45'
            b'\x54\x54\x46\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\x4e\x4c\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xed'
        )


        # use this code to overwrite if it exists
        #b = ser.read(1)
        #if b == b'\x21':
        #    # 0x21 means exists
        #    print(f'0x{b.hex()}')
        #else:
        #    print('unexpected, exiting')
        #    return

        # print('@ writing 0x15')
        # # 0x15 means NO, don't overwrite
        # ser.write(b'\x15')

        #print('@ writing 0x06')
        # 0x06 means YES, do overwrite
        #ser.write(b'\x06')




        b = ser.read(1)
        if b == b'\x06':
            # 0x06 means ok to start sending
            print(f'0x{b.hex()}')
        else:
            print('unexpected, exiting')
            return

        print('@ writing program data')
        ser.write(
            b'\x3a\x22\x42\x41\x4e\x4b\x22\x3f\x0e\x59\x0d\x59\x0e\x4d\x0d\x31'
            b'\x0e\x4c\x0d\x31\x0e\x4b\x0d\x31\x0e\x54\x0d\x30\x0e\x57\x0d\x31'
            b'\x0e\x4a\x0d\x31\x0e\x4e\x0d\x31\x0e\x4c\x0d\xe2\x30\x0d\x30\x0e'
            b'\x42\x0d\xf7\x0a\x0d\x27\x22\x42\x45\x54\x22\x3f\x0e\x42\x0d\xf7'
            b'\x00\x4d\x3e\x28\x59\x89\x32\x30\x29\x0d\xf7\x01\x31\x0e\x57\x0d'
            b'\xf7\x03\x0d\xf7\x00\x42\x3e\x4d\x0d\xf7\x01\x31\x0e\x4a\x0d\x31'
            b'\x0e\x4b\x0d\x31\x0e\x4c\x0d\xf7\x03\x0d\xf7\x00\x4d\x3c\x31\x0d'
            b'\xf7\x01\x4e\x89\x31\x0e\x4e\x0d\x59\x0e\x4d\x0d\x31\x0e\x4a\x0d'
            b'\x31\x0e\x4b\x0d\x31\x0e\x4c\x0d\xf7\x03\x0d\x4c\x0e\x42\x0d\xf7'
            b'\x0b\x42\x3e\x4d\x7f\xb1\x42\x10\x30\x7f\xb1\x42\x3e\x31\x30\x30'
            b'\x30\x0d\xde\x33\x37\xc1\x89\x31\x0e\x52\x0d\x4d\x99\x42\x0e\x4d'
            b'\x0d\x27\xf7\x10\x31\x2c\x31\x2c\x22\x42\x41\x4e\x4b\x3a\x22\x20'
            b'\x20\x20\x20\x20\x20\x22\x0d\x27\xf7\x10\x37\x2c\x31\x2c\x4d\x0d'
            b'\x27\x22\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99'
            b'\x99\x99\x99\x99\x99\x99\x99\x22\x0d\xf7\x00\x52\x10\x31\x32\x0d'
            b'\xf7\x01\x27\xf7\x10\x31\x2c\x33\x2c\x22\x57\x49\x4e\xab\x20\x22'
            b'\x0d\x4d\x89\x33\x42\x0e\x4d\x0d\x31\x0e\x4a\x0d\x31\x0e\x4b\x0d'
            b'\x31\x0e\x4c\x0d\x31\x0e\x42\x0d\xf7\x02\x27\xf7\x10\x31\x2c\x33'
            b'\x2c\x22\x4c\x4f\x53\x45\xab\x22\x0d\x4a\x89\x4b\x0e\x4c\x0d\x4b'
            b'\x0e\x4a\x0d\x4c\x0e\x4b\x0d\xf7\x03\x0d\xf7\x10\x31\x2c\x35\x2c'
            b'\x54\xb9\x4e\x0d\xf7\x04\x31\x0e\x46\xf7\x05\x35\x30\x0d\xf7\x07'
            b'\x0d\xe2\x35\x0d\xf7\x00\x57\x3d\x31\x0d\xf7\x01\x59\x0e\x4d\x0d'
            b'\x31\x0e\x4a\x0d\x31\x0e\x4b\x0d\x31\x0e\x4c\x0d\x31\x0e\x42\x0d'
            b'\x54\x89\x31\x0e\x54\x0d\x4e\x89\x31\x0e\x4e\x0d\x30\x0e\x57\x0d'
            b'\xf7\x03\x0d\xec\x30\x0d\xff\x89'
        )

        b = ser.read(1)
        if b == b'\x06':
            # 0x06 means ok
            print(f'0x{b.hex()}')
        else:
            print('unexpected, exiting')
            return

        print('@ writing END packet')
        ser.write(
            b'\x3a\x45\x4e\x44\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\x56'
        )

        print('@ done.')
        return


        print('idling')
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
