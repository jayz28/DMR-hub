#!/usr/bin/python3

import sys
from dmr_utils import ambe_utils
from bitarray import bitarray
from time import time, sleep
from multiprocessing import Pool, Process, Pipe
from io import BytesIO
from functools import partial
from socket import socket, AF_INET, SOCK_DGRAM  #, MSG_DONTWAIT


def main():
   
    tones = ''
    with open('769.bin.ambe', 'rt') as dtmf:
        for line in dtmf:
            tones += '0'*8 + line.rstrip() + '0'*7
    
    dtmf_tones = bitarray(tones)

    data_buffer = b'' 
    silent = bitarray('000000001111100000000001101010011001111110001100111000001')

    sys.stdout.buffer.write(b'.amb')
    sys.stdout.buffer.write(silent.tobytes()*10 + dtmf_tones.tobytes())

    pipe = Pipe()
    p = Process(target=output_process, args=(pipe[0], dtmf_tones))
    p.start()

    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('127.0.0.1', 31000))

    sys.stdout.buffer.flush()

    data = b''
    with Pool(3) as p:
        while True:
            # data = sys.stdin.buffer.read(9*6)
            #try:
            data = sock.recv(9*6) #, MSG_DONTWAIT)
            #except:
                #pass

            if data:
                data_buffer += data
                if len(data_buffer) > 8:  # need 9 bytes for one ambe72 frame
                    io_data = BytesIO(data_buffer)
                    ambe72_frames = iter(partial(io_data.read, 9), b'')
                    ambe49_DSD_frames = p.map(convert_to_DSD, ambe72_frames)
                    pipe[1].send_bytes(b''.join(ambe49_DSD_frames))
                    data_buffer = b''
            else:
                sleep(0.01)

    p.join()


def output_process(input_pipe, tones):
    silent = bitarray('000000001111100000000001101010011001111110001100111000001')

    start = time()
    while True:
        if input_pipe.poll():
            sys.stdout.buffer.write(input_pipe.recv_bytes())
            sys.stdout.buffer.flush()
            start = time()
        else:
            # when no data, output silent frame
            if time() - start > 0.5:
                sys.stdout.buffer.write(silent.tobytes()*20)
                sys.stdout.flush()
                start = time()
            elif time() - start > 9 * 60:
                sys.stdout.buffer.write(tones.tobytes())
                sys.stdout.flush()
                start = time()
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
