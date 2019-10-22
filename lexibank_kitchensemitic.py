from pathlib import Path

import attr
import lingpy as lp
from clldutils.misc import lazyproperty
from pylexibank import Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.forms import FormSpec
from pylexibank.util import pb

from kitchensemitic_helpers import PREPARSE, CONVERSION, RELABLE_WORDS, make_cognate_table


@attr.s
class KSLanguage(Language):
    Sources = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "kitchensemitic"
    language_class = KSLanguage

    form_spec = FormSpec(
        brackets={"(": ")"}, separators=";/,", missing_data=("?", "---"), strip_inside_brackets=True
    )

    def cmd_download(self, args):
        self.raw_dir.xls2csv("Semitic.Wordlists.xls")
        self.raw_dir.xls2csv("Semitic.Codings.Multistate.xlsx")

    @lazyproperty
    def tokenizer(self):
        return lambda row, col: lp.sequence.sound_classes.clean_string(
            col, merge_vowels=False, preparse=PREPARSE, rules=CONVERSION, semi_diacritics=""
        )[0].split()

    def cmd_makecldf(self, args):
        lexeme_rows = self.raw_dir.read_csv("Semitic.Wordlists.ActualWordlists.csv")
        lexeme_header = lexeme_rows.pop(0)

        cognate_table = make_cognate_table(
            self.raw_dir.read_csv("Semitic.Codings.Multistate.Sheet1.csv")
        )

        languages, concepts = {}, {}

        for concept in self.conceptlist.concepts.values():
            args.writer.add_concept(
                ID=concept.id,
                Name=concept.english,
                Concepticon_ID=concept.concepticon_id,
                Concepticon_Gloss=concept.concepticon_gloss,
            )
            concepts[concept.english] = concept.id

        for language in self.languages:
            args.writer.add_language(
                ID=language["ID"],
                Name=language["Name"],
                Glottocode=language["Glottocode"],
                Sources=language["Sources"],
            )
            languages[language["Name"]] = (language["ID"], language["Sources"].split(";"))

        for row in pb(lexeme_rows, desc=f"Build CLDF for {self.id}"):
            row = dict(zip(lexeme_header, row))
            gloss = row.pop("Gloss")

            for lang, lexeme in row.items():
                lid, src = languages[lang]
                cogs = cognate_table[lang][RELABLE_WORDS.get(gloss, gloss.upper())]

                forms = [f.strip() for f in lexeme.replace(",", "/").split("/") if len(f.strip())]
                cogs = [c.strip() for c in cogs.replace(",", "/").split("/") if len(c.strip())]

                if len(forms) > len(cogs):
                    cogs.extend('-' for _ in range(len(forms) - len(cogs)))

                for form, cog in zip(forms, cogs):
                    cogid = '%s-%s' % (concepts[gloss], cog)

                    for lex in args.writer.add_lexemes(
                        Language_ID=lid, Parameter_ID=concepts[gloss], Value=form, Source=src
                    ):
                        if cog != "-":
                            args.writer.add_cognate(
                                lexeme=lex, Cognateset_ID=cogid, Source=["Kitchen2009"]
                            )
