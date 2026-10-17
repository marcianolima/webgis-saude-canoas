import unittest
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('sus',ROOT/'scripts/sus_sources.py')
m=module_from_spec(spec);spec.loader.exec_module(m)
class SusMGDITests(unittest.TestCase):
 def test_parse_decimal_units(self):
  self.assertEqual(m.decimal_value('1.234,50'),m.Decimal('1234.50'))
  self.assertEqual(m.decimal_value('234.5'),m.Decimal('234.5'))
  self.assertIsNone(m.decimal_value(''))
 def test_monthly_municipal_source_and_unit(self):
  rows=iter([{'co_ibge':str(400000+i),'co_anomes':'202607','vl_indicador_calculado_mun':'1'} for i in range(700)]+[
   {'co_ibge':'430460','co_anomes':'202607','vl_indicador_calculado_mun':'7'},
   {'co_ibge':'430460','co_anomes':'202608','vl_indicador_calculado_mun':'8'},
   {'co_ibge':'431490','co_anomes':'202608','vl_indicador_calculado_mun':'999'}])
  p=m.extract(rows,['co_ibge','co_anomes','vl_indicador_calculado_mun'],'count')
  self.assertEqual(p['lastValue'],8)
  self.assertEqual(p['municipalRecords'],2)
  self.assertEqual(len(p['series']),2)
 def test_reject_uf_only_not_municipal(self):
  with self.assertRaisesRegex(ValueError,'colunas'):m.extract(iter([]),['co_uf','co_anomes'],'count')
 def test_reject_incomplete_national_extract(self):
  rows=iter([{'co_ibge':'430460','co_anomes':'202608','vl_indicador_calculado_mun':'8'}])
  with self.assertRaisesRegex(ValueError,'cobertura'):m.extract(rows,['co_ibge','co_anomes','vl_indicador_calculado_mun'],'count')
 def test_reject_duplicate_discrepancy(self):
  rows=[{'co_ibge':str(400000+i),'co_anomes':'202607','vl_indicador_calculado_mun':'1'} for i in range(700)]
  rows +=[{'co_ibge':'430460','co_anomes':'202608','vl_indicador_calculado_mun':'8'},
          {'co_ibge':'430460','co_anomes':'202608','vl_indicador_calculado_mun':'9'}]
  with self.assertRaisesRegex(ValueError,'divergência'):m.extract(iter(rows),['co_ibge','co_anomes','vl_indicador_calculado_mun'],'count')
 def test_no_patient_identifiers_in_configuration(self):
  for s in m.CONFIG.values():
   self.assertIn(s['kind'],('count','currency','rate'))
   self.assertTrue(s['method'])
if __name__=='__main__':unittest.main()
