try:
    from functools import reduce
except ImportError:
    from __builtin__ import reduce
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from .util import _unpack_from, _take_bits, _fix_keys
from . import maps

__all__ = ['Inibin']

class Inibin(dict):
    """
    Inibin reader.

    """
    # Flag constants
    # Not all flags are supported, but this set covers the most common.
    # It is not clear which flags, if any, have signed values.
    # Flags are listed in the order their data sections appear in the file.
    # Each line is (bit_mask, [quantity,] function_or_format)
    FLAGS = [
        (0b0000000000000001, 'i'),
        (0b0000000000000010, 'f'),
        (0b0000000000000100, 'b', lambda x: float(x) / 10),  # Integer divided by 10
        (0b0000000000001000, 'h'),  # Short
        (0b0000000000010000, 'b'),  # 1-byte integer
        (0b0000000000100000, _take_bits),  # 1-bit booleans, 8 per byte
        (0b0000000001000000, 3, 'b'),  # RGB Color?
        (0b0000000010000000, 3, 'i'),  # Unknown
        (0b0000010000000000, 4, 'b'),  # RGBA Color?
        (0b0001000000000000, None),  # String offsets, processed by _read_string_table
    ]
    RECOGNIZED_FLAGS = reduce(lambda a, b: a | b, (f[0] for f in FLAGS), 0)

    version = 0
    string_table_length = 0
    flags = 0

    def __init__(self, fileobj=None, data=None, **kwargs):
        """
        Inibin can be loaded using either of these parameters:
        fileobj -- file-like object. Must have been opened in binary mode.
        data -- string.
        """
        super(Inibin, self).__init__(**kwargs)

        if not fileobj and not data:
            raise TypeError("Must provide one of fileobj and data.")
        if data:
            fileobj = StringIO(data)
        self.buffer = fileobj

        data = self._read_inibin()

        self.clear()
        self.update(data)

    def as_champion(self, string_table=None):
        """Return a dictionary of the inibin interpreted as a champion."""
        return self._translate(maps.CHAMPION, string_table)

    def as_ability(self, string_table=None):
        """Return a dictionary of the inibin interpreted as an ability."""
        return self._translate(maps.ABILITY, string_table)

    def _translate(self, key_mapping, string_table):
        """Return a dictionary of the inibin interpreted using key_mapping."""
        return _fix_keys(key_mapping, self, string_table)

    def _read_inibin(self):
        self._read_header()

        data = {}

        # Abort if an unrecognized flag is present
        masked_flags = self.flags & (~Inibin.RECOGNIZED_FLAGS)
        if masked_flags != 0:
            raise IOError("Unrecognized flags: %s" % bin(masked_flags))

        # Inibin v2 blocks
        for row in Inibin.FLAGS:
            if not row[0] & self.flags:
                continue

            mapping_update = self._process_flag(row)
            for key, value in mapping_update.items():
                # Do not overwrite any keys
                assert key not in data
                data[key] = value

        # There should be no non-padding bytes remaining
        remaining = bytearray(self.buffer.read())
        if any(c == 0 for c in remaining):
            raise IOError("Finished reading but not at EOF")

        return data

    def _read_header(self):
        self.version = _unpack_from(self.buffer, 'B')
        if not self.version == 2:
            raise ValueError("Invalid version number: %s" % self.version)

        # TODO: Do not put string_table_length on class
        self.string_table_length = _unpack_from(self.buffer, 'H')

        self.flags = _unpack_from(self.buffer, 'H')

    def _process_flag(self, flag_definition):
        if flag_definition[1] is None:
            # String table is handled differently
            return self._read_string_table()

        # Read number of keys
        count = _unpack_from(self.buffer, 'H')
        keys = _unpack_from(self.buffer, 'i', count)

        # Does the flag specify multiple values per key?
        per_count = 1
        try:
            per_count = int(flag_definition[1])
        except (ValueError, TypeError):
            pass
        else:
            # Remove multiplier from the row
            flag_definition = [flag_definition[0]] + list(flag_definition[2:])

        # Read values
        if isinstance(flag_definition[1], str):
            values = _unpack_from(self.buffer, flag_definition[1], per_count * count)

            # Apply row functions (if any)
            for transform in flag_definition[2:]:
                values = [transform(v) for v in values]
        elif callable(flag_definition[1]):
            # Custom function (ex. bits)
            values = flag_definition[1](self.buffer, count)
        else:
            raise RuntimeError("Unknown operation.")

        # If there were multiple values per key, group them
        # TODO: This creates a list of lists even if count == 1
        if per_count > 1:
            values_out = []
            for i, val in enumerate(values):
                if i % per_count == 0:
                    values_out.append([])
                values_out[-1].append(val)
            values = values_out
            del values_out

        return dict(zip(keys, values))

    def _read_string_table(self):
        # Must only be called after all flags have been read
        count = _unpack_from(self.buffer, 'H')
        keys = _unpack_from(self.buffer, 'i', count)
        offsets = _unpack_from(self.buffer, 'H', count)
        strings = self.buffer.read(self.string_table_length)
        values = [strings[v:].partition(bytearray([0]))[0] for v in offsets]

        return dict(zip(keys, values))
