from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QGroupBox, QLineEdit, QTextEdit, QComboBox, QTabWidget, QFrame, QButtonGroup
)
from PyQt6.QtGui import (
    QShortcut, QKeySequence, QPainter, QColor, QPen, QFont, QPainterPath
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QThread, QTimer

from core.utils import RANKS, determine_street
from core.hand_evaluator import HandEvaluator
from core.monte_carlo import MonteCarloSimulator
from core.pot_odds import PotOddsCalculator
from core.equity_calculator import EquityCalculator
from core.bankroll_manager import BankrollManager
from core.decision_engine import DecisionEngine
from core.settings_store import load_settings, save_settings


# ============================ MOTYW (CASINO NOIR) ============================
# Grafit + brass(złoto) jako kolor interakcji/brandu; zieleń/czerwień = dane.
C = {
    "bg": "#101319",
    "panel": "#171B22",
    "panel_alt": "#1E232C",
    "input": "#1F2530",
    "border": "#2A3039",
    "border_lt": "#3A424F",
    "text": "#E8EAEF",
    "muted": "#7E879A",
    "gold": "#D4A33C",       # akcent / interakcja / brand
    "gold_dk": "#B8862A",
    "green": "#3FB57A",      # pozytywne / win
    "red": "#E25563",        # negatywne / lose
    "felt": "#16382B",       # zielony filc (subtelne tło sceny kart)
}

SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
# Klasyczna 4-kolorowa talia NA BIAŁEJ karcie (maksymalna czytelność)
SUIT_ON_WHITE = {
    "s": "#1C1C1C",  # pik   – czarny
    "h": "#D2342B",  # kier  – czerwony
    "d": "#2E6FD6",  # karo  – niebieski
    "c": "#2C8A4A",  # trefl – zielony
}

SLOT_LABELS = ["HERO", "HERO", "FLOP", "FLOP", "FLOP", "TURN", "RIVER"]


# ------------------------------- Malowana karta -----------------------------
class CardFace(QWidget):
    """Realistyczna karta rysowana QPainterem (matryca i sloty stołu)."""

    clicked = pyqtSignal()

    def __init__(self, w, h, placeholder="", mini=False, fixed_card=None):
        super().__init__()
        self.setFixedSize(w, h)
        self.card = fixed_card
        self.placeholder = placeholder
        self.mini = mini
        self.used = False
        self.active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def update_state(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        radius = 6 if self.mini else 9

        # --- pusty slot ---
        if not self.card:
            pen = QPen(QColor(C["gold"] if self.active else C["border_lt"]))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.SolidLine if self.active else Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(QColor(C["felt"] if self.active else "#13161C"))
            p.drawRoundedRect(rect, radius, radius)
            if self.placeholder:
                p.setPen(QColor(C["gold"] if self.active else "#566072"))
                f = QFont("Segoe UI", 8)
                f.setBold(True)
                f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
                p.setFont(f)
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.placeholder)
            p.end()
            return

        suit = self.card[1]
        rank = "10" if self.card[0] == "T" else self.card[0]
        sym = SUIT_SYMBOLS[suit]

        if self.used:  # karta zajęta w innym slocie – wyszarzona
            face, ink, border = QColor("#2A2F38"), QColor("#5A6373"), QColor(C["border"])
        else:
            face, ink = QColor("#F5F2EA"), QColor(SUIT_ON_WHITE[suit])
            border = QColor(C["gold"]) if self.active else QColor("#0B0D11")

        p.setBrush(face)
        bp = QPen(border)
        bp.setWidth(2 if self.active else 1)
        p.setPen(bp)
        p.drawRoundedRect(rect, radius, radius)

        p.setPen(ink)
        idx = QFont("Segoe UI", 9 if self.mini else 12, QFont.Weight.Bold)
        p.setFont(idx)
        p.drawText(QRectF(rect.left() + 4, rect.top() + 2, rect.width(), 18),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), rank)

        pip = QFont("Segoe UI", 18 if self.mini else 28, QFont.Weight.Bold)
        p.setFont(pip)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, sym)

        if not self.mini:  # drugi indeks (obrócony) jak na prawdziwej karcie
            p.save()
            p.translate(rect.right() - 4, rect.bottom() - 2)
            p.rotate(180)
            p.setFont(idx)
            p.drawText(QRectF(0, 0, 30, 18),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), rank)
            p.restore()
        p.end()


# ------------------------------- Pasek equity -------------------------------
class EquityBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(38)
        self.win = self.tie = self.lose = 0.0

    def set_values(self, win, tie, lose):
        self.win, self.tie, self.lose = win, tie, lose
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        p.setClipPath(path)
        p.fillRect(rect, QColor("#13161C"))

        total = self.win + self.tie + self.lose
        if total <= 0:
            p.setPen(QColor(C["muted"]))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "EQUITY —")
            p.end()
            return

        x = 0.0
        segs = [(self.win, QColor(C["green"]), "WIN"),
                (self.tie, QColor(C["gold"]), "TIE"),
                (self.lose, QColor(C["red"]), "LOSE")]
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        for val, col, name in segs:
            seg_w = self.width() * (val / total)
            seg = QRectF(x, 0, seg_w, self.height())
            p.fillRect(seg, col)
            if seg_w > 56:
                p.setPen(QColor("#0B0D11"))
                p.drawText(seg, Qt.AlignmentFlag.AlignCenter, f"{name} {val:.0f}%")
            x += seg_w
        p.end()


class SimulationWorker(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, hand, board, simulations=30000):
        super().__init__()
        self.hand = hand
        self.board = board
        self.simulator = MonteCarloSimulator(simulations=simulations)

    def run(self):
        try:
            result = self.simulator.run(self.hand, self.board)
            self.result_ready.emit(result)
        except Exception as e:  # noqa: BLE001 – błąd przekazywany do UI
            self.result_ready.emit({"error": str(e)})


QSS = f"""
QWidget {{
    background-color: {C['bg']};
    color: {C['text']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QGroupBox {{
    background-color: {C['panel']};
    border: 1px solid {C['border']};
    border-radius: 12px;
    margin-top: 16px;
    padding: 16px 14px 14px 14px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 2px 8px;
    color: {C['muted']};
    text-transform: uppercase;
    letter-spacing: 2px;
    font-size: 10px;
}}
QLabel {{ background: transparent; }}

QComboBox, QLineEdit {{
    background-color: {C['input']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {C['gold']};
    selection-color: #14110A;
}}
QComboBox:hover, QLineEdit:hover {{ border: 1px solid {C['border_lt']}; }}
QComboBox:focus, QLineEdit:focus {{ border: 1px solid {C['gold']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {C['panel_alt']};
    border: 1px solid {C['border']};
    selection-background-color: {C['gold_dk']};
    selection-color: #14110A;
    outline: none;
}}

QPushButton#btnPrimary {{
    background-color: {C['gold']};
    color: #14110A;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 700;
}}
QPushButton#btnPrimary:hover {{ background-color: {C['gold_dk']}; }}
QPushButton#btnGhost {{
    background-color: transparent;
    color: {C['text']};
    border: 1px solid {C['border_lt']};
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 600;
}}
QPushButton#btnGhost:hover {{ border: 1px solid {C['gold']}; color: {C['gold']}; }}
QPushButton#btnDanger {{
    background-color: transparent;
    color: {C['red']};
    border: 1px solid #46303A;
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 600;
}}
QPushButton#btnDanger:hover {{ background-color: #281A1E; border: 1px solid {C['red']}; }}

QPushButton#seg {{
    background-color: {C['panel_alt']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 9px 20px;
    font-weight: 700;
    color: {C['muted']};
    letter-spacing: 1px;
}}
QPushButton#seg:checked {{
    background-color: {C['gold']};
    color: #14110A;
    border: 1px solid {C['gold']};
}}

QPushButton#fav {{
    background-color: {C['panel_alt']};
    border: 1px solid {C['border_lt']};
    border-radius: 13px;
    padding: 5px 12px;
    color: {C['gold']};
    font-weight: 700;
}}
QPushButton#fav:hover {{ border: 1px solid {C['red']}; color: {C['red']}; }}

QTabWidget::pane {{ border: 1px solid {C['border']}; border-radius: 12px; top: -1px; }}
QTabBar::tab {{
    background: transparent;
    color: {C['muted']};
    padding: 10px 24px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QTabBar::tab:selected {{
    background: {C['panel']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-bottom: 2px solid {C['gold']};
}}

QTextEdit {{
    background-color: #0B0D12;
    border: 1px solid {C['border']};
    border-radius: 10px;
    font-family: 'Cascadia Code', Consolas, monospace;
    font-size: 13px;
}}
QScrollBar:vertical {{ background: {C['bg']}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #313845; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


class PokerAssistantGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poker Assistant — PRO")
        self.resize(1340, 880)
        self.setStyleSheet(QSS)

        self.hero = [None, None]
        self.board = [None, None, None, None, None]
        self.active = 0

        self.settings = load_settings()
        self.game_mode = self.settings.get("mode", "CASH")
        self.favorites = list(self.settings.get("favorite_stakes", []))
        self.sessions = list(self.settings.get("sessions", []))

        self.evaluator = HandEvaluator()
        self.pot_odds_calc = PotOddsCalculator()
        self.equity_calc = EquityCalculator()
        self.bankroll_mgr = BankrollManager()
        self.engine = DecisionEngine()

        self.worker = None
        self.analysis_data_cache = {}
        self.analyze_timer = QTimer()
        self.analyze_timer.setSingleShot(True)
        self.analyze_timer.timeout.connect(self.run_analysis_logic)

        self.card_faces = {}
        self.slot_faces = []
        self.fav_buttons = []

        self.init_ui()
        self.register_shortcuts()
        self.refresh_board()
        self.update_bankroll_view()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        root.addWidget(self.create_header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_analyzer_tab(), "  ANALIZATOR  ")
        self.tabs.addTab(self.create_bankroll_tab(), "  BANKROLL  ")
        root.addWidget(self.tabs)

    def create_header(self) -> QWidget:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(2, 0, 2, 0)
        v.setSpacing(8)

        row = QHBoxLayout()
        accent = QFrame()
        accent.setFixedSize(5, 26)
        accent.setStyleSheet(f"background-color: {C['gold']}; border-radius: 2px;")
        title = QLabel("POKER ASSISTANT")
        title.setStyleSheet(f"font-size: 19px; font-weight: 800; letter-spacing: 3px; color: {C['text']};")
        pro = QLabel("PRO")
        pro.setStyleSheet(
            f"color: {C['gold']}; font-weight: 800; font-size: 11px; letter-spacing: 2px; "
            f"border: 1px solid {C['gold_dk']}; border-radius: 4px; padding: 1px 6px;"
        )
        self.mode_badge = QLabel(self.game_mode)
        self.mode_badge.setStyleSheet(
            f"color: {C['muted']}; font-weight: 700; font-size: 11px; letter-spacing: 1px;"
        )
        row.addWidget(accent)
        row.addSpacing(8)
        row.addWidget(title)
        row.addSpacing(8)
        row.addWidget(pro)
        row.addStretch()
        row.addWidget(self.mode_badge)
        row.addSpacing(14)
        hint = QLabel("Backspace cofnij  ·  Delete reset board  ·  Esc wyczyść")
        hint.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")
        row.addWidget(hint)
        v.addLayout(row)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background-color: {C['border']};")
        v.addWidget(rule)
        return wrap

    # ---------------------------------------------------------- Analyzer tab
    def create_analyzer_tab(self) -> QWidget:
        tab = QWidget()
        main = QHBoxLayout(tab)
        main.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(self.create_top_controls())
        left.addWidget(self.create_board_view())
        left.addWidget(self.create_card_matrix())
        left.addWidget(self.create_pot_inputs())
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(self.create_dashboard_view())

        main.addLayout(left, 6)
        main.addLayout(right, 4)
        return tab

    def create_top_controls(self) -> QGroupBox:
        group = QGroupBox("Ustawienia stołu")
        layout = QHBoxLayout()

        self.cb_position = QComboBox()
        self.cb_position.addItems(["BTN", "CO", "MP", "UTG", "SB", "BB"])
        self.cb_position.setCurrentText(self.settings.get("position", "BTN"))
        self.cb_position.currentIndexChanged.connect(self.on_setting_changed)

        self.cb_players = QComboBox()
        self.cb_players.addItems([str(i) for i in range(9, 1, -1)])
        self.cb_players.setCurrentText(self.settings.get("players", "6"))
        self.cb_players.currentIndexChanged.connect(self.on_setting_changed)

        self.cb_sims = QComboBox()
        self.cb_sims.addItems(["10000", "30000", "50000", "100000"])
        self.cb_sims.setCurrentText(self.settings.get("sims", "30000"))
        self.cb_sims.currentIndexChanged.connect(self.on_sims_changed)

        self.lbl_warning = QLabel("")
        self.lbl_warning.setStyleSheet(f"color: {C['gold']}; font-weight: bold;")

        layout.addWidget(self._field("Pozycja", self.cb_position))
        layout.addWidget(self._field("Gracze", self.cb_players))
        layout.addWidget(self._field("Symulacje", self.cb_sims))
        layout.addWidget(self.lbl_warning)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def _field(self, label: str, widget: QWidget) -> QWidget:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        cap = QLabel(label.upper())
        cap.setStyleSheet(f"color: {C['muted']}; font-size: 10px; letter-spacing: 1px;")
        v.addWidget(cap)
        v.addWidget(widget)
        return box

    def create_board_view(self) -> QGroupBox:
        group = QGroupBox("Twoja ręka i stół")
        outer = QVBoxLayout()

        row = QHBoxLayout()
        row.setSpacing(8)

        hero_box = QVBoxLayout()
        hero_cap = QLabel("HERO")
        hero_cap.setStyleSheet(f"color: {C['gold']}; font-weight: 800; font-size: 10px; letter-spacing: 2px;")
        hero_box.addWidget(hero_cap)
        hero_cards = QHBoxLayout()
        hero_cards.setSpacing(8)
        for i in range(2):
            hero_cards.addWidget(self._make_slot(i))
        hero_cards.addStretch()
        hero_box.addLayout(hero_cards)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {C['border']};")

        board_box = QVBoxLayout()
        board_cap = QLabel("BOARD")
        board_cap.setStyleSheet(f"color: {C['muted']}; font-weight: 800; font-size: 10px; letter-spacing: 2px;")
        board_box.addWidget(board_cap)
        board_cards = QHBoxLayout()
        board_cards.setSpacing(8)
        for i in range(2, 7):
            board_cards.addWidget(self._make_slot(i))
        board_cards.addStretch()
        board_box.addLayout(board_cards)

        row.addLayout(hero_box)
        row.addSpacing(10)
        row.addWidget(sep)
        row.addSpacing(10)
        row.addLayout(board_box, 1)
        outer.addLayout(row)

        actions = QHBoxLayout()
        nxt_cap = QLabel("NASTĘPNA")
        nxt_cap.setStyleSheet(f"color: {C['muted']}; font-size: 10px; letter-spacing: 1px;")
        self.lbl_next = QLabel("")
        self.lbl_next.setStyleSheet(f"color: {C['gold']}; font-weight: 700;")
        actions.addWidget(nxt_cap)
        actions.addSpacing(6)
        actions.addWidget(self.lbl_next)
        actions.addStretch()

        btn_undo = QPushButton("Cofnij kartę")
        btn_undo.setObjectName("btnGhost")
        btn_undo.clicked.connect(self.undo_last)
        btn_reset = QPushButton("Reset Board")
        btn_reset.setObjectName("btnGhost")
        btn_reset.clicked.connect(self.reset_board)
        btn_clear = QPushButton("Wyczyść wszystko")
        btn_clear.setObjectName("btnDanger")
        btn_clear.clicked.connect(self.clear_all)
        for b in (btn_undo, btn_reset, btn_clear):
            actions.addWidget(b)

        outer.addSpacing(8)
        outer.addLayout(actions)
        group.setLayout(outer)
        return group

    def _make_slot(self, idx: int) -> CardFace:
        face = CardFace(66, 92, placeholder=SLOT_LABELS[idx])
        face.clicked.connect(lambda i=idx: self.on_slot_clicked(i))
        self.slot_faces.append(face)
        return face

    def create_card_matrix(self) -> QGroupBox:
        group = QGroupBox("Wybór kart — kliknij, by dodać do aktywnego slotu")
        grid = QGridLayout()
        grid.setSpacing(5)

        display_ranks = list(reversed(RANKS))  # A K Q J T 9 ... 2
        for col, rank in enumerate(display_ranks, start=1):
            head = QLabel("10" if rank == "T" else rank)
            head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            head.setStyleSheet(f"color: {C['muted']}; font-weight: 700; font-size: 11px;")
            grid.addWidget(head, 0, col)

        for r, suit in enumerate(["s", "h", "d", "c"], start=1):
            sym = QLabel(SUIT_SYMBOLS[suit])
            sym.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sym.setStyleSheet(f"color: {SUIT_ON_WHITE[suit]}; font-size: 17px; font-weight: 700;")
            grid.addWidget(sym, r, 0)
            for col, rank in enumerate(display_ranks, start=1):
                card = f"{rank}{suit}"
                face = CardFace(48, 64, mini=True, fixed_card=card)
                face.clicked.connect(lambda c=card: self.on_chip_clicked(c))
                grid.addWidget(face, r, col)
                self.card_faces[card] = face

        group.setLayout(grid)
        return group

    def create_pot_inputs(self) -> QGroupBox:
        group = QGroupBox("Pula i pot odds")
        layout = QGridLayout()

        self.in_pot = QLineEdit("100")
        self.in_call = QLineEdit("0")
        self.in_stack = QLineEdit("200")
        for field in (self.in_pot, self.in_call, self.in_stack):
            field.textChanged.connect(self.trigger_analysis)

        layout.addWidget(self._field("Wielkość puli ($)", self.in_pot), 0, 0)
        layout.addWidget(self._field("Do dorównania ($)", self.in_call), 0, 1)
        layout.addWidget(self._field("Efektywny stack ($)", self.in_stack), 0, 2)
        group.setLayout(layout)
        return group

    def create_dashboard_view(self) -> QGroupBox:
        group = QGroupBox("Analiza i rekomendacja")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.action_banner = QLabel("CZEKAM NA KARTY")
        self.action_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._style_banner("muted", "CZEKAM NA KARTY", "")
        layout.addWidget(self.action_banner)

        self.equity_bar = EquityBar()
        layout.addWidget(self.equity_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            f"background-color: #0B0D12; color: {C['text']}; "
            "font-family: 'Cascadia Code', Consolas, monospace; font-size: 13px;"
        )
        layout.addWidget(self.log_area)
        group.setLayout(layout)
        return group

    def _style_banner(self, kind: str, action: str, sub: str):
        colors = {"green": C["green"], "gold": C["gold"], "red": C["red"], "muted": C["muted"]}
        col = colors.get(kind, C["muted"])
        text = action if not sub else f"{action}   ·   {sub}"
        self.action_banner.setText(text)
        self.action_banner.setStyleSheet(
            f"color: {col}; background-color: {C['panel_alt']}; "
            f"border: 1px solid {col}; border-radius: 10px; padding: 12px; "
            f"font-size: 18px; font-weight: 800; letter-spacing: 1px;"
        )

    # ---------------------------------------------------------- Bankroll tab
    def create_bankroll_tab(self) -> QWidget:
        tab = QWidget()
        main = QHBoxLayout(tab)
        main.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(self.create_bankroll_input())
        left.addWidget(self.create_session_entry())
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(self.create_suggestion_panel())
        right.addWidget(self.create_history_panel())
        right.addStretch()

        main.addLayout(left, 5)
        main.addLayout(right, 5)
        return tab

    def create_bankroll_input(self) -> QGroupBox:
        group = QGroupBox("Kapitał i tryb gry")
        layout = QVBoxLayout()

        seg_row = QHBoxLayout()
        self.btn_cash = QPushButton("CASH")
        self.btn_mtt = QPushButton("MTT")
        self.mode_group = QButtonGroup(self)
        for btn, mode in ((self.btn_cash, "CASH"), (self.btn_mtt, "MTT")):
            btn.setObjectName("seg")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self.set_mode(m))
            self.mode_group.addButton(btn)
            seg_row.addWidget(btn)
        seg_row.addStretch()
        (self.btn_mtt if self.game_mode == "MTT" else self.btn_cash).setChecked(True)
        layout.addLayout(seg_row)

        cap = QLabel("AKTUALNY BANKROLL ($)")
        cap.setStyleSheet(f"color: {C['muted']}; font-size: 10px; letter-spacing: 1px;")
        self.in_bankroll = QLineEdit(self._fmt(self.settings.get("bankroll", 1000.0)))
        self.in_bankroll.setStyleSheet(
            f"background-color: {C['input']}; border: 1px solid {C['border']}; "
            f"border-radius: 10px; padding: 12px 14px; font-size: 26px; font-weight: 800; "
            f"color: {C['gold']};"
        )
        self.in_bankroll.textChanged.connect(self.on_bankroll_changed)
        self.in_bankroll.editingFinished.connect(self.persist)

        layout.addSpacing(8)
        layout.addWidget(cap)
        layout.addWidget(self.in_bankroll)
        group.setLayout(layout)
        return group

    def create_session_entry(self) -> QGroupBox:
        group = QGroupBox("Szybki wpis sesji")
        layout = QVBoxLayout()

        row = QHBoxLayout()
        self.in_buyin = QLineEdit("")
        self.in_buyin.setPlaceholderText("np. 10")
        self.in_result = QLineEdit("")
        self.in_result.setPlaceholderText("np. +25  /  -15")
        self.in_result.returnPressed.connect(self.save_session)
        row.addWidget(self._field("Buy-in ($)", self.in_buyin))
        row.addWidget(self._field("Wynik sesji (+/−)", self.in_result))
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        btn_win = QPushButton("Wygrana")
        btn_win.setObjectName("btnPrimary")
        btn_win.clicked.connect(lambda: self.quick_result(positive=True))
        btn_loss = QPushButton("Przegrana")
        btn_loss.setObjectName("btnDanger")
        btn_loss.clicked.connect(lambda: self.quick_result(positive=False))
        btn_save = QPushButton("Zapisz")
        btn_save.setObjectName("btnGhost")
        btn_save.clicked.connect(self.save_session)
        btn_undo = QPushButton("Cofnij sesję")
        btn_undo.setObjectName("btnGhost")
        btn_undo.clicked.connect(self.undo_session)
        for b in (btn_win, btn_loss, btn_save, btn_undo):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        group.setLayout(layout)
        return group

    def create_suggestion_panel(self) -> QGroupBox:
        group = QGroupBox("Rekomendowana stawka")
        layout = QVBoxLayout()

        self.lbl_headline = QLabel("—")
        self.lbl_headline.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {C['gold']};")
        self.lbl_rule = QLabel("")
        self.lbl_rule.setStyleSheet(f"color: {C['muted']}; font-size: 12px;")
        layout.addWidget(self.lbl_headline)
        layout.addWidget(self.lbl_rule)
        layout.addSpacing(8)

        tiers = QHBoxLayout()
        self.lbl_aggro = self._tier_card("Agresywnie", C["red"])
        self.lbl_standard = self._tier_card("Standard", C["green"])
        self.lbl_nit = self._tier_card("Ostrożnie", C["gold"])
        for w in (self.lbl_aggro, self.lbl_standard, self.lbl_nit):
            tiers.addWidget(w["box"])
        layout.addLayout(tiers)

        self.lbl_next_target = QLabel("")
        self.lbl_next_target.setStyleSheet(f"color: {C['muted']}; font-size: 12px;")
        layout.addSpacing(6)
        layout.addWidget(self.lbl_next_target)

        fav_cap = QLabel("ULUBIONE STAWKI")
        fav_cap.setStyleSheet(f"color: {C['muted']}; font-size: 10px; letter-spacing: 1px;")
        layout.addSpacing(10)
        layout.addWidget(fav_cap)
        self.fav_row = QHBoxLayout()
        self.fav_row.setSpacing(6)
        btn_add_fav = QPushButton("Dodaj do ulubionych")
        btn_add_fav.setObjectName("btnGhost")
        btn_add_fav.clicked.connect(self.add_favorite)
        self.fav_row.addWidget(btn_add_fav)
        self.fav_row.addStretch()
        layout.addLayout(self.fav_row)
        self.render_favorites()

        group.setLayout(layout)
        return group

    def _tier_card(self, title: str, color: str) -> dict:
        box = QFrame()
        box.setStyleSheet(
            f"background-color: {C['panel_alt']}; border: 1px solid {C['border']}; border-radius: 10px;"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(12, 10, 12, 10)
        cap = QLabel(title.upper())
        cap.setStyleSheet(f"color: {C['muted']}; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        val = QLabel("—")
        val.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 800;")
        v.addWidget(cap)
        v.addWidget(val)
        return {"box": box, "val": val}

    def create_history_panel(self) -> QGroupBox:
        group = QGroupBox("Historia sesji")
        layout = QVBoxLayout()
        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(self.lbl_stats)
        self.history_area = QTextEdit()
        self.history_area.setReadOnly(True)
        self.history_area.setFixedHeight(190)
        layout.addWidget(self.history_area)
        group.setLayout(layout)
        self.render_history()
        return group

    # ------------------------------------------------------------ Skróty
    def register_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self, self.undo_last)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self.reset_board)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.clear_all)

    # ----------------------------------------------------- Logika slotów
    def _card_at(self, idx: int):
        return self.hero[idx] if idx < 2 else self.board[idx - 2]

    def _set_card_at(self, idx: int, val):
        if idx < 2:
            self.hero[idx] = val
        else:
            self.board[idx - 2] = val

    def used_cards(self) -> set:
        return {c for c in (self.hero + self.board) if c}

    def _next_empty(self, start: int = 0):
        for i in range(start, 7):
            if self._card_at(i) is None:
                return i
        return None

    def on_chip_clicked(self, card: str):
        if card in self.used_cards():
            return
        idx = self.active
        if idx is None or idx >= 7 or self._card_at(idx) is not None:
            idx = self._next_empty()
        if idx is None:
            return
        self._set_card_at(idx, card)
        nxt = self._next_empty(idx + 1)
        self.active = nxt if nxt is not None else (self._next_empty() or 0)
        self.refresh_board()
        self.trigger_analysis()

    def on_slot_clicked(self, idx: int):
        if self._card_at(idx) is not None:
            self._set_card_at(idx, None)
        self.active = idx
        self.refresh_board()
        self.trigger_analysis()

    def undo_last(self):
        last = None
        for i in range(7):
            if self._card_at(i) is not None:
                last = i
        if last is not None:
            self._set_card_at(last, None)
            self.active = last
            self.refresh_board()
            self.trigger_analysis()

    def reset_board(self):
        self.board = [None, None, None, None, None]
        self.active = self._next_empty() if self._next_empty() is not None else 2
        self.refresh_board()
        self.trigger_analysis()

    def clear_all(self):
        self.hero = [None, None]
        self.board = [None, None, None, None, None]
        self.active = 0
        self.log_area.clear()
        self.equity_bar.set_values(0, 0, 0)
        self._style_banner("muted", "CZEKAM NA KARTY", "")
        self.refresh_board()

    def refresh_board(self):
        used = self.used_cards()
        for card, face in self.card_faces.items():
            is_used = card in used
            face.update_state(used=is_used)
            face.setEnabled(not is_used)
        for i, face in enumerate(self.slot_faces):
            face.update_state(card=self._card_at(i), active=(i == self.active))
        if self.active is None or self.active >= 7:
            self.lbl_next.setText("komplet kart")
        else:
            self.lbl_next.setText(SLOT_LABELS[self.active])

    # ----------------------------------------------------- Analiza (pipeline)
    def safe_float(self, text: str) -> float:
        try:
            val = float(text.strip().replace(",", "."))
            return val if val >= 0 else 0.0
        except (ValueError, AttributeError):
            return 0.0

    def on_sims_changed(self):
        sims = int(self.cb_sims.currentText())
        self.lbl_warning.setText("⚠ Duża liczba symulacji — może chwilę potrwać" if sims >= 50000 else "")
        self.on_setting_changed()

    def on_setting_changed(self):
        self.persist()
        self.trigger_analysis()

    def trigger_analysis(self):
        self.analyze_timer.start(450)

    def run_analysis_logic(self):
        hero_list = [c for c in self.hero if c]
        board_list = [c for c in self.board if c]

        if len(hero_list) < 2:
            self.log_area.clear()
            self.equity_bar.set_values(0, 0, 0)
            self._style_banner("muted", "CZEKAM NA KARTY", "Wybierz 2 karty HERO")
            self.log("Wybierz 2 karty HERO, aby rozpocząć analizę.")
            return

        if len(board_list) in (1, 2):
            self.log_area.clear()
            self._style_banner("muted", "FLOP NIEKOMPLETNY", f"{len(board_list)}/3 kart")
            self.log(f"Wybrano {len(board_list)}/3 kart flopa. Uzupełnij flop...")
            return

        self.log_area.clear()
        phase = determine_street(board_list)
        self.log(f"━━━  FAZA: {phase}  ━━━\n")

        preflop_str = "UNKNOWN"
        if phase == "PREFLOP":
            strength, _action = self.evaluator.evaluate_preflop(hero_list)
            preflop_str = strength
            self.log(f"Siła ręki:  {strength}")
        else:
            current_hand, pct = self.evaluator.evaluate_postflop(hero_list, board_list)
            self.log(f"Układ:  {current_hand}  (siła wzgl.: {pct}%)")
            draw_data = self.equity_calc.calculate_draws(hero_list, board_list)
            if draw_data["outs"] > 0:
                self.log(f"Outy:  {draw_data['outs']}   ·   Szansa trafienia: {draw_data['hit_chance']}%")
                self.log(f"Dobierane:  {', '.join(draw_data['draw_types'])}")

        pot = self.safe_float(self.in_pot.text())
        call_amt = self.safe_float(self.in_call.text())
        stack = self.safe_float(self.in_stack.text())
        br = self.get_bankroll()

        odds_data = self.pot_odds_calc.calculate(pot, call_amt)
        self.log(f"\nPot odds:  1 : {odds_data['pot_odds_ratio']}   (wymagane equity: {odds_data['req_equity']}%)")

        br_data = self.bankroll_mgr.analyze(br, pot, stack)
        self.log(f"Ryzyko bankrolla:  {br_data['risk_level']}  ({br_data['engaged_pct']}% zaangażowane)")

        sims = int(self.cb_sims.currentText())
        self._style_banner("gold", "LICZĘ...", f"{sims:,} symulacji")
        self.log(f"\nUruchamiam {sims:,} symulacji Monte Carlo...")

        self.analysis_data_cache = {
            "phase": phase,
            "preflop_strength": preflop_str,
            "req_equity": odds_data["req_equity"],
            "position": self.cb_position.currentText(),
            "players": int(self.cb_players.currentText()),
        }

        if self.worker is not None and self.worker.isRunning():
            try:
                self.worker.result_ready.disconnect()
            except TypeError:
                pass

        self.worker = SimulationWorker(hero_list.copy(), board_list.copy(), simulations=sims)
        self.worker.result_ready.connect(self.on_simulation_complete)
        self.worker.start()

    def on_simulation_complete(self, mc_results: dict):
        if "error" in mc_results:
            self._style_banner("red", "BŁĄD SYMULACJI", "")
            self.log(f"\n[!] BŁĄD SYMULACJI: {mc_results['error']}")
            return

        win, tie, lose = mc_results["win"], mc_results["tie"], mc_results["lose"]
        self.equity_bar.set_values(win, tie, lose)
        self.log(f"\nMonte Carlo:  Win {win}%  ·  Tie {tie}%  ·  Lose {lose}%")

        self.analysis_data_cache["equity"] = win
        decision = self.engine.get_recommendation(self.analysis_data_cache)
        action = decision.get("action", "—")
        conf = decision.get("confidence", 0.0)

        self._style_banner(self._action_kind(action), action, f"pewność {conf:.0f}%")
        self.log("\n──  REKOMENDACJA  ──")
        self.log(f"   Akcja:    {action}")
        self.log(f"   Pewność:  {conf}%")
        for reason in decision.get("reason", []):
            self.log(f"   • {reason}")

    @staticmethod
    def _action_kind(action: str) -> str:
        a = action.upper()
        if "FOLD" in a:
            return "red"
        if "CALL" in a:
            return "gold"
        if any(k in a for k in ("RAISE", "BET", "ALL-IN", "3-BET", "VALUE")):
            return "green"
        return "muted"

    def log(self, text: str):
        self.log_area.append(text)

    # --------------------------------------------------------- Bankroll logika
    def _fmt(self, value: float) -> str:
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def get_bankroll(self) -> float:
        return self.safe_float(self.in_bankroll.text())

    def set_mode(self, mode: str):
        self.game_mode = mode
        self.mode_badge.setText(mode)
        self.update_bankroll_view()
        self.persist()

    def on_bankroll_changed(self):
        self.update_bankroll_view()
        self.trigger_analysis()

    def update_bankroll_view(self):
        data = self.bankroll_mgr.suggest(self.get_bankroll(), self.game_mode)
        self.lbl_headline.setText(data["headline"])
        self.lbl_headline.setStyleSheet(
            f"font-size: 30px; font-weight: 800; "
            f"color: {C['gold'] if data['ok'] else C['red']};"
        )
        self.lbl_rule.setText("Zasada: " + data["rule"])
        self.lbl_aggro["val"].setText(data["aggressive"])
        self.lbl_standard["val"].setText(data["standard"])
        self.lbl_nit["val"].setText(data["conservative"])
        self.lbl_next_target.setText(data["next_target"])

    def quick_result(self, positive: bool):
        amount = self.safe_float(self.in_result.text())
        if amount == 0:
            return
        self._commit_session(amount if positive else -amount)

    def save_session(self):
        text = self.in_result.text().strip().replace(",", ".")
        try:
            amount = float(text)
        except ValueError:
            return
        self._commit_session(amount)

    def _commit_session(self, amount: float):
        new_balance = self.get_bankroll() + amount
        self.in_bankroll.setText(self._fmt(new_balance))
        self.sessions.append({
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "result": round(amount, 2),
            "mode": self.game_mode,
            "buyin": self.safe_float(self.in_buyin.text()),
        })
        self.in_result.clear()
        self.update_bankroll_view()
        self.render_history()
        self.persist()

    def undo_session(self):
        if not self.sessions:
            return
        last = self.sessions.pop()
        self.in_bankroll.setText(self._fmt(self.get_bankroll() - last["result"]))
        self.update_bankroll_view()
        self.render_history()
        self.persist()

    def render_history(self):
        total = sum(s["result"] for s in self.sessions)
        count = len(self.sessions)
        color = C["green"] if total >= 0 else C["red"]
        sign = "+" if total >= 0 else ""
        self.lbl_stats.setText(
            f"<span style='color:{C['muted']}'>Sesji: {count}   ·   Bilans: </span>"
            f"<span style='color:{color}'>{sign}{total:.2f} $</span>"
        )
        lines = []
        for s in reversed(self.sessions[-12:]):
            r = s["result"]
            col = C["green"] if r >= 0 else C["red"]
            sign = "+" if r >= 0 else ""
            lines.append(
                f"<span style='color:{C['muted']}'>{s['ts']}  [{s.get('mode','')}]</span>  "
                f"<span style='color:{col}; font-weight:700'>{sign}{r:.2f} $</span>"
            )
        self.history_area.setHtml("<br>".join(lines) if lines else
                                  f"<span style='color:{C['muted']}'>Brak zapisanych sesji.</span>")

    # --------------------------------------------------------- Faworyci
    def add_favorite(self):
        data = self.bankroll_mgr.suggest(self.get_bankroll(), self.game_mode)
        pick = data["standard"]
        if not pick or pick == "—":
            return
        label = pick if self.game_mode == "CASH" else f"MTT {pick}"
        if label not in self.favorites and len(self.favorites) < 6:
            self.favorites.append(label)
            self.render_favorites()
            self.persist()

    def remove_favorite(self, label: str):
        if label in self.favorites:
            self.favorites.remove(label)
            self.render_favorites()
            self.persist()

    def render_favorites(self):
        for btn in self.fav_buttons:
            self.fav_row.removeWidget(btn)
            btn.deleteLater()
        self.fav_buttons.clear()
        for label in self.favorites:
            btn = QPushButton(label)
            btn.setObjectName("fav")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip("Kliknij, aby usunąć z ulubionych")
            btn.clicked.connect(lambda _, l=label: self.remove_favorite(l))
            self.fav_row.insertWidget(self.fav_row.count() - 1, btn)
            self.fav_buttons.append(btn)

    # --------------------------------------------------------- Trwałość
    def persist(self):
        self.settings.update({
            "bankroll": self.get_bankroll(),
            "mode": self.game_mode,
            "position": self.cb_position.currentText(),
            "players": self.cb_players.currentText(),
            "sims": self.cb_sims.currentText(),
            "favorite_stakes": self.favorites,
            "sessions": self.sessions,
        })
        save_settings(self.settings)
