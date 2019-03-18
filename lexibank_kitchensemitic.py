# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import Path
from clldutils.misc import lazyproperty, slug

from pylexibank.dataset import Metadata
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.util import getEvoBibAsBibtex

import lingpy as lp

PREPARSE = [("'", "ʼ"), ("j", "d͡ʒ"), ("y", "j"), ("-", "+"), ("'", "ˈ"), ('?', "ʔ"),
            ('//', '/'), ('', ''), ('7', 's'), ('', '')]
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


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "kitchensemitic"
    
    def cmd_download(self, **kw):
        self.raw.xls2csv('Semitic.Wordlists.xls')
        self.raw.xls2csv('Semitic.Codings.Multistate.xlsx')
        self.raw.write('sources.bib', getEvoBibAsBibtex('Kitchen2009', **kw))

    def clean_form(self, row, form):
        form = BaseDataset.clean_form(self, row, form)
        if form != '---':
            return form

    def read_csv(self, fname, **kw):
        header, rows = None, []
        for i, row in enumerate(self.raw.read_csv(fname)):
            row = [c.strip() for c in row]
            if i == 0:
                header = row
            if i > 0:
                rows.append(row)
        return header, rows

    @lazyproperty
    def tokenizer(self):
        return lambda row, col: lp.sequence.sound_classes.clean_string(
            col,
            merge_vowels=False,
            preparse=PREPARSE,
            rules=CONVERSION,
            semi_diacritics='')[0].split()

    def cmd_install(self, **kw):
        concepticon = {
            c.english: c.concepticon_id for c in self.conceptlist.concepts.values()}
        language_map = {l['NAME']: l['GLOTTOCODE'] or None for l in self.languages}

        header, rows = self.read_csv('Semitic.Wordlists.ActualWordlists.csv')
        cheader, crows = self.read_csv('Semitic.Codings.Multistate.Sheet1.csv')

        langs = header[1:]
        clean_langs = {
            """Gɛ'ɛz""": "Ge'ez",
            "Tigrɛ": "Tigre",
            'ʷalani': "Walani",
            "Ogadɛn Arabic": "Ogaden Arabic",
            "Mɛhri": "Mehri",
            "Gibbali": "Jibbali",
        }

        with self.cldf as ds:
            D = {0: ['doculect', 'concept', 'ipa', 'tokens']}
            idx2word_id = {}
            idx = 1
            ds.add_sources(*self.raw.read_bib())
            for row in rows:
                concept = row[0]
                for i, col in enumerate(row[1:]):
                    lang = langs[i]
                    ds.add_language(
                        ID=language_map[lang],
                        Name=clean_langs.get(lang, lang),
                        Glottocode=language_map[lang])
                    ds.add_concept(
                        ID=concepticon[concept],
                        Name=concept,
                        Concepticon_ID=concepticon[concept])

                    for r in ds.add_lexemes(
                            Language_ID=language_map[lang],
                            Parameter_ID=concepticon[concept],
                            Value=col):
                        idx2word_id[idx] = r['ID']
                        D[idx] = [
                            clean_langs.get(lang, lang), concept, col, r['Segments']]
                        idx += 1
                        break

            wl = lp.Wordlist(D)
            id2cog = {}
            errors = []
            for row in crows:
                taxon = row[0]
                for i, (concept, cog) in enumerate(zip(cheader[1:], row[1:])):
                    nconcept = rows[i][0]
                    if cog != '-':
                        idxs = wl.get_dict(taxon=taxon)
                        if idxs.get(nconcept, ''):
                            id2cog[idxs[nconcept][0]] = concept + '-' + cog
                        else:
                            errors += [(concept, nconcept, taxon)]
            bad_cogs = 1
            for k in wl:
                if k not in id2cog:
                    cogid = str(bad_cogs)
                    bad_cogs += 1
                    id2cog[k] = cogid

            wl.add_entries('cog', id2cog, lambda x: x)
            wl.renumber('cog')
            for k in wl:
                ds.add_cognate(
                    Form_ID=idx2word_id[k],
                    ID=k,
                    Form=wl[k, 'ipa'],
                    Cognateset_ID=slug(wl[k, 'concept']) + '-' + str(wl[k, 'cogid']),
                    Source=['Kitchen2009'])
            ds.align_cognates(lp.Alignments(wl))
