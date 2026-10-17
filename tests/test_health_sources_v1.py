import unittest
from unittest.mock import patch
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('health_sources_v1',ROOT/'scripts/health_sources_v1.py')
h=module_from_spec(spec);spec.loader.exec_module(h)

class HealthSourcesV1Tests(unittest.TestCase):
    def test_municipality(self):
        self.assertTrue(h.municipal('430460'))
        self.assertTrue(h.municipal('4304606'))
        self.assertFalse(h.municipal('431490'))
        self.assertFalse(h.municipal(None))
    def test_aggregate_residence_dengue(self):
        rows=[{'ID_MN_RESI':'430460','NU_ANO':'2026','CLASSI_FIN':''}]*10001
        rows.append({'ID_MN_RESI':'431490','NU_ANO':'2026','CLASSI_FIN':'10'})
        r=h.aggregate(iter(rows),'dengue',2026,['ID_MN_RESI','NU_ANO','CLASSI_FIN'])
        self.assertEqual(r['value'],10001)
        self.assertEqual(r['scanned'],10002)
    def test_aggregate_sinasc_subtotals(self):
        rows=[{'CODMUNRES':'430460','SEXO':'1','PARTO':'2'}]*150
        rows+= [{'CODMUNRES':'431490','SEXO':'2','PARTO':'1'}]*10000
        r=h.aggregate(iter(rows),'sinasc',2024,['CODMUNRES','SEXO','PARTO'])
        self.assertEqual(r['value'],150)
        self.assertEqual(r['breakdown']['parto_cesarea'],150)
        h.check_consistency('sinasc',r)
    def test_sim_fetal_excluded(self):
        rows=[{'CODMUNRES':'430460','TIPOBITO':'1','CAUSABAS':'P00'}]*40
        rows +=[{'CODMUNRES':'430460','TIPOBITO':'2','CAUSABAS':'I21'}]*220
        rows +=[{'CODMUNRES':'431490','TIPOBITO':'2','CAUSABAS':'I21'}]*10000
        r=h.aggregate(iter(rows),'sim',2024,['CODMUNRES','TIPOBITO','CAUSABAS'])
        self.assertEqual(r['value'],220)
    def test_chikungunya_residence_filter(self):
        rows=[{'ID_MN_RESI':'430460','NU_ANO':'2026'}]*11
        rows += [{'ID_MN_RESI':'431490','NU_ANO':'2026'}]*11000
        result=h.aggregate(iter(rows),'chikungunya',2026,['ID_MN_RESI','NU_ANO'])
        self.assertEqual(result['value'],11)
        h.check_consistency('chikungunya',result)
    def test_zika_national_dataset_without_municipal_notifications(self):
        rows=[{'ID_MN_RESI':'431490','NU_ANO':'2026'}]*11000
        result=h.aggregate(iter(rows),'zika',2026,['ID_MN_RESI','NU_ANO'])
        self.assertEqual(result['value'],0)
        h.check_consistency('zika',result)
    def test_missing_required_field(self):
        with self.assertRaisesRegex(ValueError,'obrigatórias'):h.aggregate(iter([]),'dengue',2026,['ID_MN_RESI'])
    def test_inconsistent_total(self):
        with self.assertRaisesRegex(ValueError,'inconsistente'):
            h.check_consistency('dengue',{'year':2026,'value':500,'scanned':100,'breakdown':{}})
if __name__=='__main__':unittest.main()
