# Test the gdplayer decoder pipeline offline, against a real captured payload.
# The fixture is the octal-escaped 'return"..."' literal from a live gdplayer
# page (AAEncode-decoded). Values below were verified against a headless JS
# run of the same page (the app's own live E2E also decodes real sources).
import os
import unittest

from indonime.ext.gdrive import _oct_unescape, _vars_from_packed

_FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'gd_oct_literal.txt')


class TestGDPlayerDecoder(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    with open(_FIXTURE, encoding='utf-8') as f:
      lit = f.read()
    assert lit.startswith('return"')
    cls.vars = _vars_from_packed(lit)

  def test_oct_unescape_yields_packed_js(self):
    lit = open(_FIXTURE, encoding='utf-8').read()
    body = _oct_unescape(lit[len('return"'):-1])
    self.assertIn("eval(function(p,a,c,k,e,d)", body)
    self.assertIn("'.split('|')", body)

  def test_vars_match_live_page(self):
    v = self.vars
    self.assertEqual(v['apx'], 'aHR0cHM6Ly9nZHBsYXllci50by9hcGktY29uZmlnLw==')
    self.assertEqual(v['ps'], 'OHlrRVkvUUFNd08vTGp0SmlSR2Vpb3ZsYnR6Sk5ORUptQ2VrU1ZDc3AxanMxN3pGK3Y3VjBQbnErbG1zSDA5ams5UVpoN3hoVzVPR29TL2lMZ2loSHc9PQ,,')
    self.assertEqual(v['pd'], '1786614956')
    self.assertEqual(v['baseURL'], 'https://gdplayer.to/')

  def test_kaken_qsx_distinct_tokens(self):
    v = self.vars
    # kaken/qsx share a long prefix but are different tokens (qsx = "-," split
    # continuation). Live E2E proved both work against the real API.
    self.assertNotEqual(v['kaken'], v['qsx'])
    self.assertTrue(v['kaken'].startswith('VEJ1cTdtNlRqa2ty'))
    self.assertGreater(len(v['kaken']), 200)
    self.assertIn('-,', v['kaken'])


if __name__ == '__main__':
  unittest.main()
