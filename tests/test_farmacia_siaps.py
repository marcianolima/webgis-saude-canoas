"""Validação das duas novas fontes e da ausência de indicadores inventados."""
import json
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("farmacia_siaps", ROOT / "scripts/farmacia_siaps.py")
module = module_from_spec(spec)
spec.loader.exec_module(module)


class FarmaciaSiapsTests(unittest.TestCase):
    def test_discovery_uses_latest_official_workbook(self):
        html = """
        <a href="./arquivos/qualifarsus/ciclo_03_2026/2026.07.27_Status_Qualifar_SUS_3_ciclo_2026.xlsx">Anterior</a>
        <a href="./arquivos/qualifarsus/ciclo_04_2026/2026.10.13_Status_Qualifar_SUS_4_ciclo_2026.xlsx">Atual</a>
        <a href="https://other-domain.example/arquivo.xlsx">Desconhecido</a>
        """
        date, url = module.latest_qualifar(html)
        self.assertEqual(date, "2026-10-13")
        self.assertEqual(url, "https://bnafar.github.io/statusenvio/arquivos/qualifarsus/ciclo_04_2026/2026.10.13_Status_Qualifar_SUS_4_ciclo_2026.xlsx")

    def test_only_official_links_are_accepted(self):
        with self.assertRaisesRegex(ValueError, "Nenhuma planilha"):
            module.latest_qualifar('<a href="https://evil.example/arquivo.xlsx">x</a>')

    def test_snapshot_distinguishes_source_and_indicator(self):
        data = json.loads((ROOT / "public/data/farmacia_siaps.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schemaVersion"], "1.0")
        self.assertEqual(data["municipality"], "4304606")
        self.assertEqual(set(data["sources"]), {
            "bnafar_envio", "qualifar_monitoramento",
            "siaps_cofinanciamento", "siaps_qualidade", "siaps_praticas"
        })
        self.assertEqual(data["series"], {})
        self.assertEqual(data["sources"]["qualifar_monitoramento"]["status"], "partial")
        for key,source in data["sources"].items():
            self.assertTrue(source["url"].startswith("https://"))
            self.assertNotEqual(source["status"], "ok")
            self.assertNotIn("cpf", str(source).lower())
            self.assertNotIn("cns", str(source).lower())

    def test_frontend_has_mobile_route_and_catalog(self):
        app = (ROOT / "src/main.ts").read_text(encoding="utf-8")
        catalog = (ROOT / "src/lib/sourcesView.ts").read_text(encoding="utf-8")
        panel = (ROOT / "src/lib/farmaciaSiapsView.ts").read_text(encoding="utf-8")
        self.assertIn("farmacia-siaps", app)
        self.assertIn("mountFarmaciaSiaps()", app)
        self.assertIn("farmacia_siaps.json", catalog)
        self.assertIn("Nenhum valor municipal validado", panel)

if __name__ == "__main__":
    unittest.main()
