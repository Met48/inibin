try:
    import StringIO
except ImportError:
    from io import StringIO
import struct

def _take_bits(buf, count):
    """Return the booleans that were packed into bytes."""

    # TODO: Verify output
    bytes_count = (count + 7) // 8
    bytes_mod = count % 8
    data = _unpack_from(buf, 'B', bytes_count)
    values = []
    for i, byte in enumerate(data):
        for _ in range(8 if i != bytes_count - 1 else bytes_mod):
            # TODO: Convert to True / False
            values.append(byte & 0b10000000)
            byte <<= 1
    return values


def _fix_keys(key_mapping, inibin_mapping, font_config):
    """
    Create a human-readable dictionary of the values in inibin_mapping.

    Arguments:
    key_mapping -- Dictionary used for conversion. Supports nesting. Every other
        value should be a numeric inibin key, or a tuple of the key and a
        function to apply to the result
    inibin_mapping -- The dictionary returned from reading an inibin
    font_config -- The dictionary loaded from fontconfig_en_US.txt. Strings in
        the inibin are often keys of this dictionary
    """

    def walk(node, out_node):
        # Walk the nodes of the key mapping
        for key, value in node.items():
            if isinstance(value, dict):
                if key not in out_node:
                    out_node[key] = {}
                walk(value, out_node[key])
            else:
                # Can either be just the index, or the index plus a function to apply
                func = None
                if isinstance(value, tuple):
                    func = value[-1]
                    index = value[0]
                else:
                    index = value

                if index is None or index not in inibin_mapping:
                    out_node[key] = None
                    continue

                val = inibin_mapping[index]

                # Try numeric conversion
                # Inibins often store numbers in strings
                if isinstance(val, str):
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass

                # Check if value is a reference to a fontconfig key
                if val in font_config:
                    val = font_config[val]

                # Apply the function
                if callable(func):
                    val = func(val)

                out_node[key] = val

    out = {}
    walk(key_mapping, out)

    return out


def _unpack_from(buf, format_s, count=None, little_endian=True):
    """Read a binary format from the buffer."""

    if count is not None:
        assert count > 0
        format_s = '%i%s' % (count, format_s)

    if little_endian is True:
        format_s = '<' + format_s
    else:
        format_s = '>' + format_s

    size = struct.calcsize(format_s)
    res = struct.unpack_from(format_s, buf.read(size))

    if count is not None:
        return res
    else:
        return res[0]


class Inibin(dict):
    """
    Inibin reader.

    Does not support all flags yet, but covers typical use cases.

    """
    # Flag constants
    # Flags are listed in the order their data appears in the file.
    # Each flag is (bitmask, [quantity,] function_or_format)
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

    def __init__(self, buffer, font_config=None, kind=None, fix_keys=True):
        """
        Arguments:
        buffer -- file-like object or string with the inibin's contents. Make sure the file
            was opened in binary mode.
        font_config -- a dictionary representation of fontconfig_en_US.txt
        kind -- either 'CHARACTER' or 'ABILITY' (default 'CHARACTER')

        """
        self.font_config = font_config
        self.kind = kind
        self.fix_keys = fix_keys

        self.load_from(buffer)

    def load_from(self, buffer):
        """Load this instance from a new buffer."""
        # Normalize buffer parameter
        if not hasattr(buffer, 'read'):
            buf = StringIO.StringIO(buffer)
        self.buffer = buffer

        # Parse inibin
        data = self.read_inibin()

        # Convert the mapping to be more human-readable
        if self.fix_keys:
            import maps
            from maps import CHARACTER, ABILITY
            assert hasattr(maps, self.kind)
            mapping = _fix_keys(getattr(maps, self.kind), data, self.font_config)

        self.data = data

    @staticmethod
    def _lookup_in_string_table(buffer, flags, mapping, str_len):
        # String table
        # TODO: Move this into its own function
        if flags & 0b0001000000000000:
            count = _unpack_from(buffer, 'H')
            keys = _unpack_from(buffer, 'i', count)
            values = _unpack_from(buffer, 'H', count)
            strings = buffer.read(str_len)
            mapping['raw_strings'] = strings  # For debug
            values = [strings[v:].partition('\x00')[0] for v in values]

            for key, value in zip(keys, values):
                assert key not in mapping
                mapping[key] = value

    def _read_header(self):
        self.version = _unpack_from(self.buffer, 'B')
        if not self.version == 2:
            raise ValueError("Invalid version number: %s" % self.version)

        # TODO: Do not put str_len on class
        self.str_len = _unpack_from(self.buffer, 'H')

        self.flags = _unpack_from(self.buffer, 'H')

    def _process_flag(self, flag_defn, mapping):
        if flag_defn[1] is None:
            # String table must be handled differently
            return

        # Read number of keys
        count = _unpack_from(self.buffer, 'H')
        keys = _unpack_from(self.buffer, 'i', count)

        # Does the flag specify multiple values per key?
        per_count = 1
        try:
            per_count = int(flag_defn[1])
        except (ValueError, TypeError):
            pass
        else:
            # Remove multiplier from the row
            flag_defn = [flag_defn[0]] + list(flag_defn[2:])

        # Read values
        if isinstance(flag_defn[1], basestring):
            values = _unpack_from(self.buffer, flag_defn[1], per_count * count)

            # Apply row functions (if any)
            for transform in flag_defn[2:]:
                values = [transform(v) for v in values]
        elif callable(flag_defn[1]):
            # Custom function (ex. bits)
            values = flag_defn[1](self.buffer, count)
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

        # Update mapping
        for key, value in zip(keys, values):
            assert key not in mapping
            mapping[key] = value

    def read_inibin(self):
        buffer = self.buffer
        mapping = {}

        # Abort if an unrecognized flag is present
        masked_flags = self.flags & (~Inibin.RECOGNIZED_FLAGS)
        if masked_flags != 0:
            raise IOError("Unrecognized flags: %s" % bin(masked_flags))

        # Inibin v2 blocks
        # Flags are in the order they would appear in the file in
        for row in Inibin.FLAGS:
            if not row[0] & self.flags:
                continue

            self._process_flag(row, mapping)


        self._lookup_in_string_table(buffer, self.flags, mapping, self.str_len)

        # There should be no non-padding bytes remaining
        remaining = buffer.read()
        if len(remaining) > 0 and not all(c == '\x00' for c in remaining):
            raise IOError("%i bytes remaining" % len(remaining))

        return mapping
