"""Architecture-level Aurora visual token conformance (no external dependencies)."""
import ast
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOKENS=ROOT/"design"/"blackmore-aurora.tokens.json"
WALLET=ROOT/"tools"/"entity_wallet_desktop.py"
COMPOSER=ROOT/"tools"/"datachip_workspace_ui.py"
THEME=ROOT/"tools"/"blackmore_aurora_qt.py"
BUILDER=ROOT/"tools"/"build_entity_wallet_desktop.py"

class AuroraContractTests(unittest.TestCase):
    def test_source_compiles_without_importing_the_wallet(self):
        for path in (WALLET,COMPOSER,THEME,BUILDER,ROOT/"tools"/"entity_datachip_composer_preview.py"):
            with self.subTest(file=path.name):
                ast.parse(path.read_text(encoding="utf-8"))
    def test_color_and_spacing_schema(self):
        doc=json.loads(TOKENS.read_text(encoding="utf-8"))
        self.assertEqual(doc["schema"],"blackmore-aurora-design-tokens-v1.0.0")
        self.assertEqual(doc["colors"]["background"],"#08121F")
        self.assertTrue(all(len(color)==7 and color.startswith("#") for color in doc["colors"].values()))
        self.assertGreaterEqual(doc["accessibility"]["min_touch_px"],44)
    def test_theme_integrated_in_all_qt_entrypoints(self):
        source=WALLET.read_text(encoding="utf-8")
        for required in ("AURORA.stylesheet()","AURORA.palette()","self.setStyleSheet(self.styleSheet() + AURORA.stylesheet())"):
            self.assertIn(required,source)
        self.assertIn("AURORA.color",COMPOSER.read_text(encoding="utf-8"))
        self.assertIn('"tools/blackmore_aurora_qt.py"',BUILDER.read_text(encoding="utf-8"))
    def test_no_new_authority_implicit_in_theme(self):
        s=THEME.read_text(encoding="utf-8")
        for forbidden in ("sqlite3.connect(","subprocess.Popen(","eval(","exec(","socket.connect(","issue_grant(","approve_device("):
            self.assertNotIn(forbidden,s)
    def test_text_contrast(self):
        doc=json.loads(TOKENS.read_text(encoding="utf-8"))
        def lum(h):
            v=[int(h[i:i+2],16)/255 for i in (1,3,5)]
            v=[(x/12.92 if x<=0.04045 else ((x+0.055)/1.055)**2.4) for x in v]
            return .2126*v[0]+.7152*v[1]+.0722*v[2]
        c=doc["colors"]
        for foreground,background in [("text","background"),("muted","surface"),("text","surfaceRaised"),("primary","background")]:
            a,b=sorted((lum(c[foreground]),lum(c[background])),reverse=True)
            self.assertGreaterEqual((a+.05)/(b+.05),4.5)

if __name__=="__main__":
    unittest.main()
