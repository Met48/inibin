"""
A reader for the inibin file format.

One function, read_inibin, is exported for use. It will read the file buffer,
parse the inibin, and map the inibin keys to have human-readable names.

Champion and ability inibins are supported.
"""

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from util import _unpack_from, _take_bits, _fix_keys


class Inibin(dict):
    """
    Inibin reader.

    Does not support all flags yet, but covers typical use cases.

    """
    # Flag constants
    # Flags are listed in the order their data appears in the file.
    # Each line (bit_mask, [quantity,] function_or_format)
    FLAGS = [
        (0b0000000000000001, 'i'),  # Signed?
        (0b0000000000000010, 'f'),
        (0b0000000000000100, 'b', lambda x: float(x) / 10),  # Integer divided by 10
        (0b0000000000001000, 'h'),  # Short. Signed?
        (0b0000000000010000, 'b'),  # 1-byte integer. Signed?
        (0b0000000000100000, _take_bits),  # 1-bit booleans, 8 per byte
        (0b0000000001000000, 3, 'b'),  # RGB Color?
        (0b0000000010000000, 3, 'i'),  # ?
        (0b0000010000000000, 4, 'b'),  # RGBA Color?
        (0b0001000000000000, None),  # String offsets, processed by _lookup_in_string_table
    ]
    RECOGNIZED_FLAGS = reduce(lambda a, b: a | b, (f[0] for f in FLAGS), 0)

    version = 0
    str_len = 0
    flags = 0

    def __init__(self, buffer, font_config=None,
                 kind=None, fix_keys=True, **kwargs):
        """
        Arguments:
        buffer -- file-like object or string to read the inibin from. Data must
            have been read in binary mode.
        font_config -- a dictionary representation of fontconfig_en_US.txt
        kind -- either 'CHARACTER' or 'ABILITY' (default CHARACTER)

        """
        super(Inibin, self).__init__(**kwargs)

        if not hasattr(buffer, 'read'):
            buffer = StringIO(buffer)
        self.buffer = buffer

        data = self._read_inibin()

        if fix_keys:
            import maps
            from maps import CHARACTER, ABILITY

            assert hasattr(maps, kind)
            data = _fix_keys(getattr(maps, kind), data, font_config)

        self.clear()
        self.update(data)

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
                assert key not in data
                data[key] = value

        # There should be no non-padding bytes remaining
        remaining = self.buffer.read()
        if len(remaining) > 0 and not all(c == '\x00' for c in remaining):
            raise IOError("%i bytes remaining" % len(remaining))

        return data

    def _read_header(self):
        self.version = _unpack_from(self.buffer, 'B')
        if not self.version == 2:
            raise ValueError("Invalid version number: %s" % self.version)

        # TODO: Do not put str_len on class
        self.str_len = _unpack_from(self.buffer, 'H')

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
        if isinstance(flag_definition[1], basestring):
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
        strings = self.buffer.read(self.str_len)
        values = [strings[v:].partition('\x00')[0] for v in offsets]

        return dict(zip(keys, values))


def main():
    from pprint import pprint
    import sys
    assert len(sys.argv) in (2, 3)
    with open(sys.argv[-1], 'rb') as f:
        data = f.read()
    if len(sys.argv) == 3:
        fix_keys = True
        kind = sys.argv[1]
    else:
        fix_keys = False
        kind = None
    inibin = Inibin(data, {}, kind, fix_keys)
    pprint(inibin)


if __name__ == '__main__':
    main()
