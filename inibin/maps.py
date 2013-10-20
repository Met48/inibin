"""
Standard mappings of inibin keys.
"""

__all__ = ['CHAMPION', 'ABILITY']

# Helper functions
MULT_5 = lambda x: x * 5
PERCENTAGE = lambda x: float(x * 10) if isinstance(x, int) else x * 100

# Champion mapping
# Unmapped keys:
#   'tags': -148652351,  # Comma-delimited
#   'lore': -51751813,
#   'name': 82690155,
#   'desc': -547924932,
#   'tips_as': 70667385,
#   'tips_against': 70667386,
#   'title': -547924932,
CHAMPION = {
    'stats': {
        # Bases do not include level one per-level bonus
        #   (with the exception of apsd)
        'hp': {
            'base': 742042233,
            'per_level': -988146097,
        },
        'hp5': {
            # Convert from hp1
            'base': (-166675978, MULT_5),
            'per_level': (-1232864324, MULT_5),
        },
        'mana': {
            'base': 742370228,
            'per_level': 1003217290,
        },
        'mp5': {
            # Convert from hp1
            'base': (619143803, MULT_5),
            'per_level': (1248483905, MULT_5),
        },
        'range': 1387461685,
        'dmg': {
            'base': 1880118880,
            'per_level': 1139868982,
        },
        'aspd': {
            # Guard against negative 1 aspd
            # TODO: See what inibins have this value
            'base': (-2103674057,
                     lambda x: (0.625 / (1.0 + x)) if x != -1.0 else None),
            # Per-level aspd value is an integer percentage (ex. 2 => 2%)
            'per_level': (770205030, lambda x: x * 0.01),
        },
        'armor': {
            'base': -1695914273,
            'per_level': 1608827366,
        },
        'mr': {
            'base': 1395891205,
            # TODO: Verify if -194100563 is still in use for per-level mr
            'per_level': -262788340,
        },
        'speed': 1081768566,
    },

    # Skill names
    'abilities': {
        # TODO: Passive
        # 'passive_desc': 743602011,
        'skill1': 404599689,
        'skill2': 404599690,
        'skill3': 404599691,
        'skill4': 404599692,
    },
}

# Unused keys:
#   # The tags seem inaccurate most of the time
#   'tags': (1829373218, lambda s: s.split(' | ')),
#   '?buff_tooltip?': -2007242095,
#   '?levelup?': -963665088,
ABILITY = {
    'cost': {
        # @Cost@
        'level1': -523242843,
        'level2': -523242842,
        'level3': -523242841,
        'level4': -523242840,
        'level5': -523242839,
    },
    'effect1': {
        # @Effect1Amount@
        # Usually physical / magic damage
        'level1': 466816973,
        'level2': -235012530,
        'level3': -936842033,
        'level4': -1638671536,
        'level5': 1954466257
    },
    'effect2': {
        # @Effect2Amount@
        'level1': -396677938,
        'level2': -1098507441,
        'level3': -1800336944,
        'level4': 1792800849,
        'level5': 1090971346
    },
    'effect3': {
        # @Effect3Amount@
        'level1': -1260172849,
        'level2': -1962002352,
        'level3': 1631135441,
        'level4': 929305938,
        'level5': 227476435
    },
    'effect4': {
        # @Effect4Amount@
        'level1': -2123667760,
        'level2': 1469470033,
        'level3': 767640530,
        'level4': 65811027,
        'level5': -636018476
    },
    'effect5': {
        # @Effect5Amount@
        'level1': 1307804625,
        'level2': 605975122,
        'level3': -95854381,
        'level4': -797683884,
        'level5': -1499513387
    },
    'effect6': {
        # TODO: Finish
        'WARNING': 'NOT IMPLEMENTED'
    },
    # @CharAbilityPower@ and @CharBonusPhysical@
    'scale1': (844968125, PERCENTAGE),
    # @CharAbilityPower2@ and @CharBonusPhysical2@
    'scale2': (-1783890251, PERCENTAGE),
    # There is no scale3 / 4
    'cooldown': {
        # @Cooldown@
        'level1': -1665665330,
        'level2': -1665665329,
        'level3': -1665665328,
        'level4': -1665665327,
        'level5': -1665665326,
    },
    'name': 1805538005,
    'internalName': -1203593619,
    'desc': -863113692,
    'tooltip': -1660048132,
    'img': 2059614685,
    'range': -1764096472,
    # TODO: Investigate accuracy of this key.
    #   For at least one ult it is correct, but it can also be 0.
    # '?range_ult?': -1549183761,
}
