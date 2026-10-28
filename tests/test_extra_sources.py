"""Garantias para novas fontes: inventário sem dados pessoais ou indicadores não homologados."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
class ExtraSourcesContract(unittest.TestCase):
    def test_sources_are_official_and_unvalidated(self):
        d=json.loads((ROOT/'public/data/extra_sources.json').read_text(encoding='utf8'))
        self.assertEqual(d['schemaVersion'],'1.0')
        self.assertEqual(d['municipality'],'4304606')
        self.assertEqual(d['series'],{})
        self.assertEqual(set(d['sources']),{'piaps_rs_2026','srag_sivep_2026','pni_doses_2026','sisagua_vigilancia'})
        allowed={'atencaoprimaria.rs.gov.br','dadosabertos.saude.gov.br'}
        for key,source in d['sources'].items():
            self.assertEqual(source['status'],'not_loaded',key)
            self.assertIsNone(source['retrievedAt'])
            self.assertIsNone(source['reference'])
            self.assertIn(urlparse(source['url']).hostname,allowed)
            self.assertTrue(source['label'].strip())
            self.assertTrue(source['note'].strip())
            self.assertFalse(any(k in source for k in ('records','value','persons','patients','cpf','cns')))
    def test_catalog_and_smoke_include_new_sources(self):
        sources=(ROOT/'src/lib/sourcesView.ts').read_text(encoding='utf8')
        smoke=(ROOT/'scripts/smoke-mobile.cjs').read_text(encoding='utf8')
        self.assertIn("readOptional('extra_sources.json')",sources)
        self.assertIn("Vigilância complementar e programas estaduais",sources)
        self.assertIn("'farmacia-siaps'",smoke)
        self.assertIn('DESKTOP_SMOKE_OK',smoke)
if __name__=='__main__':
    unittest.main()
