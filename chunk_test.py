#!/usr/bin/python2.5

from bravo.chunk import Chunk
from bravo.packets import parse_packets

chunk1 = Chunk(1, 1)
chunk2 = Chunk(1, 1)

packet1 = chunk1.save_to_packet()

p, l = parse_packets(packet1)
header, payload = p[0]
chunk2.load_from_packet(payload)

packet2 = chunk2.save_to_packet()

print packet1 == packet2
