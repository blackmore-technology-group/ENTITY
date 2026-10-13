"""Standalone, isolated ENTITY DataChip Composer engineering preview.

This app has no connection to production ENTITY issuer, marketplace, settlement
or identity records. It writes to a separate preview-only local directory.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

from PySide6 import QtWidgets,QtCore
from datachip_workspace_ui import ComposerPage

def default_preview_state():
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Blackmore Technology Group" / "ENTITY-Composer-Preview"

def main():
    parser=argparse.ArgumentParser(description="ENTITY DataChip Composer (non-production preview)")
    parser.add_argument("--state",default=str(default_preview_state()))
    parser.add_argument("--identity",default="entity:local-preview")
    parser.add_argument("--render-preview",help="Save an offscreen screenshot; demo assembly only")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.render_preview or args.self_test:
        os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
    app=QtWidgets.QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setStyleSheet("""
       QWidget { color:#e7edf3; background:#111923;font-family:Segoe UI;font-size:10pt }
       QPushButton {background:#1e2d3e;border:1px solid #486582;border-radius:6px;padding:8px}
       QPushButton:hover {background:#273b51;border-color:#d5ac66}
       QGraphicsView {border:1px solid #354f66}
       QTextBrowser,QListWidget,QLineEdit {background:#0c1420;border:1px solid #334b62;
                                            border-radius:6px;color:#e7edf3;padding:6px}
       QSplitter::handle {background:#1d2a39}
    """)
    window=QtWidgets.QMainWindow()
    window.setWindowTitle("ENTITY DataChip Composer · Engineering Preview")
    page=ComposerPage(Path(args.state),args.identity)
    window.setCentralWidget(page)
    window.resize(1570,910)
    page.example()
    window.show()
    if args.self_test:
        result=page.graph.compile()
        print(json.dumps({"schema":"entity-composer-ui-self-test-v0.1",
                          "valid":result["state"]=="COMPOSITION_ONLY",
                          "nodes":len(page.graph.nodes),"edges":len(page.graph.edges),
                          "execution_allowed":result["security"]["execution_enabled"],
                          "market_trade_created":result["security"]["market_order_created"],
                          "plan_hash":result["sha256"]},sort_keys=True))
        return 0 if not result["security"]["execution_enabled"] else 2
    if args.render_preview:
        target=Path(args.render_preview);target.parent.mkdir(parents=True,exist_ok=True)
        app.processEvents()
        if not window.grab().save(str(target)):
            raise RuntimeError("Qt offscreen screenshot not captured")
        print("COMPOSER_SCREENSHOT",target)
        return 0
    return app.exec()

if __name__=="__main__":raise SystemExit(main())
