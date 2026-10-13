"""ENTITY Workspace DataChip Composer — editable typed-node canvas.

Experimental engineering UI. Compiles a verifiable *plan* only. No chip
execution, marketplace transaction, wallet mutation, device mounting,
licence transfer or issuer authorization occurs through this page.
"""
from __future__ import annotations
from hashlib import sha256
import html, importlib.util, json, os, sys, threading
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

ROOT=Path(__file__).resolve().parents[1]
GRAPH_FILE=ROOT/"src"/"42_ENTITY_Wallet"/"datachip_graph.py"
_spec=importlib.util.spec_from_file_location("entity_wallet_datachip_graph",GRAPH_FILE)
if not _spec or not _spec.loader:raise RuntimeError("missing DataChip graph compiler")
GRAPH=importlib.util.module_from_spec(_spec)
sys.modules[_spec.name]=GRAPH
_spec.loader.exec_module(GRAPH)

BG=QtGui.QColor("#0b1018")
PANEL=QtGui.QColor("#172232")
BORDER=QtGui.QColor("#47627d")
TEXT=QtGui.QColor("#eef3fa")
MUTED=QtGui.QColor("#a9b9cb")
GOLD=QtGui.QColor("#d5ac66")
GREEN=QtGui.QColor("#48d4ae")
BLUE=QtGui.QColor("#73b1eb")
MIME="application/x-entity-datachip-module"

class Port(QtWidgets.QGraphicsEllipseItem):
    def __init__(self,card,side,record,x,y):
        super().__init__(-6,-6,12,12,card)
        self.card=card;self.side=side;self.record=record
        self.setPos(x,y);self.setZValue(10)
        self.setPen(QtGui.QPen(QtGui.QColor("#07131b"),2))
        self.setBrush(QtGui.QBrush(GREEN if side=="outputs" else BLUE))
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(side[:-1]+" · "+record["name"]+" : "+record["type"])
    def mousePressEvent(self,event):
        self.card.page.choose_port(self.card.node_id,self.side,self.record["name"])
        event.accept()

class Card(QtWidgets.QGraphicsRectItem):
    WIDTH=228
    def __init__(self,page,node):
        self.page=page
        self.node_id=node["id"]
        spec=page.graph.modules[node["module_id"]]
        self.spec=spec
        self.inputs={};self.outputs={}
        rows=max(1,len(spec["inputs"]),len(spec["outputs"]))
        self.height=80+27*rows
        super().__init__(0,0,self.WIDTH,self.height)
        self.setPen(QtGui.QPen(BORDER,1.5))
        self.setBrush(QtGui.QBrush(PANEL))
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(3)
        head=QtWidgets.QGraphicsRectItem(0,0,self.WIDTH,35,self)
        head.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        head.setBrush(QtGui.QBrush(QtGui.QColor("#264056")))
        label=QtWidgets.QGraphicsSimpleTextItem(spec["name"],self)
        label.setBrush(TEXT)
        label.setPos(10,7)
        small=QtWidgets.QGraphicsSimpleTextItem(spec["kind"].upper()+" · "+spec["version"],self)
        small.setBrush(MUTED)
        small.setScale(.82)
        small.setPos(11,39)
        for i,p in enumerate(spec["inputs"]):
            y=72+i*27
            self.inputs[p["name"]]=Port(self,"inputs",p,0,y)
            t=QtWidgets.QGraphicsSimpleTextItem(p["name"],self)
            t.setBrush(MUTED);t.setScale(.8);t.setPos(13,y-12)
        for i,p in enumerate(spec["outputs"]):
            y=72+i*27
            self.outputs[p["name"]]=Port(self,"outputs",p,self.WIDTH,y)
            t=QtWidgets.QGraphicsSimpleTextItem(p["name"],self)
            t.setBrush(MUTED);t.setScale(.8)
            w=t.boundingRect().width()*.8
            t.setPos(self.WIDTH-w-13,y-12)
        self.setPos(node["x"],node["y"])

    def itemChange(self,change,value):
        if change==QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            try:
                p=self.pos()
                self.page.graph.move(self.node_id,p.x(),p.y())
                self.page.draw_edges()
            except (AttributeError,GRAPH.ComposerError):
                pass
        elif change==QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            try:self.page.inspect()
            except AttributeError:pass
        return super().itemChange(change,value)

class Palette(QtWidgets.QListWidget):
    def startDrag(self,actions):
        item=self.currentItem()
        if item is None:return
        value=item.data(QtCore.Qt.UserRole)
        if not value:return
        mime=QtCore.QMimeData()
        mime.setData(MIME,str(value).encode("utf-8"))
        drag=QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.CopyAction)

class Canvas(QtWidgets.QGraphicsView):
    def __init__(self,page):
        super().__init__(page.scene)
        self.page=page
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.BoundingRectViewportUpdate)
        self.setBackgroundBrush(QtGui.QBrush(BG))
        self.setSceneRect(-2500,-2500,5000,5000)
        self.setMinimumSize(470,400)
    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat(MIME):event.acceptProposedAction()
        else:super().dragEnterEvent(event)
    def dragMoveEvent(self,event):
        if event.mimeData().hasFormat(MIME):event.acceptProposedAction()
        else:super().dragMoveEvent(event)
    def dropEvent(self,event):
        if event.mimeData().hasFormat(MIME):
            mid=bytes(event.mimeData().data(MIME)).decode("utf-8")
            pt=self.mapToScene(event.position().toPoint())
            self.page.add_module(mid,pt.x(),pt.y())
            event.acceptProposedAction()
        else:super().dropEvent(event)
    def wheelEvent(self,event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            f=1.16 if event.angleDelta().y()>0 else 1/1.16
            if .15<self.transform().m11()*f<3:
                self.scale(f,f)
            event.accept()
        else:super().wheelEvent(event)

class ComposerPage(QtWidgets.QWidget):
    chipResult=QtCore.Signal(str,object,str)
    def __init__(self,state,owner_id,parent=None):
        super().__init__(parent)
        self.owner_id=owner_id
        self.store=GRAPH.GraphStore(state,owner_id)
        self.graph=GRAPH.Graph(owner_id)
        self.pending=None
        self.cards={}
        self.edges=[]
        self.scene=QtWidgets.QGraphicsScene(self)
        self.chipResult.connect(self._chip_result)
        self._build()
        self.render()

    def _build(self):
        root=QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0);root.setSpacing(10)
        banner=QtWidgets.QLabel(
            "DATACHIP COMPOSER  ·  TYPE-SAFE ASSEMBLIES   |   "
            "Draft / compile only — no code execution or asset transfer")
        banner.setStyleSheet("color:#d5ac66;font-weight:700;padding:9px;background:#151e29;")
        root.addWidget(banner)
        actions=QtWidgets.QHBoxLayout()
        def action(title,fn):
            b=QtWidgets.QPushButton(title);b.clicked.connect(fn);actions.addWidget(b)
            return b
        action("New Graph",self.new_graph)
        action("Example Graph",self.example)
        action("Import .edcf",self.import_edcf)
        action("Import Interface",self.import_interface)
        action("Save Draft",self.save)
        action("Open Draft",self.open_saved)
        action("Compile Plan",self.compile_plan)
        action("Export Plan",self.export_plan)
        root.addLayout(actions)
        split=QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(split,1)
        sidebar=QtWidgets.QWidget()
        sidebar.setMinimumWidth(160);sidebar.setMaximumWidth(260)
        sl=QtWidgets.QVBoxLayout(sidebar);sl.setContentsMargins(2,0,2,0)
        title=QtWidgets.QLabel("MODULE PALETTE");title.setStyleSheet("font-weight:700;color:#d5ac66")
        sl.addWidget(title)
        sl.addWidget(QtWidgets.QLabel("Drag chips onto the canvas.\nClick output port then input port."))
        self.palette=Palette()
        self.palette.setDragEnabled(True)
        self.palette.itemDoubleClicked.connect(lambda _:self.palette_add())
        sl.addWidget(self.palette,1)
        split.addWidget(sidebar)
        self.canvas=Canvas(self)
        split.addWidget(self.canvas)
        inspector=QtWidgets.QWidget()
        il=QtWidgets.QVBoxLayout(inspector)
        il.setContentsMargins(4,0,0,0)
        il.addWidget(QtWidgets.QLabel("ASSEMBLY / PORT INSPECTOR"))
        self.detail=QtWidgets.QTextBrowser()
        self.detail.setOpenExternalLinks(False)
        il.addWidget(self.detail,1)
        delete=QtWidgets.QPushButton("Remove Selected Node")
        delete.clicked.connect(self.delete_node)
        il.addWidget(delete)
        split.addWidget(inspector)
        split.setStretchFactor(0,0);split.setStretchFactor(1,1);split.setStretchFactor(2,0)
        split.setSizes([195,750,270])
        self.status=QtWidgets.QLabel("Ready — assembly plans are not deployment authorization.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.fill_palette()

    def fill_palette(self):
        self.palette.clear()
        for mid,mod in sorted(self.graph.modules.items(),key=lambda x:x[1]["name"]):
            item=QtWidgets.QListWidgetItem(mod["name"]+"\n"+mod["version"]+" · "+mod["kind"])
            item.setData(QtCore.Qt.UserRole,mid)
            item.setToolTip(mid)
            self.palette.addItem(item)

    def notify(self,message):
        self.status.setText(message)

    def show_error(self,label,error):
        self.notify(label+": "+str(error))
        QtWidgets.QMessageBox.warning(self,label,str(error))

    def add_module(self,mid,x=100,y=100,chip_id=None):
        try:
            nid=self.graph.add(mid,x,y,chip_id=chip_id)
            self.render(selected=nid)
            self.notify("Added "+self.graph.modules[mid]["name"]+" · not executable or licensed")
        except GRAPH.ComposerError as e:self.show_error("Cannot add DataChip",e)

    def palette_add(self):
        item=self.palette.currentItem()
        if item:self.add_module(item.data(QtCore.Qt.UserRole),
                                100+len(self.graph.nodes)*40,100+len(self.graph.nodes)*30)

    def choose_port(self,nid,side,name):
        if side=="outputs":
            self.pending=(nid,name)
            self.notify("Output selected: "+name+" — click a compatible input port")
            return
        if not self.pending:
            self.notify("Choose an output port first.")
            return
        source,output=self.pending
        self.pending=None
        try:
            self.graph.connect(source,output,nid,name)
            self.draw_edges()
            self.inspect()
            self.notify("Typed connection accepted and graph cycle checked.")
        except GRAPH.ComposerError as e:self.show_error("Connection rejected",e)

    def draw_edges(self):
        for item in self.edges:
            self.scene.removeItem(item)
        self.edges=[]
        for e in self.graph.edges:
            a=self.cards.get(e["from"]);b=self.cards.get(e["to"])
            if not a or not b:continue
            p=a.outputs[e["out"]].scenePos()
            q=b.inputs[e["in"]].scenePos()
            line=QtGui.QPainterPath(p)
            delta=max(60,abs(q.x()-p.x())*.5)
            line.cubicTo(p.x()+delta,p.y(),q.x()-delta,q.y(),q.x(),q.y())
            item=QtWidgets.QGraphicsPathItem(line)
            item.setPen(QtGui.QPen(GREEN,2))
            item.setZValue(1)
            self.scene.addItem(item);self.edges.append(item)

    def render(self,selected=None):
        self.scene.clear()
        self.cards={}
        self.edges=[]
        self.pending=None
        for row in self.graph.nodes:
            item=Card(self,row)
            self.scene.addItem(item)
            self.cards[row["id"]]=item
        self.draw_edges()
        if selected in self.cards:self.cards[selected].setSelected(True)
        self.inspect()
        self.fill_palette()

    def inspect(self):
        current=next((card for card in self.cards.values() if card.isSelected()),None)
        if current is None:
            self.detail.setHtml(
                "<h3>DataChip Graph</h3><p>"+html.escape(self.graph.name)+"</p>"
                "<p>"+str(len(self.graph.nodes))+" nodes · "+str(len(self.graph.edges))+
                " connections</p><p>Connect matching port types. Imported interfaces do "
                "not acquire execution rights.</p>"
            )
            return
        rec=self.graph.node(current.node_id)
        spec=self.graph.modules[rec["module_id"]]
        def ports(k):
            return "".join("<li>"+html.escape(p["name"])+" : <code>"+
                           html.escape(p["type"])+"</code></li>" for p in spec[k]) or "<li>none</li>"
        self.detail.setHtml(
            "<h3>"+html.escape(spec["name"])+"</h3><p><code>"+
            html.escape(spec["module_id"])+"</code> · "+html.escape(spec["version"])+
            "</p><p>Type: "+html.escape(spec["kind"])+
            "</p><b>Inputs</b><ul>"+ports("inputs")+"</ul><b>Outputs</b><ul>"+
            ports("outputs")+"</ul><p>Chip: "+
            html.escape(rec["chip_id"] or "interface template")+
            "</p><p><b>Authority:</b> NOT GRANTED</p>"
        )

    def delete_node(self):
        card=next((x for x in self.cards.values() if x.isSelected()),None)
        if not card:return
        self.graph.remove(card.node_id)
        self.render();self.notify("Node and incident connections removed.")

    def new_graph(self):
        if QtWidgets.QMessageBox.question(self,"New composition",
            "Start a new draft? Unsaved changes will be lost.")!=QtWidgets.QMessageBox.Yes:
            return
        self.graph=GRAPH.Graph(self.owner_id)
        self.render()
        self.notify("New empty graph. Existing saved drafts and wallet assets unchanged.")

    def example(self):
        if self.graph.nodes and QtWidgets.QMessageBox.question(
                self,"Replace draft","Replace the unsaved canvas with an example?")!=QtWidgets.QMessageBox.Yes:
            return
        self.graph=GRAPH.Graph(self.owner_id,name="Terrain DataChip Assembly")
        a=self.graph.add("entity.edcf.source",40,110)
        b=self.graph.add("entity.edcf.verify",315,110)
        c=self.graph.add("entity.geo.decode",590,110)
        d=self.graph.add("entity.geo.terrain",865,110)
        e=self.graph.add("entity.host.visual",1140,110)
        self.graph.connect(a,"archive",b,"archive")
        self.graph.connect(b,"content",c,"content")
        self.graph.connect(c,"layer",d,"layer")
        self.graph.connect(d,"profile",e,"profile")
        self.render()
        self.canvas.fitInView(self.scene.itemsBoundingRect().adjusted(-60,-60,60,60),
                              QtCore.Qt.KeepAspectRatio)
        self.notify("Five compatible interfaces linked. This does NOT run terrain computation.")

    def save(self):
        try:
            self.graph.name=self.graph.name.strip() or "Untitled assembly"
            path=self.store.save(self.graph)
            self.notify("Draft saved locally: "+str(path))
        except (GRAPH.ComposerError,OSError) as e:self.show_error("Save refused",e)

    def open_saved(self):
        items=self.store.list_drafts()
        if not items:
            self.notify("No saved graphs for this wallet identity.")
            return
        names=[x["name"]+"  ·  "+x["id"] for x in items]
        value,accepted=QtWidgets.QInputDialog.getItem(
            self,"Open an ENTITY assembly","Saved drafts:",names,0,False)
        if not accepted:return
        try:
            self.graph=self.store.load(items[names.index(value)]["id"])
            self.render();self.notify("Integrity-verified wallet-specific draft opened.")
        except (GRAPH.ComposerError,OSError,ValueError) as e:self.show_error("Open refused",e)

    def compile_plan(self):
        try:
            plan=self.graph.compile()
            self.detail.setPlainText(json.dumps(plan,indent=2,sort_keys=True))
            self.notify("Plan verified: "+plan["sha256"]+
                        " · EXECUTION, RIGHTS, TRANSFER and DEPLOYMENT DISABLED")
            return plan
        except GRAPH.ComposerError as e:
            self.show_error("Compile refused",e)
            return None

    def export_plan(self):
        plan=self.compile_plan()
        if plan is None:return
        base=self.store.root.parent/"exports"
        candidate=base/(self.graph.graph_id+".assembly.json")
        name,_=QtWidgets.QFileDialog.getSaveFileName(
            self,"Export composition plan (not runnable)",str(candidate),"JSON (*.json)")
        if not name:return
        target=Path(name)
        if target.exists():
            self.show_error("Export refused","Existing files are never overwritten.")
            return
        try:
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("xb") as f:
                f.write(GRAPH.canonical(plan)+b"\n")
            self.notify("Plan exported. Not licensed or executable: "+str(target))
        except (OSError,ValueError) as e:self.show_error("Export refused",e)

    def import_interface(self):
        name,_=QtWidgets.QFileDialog.getOpenFileName(
            self,"Import DataChip typed-interface manifest","","JSON (*.json)")
        if not name:return
        try:
            path=Path(name)
            if path.is_symlink() or not path.is_file() or path.stat().st_size>16384:
                raise GRAPH.ComposerError("missing/unsafe or oversized module manifest")
            spec=json.loads(path.read_text(encoding="utf-8"))
            mid=self.graph.register(spec)
            self.fill_palette()
            self.notify("Imported untrusted interface: "+mid+
                        " · declarations do not establish software execution or issuer identity.")
        except (GRAPH.ComposerError,ValueError,OSError,UnicodeError) as e:
            self.show_error("Import refused",e)

    def import_edcf(self):
        name,_=QtWidgets.QFileDialog.getOpenFileName(
            self,"Import independently verified EDCF archive","","Entity Formula Chips (*.edcf)")
        if not name:return
        path=Path(name)
        if path.is_symlink() or not path.is_file() or path.stat().st_size>80*1024*1024:
            self.show_error("Chip rejected","Missing/unsafe or oversized archive")
            return
        self.notify("Verifying EDCF integrity off the UI thread — no rights are granted.")
        def task():
            try:
                root=str(ROOT)
                if root not in sys.path:sys.path.insert(0,root)
                from sdk.datachip.formula_chip import verify_formula
                result=verify_formula(path)
                if result.get("integrity_verified") is not True or result.get("formula_native") is not True:
                    raise GRAPH.ComposerError("formula integrity not independently verified")
                if result.get("rights_authorized") is not False:
                    raise GRAPH.ComposerError("unexpected implicit rights state")
                self.chipResult.emit(name,result,"")
            except Exception as error:
                self.chipResult.emit(name,{},str(error))
        threading.Thread(target=task,daemon=True).start()

    @QtCore.Slot(str,object,str)
    def _chip_result(self,path,receipt,error):
        if error:
            self.show_error("DataChip integrity rejected",error)
            return
        cid=receipt.get("chip_id","")
        if not isinstance(cid,str) or not GRAPH.CHIPID.fullmatch(cid):
            self.show_error("DataChip rejected","unrecognized ENTITY chip identity")
            return
        mid="entity.pinned."+cid.split(":")[-1]
        spec={"schema":GRAPH.MODULE_SCHEMA,"module_id":mid,"name":"Verified "+Path(path).name[:50],
              "version":"0.1.0","kind":"source","inputs":[],
              "outputs":[{"name":"content","type":"entity.content.verified","required":False}]}
        try:
            self.graph.register(spec)
            self.add_module(mid,100+len(self.graph.nodes)*34,120+len(self.graph.nodes)*25,chip_id=cid)
            self.notify("Content integrity PASS: "+cid+
                        " · issuer, rights, licence and device deployment NOT VERIFIED.")
        except GRAPH.ComposerError as e:self.show_error("DataChip rejected",e)
