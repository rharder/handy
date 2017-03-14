import io
from struct import unpack

HEX = """
06 0E 2B 34 02 0B 01 01  0E 01 03 01 01 00 00 00
61 02 08 00 04 60 50 58  4E 01 80 05 02 71 C2 06
02 FD 3D 07 02 08 B8 0D  04 55 95 B6 6D 0E 04 5B
53 60 C4 0F 02 C2 21 10  02 CD 9C 11 02 D9 17 12
04 72 4A 0A 20 13 04 87  F8 4B 86 14 04 00 00 00
00 15 04 03 83 09 26 16  02 12 81 17 04 F1 01 A2
29 18 04 14 BC 08 2B 19  02 34 F3 41 01 02 01 02
C8 4C
"""
LENGTH_1_BYTE = 1
LENGTH_2_BYTES = 2
LENGTH_4_BYTES = 4
LENGTH_BER = "BER"
VALID_LENGTH_ENCODING = (LENGTH_1_BYTE, LENGTH_2_BYTES, LENGTH_4_BYTES, LENGTH_BER)

def parse(stream:io.BufferedReader, key_size, length_encoding):
    if length_encoding not in VALID_LENGTH_ENCODING:
        raise Exception("Invalid length encoding: {}".format(length_encoding))
    key = None  # type: bytes
    length = None  # type: int
    value = None  # type: bytes

    # Key size: 16 bytes
    key = stream.read(key_size)
    if length_encoding in (LENGTH_1_BYTE, LENGTH_2_BYTES, LENGTH_4_BYTES):
        length = stream.read(length_encoding)
        (length,) = unpack(">B", length)
    else:
        assert length_encoding == LENGTH_BER
        ber = stream.read(1)
        if ber & 0x80 == 0x80:  # High bit set
            ber = ber & int('011111111',2)
            ber = unpack(">B", ber)
            length = stream.read(ber)
            (length,) = unpack(">B", length)


    print("length", length)
    value = stream.read(length)
    print("value", len(value), value)
    print()
    return (key, value)


with open("out.klv", "rb") as f:
    for klv in parse(f, 16, LENGTH_BER):
        print(klv)
