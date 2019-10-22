PREPARSE = [
    ("'", "ʼ"),
    ("j", "d͡ʒ"),
    ("y", "j"),
    ("-", "+"),
    ("'", "ˈ"),
    ("?", "ʔ"),
    ("//", "/"),
    ("", ""),
    ("7", "s"),
    ("", ""),
]

CONVERSION = {
    "nn": "nː",
    "9": "ʕ",
    "7": "ʔ",
    "c": "tʃ",
    "ii": "iː",
    "bb": "bː",
    "oo": "oː",
    "dd": "dː",
    "ss": "sː",
    "kk": "kː",
    "ww": "wː",
    "uu": "uː",
    "tt": "tː",
    "ɔɔ": "ɔː",
    "éé": "eː",
    "gg": "gː",
    "pp": "pː",
    "ɛɛ": "ɛː",
    "": "ɔ",
    "ʃʃ": "ʃː",
    "ff": "fː",
    "ll": "lː",
    "rr": "rː",
    "jj": "jː",
    "mm": "mː",
    "zz": "zː",
}

RELABLE_LANGUAGES = {
    "Ge'ez": "Gɛ'ɛz",
    "Tigre": "Tigrɛ",
    "Walani": "ʷalani",
    "Ogaden Arabic": "Ogadɛn Arabic",
    "Mehri": "Mɛhri",
    "Jibbali": "Gibbali",
}

RELABLE_WORDS = {
    "Cold (air)": "COLD (OF AIR)",
    "Fat (n.)": "FAT",
    "Fish (n.)": "FISH",
    "Hair (head)": "HAIR",
    "Skin (human)": "SKIN (N.)",
}


def make_cognate_table(kitchensemitic_cognate_table):
    cognate_rows = kitchensemitic_cognate_table[1:]
    cognate_header = kitchensemitic_cognate_table[0]
    cognates = {}

    for row in cognate_rows:
        row = dict(zip(cognate_header, row))
        language = row.pop("")  # This is the untitled first column in the cognate table.
        cognates[RELABLE_LANGUAGES.get(language, language)] = row

    return cognates
