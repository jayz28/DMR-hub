#!/usr/bin/python3

import sys
from dmr_utils import ambe_utils
from bitarray import bitarray
from time import time, sleep
from multiprocessing import Pool


def main():

    data_buffer = [] 
    sys.stdout.buffer.write(b'.amb')
    with Pool(4) as p:
        while True:
            data = sys.stdin.buffer.read(1024)
            if data:
                data_buffer += [data]
                if len(data_buffer) > 8:  # need 9 bytes for one ambe72 frame
                    ambe49_DSD_frames = p.map(convert_to_DSD, data_buffer)
                    sys.stdout.buffer.write(b''.join(ambe49_DSD_frames))
                    data_buffer = []
            else:
                sleep(0.01)


def convert_to_DSD(frames):

    output = b''
    for ambe72_frame in [frames]:
        ambe72_bits = bitarray()
        ambe72_bits.frombytes(ambe72_frame)

        ambe49_bits = ambe_utils.convert72BitTo49BitAMBE(ambe72_bits)
        tail_bits = bitarray('0' * 7)
        tail_bits[-1] = ambe49_bits[-1]
        ambe49_bits[-1] = 0

        output += b'\x00' + (ambe49_bits + tail_bits).tobytes()

    return output


if __name__ == "__main__":
    main()
