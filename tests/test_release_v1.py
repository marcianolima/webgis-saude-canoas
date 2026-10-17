import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PublishedSnapshotsV1Tests(unittest.TestCase):
    def test_indicator_contract(self):
        s=json.loads((ROOT/'public/data/indicators.json').read_text(encoding='utf8'))
        self.assertEqual(s['schemaVersion'],'1.0')
        self.assertIsInstance(s['sources'],dict)
        self.assertIsInstance(s['series'],dict)
        for rows in s['series'].values():
            years=set()
            for r in rows:
                self.assertNotIn(r['year'],years)
                years.add(r['year'])
                self.assertIsInstance(r['value'],int)
                self.assertGreaterEqual(r['value'],0)
                self.assertGreaterEqual(r['scanned'],r['value'])
                self.assertTrue(r['residence'])
                self.assertFalse(set(r) & {'cpf','cns','nome_paciente','dt_obito','dt_nasc'})
    def test_cnes_geojson_and_summary_agree(self):
        summary=json.loads((ROOT/'public/data/summary.json').read_text(encoding='utf8'))
        geo=json.loads((ROOT/'public/data/establishments.geojson').read_text(encoding='utf8'))
        self.assertEqual(summary['municipality']['ibge'],'4304606')
        if summary['sourceInfo']['cnes']['status']=='ok':
            self.assertEqual(summary['facilities']['withCoordinates'],len(geo['features']))
            self.assertGreaterEqual(summary['facilities']['total'],len(geo['features']))
        if summary['sourceInfo']['beds']['status']=='ok':
            self.assertGreaterEqual(summary['beds']['total'],summary['beds']['sus'])
        sensitive={'cpf','cns','paciente','nome_mae','dt_nasc','data_nascimento'}
        for f in geo['features']:
            self.assertFalse(sensitive & set(f['properties']))
if __name__=='__main__':unittest.main()
