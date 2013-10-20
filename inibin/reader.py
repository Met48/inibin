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


inibin_format = [
    ('version', 'B'),
    ('end_len', 'H'),
    ('subversion', 'H'),
]
VERSION = 2
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
    (0b0001000000000000, None),  # String offsets
    # String offsets will be handled manually
]


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


def read_inibin(buf, font_config, kind='character', fix_keys=True):
    """
    Read an inibin file.

    Arguments:
    buf -- file-like object with the inibin's contents. Make sure the file
        was opened in binary mode.
    font_config -- a dictionary representation of fontconfig_en_US.txt
    kind -- either 'character' or 'ability' (default 'character')
    """

    try:
        buf.read
    except AttributeError:
        buf = StringIO.StringIO(buf)

    mapping = {}

    # Header

    version = _unpack_from(buf, 'B')
    assert version == 2

    str_len = _unpack_from(buf, 'H')

    flags = _unpack_from(buf, 'H')

    # Verify that we can process all the flags this inibin uses
    #   (support is not comprehensive yet, but handles all the typical flags)
    recognized_flags = reduce(lambda a, b: a | b, (f[0] for f in FLAGS), 0)
    masked_flags = flags & (~recognized_flags)

    if masked_flags != 0:
        raise RuntimeError(
            "Unrecognized flags. Observed: %s, whitelisted: %s, difference: %s" %
            (bin(flags), bin(recognized_flags), bin(masked_flags)))

    # Inibin v2 blocks
    # Flags are in the order they would appear in the file in
    for row in FLAGS:
        if row[0] & flags:
            # This skip is here for the last flag, the string table
            if row[1] is None:
                continue

            # Read number of keys
            count = _unpack_from(buf, 'H')
            keys = _unpack_from(buf, 'i', count)

            # Does the flag specify multiple values per key?
            per_count = 1
            try:
                per_count = int(row[1])
            except (ValueError, TypeError):
                pass
            else:
                # Remove multiplier from the row
                row = [row[0]] + list(row[2:])

            # Read values
            if isinstance(row[1], basestring):
                values = _unpack_from(buf, row[1], per_count * count)

                # Apply row functions (if any)
                for transform in row[2:]:
                    values = [transform(v) for v in values]
            elif callable(row[1]):
                # Custom function (ex. bits)
                values = row[1](buf, count)
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

    # String table
    # TODO: Move this into its own function
    if flags & 0b0001000000000000:
        count = _unpack_from(buf, 'H')
        keys = _unpack_from(buf, 'i', count)
        values = _unpack_from(buf, 'H', count)
        strings = buf.read(str_len)
        mapping['raw_strings'] = strings  # For debug
        values = [strings[v:].partition('\x00')[0] for v in values]

        for key, value in zip(keys, values):
            assert key not in mapping
            mapping[key] = value

    # There should be no non-padding bytes remaining
    remaining = buf.read()
    if len(remaining) > 0 and not all(c == '\x00' for c in remaining):
        raise RuntimeError("%i bytes remaining!" % len(remaining))

    # Convert the mapping to be more human-readable
    if fix_keys:
        from maps import CHARACTER, ABILITY
        key_maps = {
            'character': CHARACTER,
            'ability': ABILITY,
        }
        assert kind in key_maps
        mapping = _fix_keys(key_maps[kind], mapping, font_config)

    return mapping

