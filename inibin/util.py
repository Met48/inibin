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


def _fix_keys(key_mapping, inibin, string_table=None):
    """
    Return a human-readable dictionary from the inibin.

    Arguments:
    key_mapping -- Dictionary used for conversion. Supports nesting. Every other
        value should be a numeric inibin key, or a tuple of the key and a
        function to apply to the result.
    inibin -- The dictionary returned from reading an inibin.
    string_table -- Used to translate strings. Any string with a key in
        string_table will be replaced. Typically loaded from a fontconfig_*.txt.
    """
    if string_table is None:
        string_table = {}

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

                if index is None or index not in inibin:
                    out_node[key] = None
                    continue

                val = inibin[index]

                # Try numeric conversion
                # Inibins often store numbers in strings
                if isinstance(val, bytes):
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            val = val.decode('utf8')

                # Check if value is a reference to a fontconfig key
                if val in string_table:
                    val = string_table[val]

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
