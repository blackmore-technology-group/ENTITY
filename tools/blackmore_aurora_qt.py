"""Blackmore Aurora v1.0 — shared Qt presentation; no business/runtime mutations.

This module intentionally has no access to wallets, signing keys, databases or
external network. The exact semantic colors match blackmore-aurora.tokens.json.
"""
from __future__ import annotations
from PySide6 import QtGui

C = {
    'BG': "#08121F",
    'CANVAS': "#0B1728",
    'SURFACE': "#101F32",
    'RAISED': "#142740",
    'HOVER': "#1B3150",
    'LINE': "#29435F",
    'STRONG': "#416581",
    'TEXT': "#F4F8FF",
    'MUTED': "#9CB3CF",
    'SUBTLE': "#6683A6",
    'CYAN': "#57D7F7",
    'BLUE': "#77BBFF",
    'MINT': "#65E8BD",
    'VIOLET': "#CC9CFF",
    'AMBER': "#F6C879",
    'RED': "#FD8C9D",
    'INK': "#041723"
}
FAMILY = "Blackmore Aurora"
VERSION = "1.0.0"

def color(key: str) -> QtGui.QColor:
    return QtGui.QColor(C[key])

def stylesheet() -> str:
    """Append this after pre-existing styles to retain page semantics."""
    return """
    QWidget { color: #F4F8FF; font-family: "Segoe UI"; selection-background-color: #245B76; }
    QMainWindow, QDialog, QStackedWidget { background: #08121F; }
    QToolTip { background: #142740; color: #F4F8FF; border: 1px solid #416581; padding: 7px; }
    QWidget#sidebar { background: #0B1728; border-right: 1px solid #29435F; }
    QLabel[class="brand"] { color: #F4F8FF; font-size: 26pt; font-weight: 800; letter-spacing: 2px; }
    QLabel[class="brandSub"], QLabel[class="eyebrow"] { color: #57D7F7; font-weight: 700; letter-spacing: 1px; }
    QLabel[class="pageTitle"] { font-size: 22pt; font-weight: 750; color: #F4F8FF; }
    QLabel[class="sectionTitle"] { font-size: 12pt; font-weight: 750; color: #F4F8FF; }
    QLabel[class="muted"], QLabel[class="pageSub"], QLabel[class="monoMuted"] { color: #9CB3CF; }
    QLabel[class="chip"], QLabel[class="identityChip"] {
        border: 1px solid #29435F; border-radius: 9px; background: #142740;
        color: #9CB3CF; padding: 8px 11px;
    }
    QLabel[class="tickerPreview"], QLabel[class="tickerHero"], QLabel[class="tape"] {
        background: #101F32; border: 1px solid #29435F;
        color: #F6C879; border-radius: 9px; padding: 9px;
    }
    QFrame[class="panel"], QFrame[class="metricCard"], QFrame[class="card"] {
        background: #101F32; border: 1px solid #29435F; border-radius: 15px;
    }
    QPushButton { background: #142740; color: #F4F8FF; border: 1px solid #29435F;
        border-radius: 10px; padding: 10px 14px; min-height: 22px; font-weight: 650; }
    QPushButton:hover { background: #1B3150; border-color: #57D7F7; color: #FFFFFF; }
    QPushButton:pressed { background: #1C4961; border-color: #8DEBFF; }
    QPushButton:disabled { color: #6683A6; background: #101F32; border-color: #29435F; }
    QPushButton:focus { border: 2px solid #8DEBFF; }
    QPushButton[primary="true"] { background: #57D7F7; border: 1px solid #57D7F7; color: #041723; font-weight: 800; }
    QPushButton[primary="true"]:hover { background: #8DEBFF; border-color: #8DEBFF; color: #041723; }
    QPushButton[nav="true"] { background: transparent; color: #9CB3CF; border: 1px solid transparent;
        border-radius: 9px; min-height: 27px; text-align: left; padding: 11px 12px; }
    QPushButton[nav="true"]:hover { background: #142740; color: #F4F8FF; border-color: #29435F; }
    QPushButton[nav="true"]:checked { background: #163950; color: #8DEBFF; border-color: #376D86; }
    QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QListWidget, QTreeWidget, QTableView, QTableWidget {
        background: #101F32; color: #F4F8FF; border: 1px solid #29435F;
        border-radius: 9px; padding: 7px; selection-background-color: #245B76; }
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QListWidget:focus, QTreeWidget:focus, QTableView:focus { border: 2px solid #57D7F7; }
    QComboBox QAbstractItemView { background: #101F32; color: #F4F8FF;
        selection-background-color: #245B76; border: 1px solid #416581; }
    QHeaderView::section { background: #142740; color: #9CB3CF;
        border: 0; border-bottom: 1px solid #29435F; padding: 11px; font-weight: 750; }
    QTableView::item { padding: 7px; border-bottom: 1px solid #182B41; }
    QTableView::item:selected { background: #245B76; }
    QScrollArea, QScrollArea QWidget#qt_scrollarea_viewport { border: 0; background: transparent; }
    QScrollBar:vertical { background: #0B1728; width: 12px; margin: 0; }
    QScrollBar::handle:vertical { background: #355572; min-height: 30px; border-radius: 5px; }
    QScrollBar:horizontal { background: #0B1728; height: 12px; margin: 0; }
    QScrollBar::handle:horizontal { background: #355572; min-width: 30px; border-radius: 5px; }
    QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
    QTabBar::tab { background: #101F32; color: #9CB3CF; padding: 10px 15px;
        border: 1px solid #29435F; border-radius: 8px; margin-right: 4px; }
    QTabBar::tab:selected { background: #163950; color: #8DEBFF; border-color: #57D7F7; }
    QProgressBar { border: 1px solid #29435F; border-radius: 6px; background: #101F32;
        text-align: center; color: #F4F8FF; }
    QProgressBar::chunk { background: #65E8BD; border-radius: 5px; }
    QSplitter::handle { background: #29435F; }
    QGroupBox { background: #101F32; border: 1px solid #29435F; border-radius: 12px;
        margin-top: 16px; padding: 12px; font-weight: 700; }
    QGroupBox::title { color: #57D7F7; subcontrol-origin: margin; left: 12px; }
    QCheckBox, QRadioButton { spacing: 9px; color: #F4F8FF; }
    QCheckBox::indicator:checked { background: #57D7F7; border: 1px solid #57D7F7; }
    QStatusBar { background: #0B1728; color: #9CB3CF; border-top: 1px solid #29435F; }
    """

def palette():
    pal=QtGui.QPalette()
    for name,key in [("Window","BG"),("WindowText","TEXT"),("Base","SURFACE"),
                     ("AlternateBase","RAISED"),("Text","TEXT"),("Button","RAISED"),
                     ("ButtonText","TEXT"),("Highlight","CYAN"),("HighlightedText","INK"),
                     ("ToolTipBase","SURFACE"),("ToolTipText","TEXT")]:
        pal.setColor(getattr(QtGui.QPalette,name),color(key))
    return pal
