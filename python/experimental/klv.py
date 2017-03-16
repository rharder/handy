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

# Permissible Length Encodings
LENGTH_1_BYTE = 1  # 1 byte
LENGTH_2_BYTES = 2  # 2 bytes
LENGTH_4_BYTES = 4  # 4 bytes
LENGTH_BER = "BER"  # Variable number of bytes
LENGTH_VALID_ENCODINGS = (LENGTH_1_BYTE, LENGTH_2_BYTES, LENGTH_4_BYTES, LENGTH_BER)

# Permissible Key Encodings
KEY_LENGTH_1 = 1  # 1 byte
KEY_LENGTH_2 = 2  # 2 bytes
KEY_LENGTH_4 = 4  # 4 bytes
KEY_LENGTH_16 = 16  # 16 bytes
KEY_LENGTH_BER_OID = "BER-OID"  # Variable number of bytes
KEY_VALID_ENCODINGS = (KEY_LENGTH_1, KEY_LENGTH_2, KEY_LENGTH_4, KEY_LENGTH_16, KEY_LENGTH_BER_OID)
KEY_FIXED_LENGTHS = (KEY_LENGTH_1, KEY_LENGTH_2, KEY_LENGTH_4, KEY_LENGTH_16)
KEY_LENGTHS_AS_INTS = (KEY_LENGTH_1, KEY_LENGTH_2, KEY_LENGTH_4, KEY_LENGTH_BER_OID)


def parse(source, key_size, length_encoding):
    """
    Parses a stream and yields (key, value) tuples until the source is exhausted.

    Keys of less than 16 bytes are returned as an integer.  16-byte keys are returned
    as a "bytes" object.

    Raises an Exception if an invalid key size or length encoding is passed.

    :param source: data source as a stream or "bytes" object
    :param key_size: valid key sizes are 1, 2, 4, 16 or "BER-OID"
    :param length_encoding: valid length encodings are 1, 2, 4, or "BER"
    :return: (key, value) tuple
    """

    enforce_valid_key_lengths = True  # Considered making this an argument at one point
    if enforce_valid_key_lengths and key_size not in KEY_VALID_ENCODINGS:
        raise Exception("Invalid key length: {}".format(key_size))
    if key_size <= 0:
        raise Exception("Key length cannot be zero or negative: {}".format(key_size))

    if length_encoding not in LENGTH_VALID_ENCODINGS:
        raise Exception("Invalid length encoding: {}".format(length_encoding))

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

        # Convert key from bytes to int?
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
            if ber & 0b10000000 != 0:  # High bit set
                ber &= ~ 0b10000000  # clear high bit
                length = stream.read(ber)
                length = int.from_bytes(length, byteorder='big', signed=False)
            else:
                length = ber

        # Collect value
        value = stream.read(length)

        # Found a Key/Value pair
        yield (key, value)

    # Nothing left to parse
    return


def parse_into_dict(source, payload_defs_dictionary):
    """
    Parses the source according to the definition provided in the
    provided dictionary.  The source will continue to be parsed
    until it is empty.

    :param source:
    :param payload_defs_dictionary:
    :return:
    """
    key_length = payload_defs_dictionary["key_length"]
    length_encoding = payload_defs_dictionary["length_encoding"]
    field_defs = payload_defs_dictionary["fields"]

    # Make the source a stream
    stream = None  # type: io.IOBase
    if issubclass(type(source), io.IOBase):
        stream = source
    elif isinstance(source, bytes):
        stream = io.BytesIO(source)
    else:
        raise Exception("Don't know how to handle source of type {}".format(type(source)))

    vals = {}
    for fkey, fval in parse(stream, key_length, length_encoding):
        field = {"bytes": fval}  # Always save raw bytes

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
UAS_PAYLOAD_DICTIONARY = {
    "top_level_key": UAS_KEY,
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
}  # end UAS_PAYLOAD_DICTIONARY

# with open("out.klv", "rb") as f:
#     for key, value in parse(f, 16, LENGTH_BER):
for key, value in parse(KLV_EXAMPLE_1_as_bytes, 16, LENGTH_BER):
    if key == UAS_KEY:
        print("RECEIVED UAS PAYLOAD:", value)
        payload = parse_into_dict(value, UAS_PAYLOAD_DICTIONARY)
        print("\tPAYLOAD:", payload)
        pprint(payload)
    else:
        print("RECEIVED UNKNOWN KEY:", key)
        print("\tUNKNOWN PAYLOAD:", value)
