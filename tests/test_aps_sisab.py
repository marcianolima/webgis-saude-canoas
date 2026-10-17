import unittest
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location("aps",ROOT/"scripts/aps_sisab.py")
m=module_from_spec(spec);spec.loader.exec_module(m)
class SISABTests(unittest.TestCase):
    def example(self,ibge,kind,view,value,period="2024Q3"):
        return {"ibge":ibge,"ds_quadrimestre":period,"nu_competencia":"202412",
         "co_tipo_indicador":kind,"visao_equipe":view,"vl_perc_quad":str(value),
         "numerador":"270","denominador_utilizador":"1000"}
    def test_quadrimestre_uses_only_general_municipal_percentage(self):
        fields=["ibge","ds_quadrimestre","nu_competencia","co_tipo_indicador",
                "visao_equipe","vl_perc_quad","numerador","denominador_utilizador"]
        rows=[self.example(str(500000+i),"40","geral",27) for i in range(31000)]
        rows +=[self.example("430460",kind,"geral",27) for kind in ("10","20","30","40","50","70")]
        rows +=[self.example("430460",kind,"validas",27) for kind in ("10","20","30","40","50","70")]
        amounts,quality=m.extract(iter(rows),fields,"2024Q3")
        self.assertEqual(len(amounts),6)
        self.assertEqual(amounts["40"],27)
        self.assertEqual(quality["municipalRows"],12)
    def test_duplicate_general_record_is_rejected(self):
        fields=["ibge","ds_quadrimestre","nu_competencia","co_tipo_indicador",
                "visao_equipe","vl_perc_quad","numerador","denominador_utilizador"]
        rows=[self.example(str(400000+i),"40","geral",27) for i in range(450)]
        rows +=[self.example("430460",kind,"geral",27) for kind in ("10","20","30","40","50","70")]
        rows +=[self.example("430460","40","geral",27)]
        with self.assertRaisesRegex(ValueError,"duplicado"):m.extract(iter(rows),fields,"2024Q3")
    def test_percentage_inconsistency_is_rejected(self):
        fields=["ibge","ds_quadrimestre","nu_competencia","co_tipo_indicador",
                "visao_equipe","vl_perc_quad","numerador","denominador_utilizador"]
        rows=[self.example(str(400000+i),"40","geral",27) for i in range(450)]
        rows +=[self.example("430460",kind,"geral",99) for kind in ("10","20","30","40","50","70")]
        with self.assertRaisesRegex(ValueError,"incompatível"):m.extract(iter(rows),fields,"2024Q3")
    def test_only_public_aggregates_in_schema(self):
        self.assertEqual(set(m.DESCRIPTIONS),{"10","20","30","40","50","60","70"})
        self.assertTrue(m.FILES["2024Q3"].startswith("https://"))
if __name__=="__main__":unittest.main()
