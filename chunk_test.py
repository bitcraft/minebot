#!/usr/bin/python2.5

from bravo.chunk import Chunk
from bravo.packets import parse_packets

from numpy import uint8, alltrue
from numpy.random import randint



def compare_chunks(chunk1, chunk2):
    print "blocks detail:"
    print chunk1.blocks[1]
    print chunk1.blocks[-1]
    print "============================="
    print chunk2.blocks[1]
    print chunk2.blocks[-1]

    print "\nmetadata detail:"
    print chunk1.metadata[1]
    print chunk1.metadata[-1]
    print "============================="
    print chunk2.metadata[1]
    print chunk2.metadata[-1]

    print "\nsummary:"
    print "do blocks match?\t", alltrue(chunk1.blocks == chunk2.blocks)
    print "do metadata match?\t", alltrue(chunk1.metadata == chunk2.metadata)
    print "do skylights match?\t", alltrue(chunk1.skylight == chunk2.skylight)
    print "do blockslights match?\t", alltrue(chunk1.blocklight == chunk2.blocklight)

    packet1 = chunk1.save_to_packet()
    packet2 = chunk2.save_to_packet()

    print "do packets match?\t", str(packet1) == str(packet2)

def randomize_chunk(chunk, x=0, y=0, z=0, x_size=16, y_size=128, z_size=16):
    # randomly set values in the world
    for i in range(x_size * y_size * z_size):
        chunk.blocks[x, z, y] = randint(0,64)
        chunk.metadata[x, z, y] = randint(0,15)
        chunk.skylight[x, z, y] = randint(0,15)
        chunk.blocklight[x, z, y] = randint(0,15)
        y += 1
        if y >= y_size:
            z += 1
            y = 0
            if z >= z_size:
                x += 1
                z = 0

    return chunk

def full_chunk_test():
    # compare two full chunks
    chunk1 = Chunk(0, 0)
    chunk2 = Chunk(0, 0)
    randomize_chunk(chunk1)
    packet1 = chunk1.save_to_packet()
    p, l = parse_packets(packet1)
    header, payload = p[0]
    chunk2.load_from_packet(payload)
    packet2 = chunk2.save_to_packet()
    compare_chunks(chunk1, chunk2)


if __name__ == "__main__":
    import cProfile
    import sys


    speed_test = False

    full_chunk_test()

    if speed_test:
        # fastest: 1.107
        # python2.5
        test_packet = parse_packets(randomize_chunk(Chunk(0,0)).save_to_packet())[0][0][1]
        def load_test():
            for i in range(0, 10):
                c = Chunk(0,0).load_from_packet(test_packet) 
        cProfile.run("load_test()", "chunk.prof")

