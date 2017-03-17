import io
import sys
import re
from pprint import pprint
from struct import unpack
from math import log
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
KLV_EXAMPLE_1_as_bytes = bytes([int(h, base=16) for h in KLV_EXAMPLE_1.split()])

KLV_EXAMPLE_ICING_DETECTED = """
06 0E 2B 34 02 0B 01 01  0E 01 03 01 01 00 00 00
10
02 08 00 04 60 50 58 4E 01 80
22 00
05 02 71 C2
"""  # 22 00 is "Icing Detected" with a length of zero (as it should be)
KLV_EXAMPLE_ICING_DETECTED_as_bytes = bytes([int(h, base=16) for h in KLV_EXAMPLE_ICING_DETECTED.split()])

KLV_EXAMPLE_TAG_6_OUT_OF_RANGE = """
06 0E 2B 34 02 0B 01 01  0E 01 03 01 01 00 00 00
10
02 08 00 04 60 50 58 4E 01 80
06 02 80 00
"""
KLV_EXAMPLE_TAG_6_OUT_OF_RANGE_as_bytes = bytes([int(h, base=16) for h in KLV_EXAMPLE_TAG_6_OUT_OF_RANGE.split()])

KLV_EXAMPLE_TAG_47_FLAGS = """
06 0E 2B 34 02 0B 01 01  0E 01 03 01 01 00 00 00
10
02 08 00 04 60 50 58 4E 01 80
2F 01 15
"""
KLV_EXAMPLE_TAG_47_FLAGS_as_bytes = bytes([int(h, base=16) for h in KLV_EXAMPLE_TAG_47_FLAGS.split()])

# Permissible Length Encodings
LENGTH_1_BYTE = 1  # 1 byte
LENGTH_2_BYTES = 2  # 2 bytes
LENGTH_4_BYTES = 4  # 4 bytes
LENGTH_BER = "BER"  # Variable number of bytes
LENGTH_ENCODINGS_FIXED_LENGTHS = (LENGTH_1_BYTE, LENGTH_2_BYTES, LENGTH_4_BYTES)
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
BIG_ENDIAN = 'big'

# Identifying int formats
INT_FORMAT_REGEX_PATTERN = "^(u?)int([0-9]+)$"
INT_FORMAT_REGEX = re.compile(INT_FORMAT_REGEX_PATTERN)


def from_format(data: bytes, format: str):
    # Integer
    m = INT_FORMAT_REGEX.search(format)
    if m is not None:
        signed = m.group(1) != "u"
        # bits = int(m.group(2))
        return int.from_bytes(data, byteorder=BIG_ENDIAN, signed=signed)

    # Strings
    elif format in ("ISO 646", "ascii"):
        return data.decode("ascii")

def to_format(data, format:str) -> bytes:
    # Integer
    m = INT_FORMAT_REGEX.search(format)
    if m is not None:
        if not isinstance(data, int):
            raise Exception("An int format ({}) was specified, but an int was not supplied: {}"
                            .format(format, type(data)))
        signed = m.group(1) != "u"
        bits = int(m.group(2))
        bytes_reqd = bits // 8
        try:
            data_bytes = data.to_bytes(bytes_reqd, byteorder=BIG_ENDIAN, signed=signed)
        except OverflowError:
            data_bytes = (0x80 << (bytes_reqd-1)).to_bytes(bytes_reqd, byteorder=BIG_ENDIAN, signed=False)
        finally:
            return data_bytes
    elif format in ("ISO 646", "ascii"):
        if not isinstance(data, str):
            raise Exception("A string format ({}) was specified, but a string was not supplied: {}"
                            .format(format, type(data)))
        return data.encode("ascii")




# samples = ["{}int{}".format(a,x) for a in ('u','') for x in (8,16,32,64)]
# samples += ['xint8', 'int9', 'uint9']
# print(samples)
#
# for spec in samples:
#     print(spec)
#     m = re.search(INT_FORMAT_REGEX, spec)
#     print(m, m.group(0), m.group(1), m.group(2))
# sys.exit(2)

def parse_continually(source, key_size, length_encoding):
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


def parse(source, key_size, length_encoding):
    return next(parse_continually(source, key_size, length_encoding))


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
    for fkey, fval in parse_continually(stream, key_length, length_encoding):
        field = {"bytes": fval}  # Always save raw bytes

        # Name of Field
        fname = field_defs.get(fkey, {}).get("name")
        if fname is not None:
            field["name"] = fname

        # Verify size of payload
        expected_size = field_defs.get(fkey, {}).get("size")
        if expected_size is not None and len(fval) != expected_size:
            msg = "Error: For key={}, expected field of size {} but received field of size {}. Field: {}" \
                .format(fkey, expected_size, len(fval), fval)
            print(msg, file=sys.stderr)
            field["error"] = msg

        # Else we have the right sized field
        else:

            # Now, how do we process the field
            eval_technique = field_defs.get(fkey, {}).get("eval")
            if eval_technique is not None:
                fval = eval_technique(fval)
            else:
                format = field_defs.get(fkey, {}).get("format")
                if format is not None:
                    val = from_format(fval, format)
                    if val is not None:
                        fval = val
                    del val

            # Value (possibly converted from bytes)
            field["value"] = fval

            # Is there a natural way to read this data
            natural_technique = field_defs.get(fkey, {}).get("natural")
            if natural_technique:
                fnat = natural_technique(fval, field["bytes"])
                field["natural"] = fnat
            units = field_defs.get(fkey, {}).get("units")
            if units:
                field["units"] = units

        vals[fkey] = field

    return vals


def build_klv(key, value, key_length, length_encoding, value_format: str = None):
    key_bytes = None  # type: bytes
    length_bytes = None  # type: bytes
    value_bytes = None  # type: bytes

    # Convert key to bytes
    if isinstance(key, bytes):
        if key_length in KEY_FIXED_LENGTHS:
            if len(key) != key_length:
                raise Exception("Provided key ({} bytes) does not match key length {}".format(len(key), key_length))
            else:
                key_bytes = key
        elif key_length == KEY_LENGTH_BER_OID:
            # Verify provided key is valid
            print("VERIFY BER-OID KEYS NOT YET IMPLEMENTED")
            key_bytes = key
    elif isinstance(key, int):
        key_bytes = key.to_bytes(key_length, byteorder=BIG_ENDIAN, signed=False)
    else:
        raise Exception("Unknown key type: {}".format(type(key)))
    print("KEY_BYTES:", key_bytes)

    # Convert value to bytes
    if isinstance(value, bytes):
        value_bytes = value
    elif value_format is not None:
        value_bytes = to_format(value, value_format)
        if value_bytes is None:
            raise Exception("Was not able to convert value ({}) to bytes".format(value))
    else:
        raise Exception("Could not convert value {} to bytes".format(value))
    print("VALUE BYTES:", value_bytes)

    # Length
    length = len(value_bytes)
    if length_encoding in LENGTH_ENCODINGS_FIXED_LENGTHS:
        length_bytes = length.to_bytes(length_encoding, byteorder=BIG_ENDIAN, signed=False)
    elif length_encoding == LENGTH_BER:
        # Simple case: BER with length < 127
        if length <= 127:
            length_bytes = length.to_bytes(1, byteorder=BIG_ENDIAN, signed=False)
        else:
            # Complex case: BER needs to record number of bytes for length field separately
            bytes_reqd = int(log(length, 256)) + 1
            if bytes_reqd > 127:
                raise Exception("Bytes required ({}) to represent the size of the data cannot be greater than 127"
                                .format(bytes_reqd))
            ber_byte = (0b10000000 | bytes_reqd).to_bytes(1, byteorder=BIG_ENDIAN, signed=False)
            length_bytes = ber_byte + length.to_bytes(bytes_reqd, byteorder=BIG_ENDIAN, signed=False)
    else:
        raise Exception("Unknown length encoding: {}".format(length_encoding))
    print("LENGTH BYTES:", length_bytes)

    klv = key_bytes + length_bytes + value_bytes
    print("KLV:", klv)

    return klv



UAS_KEY = b'\x06\x0e\x2b\x34\x02\x0b\x01\x01\x0e\x01\x03\x01\x01\x00\x00\x00'
UAS_PAYLOAD_DICTIONARY = {
    "top_level_key": UAS_KEY,
    "key_length": KEY_LENGTH_1,
    "length_encoding": LENGTH_BER,
    "fields": {
        2: {"name": "UNIX Time Stamp",
            "size": 8,
            "format": "uint64",
            # Timestamp is in microseconds - convert to seconds for Python
            "natural": lambda x, b: datetime.datetime.utcfromtimestamp(x / 1000 / 1000).strftime('%Y-%m-%dT%H:%M:%SZ')
            },
        3: {"name": "Mission ID",
            "format": "ISO 646"
            },
        4: {"name": "Platform Tail Number",
            "format": "ISO 646"
            },
        5: {"name": "Platform Heading Angle",
            "size": 2,
            "format": "uint16",
            "natural": lambda x, b: 360.0 * (x / 0xFFFF),
            "units": "degrees",
            "from_natural": lambda x: int((x / 360.0 * 0xFFFF))#.to_bytes(2, byteorder=BIG_ENDIAN, signed=False)
            },
        6: {"name": "Platform Pitch Angle",
            "size": 2,
            "format": "int16",
            "natural": lambda x, b: 2 * 20.0 * (x / 0xFFFe) if b != b'\x80\x00' else "out of range",
            "units": "degrees",
            "from_natural": lambda x: int(x / 2.0 / 20.0 * 0xFFFe)
            },
        7: {"name": "Platform Roll Angle",
            "size": 2,
            "format": "int16",
            "natural": lambda x, b: 2 * 50.0 * (x / 0xFFFF) if b != b'\x80\x00' else "out of range",
            "units": "degrees"
            },
        8: {"name": "Platform True Airspeed",
            "size": 1,
            "format": "uint8",
            "units": "meters / second"
            },
        9: {"name": "Platform Indicated Airspeed",
            "size": 1,
            "format": "uint8",
            "units": "meters / second"
            },
        10: {"name": "Platform Designation",
             "format": "ISO 646"
             },
        11: {"name": "Image Source Sensor",
             "format": "ISO 646",
             # "eval": lambda b: b.decode("ascii")
             },
        12: {"name": "Image Coordinate System",
             "format": "ISO 646"
             },
        13: {"name": "Sensor Latitude",
             "size": 4,
             "format": "int32",
             "natural": lambda x, b: 2 * 90.0 * (x / 0xFFFFFFFe)
             if x != b'\x80\x00\x00\x00\x00\x00\x00\x00' else "error",
             "units": "degrees"
             },
        14: {"name": "Sensor Longitude",
             "size": 4,
             "format": "int32",
             "natural": lambda x, b: 2 * 180.0 * (x / 0xFFFFFFFe)
             if x != b'\x80\x00\x00\x00\x00\x00\x00\x00' else "error",
             "units": "degrees"
             },
        15: {"name": "Sensor True Altitude",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: -900.0 + 19900.0 * (x / 0xFFFF),
             "units": "meters"
             },
        16: {"name": "Sensor Horizontal Field of View",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: 180.0 * (x / 0xFFFF),
             "units": "degrees"
             },
        17: {"name": "Sensor Vertical Field of View",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: 180.0 * (x / 0xFFFF),
             "units": "degrees"
             },
        18: {"name": "Sensor Relative Azimuth Angle",
             "size": 4,
             "format": "uint32",
             "natural": lambda x, b: 360.0 * (x / 0xFFFFFFFF),
             "units": "degrees"
             },
        19: {"name": "Sensor Relative Elevation Angle",
             "size": 4,
             "format": "int32",
             "natural": lambda x, b: 2 * 180.0 * (x / 0xFFFFFFFe)
             if x != b'\x80\x00\x00\x00\x00\x00\x00\x00' else "error",
             "units": "degrees"
             },
        20: {"name": "Sensor Relative Roll Angle",
             "size": 4,
             "format": "uint32",
             "natural": lambda x, b: 360.0 * (x / 0xFFFFFFFF),
             "units": "degrees"
             },
        21: {"name": "Slant Range",
             "size": 4,
             "format": "uint32",
             "natural": lambda x, b: 5000000.0 * (x / 0xFFFFFFFF),
             "units": "meters"
             },
        22: {"name": "Target Width",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: 10000.0 * (x / 0xFFFF),
             "units": "meters"
             },
        23: {"name": "Frame Center Latitude",
             "size": 4,
             "format": "int32",
             "natural": lambda x, b: 2 * 90.0 * (x / 0xFFFFFFFe)
             if x != b'\x80\x00\x00\x00\x00\x00\x00\x00' else "error",
             "units": "degrees"
             },
        24: {"name": "Frame Center Longitude",
             "size": 4,
             "format": "int32",
             "natural": lambda x, b: 2 * 180.0 * (x / 0xFFFFFFFe)
             if x != b'\x80\x00\x00\x00\x00\x00\x00\x00' else "error",
             "units": "degrees"
             },
        25: {"name": "Frame Center Elevation",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: -900.0 + 19900 * (x / 0xFFFF),
             "units": "meters"
             },
        26: {"name": "Offset Corner Latitude Point 1",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        27: {"name": "Offset Corner Longitude Point 1",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        28: {"name": "Offset Corner Latitude Point 2",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        29: {"name": "Offset Corner Longitude Point 2",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        30: {"name": "Offset Corner Latitude Point 3",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        31: {"name": "Offset Corner Longitude Point 3",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        32: {"name": "Offset Corner Latitude Point 4",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        33: {"name": "Offset Corner Longitude Point 4",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 0.075 * (x / 0xFFFe) if x != b'\x80\x00\x00' else "error",
             "units": "degrees"
             },
        34: {"name": "Icing Detected"},
        37: {"name": "Static Pressure",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: 5000.0 * (x / 0xFFFF),
             "units": "millibar"
             },
        38: {"name": "Density Altitude",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: -900.0 + 19900.0 * (x / 0xFFFF),
             "units": "meters"
             },
        39: {"name": "Outside Air Temperature",
             "size": 1,
             "format": "int8",
             "units": "degrees celsius"
             },
        40: {"name": "Target Location Latitude",
             "size": 4,
             "format": "int32",
             "natural": lambda x, b: 2 * 90.0 * (x / 0xFFFFFFFe)
             if x != b'\x80\x00\x00\x00\x00\x00\x00\x00' else "error",
             "units": "degrees"
             },
        41: {"name": "Target Location Longitude",
             "size": 4,
             "format": "int32",
             "natural": lambda x, b: 2 * 180.0 * (x / 0xFFFFFFFe)
             if x != b'\x80\x00\x00\x00\x00\x00\x00\x00' else "error",
             "units": "degrees"
             },
        42: {"name": "Target Location Elevation",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: -900.0 + 19900.0 * (x / 0xFFFF),
             "units": "meters"
             },
        43: {"name": "Target Track Gate Width",
             "size": 1,
             "format": "uint8",
             "units": "pixels"
             },
        44: {"name": "Target Track Gate Height",
             "size": 1,
             "format": "uint8",
             "units": "pixels"
             },
        45: {"name": "Target Error Estimate - CE90",
             "size": 2,
             "format": "uint16",
             "units": "meters"
             },
        46: {"name": "Target Error Estimate - LE90",
             "size": 2,
             "format": "uint16",
             "units": "meters"
             },
        47: {"name": "Generic Flag Data 01",
             "size": 1,
             "format": "uint8",
             "bitmap": {
                 1: ("Laser Range", "off", "on"),
                 2: ("Auto-Track", "off", "on"),
                 3: ("IR Polarity", "white", "black"),
                 4: ("Icing Detected", "no", "yes"),
                 5: ("Slant Range", "calculated", "measured"),
                 6: ("Image Invalid", "no", "yes")
             },
             "natural": lambda x, b:
             {k: "{}: {}".format(
                 UAS_PAYLOAD_DICTIONARY["fields"][47]["bitmap"][k][0],
                 UAS_PAYLOAD_DICTIONARY["fields"][47]["bitmap"][k][1 + ((x & (1 << (k - 1))) >> (k - 1))]
             ) for k in UAS_PAYLOAD_DICTIONARY["fields"][47]["bitmap"].keys()}
             },
        48: {"name": "Security Local Metadata Set"},
        49: {"name": "Differential Pressure",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: 5000.0 * (x / 0xFFFF),
             "units": "millibar"
             },
        50: {"name": "Platform Angle of Attack",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 20.0 * (x / 0xFFFe) if b != b'\x80\x00' else "out of range",
             "units": "degrees"
             },
        51: {"name": "Platform Vertical Speed",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 180.0 * (x / 0xFFFe) if b != b'\x80\x00' else "out of range",
             "units": "meters / second"
             },
        52: {"name": "Platform Sideslip Angle",
             "size": 2,
             "format": "int16",
             "natural": lambda x, b: 2 * 20.0 * (x / 0xFFFe) if b != b'\x80\x00' else "out of range",
             "units": "degrees"
             },
        53: {"name": "Airfield Barometric Pressure",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: 5000.0 * (x / 0xFFFF),
             "units": "millibar"
             },
        54: {"name": "Airfield Elevation",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: -900.0 + 19900.0 * (x / 0xFFFF),
             "units": "meters"
             },
        55: {"name": "Relative Humidity",
             "size": 1,
             "format": "uint8",
             "natural": lambda x, b: 100.0 * (x / 0xFF),
             "units": "percent"
             },
        56: {"name": "Platform Ground Speed",
             "size": 1,
             "format": "uint8",
             "units": "meters / second"
             },
        57: {"name": "Ground Range",
             "size": 4,
             "format": "uint32",
             "natural": lambda x, b: 5000000.0 * (x / 0xFFFFFFFF),
             "units": "meters"
             },
        58: {"name": "Platform Fuel Remaining",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: 10000.0 * (x / 0xFFFFFFFF),
             "units": "kilograms"
             },
        59: {"name": "Platform Call Sign",
             "format": "ISO 646"
             },
        60: {"name": "Weapon Load",
             "size": 2,
             "format": "uint16",
             "natural": lambda x, b: (x, b)
             }
    }
}  # end UAS_PAYLOAD_DICTIONARY



# klv = build_klv(5, b'\x71\xc2', KEY_LENGTH_1, LENGTH_BER)
klv = build_klv(5, 0x71c2, KEY_LENGTH_1, LENGTH_BER, value_format="uint16")
field_def = UAS_PAYLOAD_DICTIONARY["fields"][5]
vb = field_def["from_natural"](159.97436484321355)
klv = build_klv(5, vb, KEY_LENGTH_1, LENGTH_BER, value_format="uint16")
print("KLV:", ' '.join('{:02X}'.format(x) for x in klv))


field_def = UAS_PAYLOAD_DICTIONARY["fields"][6]
vb = field_def["from_natural"](-0.4315317239906003)  # 0x08B8
klv = build_klv(6, vb, KEY_LENGTH_1, LENGTH_BER, value_format="int16")
print("KLV:", ' '.join('{:02X}'.format(x) for x in klv))
# TODO: LEFT OFF HERE


# with open(__file__) as f:
#     data = f.read()
# klv = build_klv(3, data, KEY_LENGTH_1, LENGTH_BER, value_format="ISO 646")
# k,v = parse(klv, KEY_LENGTH_1, LENGTH_BER)
# print(k,v)
sys.exit(3)


# bm = UAS_PAYLOAD_DICTIONARY["fields"][47]["bitmap"]
# print(bm)
# val = 0b00000011
# nat = {k: "{}: {}".format(
#     bm.get(k)[0],
#     bm.get(k)[1 + ((val & (1 << (k - 1))) >> (k - 1))]
# ) for k in bm.keys()}
# print(nat)


# for i in bm.keys():
#     bit_val = ((val & (1<<(i-1)))>>(i-1))
#     # print(i, bit_val)
#     msg = "{}: {}".format(
#         bm.get(i)[0],
#         bm.get(i)[1+((val & (1<<(i-1)))>>(i-1))]
#     )
#     print(msg)
# print(bm.get(i)) if (val & (1<<(i-1))) else print("NO")

# if val & (1<<(i-1)):
#     print(i,"set")
# def bits(n):
#     while n:
#         b = n & (~n + 1)
#         yield b
#         n ^= b


# for b in bits(val):
#     print(b)

# sys.exit(3)
# KLV_EXAMPLE_TAG_47_FLAGS_as_bytes
# with open("out.klv", "rb") as f:
#     for key, value in parse_continually(f, 16, LENGTH_BER):
for key, value in parse_continually(KLV_EXAMPLE_1_as_bytes, 16, LENGTH_BER):
        # for key, value in parse_continually(KLV_EXAMPLE_ICING_DETECTED_as_bytes, 16, LENGTH_BER):
        # for key, value in parse_continually(KLV_EXAMPLE_TAG_6_OUT_OF_RANGE_as_bytes, 16, LENGTH_BER):
        # for key, value in parse_continually(KLV_EXAMPLE_TAG_47_FLAGS_as_bytes, 16, LENGTH_BER):
        if key == UAS_KEY:
            print("RECEIVED UAS PAYLOAD:", value)
            payload = parse_into_dict(value, UAS_PAYLOAD_DICTIONARY)
            print("\tPAYLOAD:", payload)
            pprint(payload)
        else:
            print("RECEIVED UNKNOWN KEY:", key)
            print("\tUNKNOWN PAYLOAD:", value)
