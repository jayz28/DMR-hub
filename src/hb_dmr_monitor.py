#!/usr/bin/python3

import socket
import hashlib
import sys
import time
from dmr_utils import ambe_utils
from bitarray import bitarray 

global outfile

def main(args):
    global outfile


    master = '3103.repeater.net'
    port = 62030
    dmr_id = b'002F8A49'
    password = b'passw0rd'

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    sock.connect((master, port))
    out_sock.connect(('127.0.0.1', 31000))  # assume analog bridge listening on 31000

    sock.send(b'RPTL'+dmr_id)
    salt = udp_receive(sock, True)[-8:]

    key = hashlib.sha256(salt + password).hexdigest().encode('ascii')

    sock.send(b'RPTK' + dmr_id + key)

    config = b'RPTC' + b'KJ7BKP  ' + dmr_id + b'0'*9 + b'0'*9 + b'00' + b'01' + b'47.67689' + b'-122.2059' + b'000' +\
             f"{'Kirkland, WA':<20}".encode('ascii') + b' '*20 + b' '*124 + f"{'HB_HUB_V1':<40}".encode('ascii') + b' '*40

    print(len(config))

    sock.send(config)
    start = time.time()

    spin = '-\|/'
    idx = 0

    sendall = out_sock.sendall
    sendall(b'.amb')

    while True:
        data = udp_receive(sock)
        if data and 'DMRD' in str(data):
            ambe49_DSD = process_burst(data)
            sendall(ambe49_DSD, socket.MSG_DONTWAIT)
        else:
            if time.time() - start > 15:
                sock.send(b'MSTPING' + dmr_id)
                start = time.time()
            else:
                sys.stdout.write(spin[idx] + "\r")
                sys.stdout.flush()
                idx = (idx + 1) % len(spin)
                time.sleep(0.01)

    sock.close()


def process_burst(data):


    seq_no = int(data[4])
    src_id = int.from_bytes(data[5:8], byteorder='big')
    dest_id = int.from_bytes(data[8:11], byteorder='big')
    rptr_id = int.from_bytes(data[11:15], byteorder='big')
    slot_no = '1' if int(data[15]) & 1 == 0 else '2'
    call_type = 'group' if int(data[15]) & 2 >> 1 == 0 else 'private'
    frame_type = ['voice', 'voice sync', 'data sync', 'unused'][int(data[15]) & 12 >> 2]
    vsq_or_type = int(data[15]) >> 4
    voice_seq = 'ABCDEF'[vsq_or_type] if vsq_or_type < 6 else vsq_or_type
    stream_id = int.from_bytes(data[16:20], byteorder='little')

    dmr_burst = data[20:]  # 33 bytes, 264 bits here

    # the DMR AI burst consists of 2x 108bit payloads with a 48bit sync field
    # inserted in between.  here we split the burst in order to reconsruct the
    # payload
    burst_binary = bitarray()
    burst_binary.frombytes(dmr_burst)
    payload_binary = burst_binary[:108] + burst_binary[-108:]

    # there are 3x 72bit vocoder frames in each payload
    ambe72_frames = [payload_binary[:72], payload_binary[72:144], payload_binary[144:]]

    # convert to ambe49 frames to use the md380 emulator
    ambe49_frames = [ambe_utils.convert72BitTo49BitAMBE(frame) for frame in ambe72_frames]

    print(f"seq: {seq_no}\nsrc_id: {src_id}\ndest_id: {dest_id}\nrptr_id: {rptr_id}\nslot_no: {slot_no}\ncall_type: {call_type}\nframe_type: {frame_type}\nvoice_seq: {voice_seq}\nstream_id: {stream_id}\ndata: {len(dmr_burst)}\n\n")

    # md380-emu takes DSD .amb file format as input
    # construct DSD formatted frames

    start_byte = bitarray('0' * 8)  # DSD frames start with 0x00

    output = b''

    for frame in ambe49_frames:
        tail = bitarray('0' * 7)  # DSD frames are padded at the end
        tail[-1] = frame[-1]  # DSD specifes that the last bit of ambe49 goes in the LSB
        frame[-1] = 0
        output += (start_byte + frame + tail).tobytes()

    return output



def udp_receive(sock, blocking=False):
    try:
        data = sock.recv(53, socket.MSG_DONTWAIT if not blocking else 0)
    except:
        return ''

    return data


if __name__ == '__main__':
    main(sys.argv[1:])
