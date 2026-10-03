from __future__ import annotations
from pathlib import Path
import argparse, html, importlib.util, json, os, sqlite3, sys, uuid

from PySide6 import QtCore, QtGui, QtWidgets

APP_NAME = "ENTITY Wallet"
VERSION = "3.4.3"

ROOT_BG = "#090B0E"
SIDEBAR_BG = "#0D1014"
PANEL_BG = "#11151A"
PANEL_2 = "#151A20"
BORDER = "#242B34"
TEXT = "#F3F0E8"
MUTED = "#8F99A7"
ACCENT = "#C9A96A"
ACCENT_DARK = "#7D6642"
GREEN = "#43D39E"
RED = "#FF6B78"
YELLOW = "#E3BC64"

def startup_stylesheet() -> str:
    return f"""
    * {{
        font-family: "Segoe UI";
        font-size: 10pt;
        color: {TEXT};
    }}
    QDialog, QMessageBox {{ background: {ROOT_BG}; }}
    QLabel {{ background: transparent; }}
    QLabel[class="brand"] {{ font-size: 26pt; font-weight: 800; letter-spacing: 2px; color: {TEXT}; }}
    QLabel[class="eyebrow"] {{ color: {ACCENT}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
    QLabel[class="dialogTitle"] {{ font-size: 18pt; font-weight: 700; }}
    QLabel[class="muted"] {{ color: {MUTED}; }}
    QLabel[class="chip"] {{
        background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 10px; color: {MUTED};
    }}
    QLabel[class="tickerPreview"] {{
        background: {SIDEBAR_BG}; border: 1px solid {ACCENT_DARK}; border-radius: 6px;
        padding: 10px; color: {ACCENT}; font-family: Consolas; font-weight: 700;
    }}
    QFrame[class="panel"] {{ background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
    QPushButton {{
        background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px;
        padding: 8px 13px; font-weight: 600;
    }}
    QPushButton:hover {{ border-color: {ACCENT_DARK}; background: #1A2027; }}
    QPushButton[primary="true"] {{
        background: {ACCENT}; color: #0C0E11; border-color: {ACCENT}; font-weight: 800;
    }}
    QLineEdit, QComboBox {{
        background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 5px; padding: 8px;
        selection-background-color: {ACCENT_DARK};
    }}
    QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
    QCheckBox {{ spacing: 8px; }}
    """


def repo_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]

def load_module(name: str, relative: str):
    path = repo_root() / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

CLI = load_module("entity_wallet_v343_cli", "tools/entity_v3_4_cli.py")
WALLET = load_module("entity_wallet_model", "src/42_ENTITY_Wallet/canonical_wallet.py")
INGEST = load_module("entity_wallet_ingest", "src/42_ENTITY_Wallet/asset_ingest.py")
EXCHANGE = load_module("entity_wallet_exchange", "src/31_Profiles/exchange_protocol.py")
MARKET = load_module("entity_wallet_market", "src/45_ENTITY_Market/canonical_market_registry.py")
INTEL = load_module("entity_wallet_intelligence", "src/45_ENTITY_Market/economic_intelligence.py")
ONBOARDING = load_module("entity_wallet_onboarding", "src/42_ENTITY_Wallet/onboarding.py")

def default_state() -> Path:
    env = os.environ.get("ENTITY_STATE_DIR")
    if env:
        return Path(env).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Blackmore Technology Group" / "ENTITY"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Blackmore Technology Group" / "ENTITY"
    return Path.home() / ".local" / "share" / "blackmore-technology-group" / "entity"

def shorten(value: str | None, left: int = 10, right: int = 6) -> str:
    v = str(value or "")
    if len(v) <= left + right + 3:
        return v
    return v[:left] + "…" + v[-right:]

def manifests(state: Path) -> list[dict]:
    out = []
    root = state / "identity" / "manifests"
    if not root.is_dir():
        return out
    for p in sorted(root.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({"entity_id": d.get("entity_id"), "display_name": d.get("display_name") or d.get("entity_id")})
        except Exception:
            pass
    return [x for x in out if x["entity_id"]]

class Backend:
    def __init__(self, state: Path, entity_id: str):
        self.state = state
        self.entity_id = entity_id
        identity, fabric, profiles, origin, passports, packages, sdk, origin_status = CLI.runtime(state)
        self.identity = identity
        self.fabric = fabric
        self.profiles = profiles
        self.origin = origin
        self.passports = passports
        self.packages = packages
        self.sdk = sdk
        self.origin_status = origin_status
        self.rights = self.sdk.ingestion.rights
        self.identity_manifest = self.identity.load_manifest(entity_id)
        self.wallet = WALLET.EntityEconomicWallet(state)
        self.exchange = EXCHANGE.ExchangeProtocol(state, self.identity, self.fabric)
        self.market_registry = MARKET.EntityEconomicMarketRegistry(
            state, self.identity, self.fabric, self.exchange, self.rights, self.passports
        )
        self.intelligence = INTEL.EntityEconomicIntelligence(
            state, self.market_registry, self.fabric, self.passports
        )
        self.ingestor = INGEST.WalletAssetIngestor(state, CLI)
        self.wallet_record = self.wallet.ensure_wallet(
            entity_id, self.identity_manifest.get("display_name", "ENTITY") + " Wallet"
        )

    def snapshot(self):
        return self.wallet.snapshot(self.wallet_record["wallet_id"])

    def domains(self):
        return ["general"] + self.packages.list_packages()

    def asset_kinds(self, domain):
        return self.ingestor.asset_kinds(domain)

    def namespace_info(self) -> dict:
        return self.market_registry.suggest_namespace(self.entity_id)

    def namespace(self) -> str | None:
        return self.namespace_info().get("namespace")

    def asset_record(self, object_id: str) -> dict:
        return self.fabric.get_object(object_id)

    def asset_disclosure(self, object_id: str) -> dict | None:
        return self.market_registry.latest_asset_disclosure(object_id)

    def publish_asset_disclosure(self, object_id: str, options: dict) -> dict:
        return self.market_registry.publish_asset_disclosure(
            self.entity_id, object_id,
            description=options["description"],
            purpose=options.get("purpose", ""),
            capabilities=options.get("capabilities", []),
            contents=options.get("contents", []),
            intended_uses=options.get("intended_uses", []),
            limitations=options.get("limitations", []),
            dependencies=options.get("dependencies", []),
            validation_notes=options.get("validation_notes", []),
            release_notes=options.get("release_notes", ""),
            source_refs=options.get("source_refs", []),
        )

    def latest_global_passport(self, object_id: str) -> dict:
        dbp = self.state / "entity_v3_4_global_passports.sqlite"
        db = sqlite3.connect(dbp)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                """SELECT passport_id FROM global_passports WHERE object_id=?
                   ORDER BY created_at_ms DESC, passport_id DESC LIMIT 1""",
                (str(object_id),),
            ).fetchone()
        finally:
            db.close()
        if not row:
            raise KeyError("asset has no Global Passport")
        return self.passports.get(row["passport_id"])

    def instruments(self) -> list[dict]:
        if not self.market_registry.path.exists():
            return []
        db = sqlite3.connect(self.market_registry.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                """SELECT instrument_id FROM instrument_packages
                   WHERE issuer_entity_id=? AND status='ACTIVE'
                   ORDER BY created_at_ms, instrument_id""",
                (self.entity_id,),
            ).fetchall()
        finally:
            db.close()
        return [self.market_registry.instrument(r["instrument_id"]) for r in rows]

    def instrument_map_by_asset(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        if not self.market_registry.path.exists():
            return out
        db = sqlite3.connect(self.market_registry.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                """SELECT instrument_id,underlying_dco_id FROM instrument_packages
                   WHERE issuer_entity_id=? AND status='ACTIVE'
                   ORDER BY created_at_ms""", (self.entity_id,)
            ).fetchall()
        finally:
            db.close()
        for r in rows:
            out.setdefault(r["underlying_dco_id"], []).append(self.market_registry.instrument(r["instrument_id"]))
        return out

    def venues(self) -> list[dict]:
        if not self.exchange.path.exists():
            return []
        db = sqlite3.connect(self.exchange.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                "SELECT venue_id,name,jurisdiction,status FROM venues WHERE status='ACTIVE' ORDER BY name"
            ).fetchall()
        finally:
            db.close()
        return [dict(r) for r in rows]

    def market(self) -> list[dict]:
        rows = self.market_registry.active_market()
        if not rows:
            return []
        db = sqlite3.connect(self.exchange.path)
        db.row_factory = sqlite3.Row
        try:
            out = []
            for row in rows:
                e = db.execute(
                    "SELECT settlement_currency FROM instruments WHERE instrument_id=? AND status='ACTIVE'",
                    (row["instrument_id"],),
                ).fetchone()
                if not e:
                    continue
                d = dict(row)
                d["settlement_currency"] = e["settlement_currency"]
                d["market"] = self.wallet._market(db, d["instrument_id"])
                out.append(d)
            return out
        finally:
            db.close()

    def economic_metrics(self) -> list[dict]:
        seen = set()
        out = []
        for row in self.market_registry.active_market():
            iid = row["instrument_id"]
            if iid in seen:
                continue
            seen.add(iid)
            out.append(self.intelligence.instrument_metrics(iid))
        return out

    def economy_rollup(self, group_by="asset_class") -> dict:
        return self.intelligence.economy_rollup(group_by=group_by)

    def ingest(self, path, options):
        return self.ingestor.ingest_file(
            self.entity_id, path,
            title=options["title"], package=options["domain"],
            asset_kind=options.get("asset_kind") or None,
            jurisdiction=options.get("jurisdiction", ""),
            authority_basis=options["authority"],
            commodity_class=options["class"], measurement_unit=options["unit"],
            version=options.get("version") or "1.0",
            previous_object_id=options.get("parent_object_id") or None,
        )

    def create_instrument(self, object_id: str, options: dict) -> dict:
        gp = self.latest_global_passport(object_id)
        return self.market_registry.create_instrument(
            self.entity_id, object_id,
            instrument_name=options["name"], display_symbol=options["symbol"],
            instrument_class=options["instrument_class"], rights_class=options["rights_class"],
            rights={"actions": options["actions"]}, supply=options["supply"],
            rights_passport_id=gp["rights_passport_id"], global_passport_id=gp["passport_id"],
            settlement_currency=options["currency"], jurisdiction=options["jurisdiction"],
            series=options["series"], fungibility=options["fungibility"],
            divisibility=options["divisibility"], transferable=options["transferable"],
            duration_ms=options.get("duration_ms"),
            transfer_rules={"wallet_defined": True},
            economic_terms={"market_value_created_by_issuance": False},
            royalty_terms={"automatic_protocol_royalty_bps": 0},
            buyer_receives=options["buyer_receives"],
            buyer_does_not_receive=options["buyer_does_not_receive"],
            evidence_refs=gp.get("evidence_refs") or [],
            namespace=options.get("namespace") or None,
        )

    def create_listing(self, instrument_id: str, options: dict) -> dict:
        return self.market_registry.create_listing(
            self.entity_id, instrument_id, options["venue_id"],
            market_id=options["market_id"], quote_unit=options["quote_unit"],
            trade_mode=options["trade_mode"], settlement_method=options["settlement_method"],
            minimum_quantity=options["minimum_quantity"],
            quantity_precision=options["quantity_precision"], price_precision=options["price_precision"],
            pricing_method=options["pricing_method"], listing_series=options["listing_series"],
            tick_size=options["tick_size"],
        )

    def submit_order(self, row: dict, side: str, quantity: int, limit_price: int):
        venue = row.get("venue_id")
        if not venue:
            raise ValueError("This instrument has no active market listing.")
        order = self.exchange.submit_order(
            venue, row["instrument_id"], self.entity_id, side, quantity, limit_price,
            nonce="wallet-" + uuid.uuid4().hex, tif="GTC"
        )
        trades = self.exchange.match_order_book(venue, row["instrument_id"])
        return {"order": order, "trades": trades}

class Ui:
    @staticmethod
    def label(text="", cls=""):
        w = QtWidgets.QLabel(text)
        if cls:
            w.setProperty("class", cls)
        return w

    @staticmethod
    def button(text, primary=False):
        b = QtWidgets.QPushButton(text)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setProperty("primary", primary)
        return b

    @staticmethod
    def table(headers):
        t = QtWidgets.QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        t.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        t.setShowGrid(False)
        t.setAlternatingRowColors(False)
        t.setWordWrap(False)
        t.setTextElideMode(QtCore.Qt.ElideRight)
        t.verticalHeader().setDefaultSectionSize(38)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        t.setSortingEnabled(False)
        return t

    @staticmethod
    def fill_table(table, rows):
        table.setRowCount(0)
        for row in rows:
            i = table.rowCount()
            table.insertRow(i)
            for j, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem("" if value is None else str(value))
                item.setData(QtCore.Qt.UserRole, value)
                table.setItem(i, j, item)
        for i in range(table.rowCount()):
            table.setRowHeight(i, 38)

class MetricCard(QtWidgets.QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setProperty("class", "metricCard")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 15, 18, 15)
        lay.setSpacing(5)
        title_label = Ui.label(title.upper(), "eyebrow")
        self.value = Ui.label("—", "metric")
        self.note = Ui.label("", "muted")
        lay.addWidget(title_label)
        lay.addWidget(self.value)
        lay.addWidget(self.note)

class EmptyState(QtWidgets.QFrame):
    def __init__(self, title, body):
        super().__init__()
        self.setProperty("class", "empty")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.addWidget(Ui.label(title, "emptyTitle"))
        body_label = Ui.label(body, "muted")
        body_label.setWordWrap(True)
        lay.addWidget(body_label)

class EntitySetupDialog(QtWidgets.QDialog):
    def __init__(self, parent, onboarding):
        super().__init__(parent)
        self.onboarding = onboarding
        self.profile = None
        self.setWindowTitle("Create your ENTITY identity")
        self.resize(760, 690)
        self.setMinimumSize(690, 610)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        layout.addWidget(Ui.label("WELCOME TO ENTITY", "eyebrow"))
        layout.addWidget(Ui.label("Create your sovereign identity", "dialogTitle"))
        intro = Ui.label(
            "This creates your own cryptographic ENTITY identity and public .entity name. "
            "Your device receives a separate device identity; device information never becomes your human or company identity.",
            "muted"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        principal_box = QtWidgets.QFrame()
        principal_box.setProperty("class", "panel")
        pf = QtWidgets.QFormLayout(principal_box)
        pf.setContentsMargins(18, 18, 18, 18)
        pf.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.principal_type = QtWidgets.QComboBox()
        self.principal_type.addItems(["person", "business", "organization", "project", "community", "family"])
        self.principal_name = QtWidgets.QLineEdit()
        self.principal_name.setPlaceholderText("Jane Smith")
        self.principal_public = QtWidgets.QLineEdit()
        self.principal_public.setPlaceholderText("jane.smith")
        self.principal_preview = Ui.label("jane.smith.entity", "tickerPreview")
        pf.addRow("Identity type", self.principal_type)
        pf.addRow("Public display name", self.principal_name)
        pf.addRow("Public ENTITY name", self.principal_public)
        pf.addRow("Address preview", self.principal_preview)
        layout.addWidget(principal_box)

        self.add_org = QtWidgets.QCheckBox("Create an operating organization/business under this identity")
        self.add_org.setChecked(False)
        layout.addWidget(self.add_org)

        self.org_box = QtWidgets.QFrame()
        self.org_box.setProperty("class", "panel")
        of = QtWidgets.QFormLayout(self.org_box)
        of.setContentsMargins(18, 18, 18, 18)
        of.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.org_type = QtWidgets.QComboBox()
        self.org_type.addItems(["business", "organization", "project"])
        self.org_name = QtWidgets.QLineEdit()
        self.org_name.setPlaceholderText("Acme Corporation")
        self.org_public = QtWidgets.QLineEdit()
        self.org_public.setPlaceholderText("acme")
        self.org_preview = Ui.label("acme.entity", "tickerPreview")
        self.operate_as_org = QtWidgets.QCheckBox("Open the wallet as this operating entity")
        self.operate_as_org.setChecked(True)
        of.addRow("Entity type", self.org_type)
        of.addRow("Organization name", self.org_name)
        of.addRow("Public ENTITY name", self.org_public)
        of.addRow("Address preview", self.org_preview)
        of.addRow("", self.operate_as_org)
        layout.addWidget(self.org_box)
        self.org_box.setVisible(False)

        self.lineage_preview = Ui.label("LINEAGE  —", "chip")
        self.lineage_preview.setWordWrap(True)
        layout.addWidget(self.lineage_preview)

        note = Ui.label(
            "Public names are human-readable aliases. The immutable ENTITY ID and signatures remain authoritative. "
            "A local name conflict does not let one user impersonate another.",
            "muted"
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

        buttons = QtWidgets.QHBoxLayout()
        cancel = Ui.button("Exit")
        create = Ui.button("Create ENTITY and wallet", True)
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self.create_identity)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(create)
        layout.addLayout(buttons)

        self.add_org.toggled.connect(self.org_box.setVisible)
        self.add_org.toggled.connect(self.update_preview)
        self.principal_public.textChanged.connect(self.update_preview)
        self.org_public.textChanged.connect(self.update_preview)
        self.update_preview()

    @staticmethod
    def _address(text):
        raw = str(text or "").strip().lower()
        if raw.endswith(".entity"):
            raw = raw[:-7]
        return (raw + ".entity") if raw else "—"

    def update_preview(self):
        p = self._address(self.principal_public.text())
        self.principal_preview.setText(p)
        if self.add_org.isChecked():
            o = self._address(self.org_public.text())
            self.org_preview.setText(o)
            self.lineage_preview.setText(f"LINEAGE  {p}  →  {o}")
        else:
            self.lineage_preview.setText(f"LINEAGE  {p}")

    def create_identity(self):
        if not self.principal_name.text().strip() or not self.principal_public.text().strip():
            QtWidgets.QMessageBox.warning(self, "ENTITY setup", "Display name and public ENTITY name are required.")
            return
        if self.add_org.isChecked() and (not self.org_name.text().strip() or not self.org_public.text().strip()):
            QtWidgets.QMessageBox.warning(
                self, "ENTITY setup",
                "Organization name and public ENTITY name are required when an operating organization is enabled."
            )
            return
        try:
            self.profile = self.onboarding.create_profile(
                principal_display_name=self.principal_name.text().strip(),
                principal_public_name=self.principal_public.text().strip(),
                principal_entity_type=self.principal_type.currentText(),
                organization_display_name=self.org_name.text().strip() if self.add_org.isChecked() else None,
                organization_public_name=self.org_public.text().strip() if self.add_org.isChecked() else None,
                organization_entity_type=self.org_type.currentText(),
                operate_as_organization=self.operate_as_org.isChecked(),
            )
            auth = self.onboarding.authenticate(self.profile)
            if not auth.get("authenticated"):
                raise RuntimeError("new identity was created but device-bound authentication failed")
            self.accept()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "ENTITY setup failed", str(exc))


class EntityLoginDialog(QtWidgets.QDialog):
    def __init__(self, parent, onboarding):
        super().__init__(parent)
        self.onboarding = onboarding
        self.profile = None
        self.create_new = False
        self.profiles = onboarding.list_profiles()
        self.setWindowTitle("Unlock ENTITY")
        self.resize(620, 390)
        self.setMinimumWidth(580)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        layout.addWidget(Ui.label("ENTITY", "brand"))
        layout.addWidget(Ui.label("SOVEREIGN WALLET ACCESS", "eyebrow"))
        layout.addWidget(Ui.label("Unlock your local ENTITY identity", "dialogTitle"))
        note = Ui.label(
            "ENTITY uses possession of your local signing identity plus the bound device identity. "
            "The operating-system account name is not treated as your ENTITY identity.",
            "muted"
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.selector = QtWidgets.QComboBox()
        for profile in self.profiles:
            active = onboarding.identity.load_manifest(profile["active_entity_id"])
            self.selector.addItem(
                f"{profile['display_path']}   ·   {active['display_name']}",
                profile["profile_id"]
            )
        layout.addWidget(self.selector)

        self.detail = Ui.label("", "chip")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        self.selector.currentIndexChanged.connect(self.update_detail)
        self.update_detail()
        layout.addStretch()

        buttons = QtWidgets.QHBoxLayout()
        create = Ui.button("Create another identity")
        unlock = Ui.button("Unlock wallet", True)
        create.clicked.connect(self.choose_create)
        unlock.clicked.connect(self.unlock)
        buttons.addWidget(create)
        buttons.addStretch()
        buttons.addWidget(unlock)
        layout.addLayout(buttons)

    def update_detail(self):
        idx = self.selector.currentIndex()
        if idx < 0 or idx >= len(self.profiles):
            self.detail.setText("No local wallet profile.")
            return
        p = self.profiles[idx]
        self.detail.setText(
            f"LINEAGE  {p['display_path']}\n"
            f"LOGIN  device-bound signing key\n"
            f"ACTIVE ENTITY  {shorten(p['active_entity_id'], 14, 10)}"
        )

    def choose_create(self):
        self.create_new = True
        self.accept()

    def unlock(self):
        idx = self.selector.currentIndex()
        if idx < 0 or idx >= len(self.profiles):
            return
        profile = self.profiles[idx]
        auth = self.onboarding.authenticate(profile)
        if not auth.get("authenticated"):
            QtWidgets.QMessageBox.critical(
                self, "ENTITY unlock failed",
                "The local signing identity or bound device could not authenticate this wallet.\n\n"
                + str(auth.get("reason") or "authentication failed")
                + ("\n\nRecovery or device re-binding is required." if auth.get("recovery_or_rebind_required") else "")
            )
            return
        self.onboarding.set_active(profile["profile_id"])
        self.profile = profile
        self.accept()


class AssetDisclosureDialog(QtWidgets.QDialog):
    def __init__(self, parent, asset: dict, current: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Asset Information")
        self.resize(820, 820)
        self.setMinimumSize(720, 680)
        self.result_data = None
        current = current or {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.addWidget(Ui.label("SIGNED ASSET DISCLOSURE", "dialogTitle"))
        title = Ui.label(asset.get("title") or asset.get("object_id"), "tickerHero")
        title.setWordWrap(True)
        layout.addWidget(title)
        note = Ui.label(
            "This is the buyer-facing description of the underlying DCO. It is signed and versioned. "
            "It describes the asset; it does not expand the Rights Passport or manufacture market value.",
            "muted"
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        host = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(host)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        def area(value="", height=86):
            w = QtWidgets.QPlainTextEdit(str(value or ""))
            w.setMinimumHeight(height)
            return w

        def lines(values):
            return "\n".join(str(x) for x in (values or []))

        self.description = area(current.get("description"), 130)
        self.purpose = area(current.get("purpose"), 80)
        self.capabilities = area(lines(current.get("capabilities")), 90)
        self.contents = area(lines(current.get("contents")), 90)
        self.intended = area(lines(current.get("intended_uses")), 90)
        self.limitations = area(lines(current.get("limitations")), 90)
        self.dependencies = area(lines(current.get("dependencies")), 80)
        self.validation = area(lines(current.get("validation_notes")), 90)
        self.release_notes = area(current.get("release_notes"), 80)
        self.source_refs = area(lines(current.get("source_refs")), 70)

        for label, widget in [
            ("Detailed asset description", self.description),
            ("Purpose / problem addressed", self.purpose),
            ("Key capabilities\n(one per line)", self.capabilities),
            ("Included content / components\n(one per line)", self.contents),
            ("Intended uses\n(one per line)", self.intended),
            ("Known limitations / exclusions\n(one per line)", self.limitations),
            ("Dependencies / prerequisites\n(one per line)", self.dependencies),
            ("Validation / qualification notes\n(one per line)", self.validation),
            ("Version / release notes", self.release_notes),
            ("Supporting source references\n(one per line)", self.source_refs),
        ]:
            form.addRow(label, widget)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)

        boundary = Ui.label(
            "ENTITY records this as an issuer statement. Evidence and passport references remain independently inspectable.",
            "muted"
        )
        boundary.setWordWrap(True)
        layout.addWidget(boundary)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        cancel = Ui.button("Cancel")
        publish = Ui.button("Sign and publish asset information", True)
        cancel.clicked.connect(self.reject)
        publish.clicked.connect(self.accept_data)
        buttons.addWidget(cancel)
        buttons.addWidget(publish)
        layout.addLayout(buttons)

    @staticmethod
    def _items(editor):
        return [x.strip() for x in editor.toPlainText().splitlines() if x.strip()]

    def accept_data(self):
        description = self.description.toPlainText().strip()
        if len(description) < 20:
            QtWidgets.QMessageBox.warning(
                self, "Asset description",
                "Provide a meaningful buyer-facing asset description before publishing."
            )
            return
        self.result_data = {
            "description": description,
            "purpose": self.purpose.toPlainText().strip(),
            "capabilities": self._items(self.capabilities),
            "contents": self._items(self.contents),
            "intended_uses": self._items(self.intended),
            "limitations": self._items(self.limitations),
            "dependencies": self._items(self.dependencies),
            "validation_notes": self._items(self.validation),
            "release_notes": self.release_notes.toPlainText().strip(),
            "source_refs": self._items(self.source_refs),
        }
        self.accept()


class ListingInformationDialog(QtWidgets.QDialog):
    def __init__(self, parent, market_identifier: str, markdown: str):
        super().__init__(parent)
        self.setWindowTitle(f"Listing Information Sheet · {market_identifier}")
        self.resize(1060, 820)
        self.setMinimumSize(820, 620)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(Ui.label("LISTING INFORMATION SHEET", "dialogTitle"))
        head.addStretch()
        head.addWidget(Ui.label(market_identifier, "tickerHero"))
        layout.addLayout(head)
        browser = QtWidgets.QTextBrowser()
        browser.setProperty("class", "detail")
        browser.setOpenExternalLinks(False)
        browser.setMarkdown(markdown)
        layout.addWidget(browser, 1)
        foot = QtWidgets.QHBoxLayout()
        foot.addWidget(Ui.label(
            "Buyer-facing disclosure snapshot · canonical passports and instrument records remain authoritative.",
            "muted"
        ))
        foot.addStretch()
        close = Ui.button("Close", True)
        close.clicked.connect(self.accept)
        foot.addWidget(close)
        layout.addLayout(foot)


class InstrumentDialog(QtWidgets.QDialog):
    def __init__(self, parent, asset, namespace):
        super().__init__(parent)
        self.setWindowTitle("Issue Economic Instrument")
        self.setMinimumWidth(650)
        self.result_data = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(Ui.label("ISSUE ECONOMIC INSTRUMENT", "dialogTitle"))
        layout.addWidget(Ui.label(
            "Create a canonical rights instrument against this DCO. This does not list it or establish market value.",
            "muted"))
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        title = asset.get("title") or "Asset"
        self.name = QtWidgets.QLineEdit(f"{title} Commercial Rights")
        self.namespace = QtWidgets.QLineEdit(namespace or "")
        self.symbol = QtWidgets.QLineEdit((title.upper().replace(" ", "")[:10] + "-COM")[:24])
        self.iclass = QtWidgets.QComboBox()
        self.iclass.addItems(["SPOT_LICENSE","SUBSCRIPTION","COMPUTE_TO_DATA","PROCUREMENT","CONTRIBUTION","SECONDARY_LICENSE"])
        self.rclass = QtWidgets.QLineEdit("COMMERCIAL")
        self.actions = QtWidgets.QLineEdit("COMMERCIALIZE")
        self.supply = QtWidgets.QSpinBox(); self.supply.setRange(1, 2_000_000_000); self.supply.setValue(1)
        self.currency = QtWidgets.QLineEdit("CAD")
        self.jurisdiction = QtWidgets.QLineEdit("CA")
        self.series = QtWidgets.QSpinBox(); self.series.setRange(1, 999999); self.series.setValue(1)
        self.fungibility = QtWidgets.QComboBox(); self.fungibility.addItems(["FUNGIBLE","SERIES-FUNGIBLE","NON-FUNGIBLE"])
        self.divisibility = QtWidgets.QSpinBox(); self.divisibility.setRange(0, 9)
        self.transferable = QtWidgets.QCheckBox("Secondary transfer permitted")
        self.receives = QtWidgets.QPlainTextEdit("Defined commercial-use right")
        self.excludes = QtWidgets.QPlainTextEdit("Ownership of the underlying DCO\nCopyright ownership\nRights not stated in the Rights Passport")
        for label, widget in [
            ("Instrument name", self.name), ("Issuer namespace", self.namespace),
            ("Display ticker / symbol", self.symbol), ("EEP class", self.iclass),
            ("Rights class", self.rclass), ("Actions", self.actions),
            ("Supply", self.supply), ("Settlement currency", self.currency),
            ("Jurisdiction", self.jurisdiction), ("Series", self.series),
            ("Fungibility", self.fungibility), ("Divisibility", self.divisibility),
            ("Transferability", self.transferable), ("Buyer receives", self.receives),
            ("Buyer does NOT receive", self.excludes),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        self.preview = Ui.label("", "tickerPreview")
        layout.addWidget(self.preview)
        self.namespace.textChanged.connect(self._preview)
        self.symbol.textChanged.connect(self._preview)
        self._preview()
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        cancel = Ui.button("Cancel"); create = Ui.button("Issue instrument", True)
        cancel.clicked.connect(self.reject); create.clicked.connect(self.accept_data)
        buttons.addWidget(cancel); buttons.addWidget(create)
        layout.addLayout(buttons)

    def _preview(self):
        ns = (self.namespace.text().strip() or "NAMESPACE").upper()
        sym = (self.symbol.text().strip() or "SYMBOL").upper()
        self.preview.setText(f"MARKET IDENTIFIER PREVIEW   {ns}:{sym}")

    def accept_data(self):
        actions = [x.strip().upper() for x in self.actions.text().split(",") if x.strip()]
        if not actions or not self.symbol.text().strip() or not self.name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Instrument", "Name, ticker and at least one rights action are required.")
            return
        self.result_data = {
            "name": self.name.text().strip(), "namespace": self.namespace.text().strip(),
            "symbol": self.symbol.text().strip(), "instrument_class": self.iclass.currentText(),
            "rights_class": self.rclass.text().strip(), "actions": actions, "supply": self.supply.value(),
            "currency": self.currency.text().strip(), "jurisdiction": self.jurisdiction.text().strip(),
            "series": self.series.value(), "fungibility": self.fungibility.currentText(),
            "divisibility": self.divisibility.value(), "transferable": self.transferable.isChecked(),
            "duration_ms": None,
            "buyer_receives": [x.strip() for x in self.receives.toPlainText().splitlines() if x.strip()],
            "buyer_does_not_receive": [x.strip() for x in self.excludes.toPlainText().splitlines() if x.strip()],
        }
        self.accept()

class ListingDialog(QtWidgets.QDialog):
    def __init__(self, parent, backend: Backend, instrument: dict):
        super().__init__(parent)
        self.setWindowTitle("Create Market Listing")
        self.setMinimumWidth(600)
        self.result_data = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(Ui.label("CREATE MARKET LISTING", "dialogTitle"))
        layout.addWidget(Ui.label(instrument["market_identifier"], "tickerHero"))
        layout.addWidget(Ui.label(
            "A listing is separate from the canonical instrument. It binds a buyer-facing Listing Information Sheet and machine manifest.",
            "muted"))
        form = QtWidgets.QFormLayout()
        self.venue = QtWidgets.QComboBox()
        self.venues = backend.venues()
        for v in self.venues:
            self.venue.addItem(f"{v['name']}  ·  {v['jurisdiction']}", v["venue_id"])
        self.market_id = QtWidgets.QLineEdit("ENTITY-MKT")
        self.quote = QtWidgets.QLineEdit("CAD")
        self.mode = QtWidgets.QComboBox(); self.mode.addItems(["ORDER_BOOK","CALL_AUCTION","RFQ"])
        self.settlement = QtWidgets.QComboBox(); self.settlement.addItems(["PAYMENT_VERSUS_RIGHT"])
        self.min_qty = QtWidgets.QSpinBox(); self.min_qty.setRange(1, 2_000_000_000); self.min_qty.setValue(1)
        self.qprec = QtWidgets.QSpinBox(); self.qprec.setRange(0, 9)
        self.pprec = QtWidgets.QSpinBox(); self.pprec.setRange(0, 9)
        self.pricing = QtWidgets.QComboBox(); self.pricing.addItems(["ORDER_BOOK","CALL_AUCTION","RFQ"])
        self.series = QtWidgets.QSpinBox(); self.series.setRange(1, 999999); self.series.setValue(1)
        self.tick = QtWidgets.QSpinBox(); self.tick.setRange(1, 2_000_000_000); self.tick.setValue(1)
        for label, widget in [
            ("Venue", self.venue), ("Market ID", self.market_id), ("Quote unit", self.quote),
            ("Trade mode", self.mode), ("Settlement", self.settlement), ("Minimum quantity", self.min_qty),
            ("Quantity precision", self.qprec), ("Price precision", self.pprec),
            ("Pricing method", self.pricing), ("Listing series", self.series), ("Tick size", self.tick),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QtWidgets.QHBoxLayout(); buttons.addStretch()
        cancel = Ui.button("Cancel"); create = Ui.button("Create listing", True)
        cancel.clicked.connect(self.reject); create.clicked.connect(self.accept_data)
        buttons.addWidget(cancel); buttons.addWidget(create); layout.addLayout(buttons)

    def accept_data(self):
        if self.venue.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Listing", "No active ENTITY-compatible venue is available.")
            return
        self.result_data = {
            "venue_id": self.venue.currentData(), "market_id": self.market_id.text().strip(),
            "quote_unit": self.quote.text().strip(), "trade_mode": self.mode.currentText(),
            "settlement_method": self.settlement.currentText(), "minimum_quantity": self.min_qty.value(),
            "quantity_precision": self.qprec.value(), "price_precision": self.pprec.value(),
            "pricing_method": self.pricing.currentText(), "listing_series": self.series.value(),
            "tick_size": self.tick.value(),
        }
        self.accept()

class OrderDialog(QtWidgets.QDialog):
    def __init__(self, parent, row, side):
        super().__init__(parent)
        self.setWindowTitle(f"{side.title()} {row.get('market_identifier') or row['instrument_id']}")
        self.result_data = None
        m = row["market"]
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(Ui.label(side, "eyebrow"))
        layout.addWidget(Ui.label(row.get("market_identifier") or row["instrument_id"], "tickerHero"))
        form = QtWidgets.QFormLayout()
        self.qty = QtWidgets.QSpinBox(); self.qty.setRange(1, 2_000_000_000); self.qty.setValue(1)
        self.price = QtWidgets.QSpinBox(); self.price.setRange(0, 2_000_000_000)
        default = m.get("ask") if side == "BUY" else m.get("bid")
        if default is not None: self.price.setValue(int(default))
        form.addRow("Quantity", self.qty); form.addRow(f"Limit price ({row['settlement_currency']})", self.price)
        layout.addLayout(form)
        layout.addWidget(Ui.label(f"Bid {m.get('bid') or '—'}    Ask {m.get('ask') or '—'}    Last {m.get('last') or '—'}", "muted"))
        buttons = QtWidgets.QHBoxLayout(); buttons.addStretch()
        cancel = Ui.button("Cancel"); submit = Ui.button(f"Submit {side}", True)
        cancel.clicked.connect(self.reject); submit.clicked.connect(self.accept_data)
        buttons.addWidget(cancel); buttons.addWidget(submit); layout.addLayout(buttons)

    def accept_data(self):
        self.result_data = (self.qty.value(), self.price.value())
        self.accept()

class AssetIngestDialog(QtWidgets.QDialog):
    def __init__(self, parent, path: Path, backend: Backend):
        super().__init__(parent)
        self.setWindowTitle("Ingest Digital Asset")
        self.setMinimumWidth(650)
        self.result_data = None
        self.backend = backend
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(Ui.label("INGEST DIGITAL ASSET", "dialogTitle"))
        layout.addWidget(Ui.label(str(path), "monoMuted"))
        form = QtWidgets.QFormLayout()
        self.title = QtWidgets.QLineEdit(path.name)
        self.domain = QtWidgets.QComboBox(); self.domain.addItems(backend.domains())
        self.kind = QtWidgets.QComboBox()
        self.juris = QtWidgets.QLineEdit("")
        self.cclass = QtWidgets.QLineEdit("DIGITAL_ASSET")
        self.unit = QtWidgets.QLineEdit("ASSET")
        self.authority = QtWidgets.QLineEdit(f"CONTROLLER_ENTITY:{backend.entity_id}")
        self.version = QtWidgets.QLineEdit("1.0")
        self.parent_id = QtWidgets.QLineEdit("")
        self.attest = QtWidgets.QCheckBox("I have authority to register this asset and attest its provenance.")
        for label, widget in [
            ("Asset title", self.title), ("Domain profile", self.domain), ("Asset kind", self.kind),
            ("Jurisdiction", self.juris), ("Commodity class", self.cclass), ("Measurement unit", self.unit),
            ("Authority basis", self.authority), ("Passport version", self.version),
            ("Parent object ID", self.parent_id), ("Authority attestation", self.attest),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        layout.addWidget(Ui.label(
            "Creates the governed DCO + evidence + Rights Passport + Global Passport + BTDU binding. No ticker, instrument, listing or price is created automatically.",
            "muted"))
        self.domain.currentTextChanged.connect(self._domain)
        self._domain(self.domain.currentText())
        buttons = QtWidgets.QHBoxLayout(); buttons.addStretch()
        cancel = Ui.button("Cancel"); ingest = Ui.button("Ingest asset", True)
        cancel.clicked.connect(self.reject); ingest.clicked.connect(self.accept_data)
        buttons.addWidget(cancel); buttons.addWidget(ingest); layout.addLayout(buttons)

    def _domain(self, domain):
        self.kind.clear()
        kinds = self.backend.asset_kinds(domain)
        self.kind.addItems(kinds)
        self.cclass.setText("DIGITAL_ASSET" if domain == "general" else domain.upper().replace("-", "_") + "_ASSET")

    def accept_data(self):
        if not self.attest.isChecked():
            QtWidgets.QMessageBox.warning(self, "Authority", "Authority attestation is required.")
            return
        if self.domain.currentText() != "general" and not self.juris.text().strip():
            QtWidgets.QMessageBox.warning(self, "Jurisdiction", "Domain package ingest requires an explicit jurisdiction.")
            return
        self.result_data = {
            "title": self.title.text().strip(), "domain": self.domain.currentText(),
            "asset_kind": self.kind.currentText(), "jurisdiction": self.juris.text().strip(),
            "class": self.cclass.text().strip(), "unit": self.unit.text().strip(),
            "authority": self.authority.text().strip(), "version": self.version.text().strip(),
            "parent_object_id": self.parent_id.text().strip(),
        }
        self.accept()

class WalletWindow(QtWidgets.QMainWindow):
    NAV = [
        ("overview", "OVERVIEW"), ("assets", "DIGITAL ASSETS"), ("instruments", "INSTRUMENTS"),
        ("market", "ENTITY MARKET"), ("intelligence", "ECONOMIC INTELLIGENCE"), ("orders", "ORDERS"),
    ]

    def __init__(self, state: Path, entity_id: str, wallet_profile: dict | None = None):
        super().__init__()
        self.state = state
        self.entity_id = entity_id
        self.wallet_profile = wallet_profile
        self.backend = Backend(state, entity_id)
        self.snapshot_data = {}
        self.assets_rows: list[dict] = []
        self.instruments_rows: list[dict] = []
        self.market_rows: list[dict] = []
        self.metrics_rows: list[dict] = []
        self.setWindowTitle(f"{APP_NAME} · Data Economy Terminal")
        self.resize(1560, 940)
        self.setMinimumSize(1180, 720)
        self._build()
        self._apply_style()
        self.refresh()
        self.navigate("overview")

    def _build(self):
        root = QtWidgets.QWidget(); self.setCentralWidget(root)
        outer = QtWidgets.QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        side = QtWidgets.QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(238)
        sl = QtWidgets.QVBoxLayout(side); sl.setContentsMargins(18, 22, 18, 20); sl.setSpacing(7)
        sl.addWidget(Ui.label("ENTITY", "brand"))
        sl.addWidget(Ui.label("DATA ECONOMY TERMINAL", "brandSub"))
        sl.addSpacing(24)
        self.nav_buttons = {}
        for key, label in self.NAV:
            b = QtWidgets.QPushButton(label); b.setCheckable(True); b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setProperty("nav", True); b.clicked.connect(lambda checked=False, k=key: self.navigate(k))
            self.nav_buttons[key] = b; sl.addWidget(b)
        sl.addStretch()
        sl.addWidget(Ui.label("SOVEREIGN LOCAL STATE", "eyebrow"))
        sl.addWidget(Ui.label("Protocol tax 0\nNo cryptocurrency required\nExternal settlement evidence required", "sidebarFoot"))
        outer.addWidget(side)

        body = QtWidgets.QWidget(); bl = QtWidgets.QVBoxLayout(body)
        bl.setContentsMargins(26, 18, 26, 22); bl.setSpacing(14)
        header = QtWidgets.QHBoxLayout()
        titlebox = QtWidgets.QVBoxLayout()
        self.page_title = Ui.label("", "pageTitle")
        self.page_sub = Ui.label("", "pageSub")
        titlebox.addWidget(self.page_title); titlebox.addWidget(self.page_sub)
        header.addLayout(titlebox); header.addStretch()
        self.lineage_chip = Ui.label("", "chip")
        self.namespace_chip = Ui.label("", "chip")
        self.market_chip = Ui.label("", "chip")
        self.identity_chip = Ui.label("", "identityChip")
        header.addWidget(self.lineage_chip); header.addWidget(self.namespace_chip); header.addWidget(self.market_chip); header.addWidget(self.identity_chip)
        bl.addLayout(header)

        self.tape = Ui.label("", "tape")
        bl.addWidget(self.tape)

        self.stack = QtWidgets.QStackedWidget()
        bl.addWidget(self.stack, 1)
        outer.addWidget(body, 1)

        self.pages = {}
        self.pages["overview"] = self._overview_page()
        self.pages["assets"] = self._assets_page()
        self.pages["instruments"] = self._instruments_page()
        self.pages["market"] = self._market_page()
        self.pages["intelligence"] = self._intelligence_page()
        self.pages["orders"] = self._orders_page()
        for key, _ in self.NAV:
            self.stack.addWidget(self.pages[key])

    def _overview_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(14)
        cards = QtWidgets.QHBoxLayout(); cards.setSpacing(12)
        self.cards = {}
        for key, title in [
            ("assets", "Digital Assets"), ("instruments", "Issued Instruments"), ("listings", "Active Listings"),
            ("positions", "Market Positions"), ("settled", "30D Settled Volume"),
        ]:
            c = MetricCard(title); self.cards[key] = c; cards.addWidget(c)
        lay.addLayout(cards)
        row = QtWidgets.QHBoxLayout(); row.setSpacing(14)
        market_box = QtWidgets.QFrame(); market_box.setProperty("class", "panel")
        ml = QtWidgets.QVBoxLayout(market_box); ml.setContentsMargins(18, 16, 18, 18)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(Ui.label("MARKET PULSE", "sectionTitle")); head.addStretch()
        b = Ui.button("Open market"); b.clicked.connect(lambda: self.navigate("market")); head.addWidget(b)
        ml.addLayout(head)
        self.overview_market_stack=QtWidgets.QStackedWidget()
        self.overview_market = Ui.table(["TICKER", "RIGHTS", "LAST", "24H VOL", "30D VOL", "BUYERS", "INTEGRITY"])
        self.overview_market_empty=EmptyState(
            "NO ACTIVE LISTINGS",
            "The universal market is clean. Issue an economic instrument from a controlled DCO, then create a listing to establish a ticker-addressable market."
        )
        self.overview_market_stack.addWidget(self.overview_market)
        self.overview_market_stack.addWidget(self.overview_market_empty)
        ml.addWidget(self.overview_market_stack, 1)
        row.addWidget(market_box, 2)

        asset_box = QtWidgets.QFrame(); asset_box.setProperty("class", "panel")
        al = QtWidgets.QVBoxLayout(asset_box); al.setContentsMargins(18, 16, 18, 18)
        ah = QtWidgets.QHBoxLayout(); ah.addWidget(Ui.label("ASSET PORTFOLIO", "sectionTitle")); ah.addStretch()
        ab = Ui.button("+ Ingest asset", True); ab.clicked.connect(self.ingest_asset); ah.addWidget(ab); al.addLayout(ah)
        self.overview_assets = Ui.table(["TICKER", "ASSET", "CLASS", "DOMAIN", "ASSET INFO"])
        self.overview_assets.setColumnWidth(0,150)
        self.overview_assets.setColumnWidth(1,310)
        self.overview_assets.setColumnWidth(2,170)
        self.overview_assets.horizontalHeader().setSectionResizeMode(1,QtWidgets.QHeaderView.Stretch)
        al.addWidget(self.overview_assets, 1)
        row.addWidget(asset_box, 3)
        lay.addLayout(row, 1)

        boundary = QtWidgets.QFrame(); boundary.setProperty("class", "notice")
        nl = QtWidgets.QHBoxLayout(boundary); nl.setContentsMargins(16, 12, 16, 12)
        nl.addWidget(Ui.label("VALUE BOUNDARY", "eyebrow"))
        n = Ui.label("ENTITY measures market demand for bounded rights. A rights price is not intrinsic DCO value and is not accounting fair value.", "muted")
        n.setWordWrap(True); nl.addWidget(n, 1)
        lay.addWidget(boundary)
        return p

    def _assets_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        actions = QtWidgets.QHBoxLayout()
        ingest = Ui.button("+ Ingest digital asset", True); ingest.clicked.connect(self.ingest_asset)
        disclose = Ui.button("Asset information"); disclose.clicked.connect(self.edit_asset_information)
        issue = Ui.button("Issue economic instrument"); issue.clicked.connect(self.issue_selected_asset)
        lineage = Ui.button("Inspect lineage"); lineage.clicked.connect(self.show_asset_lineage)
        actions.addWidget(ingest); actions.addWidget(disclose); actions.addWidget(issue); actions.addWidget(lineage); actions.addStretch()
        lay.addLayout(actions)
        split = QtWidgets.QSplitter()
        self.assets_table = Ui.table(["TICKER(S)", "ASSET", "CLASS", "TYPE", "DOMAIN", "ASSET INFO", "PASSPORT", "BTDU", "DCO ID"])
        self.assets_table.itemSelectionChanged.connect(self.update_asset_detail)
        split.addWidget(self.assets_table)
        self.asset_detail = QtWidgets.QTextBrowser(); self.asset_detail.setProperty("class", "detail")
        split.addWidget(self.asset_detail); split.setSizes([1050, 410])
        lay.addWidget(split, 1)
        return p

    def _instruments_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        actions = QtWidgets.QHBoxLayout()
        list_btn = Ui.button("+ Create listing", True); list_btn.clicked.connect(self.list_selected_instrument)
        actions.addWidget(list_btn); actions.addStretch()
        lay.addLayout(actions)
        split = QtWidgets.QSplitter()
        self.instruments_table = Ui.table(["TICKER", "INSTRUMENT", "RIGHTS", "CLASS", "SUPPLY", "DCO", "STATUS"])
        self.instruments_table.itemSelectionChanged.connect(self.update_instrument_detail)
        split.addWidget(self.instruments_table)
        self.instrument_detail = QtWidgets.QTextBrowser(); self.instrument_detail.setProperty("class", "detail")
        split.addWidget(self.instrument_detail); split.setSizes([1050, 410])
        lay.addWidget(split, 1)
        return p

    def _market_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        actions = QtWidgets.QHBoxLayout()
        buy = Ui.button("BUY", True); buy.clicked.connect(lambda: self.trade_selected("BUY"))
        sell = Ui.button("SELL"); sell.clicked.connect(lambda: self.trade_selected("SELL"))
        info = Ui.button("Listing information"); info.clicked.connect(self.show_listing_info)
        export = Ui.button("Export instrument package"); export.clicked.connect(self.export_listing)
        actions.addWidget(buy); actions.addWidget(sell); actions.addWidget(info); actions.addWidget(export); actions.addStretch()
        lay.addLayout(actions)
        split = QtWidgets.QSplitter()
        self.market_table = Ui.table(["TICKER", "INSTRUMENT", "ISSUER", "RIGHTS", "LAST", "BID", "ASK", "24H VOL", "30D VOL", "BUYERS", "HOLDERS", "INTEGRITY"])
        self.market_table.itemSelectionChanged.connect(self.update_market_detail)
        split.addWidget(self.market_table)
        self.market_detail = QtWidgets.QTextBrowser(); self.market_detail.setProperty("class", "detail")
        split.addWidget(self.market_detail); split.setSizes([1110, 350])
        lay.addWidget(split, 1)
        return p

    def _intelligence_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        notice = EmptyState("DATA VALUE DISCOVERY", "Settled market activity reveals which bounded rights attract demand. Orders and quotes do not count as realized demand; self-trades and reciprocal flows are flagged.")
        lay.addWidget(notice)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        top = QtWidgets.QFrame(); top.setProperty("class", "panel"); tl = QtWidgets.QVBoxLayout(top)
        tl.addWidget(Ui.label("INSTRUMENT RIGHTS DEMAND", "sectionTitle"))
        self.intel_table = Ui.table(["TICKER", "RIGHTS", "ASSET CLASS", "LAST", "24H UNITS", "30D UNITS", "30D TRADES", "BUYERS", "HOLDERS", "LOW", "HIGH", "VERIFIED", "INTEGRITY"])
        tl.addWidget(self.intel_table)
        splitter.addWidget(top)
        bottom = QtWidgets.QFrame(); bottom.setProperty("class", "panel"); bl = QtWidgets.QVBoxLayout(bottom)
        bl.addWidget(Ui.label("ASSET-CLASS ROLLUP · 30 DAYS", "sectionTitle"))
        self.rollup_table = Ui.table(["ASSET CLASS", "INSTRUMENTS", "TRADES", "UNITS", "NOTIONAL BY CURRENCY"])
        bl.addWidget(self.rollup_table); splitter.addWidget(bottom)
        splitter.setSizes([430, 280]); lay.addWidget(splitter, 1)
        return p

    def _orders_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        box = QtWidgets.QFrame(); box.setProperty("class", "panel"); bl = QtWidgets.QVBoxLayout(box)
        bl.addWidget(Ui.label("OPEN / RECENT ORDERS", "sectionTitle"))
        self.orders_table = Ui.table(["TICKER / INSTRUMENT", "SIDE", "REMAINING", "LIMIT", "STATUS"])
        bl.addWidget(self.orders_table); lay.addWidget(box, 1)
        return p

    def navigate(self, key):
        idx = list(self.pages).index(key)
        self.stack.setCurrentIndex(idx)
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)
        titles = {
            "overview": ("Portfolio Overview", "Your sovereign asset state and market activity."),
            "assets": ("Digital Assets", "DCO holdings, lineage, passports and optional economic issuance."),
            "instruments": ("Economic Instruments", "Ticker-addressable bounded rights issued against controlled DCOs."),
            "market": ("ENTITY Market", "Universal multi-issuer listings and wallet-to-wallet rights trading."),
            "intelligence": ("Economic Intelligence", "Settlement-aware price discovery and rights-demand analytics."),
            "orders": ("Orders", "Open and recent exchange instructions."),
        }
        self.page_title.setText(titles[key][0]); self.page_sub.setText(titles[key][1])

    def refresh(self):
        self.snapshot_data = self.backend.snapshot()
        self.assets_rows = self.snapshot_data.get("assets", [])
        self.instruments_rows = self.backend.instruments()
        self.market_rows = self.backend.market()
        self.metrics_rows = self.backend.economic_metrics()
        rollup = self.backend.economy_rollup("asset_class")
        amap = self.backend.instrument_map_by_asset()
        ns_info=self.backend.namespace_info()
        ns=ns_info.get("namespace") or "UNASSIGNED"
        venues = self.backend.venues()

        name = self.backend.identity_manifest.get("display_name") or self.entity_id
        public_aliases = [str(x) for x in (self.backend.identity_manifest.get("aliases") or []) if str(x).endswith(".entity")]
        active_public = public_aliases[0] if public_aliases else shorten(self.entity_id, 12, 8)
        self.identity_chip.setText(f"{name}\n{active_public}")
        if self.wallet_profile:
            self.lineage_chip.setText("LINEAGE  " + self.wallet_profile.get("display_path", active_public))
            self.lineage_chip.setToolTip(
                "User/organization lineage for this wallet. This is separate from ENTITY protocol origin."
            )
        else:
            self.lineage_chip.setText("LINEAGE  " + active_public)
        self.namespace_chip.setText(f"NAMESPACE  {ns}" + ("" if ns_info.get("registered") else "  ·  RESERVED ON ISSUE"))
        self.market_chip.setText(f"ENTITY-MKT  ·  {len(venues)} VENUE{'S' if len(venues)!=1 else ''}")
        if self.market_rows:
            tape = "    ".join(
                f"{r['market_identifier']}  {r['market'].get('last') if r['market'].get('last') is not None else '—'}"
                for r in self.market_rows[:8]
            )
            self.tape.setText("MARKET TAPE    " + tape)
        else:
            self.tape.setText("MARKET TAPE    NO ACTIVE LISTINGS · instruments remain private until explicitly listed")

        self.cards["assets"].value.setText(str(len(self.assets_rows)))
        self.cards["assets"].note.setText("Current DCO holdings")
        self.cards["instruments"].value.setText(str(len(self.instruments_rows)))
        self.cards["instruments"].note.setText("Canonical economic instruments")
        self.cards["listings"].value.setText(str(len(self.market_rows)))
        self.cards["listings"].note.setText("Visible market listings")
        self.cards["positions"].value.setText(str(len(self.snapshot_data.get("positions", []))))
        self.cards["positions"].note.setText("Active rights positions")
        by_currency = {}
        for m in self.metrics_rows:
            cur = m.get("settlement_currency") or "?"
            by_currency[cur] = by_currency.get(cur, 0) + int(m["window_30d"]["notional_amount_units"])
        self.cards["settled"].value.setText(" · ".join(f"{k} {v:,}" for k,v in by_currency.items()) or "—")
        self.cards["settled"].note.setText("Settled instrument-right notional")

        asset_table_rows = []
        overview_assets = []
        for a in self.assets_rows:
            instruments = amap.get(a["object_id"], [])
            tickers = ", ".join(i["market_identifier"] for i in instruments) or "NO TICKER"
            lin = a.get("lineage", {})
            domain = (lin.get("protocol_lineage", {}) or {}).get("primary_domain_profile") or "—"
            gp = lin.get("global_passport") or {}
            btdu = (lin.get("capability_bindings", {}).get("BTDU", {}) or {}).get("bound", False)
            disclosure = self.backend.asset_disclosure(a["object_id"])
            disclosure_status = f"SIGNED V{disclosure['version']}" if disclosure else "REQUIRED TO LIST"
            asset_table_rows.append([
                tickers, a.get("title"), a.get("commodity_class"), a.get("object_type"), domain,
                disclosure_status, gp.get("version") or "—", "BOUND" if btdu else "—", a.get("object_id")
            ])
            overview_assets.append([tickers, a.get("title"), a.get("commodity_class"), domain, disclosure_status])
        Ui.fill_table(self.assets_table, asset_table_rows)
        Ui.fill_table(self.overview_assets, overview_assets[:8])

        inst_rows = []
        for x in self.instruments_rows:
            inst_rows.append([
                x["market_identifier"], x["instrument_name"], x["rights_class"], x["instrument_class"],
                x["supply"], shorten(x["underlying_dco_id"], 12, 8), x["status"]
            ])
        Ui.fill_table(self.instruments_table, inst_rows)

        metrics_by_iid = {m["instrument_id"]: m for m in self.metrics_rows}
        market_rows = []
        overview_market = []
        for r in self.market_rows:
            mkt = r["market"]; im = metrics_by_iid.get(r["instrument_id"], {})
            w24 = im.get("window_24h", {}); w30 = im.get("window_30d", {})
            flags = ", ".join((im.get("market_integrity") or {}).get("flags") or []) or "CLEAN"
            vals = [
                r["market_identifier"], r["instrument_name"], shorten(r["issuer_entity_id"], 12, 8),
                r["rights_class"], mkt.get("last") or "—", mkt.get("bid") or "—", mkt.get("ask") or "—",
                w24.get("volume_units", 0), w30.get("volume_units", 0), w30.get("unique_buyers", 0),
                im.get("active_holder_count", 0), flags
            ]
            market_rows.append(vals)
            overview_market.append([r["market_identifier"], r["rights_class"], mkt.get("last") or "—",
                                    w24.get("volume_units", 0), w30.get("volume_units", 0),
                                    w30.get("unique_buyers", 0), flags])
        Ui.fill_table(self.market_table, market_rows)
        Ui.fill_table(self.overview_market, overview_market[:8])
        self.overview_market_stack.setCurrentIndex(0 if overview_market else 1)

        intel_rows = []
        for m in self.metrics_rows:
            w = m["window_30d"]
            flags = ", ".join(m["market_integrity"]["flags"]) or "CLEAN"
            intel_rows.append([
                m["market_identifier"], m["rights_class"], m["asset_class"], m["last_settled_price"] or "—",
                m["window_24h"]["volume_units"], w["volume_units"], w["trade_count"], w["unique_buyers"],
                m["active_holder_count"], w["low_price"] or "—", w["high_price"] or "—",
                w["externally_verified_trade_count"], flags
            ])
        Ui.fill_table(self.intel_table, intel_rows)
        Ui.fill_table(self.rollup_table, [
            [r["group"], r["instrument_count"], r["settled_trades_30d"], r["volume_units_30d"],
             ", ".join(f"{k} {v:,}" for k,v in r["notional_30d_by_currency"].items()) or "—"]
            for r in rollup.get("rows", [])
        ])

        Ui.fill_table(self.orders_table, [
            [o["instrument_id"], o["side"], o["remaining"], o["limit_price"], o["status"]]
            for o in self.snapshot_data.get("orders", [])
        ])
        if self.assets_rows:
            self.assets_table.selectRow(0)
        if self.instruments_rows:
            self.instruments_table.selectRow(0)
        if self.market_rows:
            self.market_table.selectRow(0)

    def selected_asset(self):
        row = self.assets_table.currentRow()
        return self.assets_rows[row] if 0 <= row < len(self.assets_rows) else None

    def selected_instrument(self):
        row = self.instruments_table.currentRow()
        return self.instruments_rows[row] if 0 <= row < len(self.instruments_rows) else None

    def selected_market(self):
        row = self.market_table.currentRow()
        return self.market_rows[row] if 0 <= row < len(self.market_rows) else None

    def update_asset_detail(self):
        a = self.selected_asset()
        if not a:
            self.asset_detail.setHtml("<h2>No asset selected</h2>"); return
        lin = a.get("lineage", {}); p = lin.get("protocol_lineage", {}) or {}
        al = lin.get("asset_lineage", {}) or {}; cap = lin.get("capability_bindings", {}) or {}
        instruments = self.backend.instrument_map_by_asset().get(a["object_id"], [])
        tickers = "<br>".join(html.escape(i["market_identifier"]) for i in instruments) or "<span>NO ECONOMIC INSTRUMENT ISSUED</span>"
        parents = "<br>".join(
            f"{html.escape(str(x.get('relation') or ''))} · {html.escape(str(x.get('title') or shorten(x.get('parent_object_id'))))}"
            for x in al.get("parents", [])
        ) or "None recorded"
        obj = self.backend.asset_record(a["object_id"])
        descriptor = obj.get("descriptor") or {}
        metadata = descriptor.get("metadata") or {}
        disclosure = self.backend.asset_disclosure(a["object_id"])
        try:
            gp = self.backend.latest_global_passport(a["object_id"])
        except Exception:
            gp = {}
        description = (disclosure or {}).get("description") or (
            f"{obj.get('title')} is registered as an ENTITY Digital Commodity Object of type "
            f"{obj.get('object_type')} in the {descriptor.get('commodity_class')} commodity class. "
            "No signed issuer-authored Asset Disclosure has been published yet."
        )
        def ul(items):
            vals=[html.escape(str(x)) for x in (items or []) if str(x).strip()]
            return "<ul>"+"".join("<li>"+x+"</li>" for x in vals)+"</ul>" if vals else "<span>None stated</span>"
        metadata_rows = "".join(
            f"<tr><td>{html.escape(str(k).replace('_',' ').title())}</td><td>{html.escape(str(v))}</td></tr>"
            for k,v in sorted(metadata.items())
        ) or "<tr><td colspan='2'>None recorded</td></tr>"
        disclosure_version=(disclosure or {}).get("version")
        profile_refs=(gp.get("profile_stack") or {}).get("profile_refs") or []
        self.asset_detail.setHtml(f"""
        <div class='eyebrow'>DIGITAL COMMODITY OBJECT</div>
        <h1>{html.escape(str(a.get('title') or ''))}</h1>
        <div class='ticker'>{tickers}</div>
        <hr>
        <h3>Asset description</h3>
        <p>{html.escape(str(description))}</p>
        <p><b>Disclosure:</b> {"Signed version "+str(disclosure_version) if disclosure else "Not yet published"}</p>

        <h3>Canonical identity</h3>
        <b>Canonical lineage</b><br>{html.escape(str(p.get('display_path') or 'Unresolved'))}<br><br>
        <b>Controller</b><br>{html.escape(str(al.get('controller_name') or a.get('controller_entity_id')))}<br><br>
        <b>DCO ID</b><br><code>{html.escape(str(a.get('object_id')))}</code><br><br>
        <b>Commodity class</b><br>{html.escape(str(a.get('commodity_class')))}<br><br>
        <b>Object type</b><br>{html.escape(str(a.get('object_type')))}<br><br>
        <b>Content SHA-256</b><br><code>{html.escape(str(obj.get('content_sha256') or '—'))}</code><br><br>

        <h3>Issuer disclosure</h3>
        <b>Purpose</b><br>{html.escape(str((disclosure or {}).get('purpose') or 'None stated'))}<br><br>
        <b>Capabilities</b>{ul((disclosure or {}).get('capabilities'))}
        <b>Included content / components</b>{ul((disclosure or {}).get('contents'))}
        <b>Intended uses</b>{ul((disclosure or {}).get('intended_uses'))}
        <b>Limitations</b>{ul((disclosure or {}).get('limitations'))}
        <b>Validation notes</b>{ul((disclosure or {}).get('validation_notes'))}

        <h3>Technical metadata</h3>
        <table cellspacing='0' cellpadding='4'>{metadata_rows}</table><br>
        <b>Profile stack</b>{ul(profile_refs)}
        <b>Composed profiles</b><br>{html.escape(', '.join(p.get('composed_domain_profiles') or []) or 'Primary domain only')}<br><br>
        <b>BTDU</b><br>{"Bound" if (cap.get('BTDU') or {}).get('bound') else "Not bound"}<br><br>
        <b>Provenance parents</b><br>{parents}<br><br>
        <small>Asset registration does not create a ticker, instrument, listing or market value. A signed Asset Disclosure is required before market listing.</small>
        """)


    def update_instrument_detail(self):
        x = self.selected_instrument()
        if not x:
            self.instrument_detail.setHtml("<h2>No instrument selected</h2>"); return
        self.instrument_detail.setHtml(f"""
        <div class='eyebrow'>CANONICAL ECONOMIC INSTRUMENT</div>
        <div class='ticker'>{x['market_identifier']}</div>
        <h1>{x['instrument_name']}</h1><hr>
        <b>Canonical instrument ID</b><br><code>{x['instrument_id']}</code><br><br>
        <b>Underlying DCO</b><br><code>{x['underlying_dco_id']}</code><br><br>
        <b>Rights class</b><br>{x['rights_class']}<br><br>
        <b>Instrument class</b><br>{x['instrument_class']}<br><br>
        <b>Supply</b><br>{x['supply']:,}<br><br>
        <b>Fungibility</b><br>{x['fungibility']}<br><br>
        <b>Jurisdiction</b><br>{x['jurisdiction']}<br><br>
        <b>Rights Passport</b><br><code>{x['rights_passport_id']}</code><br><br>
        <small>The ticker is a human market alias. The canonical instrument ID remains authoritative.</small>
        """)

    def update_market_detail(self):
        r = self.selected_market()
        if not r:
            self.market_detail.setHtml("<h2>No active listing</h2><p>Assets remain private until an issuer explicitly creates an instrument and listing.</p>")
            return
        m = r["market"]
        im = next((x for x in self.metrics_rows if x["instrument_id"] == r["instrument_id"]), {})
        w = im.get("window_30d", {})
        flags = ", ".join((im.get("market_integrity") or {}).get("flags") or []) or "CLEAN"
        self.market_detail.setHtml(f"""
        <div class='eyebrow'>ENTITY MARKET</div>
        <div class='ticker'>{r['market_identifier']}</div>
        <h1>{r['instrument_name']}</h1><hr>
        <table>
        <tr><td>LAST</td><td><b>{m.get('last') or '—'}</b></td></tr>
        <tr><td>BID</td><td>{m.get('bid') or '—'}</td></tr>
        <tr><td>ASK</td><td>{m.get('ask') or '—'}</td></tr>
        <tr><td>30D UNITS</td><td>{w.get('volume_units', 0):,}</td></tr>
        <tr><td>30D TRADES</td><td>{w.get('trade_count', 0):,}</td></tr>
        <tr><td>BUYERS</td><td>{w.get('unique_buyers', 0):,}</td></tr>
        <tr><td>HOLDERS</td><td>{im.get('active_holder_count', 0):,}</td></tr>
        </table><br>
        <b>Rights</b><br>{r['rights_class']}<br><br>
        <b>Issuer</b><br><code>{r['issuer_entity_id']}</code><br><br>
        <b>Integrity</b><br>{flags}<br><br>
        <small>Observed price describes this instrument's bounded rights under its terms—not intrinsic DCO value.</small>
        """)

    def ingest_asset(self):
        path = QtWidgets.QFileDialog.getOpenFileName(self, "Choose digital asset to ingest")[0]
        if not path:
            return
        d = AssetIngestDialog(self, Path(path), self.backend)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.ingest(path, d.result_data)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Digital asset registered",
                f"DCO\n{result['digital_asset']['object_id']}\n\n"
                f"Global Passport verified: {result['global_passport_verified']}\n"
                f"BTDU bound: {bool(result['btdu_binding'])}\n\n"
                "No economic instrument, ticker, listing or price was created."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Asset ingest failed", str(e))

    def edit_asset_information(self):
        asset = self.selected_asset()
        if not asset:
            QtWidgets.QMessageBox.warning(self, "Asset information", "Select a controlled DCO first.")
            return
        current = self.backend.asset_disclosure(asset["object_id"])
        dialog = AssetDisclosureDialog(self, asset, current)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.publish_asset_disclosure(asset["object_id"], dialog.result_data)
            self.refresh()
            self.update_asset_detail()
            QtWidgets.QMessageBox.information(
                self, "Asset information published",
                f"Signed Asset Disclosure version {result['version']} was published.\n\n"
                f"Disclosure ID\n{result['disclosure_id']}\n\n"
                "Future listings will snapshot this disclosure together with the canonical asset dossier."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Asset information failed", str(e))

    def issue_selected_asset(self):
        asset = self.selected_asset()
        if not asset:
            QtWidgets.QMessageBox.warning(self, "Instrument", "Select a controlled DCO first."); return
        d = InstrumentDialog(self, asset, self.backend.namespace())
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.create_instrument(asset["object_id"], d.result_data)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Economic instrument issued",
                f"{result['market_identifier']}\n\nCanonical ID\n{result['instrument_id']}\n\n"
                "The instrument is not listed and no market value was created."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Instrument creation failed", str(e))

    def list_selected_instrument(self):
        instrument = self.selected_instrument()
        if not instrument:
            QtWidgets.QMessageBox.warning(self, "Listing", "Select one of your economic instruments."); return
        if not self.backend.asset_disclosure(instrument["underlying_dco_id"]):
            QtWidgets.QMessageBox.warning(
                self, "Asset information required",
                "This DCO does not yet have a signed Asset Disclosure. Publish detailed Asset Information before creating a market listing."
            )
            return
        d = ListingDialog(self, self.backend, instrument)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.create_listing(instrument["instrument_id"], d.result_data)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Listing created",
                f"{instrument['market_identifier']}\n\nListing ID\n{result['listing_id']}\n\n"
                "Listing Information Sheet and machine manifest are hash-bound."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Listing creation failed", str(e))

    def show_asset_lineage(self):
        a = self.selected_asset()
        if not a:
            return
        lin = a.get("lineage", {})
        p = lin.get("protocol_lineage", {}) or {}
        al = lin.get("asset_lineage", {}) or {}
        parents = "\n".join(
            f"{x.get('relation')}: {x.get('title') or x.get('parent_object_id')}"
            for x in al.get("parents", [])
        ) or "None"
        QtWidgets.QMessageBox.information(
            self, "ENTITY lineage",
            f"CANONICAL PROTOCOL / DOMAIN LINEAGE\n{p.get('display_path') or 'Unresolved'}\n\n"
            f"ASSET CONTROLLER\n{al.get('controller_name') or al.get('controller_entity_id')}\n\n"
            f"PROVENANCE PARENTS\n{parents}\n\n"
            "ADAM, NIKI and BTDU are capability/evidence bindings and do not create ownership."
        )

    def show_listing_info(self):
        r = self.selected_market()
        if not r:
            QtWidgets.QMessageBox.warning(self, "Listing", "No active market listing selected."); return
        try:
            listing = self.backend.market_registry.listing(r["listing_id"])
            dialog = ListingInformationDialog(
                self, listing["information"]["market_identifier"], listing["information_markdown"]
            )
            dialog.exec()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Listing Information", str(e))


    def export_listing(self):
        r = self.selected_market()
        if not r:
            QtWidgets.QMessageBox.warning(self, "Export", "No active market listing selected."); return
        dest = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose export folder")
        if not dest:
            return
        try:
            instrument = self.backend.market_registry.instrument(r["instrument_id"])
            folder = Path(dest) / (instrument["market_identifier"].replace(":", "-") + ".entity-instrument")
            result = self.backend.market_registry.export_portable_package(r["listing_id"], folder)
            QtWidgets.QMessageBox.information(
                self, "Portable instrument package",
                f"{result['market_identifier']}\n\n{result['destination']}\n\n"
                "Includes PDF, Markdown, JSON manifests/passports, verification and SHA256SUMS."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(e))

    def trade_selected(self, side):
        r = self.selected_market()
        if not r:
            QtWidgets.QMessageBox.warning(self, "Market", "No active market listing selected."); return
        d = OrderDialog(self, r, side)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            qty, price = d.result_data
            result = self.backend.submit_order(r, side, qty, price)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Order submitted",
                f"Order accepted.\nImmediate matches: {len(result['trades'])}\n\n"
                "Matched trades remain subject to clearing and settlement evidence."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Order failed", str(e))

    def _apply_style(self):
        self.setStyleSheet(f"""
        * {{
            font-family: "Segoe UI";
            font-size: 10pt;
            color: {TEXT};
        }}
        QMainWindow, QStackedWidget {{ background: {ROOT_BG}; }}
        QWidget {{ color: {TEXT}; }}
        QLabel {{ background: transparent; }}
        #sidebar {{ background: {SIDEBAR_BG}; border-right: 1px solid {BORDER}; }}
        QLabel[class="brand"] {{ font-size: 26pt; font-weight: 800; letter-spacing: 2px; color: {TEXT}; }}
        QLabel[class="brandSub"] {{ font-size: 8pt; font-weight: 700; letter-spacing: 2px; color: {ACCENT}; }}
        QLabel[class="pageTitle"] {{ font-size: 22pt; font-weight: 700; }}
        QLabel[class="pageSub"], QLabel[class="muted"], QLabel[class="monoMuted"] {{ color: {MUTED}; }}
        QLabel[class="monoMuted"] {{ font-family: Consolas; }}
        QLabel[class="eyebrow"] {{ color: {ACCENT}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
        QLabel[class="sectionTitle"] {{ font-size: 11pt; font-weight: 700; letter-spacing: 1px; }}
        QLabel[class="metric"] {{ font-size: 20pt; font-weight: 750; }}
        QLabel[class="emptyTitle"] {{ font-size: 15pt; font-weight: 700; }}
        QLabel[class="dialogTitle"] {{ font-size: 18pt; font-weight: 700; }}
        QLabel[class="tickerHero"] {{ color: {ACCENT}; font-family: Consolas; font-size: 18pt; font-weight: 700; }}
        QLabel[class="tickerPreview"] {{ background: {SIDEBAR_BG}; border: 1px solid {ACCENT_DARK}; border-radius: 6px; padding: 10px; color: {ACCENT}; font-family: Consolas; font-weight: 700; }}
        QLabel[class="chip"] {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 7px 11px; color: {MUTED}; font-size: 8pt; font-weight: 700; }}
        QLabel[class="identityChip"] {{ background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 11px; font-size: 8pt; }}
        QLabel[class="tape"] {{ background: {SIDEBAR_BG}; border: 1px solid {BORDER}; padding: 9px 12px; color: {ACCENT}; font-family: Consolas; font-size: 9pt; }}
        QLabel[class="sidebarFoot"] {{ color: {MUTED}; font-size: 8pt; line-height: 1.4; }}
        QFrame[class="panel"], QFrame[class="metricCard"], QFrame[class="empty"] {{
            background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 8px;
        }}
        QFrame[class="notice"] {{ background: {PANEL_2}; border: 1px solid {ACCENT_DARK}; border-radius: 7px; }}
        QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px 13px; font-weight: 600; }}
        QPushButton:hover {{ border-color: {ACCENT_DARK}; background: #1A2027; }}
        QPushButton[primary="true"] {{ background: {ACCENT}; color: #0C0E11; border-color: {ACCENT}; font-weight: 800; }}
        QPushButton[nav="true"] {{ background: transparent; border: none; text-align: left; padding: 10px 10px; color: {MUTED}; font-size: 9pt; font-weight: 650; }}
        QPushButton[nav="true"]:hover {{ background: {PANEL_BG}; color: {TEXT}; }}
        QPushButton[nav="true"]:checked {{ background: {PANEL_2}; color: {TEXT}; border-left: 3px solid {ACCENT}; }}
        QTableWidget {{ background: {PANEL_BG}; alternate-background-color: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 7px; selection-background-color: #2A251A; selection-color: {TEXT}; }}
        QHeaderView::section {{ background: {SIDEBAR_BG}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 9px; font-size: 8pt; font-weight: 700; }}
        QTableWidget::item {{ border-bottom: 1px solid #181D23; padding: 7px; }}
        QTableWidget::item:selected {{ background: #2A251A; color: {TEXT}; }}
        QScrollBar:vertical {{ width: 10px; background: {ROOT_BG}; }}
        QScrollBar::handle:vertical {{ background: #303844; min-height: 30px; border-radius: 4px; }}
        QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
            background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 5px; padding: 7px; selection-background-color: {ACCENT_DARK};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
        QDialog {{ background: {ROOT_BG}; }}
        QTextBrowser[class="detail"] {{ background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 7px; padding: 14px; }}
        QSplitter::handle {{ background: {ROOT_BG}; width: 8px; height: 8px; }}
        QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; }}
        """)

def self_test(state: Path, entity_id: str, wallet_profile: dict | None = None) -> dict:
    backend = Backend(state, entity_id)
    snap = backend.snapshot()
    registry_status = backend.market_registry.status()
    onboarding = ONBOARDING.EntityWalletOnboarding(state)
    profile = wallet_profile or onboarding.profile_for_entity(entity_id)
    auth = onboarding.authenticate(profile) if profile else {"authenticated": False, "reason": "legacy_unprofiled_identity"}
    return {
        "ready": True, "ui_engine": "PySide6", "design": "ENTITY_DATA_ECONOMY_TERMINAL",
        "entity_id": entity_id, "assets": len(snap.get("assets", [])),
        "instruments": len(backend.instruments()), "positions": len(snap.get("positions", [])),
        "orders": len(snap.get("orders", [])), "venues": len(backend.venues()),
        "market_listings": len(backend.market()), "economic_demand_series": len(backend.economic_metrics()),
        "issuer_namespace": backend.namespace(),
        "asset_disclosures": registry_status["counts"].get("asset_disclosures", 0),
        "market_registry_version": registry_status["version"],
        "signed_asset_disclosure_required_for_listing": registry_status.get("signed_asset_disclosure_required_for_listing", False),
        "wallet_profile_id": profile.get("profile_id") if profile else None,
        "wallet_lineage": profile.get("display_path") if profile else None,
        "device_bound_login": bool(auth.get("authenticated")) if profile else False,
        "login_mode": (profile.get("login_policy") or {}).get("mode") if profile else None,
        "public_name_is_alias_not_authority": True,
        "device_information_creates_user_identity": False,
        "protocol_origin_is_separate_from_user_lineage": True,
        "protocol_tax_bps": 0, "cryptocurrency_required": False,
    }

def main():
    ap = argparse.ArgumentParser(description="ENTITY Data Economy Terminal")
    ap.add_argument("--state"); ap.add_argument("--entity")
    ap.add_argument("--self-test", action="store_true"); ap.add_argument("--self-test-output")
    ap.add_argument("--render-preview")
    args = ap.parse_args()
    state = Path(args.state) if args.state else default_state()
    onboarding = ONBOARDING.EntityWalletOnboarding(state)

    wallet_profile = None
    if args.entity:
        wallet_profile = onboarding.profile_for_entity(args.entity)
    else:
        wallet_profile = onboarding.active_profile()
        if wallet_profile:
            args.entity = wallet_profile["active_entity_id"]

    if args.self_test:
        if not args.entity:
            ms = manifests(state)
            if not ms:
                raise SystemExit("No ENTITY identity or wallet profile found")
            args.entity = ms[0]["entity_id"]
        report = self_test(state, args.entity, wallet_profile)
        raw = json.dumps(report, indent=2, sort_keys=True)
        if args.self_test_output:
            Path(args.self_test_output).write_text(raw + "\n", encoding="utf-8")
        else:
            print(raw)
        return

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(startup_stylesheet())

    if not args.entity:
        setup = EntitySetupDialog(None, onboarding)
        if setup.exec() != QtWidgets.QDialog.Accepted or not setup.profile:
            return
        wallet_profile = setup.profile
        args.entity = wallet_profile["active_entity_id"]
    elif wallet_profile is None and not args.render_preview:
        # A legacy explicit --entity remains supported for managed deployments.
        pass
    elif wallet_profile is not None and not args.render_preview:
        login = EntityLoginDialog(None, onboarding)
        if login.exec() != QtWidgets.QDialog.Accepted:
            return
        if login.create_new:
            setup = EntitySetupDialog(None, onboarding)
            if setup.exec() != QtWidgets.QDialog.Accepted or not setup.profile:
                return
            wallet_profile = setup.profile
        else:
            wallet_profile = login.profile
        args.entity = wallet_profile["active_entity_id"]

    window = WalletWindow(state, args.entity, wallet_profile)
    window.show()
    if args.render_preview:
        app.processEvents()
        QtCore.QTimer.singleShot(300, lambda: (
            window.grab().save(str(Path(args.render_preview))),
            app.quit()
        ))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
