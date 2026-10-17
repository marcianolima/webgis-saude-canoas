import json
import unittest
from unittest.mock import patch
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('webgis_updater',ROOT/'scripts/update_data.py')
up=module_from_spec(spec);spec.loader.exec_module(up)

class PipelineTests(unittest.TestCase):
    def test_competence_fixed_and_validation(self):
        with patch.dict('os.environ',{'BED_COMPETENCE':'202608'}):
            self.assertEqual(up.latest_bed_competence(),202608)
        with patch.dict('os.environ',{'BED_COMPETENCE':'202613'}):
            with self.assertRaises(ValueError):up.latest_bed_competence()

    def test_recent_competence_discovery(self):
        with patch.dict('os.environ',{'BED_COMPETENCE':''}):
            with patch.object(up,'request_json',side_effect=[{'dados':[],'total':0},{'dados':[{'nu_comp':202609}],'total':1}]):
                # fixa mês corrente de 2026-10 simulando fonte vazia e anterior disponível
                with patch.object(up,'datetime') as fake:
                    from datetime import datetime,timezone
                    fake.now.return_value=datetime(2026,10,16,tzinfo=timezone.utc)
                    self.assertEqual(up.latest_bed_competence(),202609)

    def test_beds_one_competence_and_per_cnes(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        rows=[{'co_ibge':430460,'nu_comp':202609,'co_cnes':'101','qt_exist':3,'qt_sus':2},
              {'co_ibge':430460,'nu_comp':202609,'co_cnes':'101','qt_exist':2,'qt_sus':1}]
        with patch.object(up,'latest_bed_competence',return_value=202609), \
             patch.object(up,'paginate',side_effect=lambda a,b,c,d,consume,e: [consume(r) for r in rows] and len(rows)), \
             patch.object(up,'write_json') as writing,patch.object(up,'GEO',Path('/tmp/webgis-no-geojson-fixture.geojson')):
            up.update_beds(s)
        self.assertEqual(s['beds']['total'],5)
        self.assertEqual(s['beds']['sus'],3)
        self.assertEqual(s['beds']['asOf'],'202609')

    def test_unmapped_bed_codes_do_not_mark_all_points_without_beds(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        with patch.object(up,'latest_bed_competence',return_value=202609), \
             patch.object(up,'paginate',side_effect=lambda a,b,c,d,consume,e: consume({'nu_comp':202609,'qt_exist':10,'qt_sus':9}) or 1):
            with self.assertRaisesRegex(ValueError,'códigos CNES'):
                up.update_beds(s)

    def test_different_competences_rejected(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        with patch.object(up,'latest_bed_competence',return_value=202609), \
             patch.object(up,'paginate',side_effect=lambda a,b,c,d,consume,e: consume({'nu_comp':202608,'qt_exist':10}) or 1):
            with self.assertRaisesRegex(ValueError,'divergente'):
                up.update_beds(s)

    def test_pagination_incomplete_does_not_publish(self):
        with patch.object(up,'request_json',return_value={'dados':[{'id':1},{'id':2}],'total':10}):
            with self.assertRaisesRegex(ValueError,'incompleto'):
                up.paginate('/fake',{},2,1,lambda r:None)

    def test_run_end_to_end_with_simulated_official_responses(self):
        """Teste de contrato: respostas sintéticas nunca são gravadas no projeto real."""
        import tempfile
        from urllib.parse import urlparse,parse_qs
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            summary=out/'summary.json'
            geo=out/'establishments.geojson'
            summary.write_text((ROOT/'public/data/summary.json').read_text(),encoding='utf8')
            geo.write_text((ROOT/'public/data/establishments.geojson').read_text(),encoding='utf8')
            records=[{'codigo_municipio':'430460','codigo_cnes':str(i+1000),
                      'nome_fantasia':'UBS teste '+str(i),'descricao_tipo_unidade':'CENTRO DE SAUDE',
                      'latitude_estabelecimento':-29.92,'longitude_estabelecimento':-51.18}
                     for i in range(21)]
            def fake_api(url,*args,**kwargs):
                if url==up.SIDRA:
                    return [{'D3C':'Ano','V':'Valor'},{'D3C':'2025','V':'351000'},{'D3C':'2026','V':'359845'}]
                path=urlparse(url).path
                q=parse_qs(urlparse(url).query)
                if path=='/cnes/estabelecimentos':
                    return {'estabelecimentos':records[20*int(q.get('offset',['0'])[0]):20*(int(q.get('offset',['0'])[0])+1)],'total':21}
                if path=='/assistencia-a-saude/cnes-leitos':
                    if q.get('nu_comp')==['202609']:
                        return {'leitos':[{'co_ibge':'430460','nu_comp':202609,'co_cnes':'1000','qt_exist':8,'qt_sus':6}],'total':1}
                    return {'leitos':[],'total':0}
                raise AssertionError('URL inesperada '+url)
            with patch.object(up,'SUMMARY',summary),patch.object(up,'GEO',geo), \
                 patch.object(up,'request_json',side_effect=fake_api),patch.object(up,'get_logo'), \
                 patch.object(up,'latest_bed_competence',return_value=202609), \
                 patch.dict('os.environ',{'SKIP_HEAVY':'true'}):
                up.run()
            result=json.loads(summary.read_text('utf8'))
            points=json.loads(geo.read_text('utf8'))['features']
            self.assertEqual(result['facilities']['total'],21)
            self.assertEqual(result['facilities']['ubs'],21)
            self.assertEqual(result['municipality']['population'],359845)
            self.assertEqual(result['beds']['total'],8)
            self.assertEqual(result['sourceInfo']['cnes']['status'],'ok')
            self.assertEqual(len(points),21)
            self.assertTrue(points[0]['properties']['hasBeds'])
            self.assertFalse(points[1]['properties']['hasBeds'])

    def test_source_status_matches_published_indicator(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        if s['sourceInfo']['cnes']['status']=='not_loaded':
            self.assertIsNone(s['facilities']['total'])
        elif s['sourceInfo']['cnes']['status']=='ok':
            self.assertIsInstance(s['facilities']['total'],int)

if __name__=='__main__':unittest.main()
