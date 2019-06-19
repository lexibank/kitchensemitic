# coding: utf8
from __future__ import unicode_literals, print_function, division

import attr

from clldutils.path import Path
from clldutils.misc import lazyproperty, slug

from pylexibank.dataset import Metadata
from pylexibank.dataset import Dataset as BaseDataset, Language as BaseLanguage

import lingpy as lp

PREPARSE = [
    ("'", "ʼ"), ("j", "d͡ʒ"), ("y", "j"), ("-", "+"), ("'", "ˈ"),
    ('?', "ʔ"), ('//', '/'), ('', ''), ('7', 's'), ('', '')
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

# because the naming scheme between the cognates file and the
# data file are inconsistent, we need this mapping
# (i.e. the cognates file is ASCII, while the data file has UTF8 tokens)
relabel_languages = {
    "Ge'ez": "Gɛ'ɛz",
    "Tigre": "Tigrɛ",
    "Walani": 'ʷalani',
    "Ogaden Arabic": "Ogadɛn Arabic",
    "Mehri": "Mɛhri",
    "Jibbali": "Gibbali",
}
# the cognate table columns are uppercase, but there are a few mismatches:
relabel_words = {
    'Cold (air)': 'COLD (OF AIR)',
    'Fat (n.)': 'FAT',
    'Fish (n.)': 'FISH', 
    'Hair (head)': 'HAIR',
    'Skin (human)': 'SKIN (N.)',
}

@attr.s
class Language(BaseLanguage):
   Sources = attr.ib(default=None)



class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "kitchensemitic"
    language_class = Language
  
    def cmd_download(self, **kw):
        self.raw.xls2csv('Semitic.Wordlists.xls')
        self.raw.xls2csv('Semitic.Codings.Multistate.xlsx')

    def clean_form(self, row, form):
        form = BaseDataset.clean_form(self, row, form)
        if form != '---':
            return form

    @lazyproperty
    def tokenizer(self):
        return lambda row, col: lp.sequence.sound_classes.clean_string(
            col,
            merge_vowels=False,
            preparse=PREPARSE,
            rules=CONVERSION,
            semi_diacritics='')[0].split()

    def cmd_install(self, **kw):
        langs = {
            l['Name']: (l['ID'], l['Sources'].split(";")) for l in self.languages
        }

        concepts = {
            c.english: (c.concepticon_id, c.concepticon_gloss)
            for c in self.conceptlist.concepts.values()
        }

        rows = self.raw.read_csv('Semitic.Wordlists.ActualWordlists.csv')
        header = rows.pop(0)
        crows = self.raw.read_csv('Semitic.Codings.Multistate.Sheet1.csv')
        cheader = crows.pop(0)
        
        # process cognates first
        cognates = {}
        for row in crows:
            row = dict(zip(cheader, row))
            # first, unnamed column is the Language & make language name consistent
            lang = row.pop('')
            cognates[relabel_languages.get(lang, lang)] = row
        
        with self.cldf as ds:
            ds.add_languages()
            ds.add_sources(*self.raw.read_bib())
            
            ##D = {0: ['doculect', 'concept', 'ipa', 'tokens']}
            ##idx2word_id = {}
            ##idx = 1
            for row in rows:
                row = dict(zip(header, row))
                gloss = row.pop('Gloss')
                concept = concepts[gloss]
                csid = slug(concept[1])
                
                ds.add_concept(
                    ID=csid,
                    Name=gloss,
                    Concepticon_ID=concept[0],
                    Concepticon_Gloss=concept[1]
                )
                
                for lang, forms in row.items():
                    if forms == '---':  # skip bad forms
                        continue

                    lid, src = langs[lang]  # get language details
                    # get cognate
                    cogs = cognates[lang][relabel_words.get(gloss, gloss.upper())]
                    assert cogs is not None, "unable to match cognate %s-%s" % (lang, concept)
                    
                    forms = [f.strip() for f in forms.replace(",", "/").split("/") if len(f.strip())]
                    cogs = [c.strip() for c in cogs.replace(",", "/").split("/") if len(c.strip())]
                    # if the number of cognates does not match the number for forms,
                    # it looks like the cognate set used is the first one, so fill the
                    # cognates to the same size with the token used as a
                    # non-cognate marker ('-')
                    if len(forms) > len(cogs):
                        cogs.extend('-' for _ in range(len(forms) - len(cogs)))
                    
                    # there does appear to be one instance of more cognates than forms:
                    #   Harsusi's "ges'" - RAIN (N.) = D/I
                    # .. but it looks cognate with Hebrew's and Ugaritic's set D rather than
                    # set I (e.g. Ogaden Arabic "matar"), so I think it's a typo and
                    # we'll ignore it.
                    
                    # there are also forms that have no lexeme but do have a cognate set...
                    # have to ignore these for now. Can't think of what to do with them
                    # otherwise:
                    #    Mɛhri Dog --- D
                    #    Mɛhri Dry (adj.) --- F
                    #    Hebrew Grass --- C/J
                    #    Hebrew New --- A
                    #    Mɛhri Seed --- C
                    #    Hebrew Three --- A
                    #    Mɛhri Warm --- H
                    #    Hebrew Ye --- A

                    for form, cog in zip(forms, cogs):
                        assert len(form), "Empty form %s - %r - %r - %r" % (lid, gloss, form, cog)
                        assert len(cog), "Empty cognate %s - %r - %r - %r" % (lid, gloss, form, cog)
                        
                        cogid = '%s-%s' % (csid, cog)
                        for row in ds.add_lexemes(
                                Language_ID=lid,
                                Parameter_ID=csid,
                                Value=form,
                                Source=src
                            ):
                            if cog != '-':
                                ds.add_cognate(lexeme=row, Cognateset_ID=cogid, Source=['Kitchen2009'])
