from pathlib import Path

import attr
from pylexibank import Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.forms import FormSpec
from pylexibank.util import progressbar

from clldutils.misc import slug

REPLACEMENTS = [
    ("u'", "u"),
    ("a'", "a"),
    ("ɔ'", "ɔ"),
    ("7", "ʔ"),
    ("?", "ʔ"),
    ("9", "ʕ"),
    ("q", "k'"),  # ق
    ("'", "ˤ"),
    ("ɤ", "ɣ"),
    ("ġ", "ɣ"), # غ
    # Remove stress marks
    ("έ", "ɛ"),
    ("έ", "ɛ"),
    ("á", "a"),
    ("é", "e"),
    ("ó", "o"),
    ("ú", "u"),
    ("í", "i"),
    ("ĩ", "i"),
    ("ź", "ɮ"),
    ("ž", "ʒ"),
    ("ž", "ʒ"),
    ("ẓ", "ðˤ"),
    ("š", "ʃ"),
    ("x", "χ"),
    ("j", "ʒ"),
    ("y", "j"),
    ("ň", "ɲ"),
    # ("x'", "xʼ"), # https://en.wikipedia.org/wiki/Tigrinya_language and matching grapheme for "voiceless velar ejective fricative consonant" under CLTS
    # ("i'", "ɪ"), # in free variance with i, is a vowel between front and center, high open; its allophone is ǔ after w. (Leslau 1963).
    # ("ɛ'", "æ"), # betweem center and front, low close; is in free variant with a (central, low) in any position except initial and final; its allophone is å (central, low, rounded) after a labial (Leslau 1963).
    # ("a:'", "a:"), # instances correspond with a long vowel
]

# Correct mismatches between the lexeme table and the table coding the cognate information.
RELABEL_LANGUAGES = {
    "Ge'ez": "Gɛ'ɛz",
    "Tigre": "Tigrɛ",
    "Walani": "ʷalani",
    "Ogaden Arabic": "Ogadɛn Arabic",
    "Mehri": "Mɛhri",
    "Jibbali": "Gibbali",
}

# Correct mismatches between the lexeme table and the table coding the cognate information.
RELABEL_WORDS = {
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
        cognates[RELABEL_LANGUAGES.get(language, language)] = row

    return cognates


@attr.s
class CustomLanguage(Language):
    Sources = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "kitchensemitic"
    language_class = CustomLanguage

    form_spec = FormSpec(
        brackets={"(": ")", "[": "]"}, separators="/,", missing_data=("---",), strip_inside_brackets=True,
        replacements=REPLACEMENTS
    )

    def cmd_download(self, args):
        self.raw_dir.xls2csv("Semitic.Wordlists.xls")
        self.raw_dir.xls2csv("Semitic.Codings.Multistate.xlsx")

    def cmd_makecldf(self, args):
        concepts = args.writer.add_concepts(
            id_factory=lambda x: x.id.split('-')[-1] + '_' + slug(x.english),
            lookup_factory="Name"
        )

        args.writer.add_concept(ID="flyverb", Name="Fly (v.)",
                                Concepticon_ID="1441", Concepticon_Gloss="FLY (MOVE THROUGH AIR)")

        concepts["fly (verb)"] = "flyverb"

        args.writer.add_concept(ID="claw", Name="Claw",
                                Concepticon_ID="72", Concepticon_Gloss="CLAW")

        concepts["Claw"] = "claw"

        args.writer.add_languages()

        languages = {}  # We use the language map for an easier sources lookup.

        for language in self.languages:
            languages[language["Name"]] = (language["ID"], sorted(language["Sources"].split(";")))

        args.writer.add_sources()

        lexeme_rows = self.raw_dir.read_csv("Semitic.Wordlists.ActualWordlists.csv")
        lexeme_header = lexeme_rows.pop(0)

        cognate_table = make_cognate_table(
            self.raw_dir.read_csv("Semitic.Codings.Multistate.Sheet1.csv")
        )

        for row in progressbar(lexeme_rows):
            row = dict(zip(lexeme_header, row))
            gloss = row.pop("Gloss")

            for lang, lexeme in row.items():
                lid, src = languages[lang]
                # Lookup is based on the relabled words (see above) due to gloss
                # mismatches between the two tables.
                cogs = cognate_table[lang][RELABEL_WORDS.get(gloss, gloss.upper())]

                # Note that we cannot use the internal splitting algorithm, because of individual
                # problems in the source data cells. Thus, we call form_spec explicitly.
                forms = self.form_spec.split(item=None, value=lexeme)
                cogs = self.form_spec.split(item=None, value=cogs)

                # Add a non-cognate marker for forms without cognate information. Additionally,
                # instances with more cognates than forms are ignored, for example
                # Harsusi's "ges'" - RAIN (N.) = D/I.
                # Likewise, there exist forms that have no lexemes but do have cognate information.
                # These are ignored as well:
                #  Mɛhri Dog --- D
                #  Mɛhri Dry (adj.) --- F
                #  Hebrew Grass --- C/J
                #  Hebrew New --- A
                #  Mɛhri Seed --- C
                #  Hebrew Three --- A
                #  Mɛhri Warm --- H
                #  Hebrew Ye --- A
                if len(forms) > len(cogs):
                    cogs.extend("-" for _ in range(len(forms) - len(cogs)))

                if lang in ["Hebrew", "Ugaritic", "Aramaic", "Akkadian"] and gloss == "Fly (n.)":
                    concept = concepts["fly (verb)"]
                else:
                    concept = concepts[gloss]

                for form, cog in zip(forms, cogs):
                    cogid = "%s-%s" % (concept, cog)

                    lex = args.writer.add_form(
                        Language_ID=lid,
                        Parameter_ID=concept,
                        Value=lexeme,
                        Source=src,
                        Form=form,
                    )

                    if cog != "-":
                        args.writer.add_cognate(
                            lexeme=lex, Cognateset_ID=cogid, Source=["Kitchen2009"]
                        )
