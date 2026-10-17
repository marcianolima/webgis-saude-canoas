import unittest
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location("production_sus",ROOT/"scripts/production_sus.py")
p=module_from_spec(spec);spec.loader.exec_module(p)

class ProductionSUSTests(unittest.TestCase):
    def test_sih_municipality_and_minimal_disclosure(self):
        rows=[{'MUNIC_MOV':'430460','CNES':'12345','VAL_TOT':'50.50','MORTE':'0'}]*5
        rows +=[{'MUNIC_MOV':'430460','CNES':'23456','VAL_TOT':'33.00','MORTE':'0'}]*2
        rows +=[{'MUNIC_MOV':'431490','CNES':'99999','VAL_TOT':'999','MORTE':'1'}]*500
        x=p.aggregate_rows(rows,'sih')
        self.assertEqual(x['municipal']['quantity'],7)
        self.assertEqual(x['municipal']['valueBRL'],318.5)
        self.assertEqual(x['byCnes']['0012345']['quantity'],5)
        self.assertNotIn('0023456',x['byCnes'])
        self.assertEqual(x['suppressedUnits'],1)
    def test_sia_approved_quantity_not_unique_patients(self):
        rows=[{'PA_UFMUN':'430460','PA_CODUNI':'12345','PA_QTDAPR':'2','PA_VALAPR':'10.25'}]*5
        rows +=[{'PA_UFMUN':'431490','PA_CODUNI':'43210','PA_QTDAPR':'50','PA_VALAPR':'1000'}]*500
        x=p.aggregate_rows(rows,'sia')
        self.assertEqual(x['municipal']['quantity'],10)
        self.assertEqual(x['municipal']['valueBRL'],51.25)
        self.assertEqual(x['byCnes']['0012345']['quantity'],10)
    def test_do_not_emit_individual_patient_fields(self):
        rows=[{'MUNIC_MOV':'430460','CNES':'12345','VAL_TOT':'10','CPF_AUT':'12345678901','MUNIC_RES':'430460'}]*5
        rows +=[{'MUNIC_MOV':'431490','CNES':'42345','VAL_TOT':'10'}]*500
        x=p.aggregate_rows(rows,'sih')
        self.assertNotIn('CPF_AUT',str(x))
        self.assertNotIn('MUNIC_RES',str(x))
        self.assertNotIn('12345678901',str(x))
    def test_months_validation(self):
        with patch.dict(p.os.environ,{'PRODUCTION_PERIODS':'202501,202502,202501'}):
            self.assertEqual(p.periods(),['202501','202502'])
        with patch.dict(p.os.environ,{'PRODUCTION_PERIODS':'202513'}):
            with self.assertRaises(ValueError):p.periods()
    def test_missing_municipal_rows_is_rejected(self):
        rows=[{'MUNIC_MOV':'431490','CNES':'12345','VAL_TOT':'10'}]*600
        with self.assertRaisesRegex(ValueError,'incompleto'):p.aggregate_rows(rows,'sih')
if __name__=="__main__":unittest.main()
