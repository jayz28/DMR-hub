#!/usr/bin/python3
from bitarray import bitarray
from dmr_utils import ambe_utils

import sys


def main():
    with open('test.ambe72', 'rb') as infile:
        padding = bitarray('0' * 8)
        tail = bitarray('0' * 7)
        sys.stdout.buffer.write(b'.amb')
        while True:
            ambe72 = infile.read(9)

            if not ambe72:
                break

            x = bitarray()
            x.frombytes(ambe72)

            ambe49 = ambe_utils.convert72BitTo49BitAMBE(x)
            tail[-1] = ambe49[-1]  # set the final bit
            ambe49[-1] = 0 


            padded49 = padding + ambe49 + tail

            # print(padded49.to01(), file=sys.stderr)
            # assert len(padded49) == 64 

            sys.stdout.buffer.write(padded49.tobytes())
            sys.stdout.flush()

    # print('all done', file=sys.stderr)
if __name__ == '__main__':
    main()
