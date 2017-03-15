import io
import sys
from pprint import pprint
from struct import unpack

import time

import datetime

KLV_EXAMPLE_1 = """
06 0E 2B 34 02 0B 01 01  0E 01 03 01 01 00 00 00
61 02 08 00 04 60 50 58  4E 01 80 05 02 71 C2 06
02 FD 3D 07 02 08 B8 0D  04 55 95 B6 6D 0E 04 5B
53 60 C4 0F 02 C2 21 10  02 CD 9C 11 02 D9 17 12
04 72 4A 0A 20 13 04 87  F8 4B 86 14 04 00 00 00
00 15 04 03 83 09 26 16  02 12 81 17 04 F1 01 A2
29 18 04 14 BC 08 2B 19  02 34 F3 41 01 02 01 02
C8 4C
"""  # http://impleotv.com/products/sdks/klvlibsdk/
KLV_EXAMPLE_1_arr = [int(h, base=16) for h in KLV_EXAMPLE_1.split()]
KLV_EXAMPLE_1_as_bytes = bytes(KLV_EXAMPLE_1_arr)

LENGTH_1_BYTE = 1
LENGTH_2_BYTES = 2
LENGTH_4_BYTES = 4
LENGTH_BER = "BER"
VALID_LENGTH_ENCODING = (LENGTH_1_BYTE, LENGTH_2_BYTES, LENGTH_4_BYTES, LENGTH_BER)

KEY_LENGTH_1 = 1
KEY_LENGTH_2 = 2
KEY_LENGTH_4 = 4
KEY_LENGTH_16 = 16
KEY_LENGTH_BER_OID = "BER-OID"
KEY_VALID_ENCODINGS = (KEY_LENGTH_1, KEY_LENGTH_2, KEY_LENGTH_4, KEY_LENGTH_16, KEY_LENGTH_BER_OID)
KEY_FIXED_LENGTHS = (KEY_LENGTH_1, KEY_LENGTH_2, KEY_LENGTH_4, KEY_LENGTH_16)
KEY_LENGTHS_AS_INTS = (KEY_LENGTH_1, KEY_LENGTH_2, KEY_LENGTH_4, KEY_LENGTH_BER_OID)


def parse(source, key_size, length_encoding):
    if length_encoding not in VALID_LENGTH_ENCODING:
        raise Exception("Invalid length encoding: {}".format(length_encoding))

    enforce_valid_key_lengths = True
    if enforce_valid_key_lengths and key_size not in KEY_VALID_ENCODINGS:
        raise Exception("Invalid key length: {}".format(key_size))
    if key_size <= 0:
        raise Exception("Key length cannot be zero or negative: {}".format(key_size))

    # Input
    stream = None  # type: io.IOBase
    if isinstance(source, io.IOBase):
        stream = source
    elif isinstance(source, bytes):
        stream = io.BytesIO(source)
    else:
        raise Exception("Don't know how to handle source of type {}".format(type(source)))

    more_to_process = True
    while more_to_process:

        # Data we will collect
        key = None  # will be int for 1,2,4-byte keys and bytes for 16-byte keys
        length = None  # type: int
        value = None  # type: bytes

        # Retrieve Key
        if key_size in KEY_FIXED_LENGTHS:
            key = stream.read(key_size)
            # FIRST READ OPERATION. IF EMPTY, THEN STREAM IS CLOSED
            if key == b'':
                more_to_process = False
                continue
        else:
            assert key_size == KEY_LENGTH_BER_OID
            # READ KEY AS BER-OID
            raise Exception("HAVE NOT IMPLEMENTED BER-OID KEY ENCODING")
            # FIRST READ OPERATION. IF EMPTY, THEN STREAM IS CLOSED
            # if key == b'':
            #     more_to_process = False
            #     continue

        if key_size in KEY_LENGTHS_AS_INTS:
            key = int.from_bytes(key, byteorder='big', signed=False)

        # Compute Length
        if length_encoding in (LENGTH_1_BYTE, LENGTH_2_BYTES, LENGTH_4_BYTES):
            length = stream.read(length_encoding)
            length = int.from_bytes(length, byteorder='big', signed=False)
        else:
            assert length_encoding == LENGTH_BER
            ber = stream.read(1)
            ber = int.from_bytes(ber, byteorder='big', signed=False)
            # (ber,) = unpack(">B", ber)
            if ber & 0x80 == 0x80:  # High bit set
                ber = ber & 0x7F  # clear high bit
                # ber = unpack(">B", ber)
                length = stream.read(ber)
                # (length,) = unpack(">B", length)
                length = int.from_bytes(length, byteorder='big', signed=False)
            else:
                length = ber

        # Value
        value = stream.read(length)

        # Found a Key/Value pair
        yield (key, value)

    # Nothing left to parse
    return


def parse_into_dict(source, payload_dictionary):
    key_length = payload_dictionary["key_length"]
    length_encoding = payload_dictionary["length_encoding"]
    field_defs = payload_dictionary["fields"]

    stream = None  # type: io.IOBase
    if issubclass(type(source), io.IOBase):
        stream = source
    elif isinstance(source, bytes):
        stream = io.BytesIO(source)
    else:
        raise Exception("Don't know how to handle source of type {}".format(type(source)))

    vals = {}
    for fkey, fval in parse(stream, key_length, length_encoding):
        field = {}

        # Raw Bytes
        field["bytes"] = fval

        # Name of Field
        fname = field_defs.get(fkey, {}).get("name")
        if fname:
            field["name"] = fname

        # Verify size of payload
        expected_size = field_defs.get(fkey, {}).get("size")
        if expected_size is not None and len(fval) != expected_size:
            print("For key={}, expected field of size {} but received field of size {}. Field: {}"
                  .format(fkey, expected_size, len(fval), fval), file=sys.stderr)

        # Else we have the right sized field
        else:
            # Now, how do we process the field
            eval_technique = field_defs.get(fkey, {}).get("eval")
            if eval_technique:
                fval = eval_technique(fval)

        # Value (possibly converted from bytes)
        field["value"] = fval

        # Is there a natural way to read this data
        natural_technique = field_defs.get(fkey, {}).get("natural")
        if natural_technique:
            fnat = natural_technique(fval)
            field["natural"] = fnat
        units = field_defs.get(fkey, {}).get("units")
        if units:
            field["units"] = units

        vals[fkey] = field

    return vals


UAS_KEY = b'\x06\x0e\x2b\x34\x02\x0b\x01\x01\x0e\x01\x03\x01\x01\x00\x00\x00'
# UAS_KEY = b'\x06\x0e+4\x02\x0b\x01\x01\x0e\x01\x03\x01\x01\x00\x00\x00'
UAS_PAYLOAD_DICTIONARY = {
    "key_length": KEY_LENGTH_1,
    "length_encoding": LENGTH_BER,
    "fields": {
        2: {"name": "UNIX Time Stamp",
            "size": 8,
            "format": "uint64",
            "eval": lambda b: int.from_bytes(b, byteorder='big', signed=False),
            # Timestamp is in microseconds - convert to seconds for Python
            "natural": lambda x: datetime.datetime.utcfromtimestamp(x / 1000 / 1000).strftime('%Y-%m-%dT%H:%M:%SZ')
            },
        3: {"name": "Mission ID",
            "format": "ISO 646",
            "eval": lambda b: b.decode("ascii")
            },
        4: {"name": "Platform Tail Number",
            "format": "ISO 646",
            "eval": lambda b: b.decode("ascii")
            },
        5: {"name": "Platform Heading Angle",
            "size": 2,
            "format": "uint16",
            "eval": lambda b: int.from_bytes(b, byteorder='big', signed=False),
            "natural": lambda x: 360.0 * (x / 0xFFFF),
            "units": "degrees"
            },
        6: {"name": "Platform Pitch Angle",
            "size": 2,
            "format": "int16",
            "eval": lambda b: int.from_bytes(b, byteorder='big', signed=True),
            "natural": lambda x: 40.0 * (x / 0xFFFF),
            "units": "degrees"
            },
        7: {"name": "Platform Roll Angle",
            "size": 2,
            "format": "int16",
            "eval": lambda b: int.from_bytes(b, byteorder='big', signed=True),
            "natural": lambda x: 100.0 * (x / 0xFFFF),
            "units": "degrees"
            },
        8: {"name": "Platform True Airspeed",
            "size": 1,
            "format": "uint8",
            "eval": lambda b: int.from_bytes(b, byteorder='big', signed=False),
            "units": "m/s"
            },
        9: {"name": "Platform Indicated Airspeed",
            "size": 1,
            "format": "uint8",
            "eval": lambda b: int.from_bytes(b, byteorder='big', signed=False),
            "units": "m/s"
            },
        10: {"name": "Platform Designation",
             "format": "ISO 646",
             "eval": lambda b: b.decode("ascii")
             },
        11: {"name": "Image Source Sensor",
             "format": "ISO 646",
             "eval": lambda b: b.decode("ascii")
             },
        12: {"name": "Image Coordinate System",
             "format": "ISO 646",
             "eval": lambda b: b.decode("ascii")
             },
        13: {"name": "Sensor Latitude",
             "size": 4,
             "format": "int32",
             "eval": lambda b: int.from_bytes(b, byteorder='big', signed=True),
             "natural": lambda x: 180.0 * (x / 0xfffffffe)
             },
        14: {"name": "Sensor Longitude",
             "size": 4,
             "format": "int32",
             "eval": lambda b: int.from_bytes(b, byteorder='big', signed=True),
             "natural": lambda x: 360.0 * (x / 0xfffffffe)
             }
    }
}
# print("{:08x}".format((2**31)-1))
# low = -((2**31)-1)
# high = +((2**31)-1)
# print(low, high)
# print("{:08x}, {:08x}".format(low,high))
# print(high - low)
# print("{:12x}".format(high - low))
# print(-90 + 180*  (1435874925 / ((2**31)-1)))
# # print("{:08x}".format((2**16)-1))
# lat = 0x5595B66D
# lat = int("5595B66D", base=16)
# print(lat/0xFFFFFFFF)
# sys.exit(3)

# x = 1231798102000000
# # print(datetime.datetime.utcfromtimestamp(x).strftime('%Y-%m-%dT%H:%M:%SZ'))
# a = datetime.datetime.fromtimestamp(x/1000/1000)


# def gen():
#     for i in range(3):
#         if i == 2:
#             return
#         yield i
# for x in gen():
#     print(x)
# sys.exit(x)


# with open("out.klv", "rb") as f:
#     for klv in parse(f, 16, LENGTH_BER):
#         print(klv)
#
for key, value in parse(KLV_EXAMPLE_1_as_bytes, 16, LENGTH_BER):
    if key == UAS_KEY:
        print("RECEIVED UAS PAYLOAD:", value)
        payload = parse_into_dict(value, UAS_PAYLOAD_DICTIONARY)
        print("\tPAYLOAD:", payload)
        pprint(payload)
    else:
        print("RECEIVED UNKNOWN KEY:", key)
        print("\tUNKNOWN PAYLOAD:", value)

# key, value = parse(KLV_EXAMPLE_1_as_bytes, 16, LENGTH_BER)
# parse_into_dict(value, UAS_PAYLOAD_DICTIONARY)

# stream = io.BytesIO(KLV_EXAMPLE_1_as_bytes)
# stream = open("out.klv", "rb")
# while True:
#     x = stream.read(1)
#     print(x)
#     # time.sleep(.1)
# stream.close()
