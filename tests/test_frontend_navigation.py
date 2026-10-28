"""Regressões estruturais de navegação e semântica do frontend (não substitui E2E)."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def contents(path):
    return (ROOT/path).read_text(encoding="utf-8")

class FrontendNavigationTests(unittest.TestCase):
    def test_all_thematic_pages_are_routed(self):
        app=contents("src/main.ts")
        for page in ("municipal","overview","map","facilities","health","vital","sus","farmacia-siaps",
                     "aps-history","screening","finance","production","sources"):
            self.assertIn("'"+page+"'",app)
            self.assertIn("'"+page+"':" if page in ("aps-history","farmacia-siaps") else page+":",app)
        self.assertIn("healthPage('vital')",app)
        self.assertIn("susPage('historic')",app)
        self.assertIn("susPage('screening')",app)
        self.assertIn("susPage('finance')",app)
    def test_mobile_drawer_and_grouped_navigation(self):
        app=contents("src/main.ts")
        css=contents("src/style.css")
        self.assertIn('id="mobile-drawer"',app)
        self.assertIn("toggleMobileDrawer(",app)
        self.assertIn("toggleNavGroup(",app)
        self.assertIn("expandedGroups",app)
        self.assertIn("aria-current=",app)
        self.assertIn("data-nav-group",app)
        self.assertIn("nav('desktop')",app)
        self.assertIn("nav('mobile')",app)
        self.assertIn(".health-drawer[hidden]",css)
        self.assertIn(".nav-group-items[hidden]",css)
        self.assertIn(".health-topbar",css)
        self.assertIn("Pular para o conteúdo principal",app)
        self.assertIn("toggleAttribute('inert',open)",app)
        self.assertIn("event.key!=='Tab'",app)
        self.assertIn("drawerLastFocus",app)
        self.assertIn(".skip-link:focus",css)
    def test_async_theme_buttons_remain_navigable(self):
        app=contents("src/main.ts")
        home=contents("src/lib/municipalView.ts")
        self.assertIn("app.onclick=(event)=>",app)
        self.assertIn(".closest<HTMLButtonElement>('[data-page]')",app)
        self.assertIn('data-page="'+chr(39)+'+group.page+',home)
    def test_legacy_empty_series_not_misrepresented(self):
        app=contents("src/main.ts")
        self.assertNotIn('data-series="sih"',app)
        self.assertNotIn('data-series="sia"',app)
        self.assertNotIn('data-series="dengue"',app)
        self.assertIn("page:'production'",app)
    def test_sources_and_production_explain_partial_coverage(self):
        prod=contents("src/lib/productionView.ts")
        sources=contents("src/lib/sourcesView.ts")
        self.assertIn("monthsRequestedPeriods",prod)
        self.assertIn("rejectedMonths",prod)
        self.assertIn("dataZoom",prod)
        self.assertIn("não são pacientes únicos",prod.lower())
        self.assertIn("Pendentes ou parciais",sources)
        self.assertIn("Parcial",sources)
    def test_previne_brasil_is_historically_labeled(self):
        sus=contents("src/lib/susView.ts")
        self.assertIn("Previne Brasil foi substituído em 2024",sus)
        self.assertIn("mode==='historic'?'data/aps.json':'data/sus.json'",sus)
        self.assertIn("quadrimestre de",sus)
if __name__=="__main__":
    unittest.main()
