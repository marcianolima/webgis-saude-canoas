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
              {'co_ibge':430460,'nu_comp':202609,'co_cnes':'102','qt_exist':2,'qt_sus':1}]
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

    def test_annual_partial_year_does_not_discard_previous_year(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        s['series']['dengue']=[{'year':2026,'value':30}]
        def fake_page(endpoint,params,limit,cap,consume,candidates):
            if params['nu_ano']==2026:raise ConnectionError('ano indisponível')
            for _ in range(4):consume({'id':'notificacao'})
            return 4
        with patch.object(up,'YEARS',[2025,2026]),patch.object(up,'paginate',side_effect=fake_page):
            up.annual(s,'dengue','/arboviroses/dengue',{'id_municip':'430460'},None)
        self.assertEqual(s['series']['dengue'],[{'year':2025,'value':4},{'year':2026,'value':30}])
        self.assertEqual(s['sourceInfo']['dengue']['status'],'partial')

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
                if path=='/assistencia-a-saude/cnes-estabelecimentos':
                    return {'estabelecimentos':records[1000*int(q.get('offset',['0'])[0]):1000*(int(q.get('offset',['0'])[0])+1)],'total':21}
                if path=='/assistencia-a-saude/cnes-leitos':
                    if q.get('nu_comp')==['202609']:
                        return {'leitos':[{'co_ibge':'430460','nu_comp':202609,'co_cnes':'1000','qt_exist':8,'qt_sus':6}, {'co_ibge':'430460','nu_comp':202609,'co_cnes':'1001','qt_exist':1,'qt_sus':1}],'total':2}
                    return {'leitos':[],'total':0}
                raise AssertionError('URL inesperada '+url)
            with patch.object(up,'SUMMARY',summary),patch.object(up,'GEO',geo), \
                 patch.object(up,'request_json',side_effect=fake_api),patch.object(up,'get_logo'), \
                 patch.object(up,'latest_bed_competence',return_value=202609), \
                 patch.object(up,'fetch_cnes_snapshot',return_value=(records,{'national':640000,'municipal':21,'disabled':0,'active':21})), \
                 patch.dict('os.environ',{'SKIP_HEAVY':'true'}):
                up.run()
            result=json.loads(summary.read_text('utf8'))
            points=json.loads(geo.read_text('utf8'))['features']
            self.assertEqual(result['facilities']['total'],21)
            self.assertEqual(result['facilities']['ubs'],21)
            self.assertEqual(result['municipality']['population'],359845)
            self.assertEqual(result['beds']['total'],9)
            self.assertEqual(result['sourceInfo']['cnes']['status'],'ok')
            self.assertEqual(len(points),21)
            self.assertTrue(points[0]['properties']['hasBeds'])
            self.assertTrue(points[1]['properties']['hasBeds'])
            self.assertFalse(points[2]['properties']['hasBeds'])

    def test_repeated_pages_are_rejected(self):
        row={'co_ibge':430460,'co_cnes':'101'}
        with patch.object(up,'request_json',return_value={'dados':[row,dict(row)]}):
            with self.assertRaisesRegex(ValueError,'página 1 repetida'):
                up.paginate('/assistencia-a-saude/cnes-estabelecimentos',{'co_ibge':430460},2,3,lambda r:None)

    def test_municipal_filter_cannot_be_assumed(self):
        self.assertFalse(up.valid_canoas({'co_cnes':'1001','no_fantasia':'UBS EXEMPLO'}))
        self.assertTrue(up.valid_canoas({'co_ibge':430460,'co_cnes':'1001'}))

    def test_cnes_competence_not_tied_to_beds(self):
        from datetime import datetime, timezone
        def api(url,*args,**kwargs):
            from urllib.parse import parse_qs,urlparse
            comp=int(parse_qs(urlparse(url).query)['nu_comp'][0])
            return {'dados':([{'co_ibge':430460,'co_cnes':str(i)} for i in range(21)] if comp==202609 else []), 'total':21 if comp==202609 else 0}
        with patch.dict('os.environ',{'CNES_COMPETENCE':''}), \
             patch.object(up,'datetime') as clock, patch.object(up,'request_json',side_effect=api):
            clock.now.return_value=datetime(2026,10,16,tzinfo=timezone.utc)
            self.assertEqual(up.latest_cnes_competence(),202609)

    def test_cnes_modern_endpoint_one_competence(self):
        records=[{'co_cnes':str(10000+i),'co_ibge':430460,'nu_comp':202607} for i in range(22)]
        with patch.object(up,'request_json',return_value={'estabelecimentos':records,'total':22}) as mock:
            rows,n=up.fetch_cnes(202607)
        self.assertEqual(len(rows),22)
        self.assertEqual(n,22)
        self.assertIn('/assistencia-a-saude/cnes-estabelecimentos',mock.call_args.args[0])
        self.assertIn('nu_comp=202607',mock.call_args.args[0])
        self.assertIn('limit=1000',mock.call_args.args[0])

    def test_single_bed_row_does_not_validate_canoas_total(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        with patch.object(up,'latest_bed_competence',return_value=202607), \
             patch.object(up,'paginate',side_effect=lambda a,b,c,d,consume,e: consume({'co_ibge':430460,'nu_comp':202607,'co_cnes':'101','qt_exist':21,'qt_sus':0}) or 1):
            with self.assertRaisesRegex(ValueError,'somente um estabelecimento'):
                up.update_beds(s)

    def test_official_beds_csv_keeps_only_latest_month_and_unique_cnes(self):
        import csv,io,tempfile,zipfile
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            geo=folder/'establishments.geojson'
            geo.write_text(json.dumps({'type':'FeatureCollection','features':[
                {'type':'Feature','geometry':{'type':'Point','coordinates':[-51.18,-29.92]},
                 'properties':{'cnes':'0031461','hasBeds':None}},
                {'type':'Feature','geometry':{'type':'Point','coordinates':[-51.18,-29.92]},
                 'properties':{'cnes':'0031569','hasBeds':None}}]}),encoding='utf-8')
            output=io.StringIO()
            fields=['COMP','CO_IBGE','CNES','MOTIVO_DESABILITACAO','LEITOS_EXISTENTES','LEITOS_SUS']
            writer=csv.DictWriter(output,fieldnames=fields,delimiter=';')
            writer.writeheader()
            for row in [
              ('202608','430460','0031461','','20','14'),
              ('202608','430460','0031569','','25','10'),
              ('202609','430460','0031461','','30','19'),
              ('202609','430460','0031569','','15','12'),
              ('202609','430460','0031569','','15','12'),
              ('202609','430460','9999999','09','100','100'),
              ('202609','431490','9999998','','300','100')]:
                writer.writerow(dict(zip(fields,row)))
            def download(url,destination,max_bytes):
                with zipfile.ZipFile(destination,'w') as archive:
                    archive.writestr('Leitos_2026.csv',output.getvalue())
            with patch.object(up,'download_cnes_zip',side_effect=download),patch.object(up,'GEO',geo),patch.object(up,'datetime') as clock:
                from datetime import datetime,timezone
                clock.now.return_value=datetime(2026,10,16,tzinfo=timezone.utc)
                up.update_beds_archive(s)
            final=json.loads(geo.read_text())
        self.assertEqual(s['beds'],{'total':45,'sus':31,'asOf':'202609'})
        self.assertEqual(s['sourceInfo']['beds']['records'],2)
        self.assertTrue(all(f['properties']['hasBeds'] for f in final['features']))

    def test_official_beds_csv_rejects_conflicting_duplicates(self):
        import csv,io,tempfile,zipfile
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            output=io.StringIO()
            cols=['COMP','CO_IBGE','CNES','MOTIVO_DESABILITACAO','LEITOS_EXISTENTES','LEITOS_SUS']
            writer=csv.DictWriter(output,fieldnames=cols,delimiter=';')
            writer.writeheader()
            for e in [10,11]:
                writer.writerow({'COMP':'202609','CO_IBGE':'430460','CNES':'0031461',
                                 'MOTIVO_DESABILITACAO':'','LEITOS_EXISTENTES':e,'LEITOS_SUS':5})
            def download(url,destination,max_bytes):
                with zipfile.ZipFile(destination,'w') as archive:
                    archive.writestr('Leitos_2026.csv',output.getvalue())
            with patch.object(up,'download_cnes_zip',side_effect=download):
                with self.assertRaisesRegex(ValueError,'conflitantes'):
                    up.update_beds_archive(s)

    def test_archive_csv_filters_canoas_actives_and_validates_geojson(self):
        import tempfile,zipfile,csv,io
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'snapshot.zip'
            out=io.StringIO()
            writer=csv.DictWriter(out,fieldnames=['CO_MUNICIPIO_GESTOR','CO_CNES','CO_MOTIVO_DESAB','TP_UNIDADE','TP_UNIDADE_DESC','NO_FANTASIA','NO_BAIRRO','NU_LATITUDE','NU_LONGITUDE'],delimiter=';')
            writer.writeheader()
            for i in range(25):
                writer.writerow({'CO_MUNICIPIO_GESTOR':'430460','CO_CNES':f'{i+100:07d}','CO_MOTIVO_DESAB':'','TP_UNIDADE':'02' if i<20 else '05','NO_FANTASIA':f'Unidade {i}','NO_BAIRRO':'CENTRO','NU_LATITUDE':'-29,92','NU_LONGITUDE':'-51,18'})
            writer.writerow({'CO_MUNICIPIO_GESTOR':'430460','CO_CNES':'9999999','CO_MOTIVO_DESAB':'08','NO_FANTASIA':'Desabilitado'})
            writer.writerow({'CO_MUNICIPIO_GESTOR':'431490','CO_CNES':'9999998','CO_MOTIVO_DESAB':'','NO_FANTASIA':'Outro município'})
            with zipfile.ZipFile(dest,'w') as z:z.writestr('CNES_Estabelecimentos.csv',out.getvalue())
            rows,q=up.extract_cnes_csv(dest,min_national=20)
        self.assertEqual(q['municipal'],26)
        self.assertEqual(q['disabled'],1)
        self.assertEqual(q['active'],25)
        self.assertEqual(len(rows),25)
        geo,stats=up.build_cnes(rows)
        self.assertEqual(stats['ubs'],20)
        self.assertEqual(stats['hospitals'],5)
        self.assertEqual(stats['withCoordinates'],25)
        self.assertEqual(geo['features'][0]['geometry']['coordinates'],[-51.18,-29.92])
        self.assertNotIn('9999999',str(geo))

    def test_archive_real_cnes_municipality_column_co_ibge(self):
        """O arquivo nacional de outubro/2026 usa CO_IBGE, não CO_MUNICIPIO_GESTOR."""
        import tempfile,zipfile,csv,io
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cnes.zip'
            out=io.StringIO()
            header=['CO_CNES','CO_IBGE','CO_MOTIVO_DESAB','TP_UNIDADE','NO_FANTASIA','NO_BAIRRO','NU_LATITUDE','NU_LONGITUDE']
            writer=csv.DictWriter(out,fieldnames=header,delimiter=';')
            writer.writeheader()
            for n in range(25):
                writer.writerow({'CO_CNES':str(3000000+n),'CO_IBGE':'430460','CO_MOTIVO_DESAB':'',
                                 'TP_UNIDADE':'02','NO_FANTASIA':f'UBS {n}',
                                 'NO_BAIRRO':'CENTRO','NU_LATITUDE':'-29.92','NU_LONGITUDE':'-51.18'})
            writer.writerow({'CO_CNES':'9999999','CO_IBGE':'431490','CO_MOTIVO_DESAB':'','TP_UNIDADE':'05'})
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('CNES_Estabelecimentos.csv',out.getvalue())
            rows,quality=up.extract_cnes_csv(path,min_municipal=20,min_national=20)
        geo,stats=up.build_cnes(rows)
        self.assertEqual(quality['active'],25)
        self.assertEqual(stats['ubs'],25)
        self.assertEqual(len(geo['features']),25)
        self.assertTrue(all(x['properties']['cnes']!='9999999' for x in geo['features']))

    def test_archive_missing_disable_field_is_rejected(self):
        import tempfile,zipfile
        with tempfile.TemporaryDirectory() as folder:
            z=Path(folder)/'cnes.zip'
            with zipfile.ZipFile(z,'w') as archive:
                archive.writestr('estabelecimentos.csv','CO_MUNICIPIO_GESTOR;CO_CNES\n430460;1234567\n')
            with self.assertRaisesRegex(ValueError,'motivo de desabilitação'):
                up.extract_cnes_csv(z,min_national=1,min_municipal=1)

    def test_archive_incomplete_cannot_update(self):
        import tempfile,zipfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cnes.zip'
            with zipfile.ZipFile(path,'w') as archive:
                archive.writestr('estabelecimentos.csv','CO_MUNICIPIO_GESTOR;CO_CNES;CO_MOTIVO_DESAB\n430460;1234567;\n')
            with self.assertRaisesRegex(ValueError,'incompleto'):
                up.extract_cnes_csv(path,min_national=2000,min_municipal=1)

    def test_source_status_matches_published_indicator(self):
        s=json.loads((ROOT/'public/data/summary.json').read_text())
        if s['sourceInfo']['cnes']['status']=='not_loaded':
            self.assertIsNone(s['facilities']['total'])
        elif s['sourceInfo']['cnes']['status']=='ok':
            self.assertIsInstance(s['facilities']['total'],int)

if __name__=='__main__':unittest.main()
