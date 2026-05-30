import os
import sys
import argparse

from . import (
    CasioSerialDevice,
    SerialCommunicationException,
    DEFAULT_CASIO_SERIAL_DEVICE,
    DEFAULT_CASIO_SERIAL_BAUDRATE,
    DEFAULT_CASIO_SERIAL_STOPBITS,
)
from . import g1mfile


def casio_serial_transmit(args):
    print(args)

    # check the file exists
    if not os.path.isfile(args.file):
        print(f'Source file {args.file} does not exist or is not a file')
        return 1

    # storage for what items were transmitted
    transmitted_item_names = []

    with CasioSerialDevice(mode='transmit',
                           device=args.device,
                           baudrate=args.baudrate,
                           stopbits=args.stopbits) as casio_device:
        # establish connection
        print(f'Establishing serial communication with {casio_device}')

        try:
            casio_device.start_communication()
        except SerialCommunicationException as e:
            print(
                f'A communication exception occurred. '
                f'Make sure the device is connected and in receive mode.'
            )
            return 1

        print(f"Serial communication is established")

        # open the g1m file
        with g1mfile.G1mFile(args.file, 'r',
                             debug=(1 if args.verbose else 0)) as g:
            for item in g.itemlist():
                # check if this item should be transmitted
                if args.itemnames and item.title not in args.itemnames:
                    print(f'Skipping transmission of {item}: not specified')
                    continue

                # check that the type is transmittable
                if not type(item) in (g1mfile.G1mProgram, g1mfile.G1mPicture):
                    print(f'Skipping transmission of {item}: not supported')
                    continue

                if type(item) is g1mfile.G1mProgram:
                    print(f'Transmitting program {item}')
                    casio_device.transmit_program(name=item.g1m_title,
                                                  program=item.g1m_program,
                                                  password=item.g1m_password,
                                                  overwrite=args.force)

                elif type(item) is g1mfile.G1mPicture:
                    print(f'Transmitting picture {item}')

                transmitted_item_names.append(item.title)

        print(f"Ending serial communication with {casio_device}")
        casio_device.end_communication()

        # TODO check that all specified items were transmitted

    return 0


def casio_serial_receive(args):
    raise NotImplementedError()
    # print('receiving!')


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
        'itemnames',
        type=str,
        help='names of items within the g1m file to transmit',
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


def main():
    args = load_arguments()
    sys.exit(args.func(args))


if __name__ == '__main__':
    main()
