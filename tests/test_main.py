#!/usr/bin/python3

import unittest
import os
from pathlib import Path

import feaxlib
import ufoLib2


class UnikeyTests(unittest.TestCase):

    def setUp(self):
        os.chdir('tests/data')
        self.font = ufoLib2.Font.open('../font-psf-test/source/PsfTest-Regular.ufo')

    def tearDown(self):
        self.font.close()
        os.chdir('../..')

    def test_sample(self):
        expected = Path('sample.fea').read_text().strip()
        actual = feaxlib.feax_get_features(self.font, feaxfile='sample.feax').strip()
        assert actual == expected

    def helper_features(self, basename, feax_basename=''):
        feafont = feaxlib.Font()
        feafont.readaps(self.font)
        feafont.make_marks()
        feafont.make_classes(None)
        p = feaxlib.feaplus_parser(None, feafont.glyphs, feafont.fontinfo, feafont.kerns, feafont.defines)
        # feafont.append_classes(self.p)
        # feafont.append_positions(self.p)

        expected = Path(f'{basename}.fea').read_text().strip()
        if not feax_basename:
            feax_basename = basename
        doc = p.parse(f'{feax_basename}.feax')
        actual = doc.asFea().strip()
        return expected, actual

    def test_calc(self):
        expected, actual = self.helper_features('calc')
        assert actual == expected

    def test_issue65(self):
        expected, actual = self.helper_features('issue65')
        assert actual == expected

    def test_kashidaR(self):
        expected, actual = self.helper_features('kashidaR', 'kashida')
        assert actual == expected

    def test_kashidaB(self):
        self.font.close()
        self.font = ufoLib2.Font.open('../font-psf-test/source/PsfTest-Bold.ufo')
        expected, actual = self.helper_features('kashidaB', 'kashida')
        assert actual == expected

    def test_ligatures(self):
        expected, actual = self.helper_features('ligatures')
        assert actual == expected


if __name__ == '__main__':
    unittest.main()
