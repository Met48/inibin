"""Usage:
  python -m inibin <file>
  python -m inibin <kind> <file>

Arguments:
  <file> -- path to an inibin file
  <kind> -- what to interpret the inibin as, must be champion or ability
"""
from pprint import pprint
import sys

from . import Inibin

KINDS = {
    'a': 'as_ability',
    'ability': 'as_ability',
    'c': 'as_champion',
    'champion': 'as_champion',
}

def main():
    if len(sys.argv) not in (2, 3):
        print("Invalid number of arguments.")
        print(__doc__)
        sys.exit(1)

    if len(sys.argv) == 3:
        kind = sys.argv[1].lower()
        if kind not in KINDS:
            print("Invalid kind %s" % kind)
            print(__doc__)
            sys.exit(1)
        else:
            kind_method = KINDS[kind]
    else:
        kind_method = None

    with open(sys.argv[-1], 'rb') as f:
        inibin = Inibin(f)

    if kind_method is not None:
        kind_method = getattr(inibin, kind_method)
        pprint(kind_method({}))
    else:
        pprint(inibin)


if __name__ == '__main__':
    main()