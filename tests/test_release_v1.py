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
    def test_individual_catalog_has_all_units_without_inventing_beds(self):
        file=ROOT/'public/data/facilities.json'
        if not file.exists():return
        s=json.loads((ROOT/'public/data/summary.json').read_text(encoding='utf8'))
        g=json.loads((ROOT/'public/data/establishments.geojson').read_text(encoding='utf8'))
        d=json.loads(file.read_text(encoding='utf8'))
        catalog=d['facilities']
        self.assertEqual(d['schemaVersion'],'1.1')
        self.assertEqual(len(catalog),s['facilities']['total'])
        indexed={f['cnes']:f for f in catalog}
        self.assertEqual(len(indexed),len(catalog))
        geolocated=[f for f in catalog if f.get('coordinates') is not None]
        self.assertEqual(len(geolocated),len(g['features']))
        self.assertEqual({f['properties']['cnes'] for f in g['features']},{f['cnes'] for f in geolocated})
        for entry in catalog:
            self.assertEqual(len(entry['cnes']),7)
            self.assertTrue(entry['cnes'].isdigit())
            self.assertFalse({'cpf','cns','nome_paciente','dt_nasc'} & set(entry))
            existing=entry.get('bedsTotal');sus=entry.get('bedsSus')
            if existing is not None:
                self.assertIsNotNone(sus)
                self.assertGreaterEqual(existing,sus)
                self.assertGreaterEqual(sus,0)
                if entry.get('utiTotal') is not None:
                    self.assertLessEqual(entry['utiTotal'],existing)
        if s['sourceInfo']['beds']['status']=='ok':
            with_data=[f for f in catalog if f.get('bedsTotal') is not None]
            self.assertGreaterEqual(len(with_data),2)
            self.assertEqual(sum(f['bedsTotal'] for f in with_data),s['beds']['total'])
            self.assertEqual(sum(f['bedsSus'] for f in with_data),s['beds']['sus'])
            self.assertTrue(all(f['bedsAsOf']==s['beds']['asOf'] for f in with_data))

    def test_sus_mgdi_contract_and_no_patient_records(self):
        import re
        path=ROOT/'public/data/sus.json'
        if not path.exists():
            return
        data=json.loads(path.read_text(encoding='utf8'))
        self.assertEqual(data['schemaVersion'],'1.0')
        self.assertIsInstance(data['sources'],dict)
        self.assertIsInstance(data['series'],dict)
        for kind,entries in data['series'].items():
            periods=set()
            for row in entries:
                period=row['period']
                self.assertNotIn(period,periods)
                periods.add(period)
                self.assertIsNotNone(re.fullmatch(r'20[0-9]{4}|20[0-9]{2}',period))
                self.assertGreaterEqual(row['value'],0)
                self.assertEqual(set(row),{'period','value'})
            if entries:
                self.assertEqual(data['sources'][kind]['status'],'ok')
        self.assertEqual(data['sources']['sih']['status'],'not_loaded')
        self.assertEqual(data['sources']['sia']['status'],'not_loaded')

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
        for row in geo['features']:
            self.assertFalse(sensitive & set(row['properties']))

if __name__=='__main__':
    unittest.main()
