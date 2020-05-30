import os
import sys
import argparse

import casioserial


def casio_serial_transmit(args):
    print(args)

    # check the file exists
    if not os.path.isfile(args.file):
        print(f'Source file {args.file} does not exist or is not a file')
        return 1

    with casioserial.CasioSerialDevice(mode='transmit',
                                       device=args.device,
                                       baudrate=args.baudrate,
                                       stopbits=args.stopbits) as casio_device:
        # establish connection
        print(f'Establishing serial communication with {casio_device}')

        try:
            casio_device.initiate()
        except casioserial.SerialCommunicationException as e:
            print(
                f'A communication exception occurred. '
                f'Make sure the device is connected and in receive mode.'
            )
            return 1

        print(f"Serial communication is established")

        # TODO: open the g1m file

    return 0


def casio_serial_receive(args):
    raise NotImplementedError()
    #print('receiving!')


def load_arguments():
    parser = argparse.ArgumentParser('casiocom')
    parser.add_argument(
        '-d',
        '--device',
        type=str,
        help='serial device (TTY)',
        default=casioserial.DEFAULT_CASIO_SERIAL_DEVICE
    )
    parser.add_argument(
        '-b',
        '--baudrate',
        type=int,
        help='baud rate',
        default=casioserial.DEFAULT_CASIO_SERIAL_BAUDRATE
    )
    parser.add_argument(
        '--stopbits',
        type=int,
        help='stop bits',
        default=casioserial.DEFAULT_CASIO_SERIAL_STOPBITS
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
    sys.exit(args.func(args))
