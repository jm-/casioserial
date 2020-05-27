import os
import sys
import argparse
from zipfile import ZipFile

from casioserial.g1mfile import G1mFile


# TODO move these to constants file
DEFAULT_CASIO_SERIAL_DEVICE = '/dev/ttyAMA0'
DEFAULT_CASIO_SERIAL_BAUDRATE = 9600
DEFAULT_CASIO_SERIAL_STOPBITS = 1


def casio_serial_transmit(args):
    print('transmitting!')


def casio_serial_receive(args):
    print('receiving!')


def load_arguments():
    parser = argparse.ArgumentParser('casiocom')
    parser.add_argument(
        '-d',
        '--device',
        type=str,
        help='serial device (TTY)',
        default=DEFAULT_CASIO_SERIAL_DEVICE
    )
    parser.add_argument(
        '-b',
        '--baudrate',
        type=int,
        help='baud rate',
        default=DEFAULT_CASIO_SERIAL_BAUDRATE
    )
    parser.add_argument(
        '--stopbits',
        type=int,
        help='stop bits',
        default=DEFAULT_CASIO_SERIAL_STOPBITS
    )
    parser.add_argument(
        '--verbose',
        help='print more info about what is happening',
        action='store_true'
    )

    subparsers = parser.add_subparsers(
        title='actions',
        dest='action',
        required=True
    )

    # transmit action
    transmit_parser = subparsers.add_parser('transmit')
    transmit_parser.add_argument(
        'file',
        type=str,
        help='source g1m file to transmit'
    )
    transmit_parser.add_argument(
        'entries',
        type=str,
        help='names of entries within the g1m file to transmit',
        nargs='*'
    )
    transmit_parser.add_argument(
        '-f',
        '--force',
        help='force overwriting entries that already exist',
        action='store_true'
    )
    transmit_parser.set_defaults(func=casio_serial_transmit)

    # receive action
    receive_parser = subparsers.add_parser('receive')
    receive_parser.add_argument(
        'file',
        type=str,
        help='target g1m file to receive into'
    )
    receive_parser.add_argument(
        '-f',
        '--force',
        help='force overwriting the target g1m file if it exists',
        action='store_true'
    )
    receive_parser.set_defaults(func=casio_serial_receive)

    config = parser.parse_args()
    return config


if __name__ == '__main__':
    # process arguments
    args = load_arguments()
    args.func(args)
