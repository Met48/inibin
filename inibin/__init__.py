"""
A reader for the inibin file format.

One function, read_inibin, is exported for use. It will read the file buffer,
parse the inibin, and map the inibin keys to have human-readable names.

Champion and ability inibins are supported.
"""

from .reader import read_inibin

__all__ = ['read_inibin']

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
    mapping = read_inibin(data, {}, kind, fix_keys)
    pprint(mapping)


if __name__ == '__main__':
    main()
