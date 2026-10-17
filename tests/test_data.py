import json, unittest
from unittest.mock import patch
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('update_data',ROOT/'scripts/update_data.py')
mod=module_from_spec(spec);spec.loader.exec_module(mod)
class DataTests(unittest.TestCase):
    def test_geojson(self):
        geo=json.loads((ROOT/'public/data/establishments.geojson').read_text())
        self.assertEqual(geo['type'],'FeatureCollection')
        for f in geo['features']:
            lon,lat=f['geometry']['coordinates']
            self.assertTrue(-51.40<lon<-50.99 and -30.10<lat<-29.73)
    def test_summary(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        self.assertEqual(s['municipality']['ibge'],'4304606')
        for key in ('population','dengue','sih','sia'):self.assertIn(key,s['series'])
    def test_missing_is_not_zero(self):
        self.assertIsNone(mod.parse_number('...'))
        self.assertIsNone(mod.coord(''))
    def test_municipality(self):
        self.assertTrue(mod.valid_canoas({'codigo_municipio':'430460'}))
        self.assertFalse(mod.valid_canoas({'codigo_municipio':'431490'}))
    def test_classification(self):
        self.assertEqual(mod.normalize_type('HOSPITAL GERAL'),'hospital')
        self.assertEqual(mod.normalize_type('UNIDADE BASICA DE SAUDE'),'ubs')
        self.assertEqual(mod.normalize_type('CENTRO DE SAÚDE'),'ubs')
    def test_pagination_page_index(self):
        payloads=[{'estabelecimentos':[{'id':i} for i in range(20)],'total':24},
                  {'estabelecimentos':[{'id':i} for i in range(20,24)],'total':24}]
        out=[]
        with patch.object(mod,'request_json',side_effect=payloads) as mock:
            n=mod.paginate('/cnes/estabelecimentos',{'codigo_municipio':'430460'},20,10,out.append)
        self.assertEqual(n,24)
        self.assertIn('offset=0',mock.call_args_list[0].args[0])
        self.assertIn('offset=1',mock.call_args_list[1].args[0])
        self.assertEqual(len(out),24)
    def test_unexpected_record_format_not_accepted(self):
        with self.assertRaises(ValueError):mod.unpack({'mensagem':'erro no servidor'})
    def test_coordinates_normalized_and_no_identifiable_patients(self):
        f,stats=mod.build_cnes([{'codigo_municipio':'430460','codigo_cnes':'123',
          'nome_fantasia':'UBS Exemplo','descricao_tipo_unidade':'CENTRO DE SAÚDE',
          'latitude_estabelecimento': '-29.92','longitude_estabelecimento':'-51.18',
          'bairro_estabelecimento':'CENTRO'}])
        self.assertEqual(stats['ubs'],1)
        self.assertEqual(f['features'][0]['geometry']['coordinates'],[-51.18,-29.92])
        self.assertNotIn('cpf',str(f).lower())
if __name__=='__main__':unittest.main()
