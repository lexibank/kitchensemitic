from pathlib import Path

import attr
from pylexibank import Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.forms import FormSpec
from pylexibank.util import pb

# Correct mismatches between the lexeme table and the table coding the cognate information.
RELABLE_LANGUAGES = {
    "Ge'ez": "Gɛ'ɛz",
    "Tigre": "Tigrɛ",
    "Walani": "ʷalani",
    "Ogaden Arabic": "Ogadɛn Arabic",
    "Mehri": "Mɛhri",
    "Jibbali": "Gibbali",
}

# Correct mismatches between the lexeme table and the table coding the cognate information.
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


@attr.s
class KSLanguage(Language):
    Sources = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "kitchensemitic"
    language_class = KSLanguage

    form_spec = FormSpec(
        brackets={}, separators="/,", missing_data=("---",), strip_inside_brackets=False
    )

    def cmd_download(self, args):
        self.raw_dir.xls2csv("Semitic.Wordlists.xls")
        self.raw_dir.xls2csv("Semitic.Codings.Multistate.xlsx")

    def cmd_makecldf(self, args):
        lexeme_rows = self.raw_dir.read_csv("Semitic.Wordlists.ActualWordlists.csv")
        lexeme_header = lexeme_rows.pop(0)

        cognate_table = make_cognate_table(
            self.raw_dir.read_csv("Semitic.Codings.Multistate.Sheet1.csv")
        )

        languages, concepts = {}, {}

        for concept in self.conceptlist.concepts.values():
            concepts[concept.english] = concept.id

        for language in self.languages:
            languages[language["Name"]] = (language["ID"], language["Sources"].split(";"))

        args.writer.add_concepts(id_factory=lambda c: c.id)
        args.writer.add_languages()
        args.writer.add_sources()

        for row in pb(lexeme_rows, desc=f"Build CLDF for {self.id}"):
            row = dict(zip(lexeme_header, row))
            gloss = row.pop("Gloss")

            for lang, lexeme in row.items():
                lid, src = languages[lang]
                # Lookup is based on the relabled words (see above) due to gloss
                # mismatches between the two tables.
                cogs = cognate_table[lang][RELABLE_WORDS.get(gloss, gloss.upper())]

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

                for form, cog in zip(forms, cogs):
                    cogid = "%s-%s" % (concepts[gloss], cog)

                    lex = args.writer.add_form(
                        Language_ID=lid,
                        Parameter_ID=concepts[gloss],
                        Value=lexeme,
                        Source=src,
                        Form=form,
                    )

                    if cog != "-":
                        args.writer.add_cognate(
                            lexeme=lex, Cognateset_ID=cogid, Source=["Kitchen2009"]
                        )
