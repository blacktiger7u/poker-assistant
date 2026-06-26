from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QGroupBox, QLineEdit, QTextEdit, QComboBox, QTabWidget, QFrame, QButtonGroup
)
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer

from core.utils import RANKS, determine_street
from core.hand_evaluator import HandEvaluator
from core.monte_carlo import MonteCarloSimulator
from core.pot_odds import PotOddsCalculator
from core.equity_calculator import EquityCalculator
from core.bankroll_manager import BankrollManager
from core.decision_engine import DecisionEngine
from core.settings_store import load_settings, save_settings


# ============================ MOTYW (PREMIUM DARK) ============================
COLORS = {
    "bg": "#0E1014",
    "panel": "#171A21",
    "panel_alt": "#1E222B",
    "input": "#202531",
    "border": "#2A2F3A",
    "text": "#E6E9EF",
    "muted": "#8B94A5",
    "accent": "#2EE6A6",     # szmaragd – akcent główny
    "accent_dk": "#1FB888",
    "gold": "#E8B23A",       # premium / nagłówki
    "danger": "#FF5C6C",
}

# 4-kolorowa talia (czytelność na ciemnym tle)
SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
SUIT_COLORS = {
    "s": "#E8EAF0",  # pik   – jasny (zamiast czarnego, widoczny na ciemnym tle)
    "h": "#FF5C6C",  # kier  – czerwony
    "d": "#4DA3FF",  # karo  – niebieski
    "c": "#3FD07F",  # trefl – zielony
}

# Kolejność slotów: 2x Hero + 5x Board
SLOT_LABELS = ["HERO 1", "HERO 2", "FLOP", "FLOP", "FLOP", "TURN", "RIVER"]

QSS = f"""
QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QGroupBox {{
    background-color: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 2px 8px;
    color: {COLORS['muted']};
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 11px;
}}
QLabel {{ background: transparent; }}

QComboBox, QLineEdit {{
    background-color: {COLORS['input']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {COLORS['accent']};
}}
QComboBox:hover, QLineEdit:hover {{ border: 1px solid #3A4150; }}
QComboBox:focus, QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent_dk']};
    outline: none;
}}

/* --- Karty w matrycy --- */
QPushButton#cardChip {{
    background-color: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    font-size: 18px;
    font-weight: 700;
    padding: 0px;
}}
QPushButton#cardChip:hover {{
    background-color: #2A303D;
    border: 1px solid {COLORS['accent']};
}}
QPushButton#cardChip:disabled {{
    background-color: #12151B;
    border: 1px solid #1B1F27;
    color: #353A45;
}}
QPushButton#cardChip[suit="s"] {{ color: {SUIT_COLORS['s']}; }}
QPushButton#cardChip[suit="h"] {{ color: {SUIT_COLORS['h']}; }}
QPushButton#cardChip[suit="d"] {{ color: {SUIT_COLORS['d']}; }}
QPushButton#cardChip[suit="c"] {{ color: {SUIT_COLORS['c']}; }}

/* --- Przyciski akcji --- */
QPushButton#btnPrimary {{
    background-color: {COLORS['accent']};
    color: #06231A;
    border: none;
    border-radius: 9px;
    padding: 10px 16px;
    font-weight: 700;
}}
QPushButton#btnPrimary:hover {{ background-color: {COLORS['accent_dk']}; }}
QPushButton#btnGhost {{
    background-color: transparent;
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
    padding: 9px 14px;
    font-weight: 600;
}}
QPushButton#btnGhost:hover {{ border: 1px solid {COLORS['accent']}; color: {COLORS['accent']}; }}
QPushButton#btnDanger {{
    background-color: transparent;
    color: {COLORS['danger']};
    border: 1px solid #4A2A30;
    border-radius: 9px;
    padding: 9px 14px;
    font-weight: 600;
}}
QPushButton#btnDanger:hover {{ background-color: #2A1A1D; border: 1px solid {COLORS['danger']}; }}

/* --- Przełącznik segmentowy Cash/MTT --- */
QPushButton#seg {{
    background-color: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
    padding: 9px 18px;
    font-weight: 700;
    color: {COLORS['muted']};
}}
QPushButton#seg:checked {{
    background-color: {COLORS['accent']};
    color: #06231A;
    border: 1px solid {COLORS['accent']};
}}

/* --- Faworyty (chipy stawek) --- */
QPushButton#fav {{
    background-color: {COLORS['panel_alt']};
    border: 1px solid #3A4150;
    border-radius: 14px;
    padding: 5px 12px;
    color: {COLORS['gold']};
    font-weight: 700;
}}
QPushButton#fav:hover {{ border: 1px solid {COLORS['danger']}; color: {COLORS['danger']}; }}

QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {COLORS['muted']};
    padding: 10px 22px;
    margin-right: 4px;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {COLORS['panel']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-bottom: 2px solid {COLORS['accent']};
}}

QTextEdit {{
    background-color: #0A0C10;
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    font-family: 'Cascadia Code', Consolas, monospace;
    font-size: 14px;
}}
QScrollBar:vertical {{ background: {COLORS['bg']}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #313845; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


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


class PokerAssistantGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poker Assistant — PRO")
        self.resize(1320, 860)
        self.setStyleSheet(QSS)

        # Stan kart: stałe sloty (None = pusty), aktywny slot = miejsce kolejnej karty
        self.hero = [None, None]
        self.board = [None, None, None, None, None]
        self.active = 0

        # Ustawienia trwałe
        self.settings = load_settings()
        self.game_mode = self.settings.get("mode", "CASH")
        self.favorites = list(self.settings.get("favorite_stakes", []))
        self.sessions = list(self.settings.get("sessions", []))

        # Moduły logiki
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

        self.card_chips = {}
        self.slot_buttons = []
        self.fav_buttons = []

        self.init_ui()
        self.register_shortcuts()
        self.refresh_board()
        self.update_bankroll_view()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.addWidget(self.create_header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_analyzer_tab(), "  Analizator  ")
        self.tabs.addTab(self.create_bankroll_tab(), "  Bankroll  ")
        root.addWidget(self.tabs)

    def create_header(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(4, 0, 4, 0)

        title = QLabel("♠ POKER ASSISTANT")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {COLORS['text']}; letter-spacing: 1px;"
        )
        sub = QLabel("PRO Analytics Engine")
        sub.setStyleSheet(f"color: {COLORS['gold']}; font-weight: 700; font-size: 12px;")

        lay.addWidget(title)
        lay.addSpacing(10)
        lay.addWidget(sub)
        lay.addStretch()

        hint = QLabel("Skróty:  Backspace = cofnij  ·  Delete = wyczyść board  ·  Esc = wyczyść wszystko")
        hint.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px;")
        lay.addWidget(hint)
        return bar

    # ---------------------------------------------------------- Analyzer tab
    def create_analyzer_tab(self) -> QWidget:
        tab = QWidget()
        main = QHBoxLayout(tab)

        left = QVBoxLayout()
        left.addWidget(self.create_top_controls())
        left.addWidget(self.create_board_view())
        left.addWidget(self.create_card_matrix())
        left.addWidget(self.create_pot_inputs())
        left.addStretch()

        right = QVBoxLayout()
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
        self.lbl_warning.setStyleSheet(f"color: {COLORS['gold']}; font-weight: bold;")

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
        cap = QLabel(label)
        cap.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px;")
        v.addWidget(cap)
        v.addWidget(widget)
        return box

    def create_board_view(self) -> QGroupBox:
        group = QGroupBox("Twoja ręka i stół")
        outer = QVBoxLayout()

        row = QHBoxLayout()

        hero_box = QVBoxLayout()
        hero_cap = QLabel("HERO")
        hero_cap.setStyleSheet(f"color: {COLORS['accent']}; font-weight: 700; font-size: 11px;")
        hero_box.addWidget(hero_cap)
        hero_cards = QHBoxLayout()
        for i in range(2):
            hero_cards.addWidget(self._make_slot(i))
        hero_box.addLayout(hero_cards)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")

        board_box = QVBoxLayout()
        board_cap = QLabel("BOARD")
        board_cap.setStyleSheet(f"color: {COLORS['muted']}; font-weight: 700; font-size: 11px;")
        board_box.addWidget(board_cap)
        board_cards = QHBoxLayout()
        for i in range(2, 7):
            board_cards.addWidget(self._make_slot(i))
        board_box.addLayout(board_cards)

        row.addLayout(hero_box)
        row.addSpacing(14)
        row.addWidget(sep)
        row.addSpacing(14)
        row.addLayout(board_box)
        row.addStretch()
        outer.addLayout(row)

        # Pasek statusu + szybkie akcje
        actions = QHBoxLayout()
        self.lbl_next = QLabel("")
        self.lbl_next.setStyleSheet(f"color: {COLORS['accent']}; font-weight: 700;")
        actions.addWidget(self.lbl_next)
        actions.addStretch()

        btn_undo = QPushButton("⌫  Cofnij kartę")
        btn_undo.setObjectName("btnGhost")
        btn_undo.clicked.connect(self.undo_last)

        btn_reset = QPushButton("↺  Reset Board")
        btn_reset.setObjectName("btnGhost")
        btn_reset.clicked.connect(self.reset_board)

        btn_clear = QPushButton("Wyczyść wszystko")
        btn_clear.setObjectName("btnDanger")
        btn_clear.clicked.connect(self.clear_all)

        actions.addWidget(btn_undo)
        actions.addWidget(btn_reset)
        actions.addWidget(btn_clear)
        outer.addSpacing(8)
        outer.addLayout(actions)

        group.setLayout(outer)
        return group

    def _make_slot(self, idx: int) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(70, 96)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, i=idx: self.on_slot_clicked(i))
        self.slot_buttons.append(btn)
        return btn

    def create_card_matrix(self) -> QGroupBox:
        group = QGroupBox("Wybór kart — kliknij, by dodać do aktywnego slotu")
        grid = QGridLayout()
        grid.setSpacing(5)

        display_ranks = list(reversed(RANKS))  # A K Q J T 9 ... 2

        # Nagłówek z rangami
        for col, rank in enumerate(display_ranks, start=1):
            head = QLabel(rank)
            head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            head.setStyleSheet(f"color: {COLORS['muted']}; font-weight: 700;")
            grid.addWidget(head, 0, col)

        # Wiersze kolorów
        suit_order = ["s", "h", "d", "c"]
        for r, suit in enumerate(suit_order, start=1):
            sym = QLabel(SUIT_SYMBOLS[suit])
            sym.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sym.setStyleSheet(f"color: {SUIT_COLORS[suit]}; font-size: 18px; font-weight: 700;")
            grid.addWidget(sym, r, 0)

            for col, rank in enumerate(display_ranks, start=1):
                card = f"{rank}{suit}"
                chip = QPushButton(f"{rank}{SUIT_SYMBOLS[suit]}")
                chip.setObjectName("cardChip")
                chip.setProperty("suit", suit)
                chip.setFixedSize(54, 46)
                chip.setCursor(Qt.CursorShape.PointingHandCursor)
                chip.clicked.connect(lambda _, c=card: self.on_chip_clicked(c))
                grid.addWidget(chip, r, col)
                self.card_chips[card] = chip

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

        layout.addWidget(QLabel("Wielkość puli ($)"), 0, 0)
        layout.addWidget(self.in_pot, 0, 1)
        layout.addWidget(QLabel("Do dorównania ($)"), 0, 2)
        layout.addWidget(self.in_call, 0, 3)
        layout.addWidget(QLabel("Efektywny stack ($)"), 0, 4)
        layout.addWidget(self.in_stack, 0, 5)

        group.setLayout(layout)
        return group

    def create_dashboard_view(self) -> QGroupBox:
        group = QGroupBox("Analiza i rekomendacja")
        layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            f"background-color: #0A0C10; color: {COLORS['text']}; "
            "font-family: 'Cascadia Code', Consolas, monospace; font-size: 14px;"
        )
        layout.addWidget(self.log_area)
        group.setLayout(layout)
        return group

    # ---------------------------------------------------------- Bankroll tab
    def create_bankroll_tab(self) -> QWidget:
        tab = QWidget()
        main = QHBoxLayout(tab)

        left = QVBoxLayout()
        left.addWidget(self.create_bankroll_input())
        left.addWidget(self.create_session_entry())
        left.addStretch()

        right = QVBoxLayout()
        right.addWidget(self.create_suggestion_panel())
        right.addWidget(self.create_history_panel())
        right.addStretch()

        main.addLayout(left, 5)
        main.addLayout(right, 5)
        return tab

    def create_bankroll_input(self) -> QGroupBox:
        group = QGroupBox("Kapitał i tryb gry")
        layout = QVBoxLayout()

        # Segment Cash / MTT
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

        # Pole bankrolla (duże)
        cap = QLabel("Aktualny bankroll ($)")
        cap.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        self.in_bankroll = QLineEdit(self._fmt(self.settings.get("bankroll", 1000.0)))
        self.in_bankroll.setStyleSheet(
            f"background-color: {COLORS['input']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 10px; padding: 12px 14px; font-size: 26px; font-weight: 800; "
            f"color: {COLORS['accent']};"
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
        self.in_buyin.setPlaceholderText("Buy-in ($) — opcjonalnie")
        self.in_result = QLineEdit("")
        self.in_result.setPlaceholderText("Wynik (+/−) $")
        self.in_result.returnPressed.connect(self.save_session)
        row.addWidget(self._field("Buy-in", self.in_buyin))
        row.addWidget(self._field("Wynik sesji", self.in_result))
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        btn_win = QPushButton("▲  Wygrana")
        btn_win.setObjectName("btnPrimary")
        btn_win.clicked.connect(lambda: self.quick_result(positive=True))
        btn_loss = QPushButton("▼  Przegrana")
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
        self.lbl_headline.setStyleSheet(
            f"font-size: 30px; font-weight: 800; color: {COLORS['accent']};"
        )
        self.lbl_rule = QLabel("")
        self.lbl_rule.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        layout.addWidget(self.lbl_headline)
        layout.addWidget(self.lbl_rule)
        layout.addSpacing(8)

        tiers = QHBoxLayout()
        self.lbl_aggro = self._tier_card("Agresywnie", COLORS["danger"])
        self.lbl_standard = self._tier_card("Standard", COLORS["accent"])
        self.lbl_nit = self._tier_card("Ostrożnie", COLORS["gold"])
        for w in (self.lbl_aggro, self.lbl_standard, self.lbl_nit):
            tiers.addWidget(w["box"])
        layout.addLayout(tiers)

        self.lbl_next_target = QLabel("")
        self.lbl_next_target.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        layout.addSpacing(6)
        layout.addWidget(self.lbl_next_target)

        # Faworyci
        fav_cap = QLabel("Ulubione stawki")
        fav_cap.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px;")
        layout.addSpacing(10)
        layout.addWidget(fav_cap)
        self.fav_row = QHBoxLayout()
        self.fav_row.setSpacing(6)
        btn_add_fav = QPushButton("★ Zapisz aktualną")
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
            f"background-color: {COLORS['panel_alt']}; border: 1px solid {COLORS['border']}; "
            "border-radius: 10px;"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(12, 10, 12, 10)
        cap = QLabel(title)
        cap.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px; font-weight: 600;")
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
        self.history_area.setFixedHeight(180)
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
            self._set_card_at(idx, None)  # klik w wypełniony slot = usuń kartę
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
        self.refresh_board()

    def refresh_board(self):
        used = self.used_cards()
        for card, chip in self.card_chips.items():
            chip.setEnabled(card not in used)
        for i, btn in enumerate(self.slot_buttons):
            self._style_slot(btn, self._card_at(i), i == self.active)
        if self.active is None or self.active >= 7:
            self.lbl_next.setText("✓  Komplet kart")
        else:
            self.lbl_next.setText(f"▶  Następna karta → {SLOT_LABELS[self.active]}")

    def _style_slot(self, btn: QPushButton, card, is_active: bool):
        border = COLORS["accent"] if is_active else COLORS["border"]
        if card:
            color = SUIT_COLORS[card[1]]
            btn.setText(f"{card[0]}{SUIT_SYMBOLS[card[1]]}")
            btn.setStyleSheet(
                f"background-color: {COLORS['panel_alt']}; border: 2px solid {border}; "
                f"border-radius: 10px; color: {color}; font-size: 26px; font-weight: 800;"
            )
        else:
            style = "dashed" if not is_active else "solid"
            btn.setText("")
            btn.setStyleSheet(
                f"background-color: #14171D; border: 2px {style} {border}; "
                f"border-radius: 10px; color: {COLORS['muted']};"
            )

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
            self.log("♙  Wybierz 2 karty HERO, aby rozpocząć analizę.")
            return

        if len(board_list) in (1, 2):
            self.log_area.clear()
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
            self.log(f"\n[!] BŁĄD SYMULACJI: {mc_results['error']}")
            return

        self.log(f"\nMonte Carlo:  Win {mc_results['win']}%  ·  Tie {mc_results['tie']}%  ·  Lose {mc_results['lose']}%")
        self.analysis_data_cache["equity"] = mc_results["win"]
        decision = self.engine.get_recommendation(self.analysis_data_cache)

        self.log("\n▶▶▶  REKOMENDACJA  ◀◀◀")
        action = decision.get("action", "—")
        conf = decision.get("confidence", 0.0)
        self.log(f"   AKCJA:      {action}")
        self.log(f"   Pewność:    {conf}%")
        for reason in decision.get("reason", []):
            self.log(f"   • {reason}")

    def log(self, text: str):
        self.log_area.append(text)

    # --------------------------------------------------------- Bankroll logika
    def _fmt(self, value: float) -> str:
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def get_bankroll(self) -> float:
        return self.safe_float(self.in_bankroll.text())

    def set_mode(self, mode: str):
        self.game_mode = mode
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
            f"color: {COLORS['accent'] if data['ok'] else COLORS['danger']};"
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
        color = COLORS["accent"] if total >= 0 else COLORS["danger"]
        sign = "+" if total >= 0 else ""
        self.lbl_stats.setText(
            f"<span style='color:{COLORS['muted']}'>Sesji: {count}   ·   Bilans: </span>"
            f"<span style='color:{color}'>{sign}{total:.2f} $</span>"
        )
        lines = []
        for s in reversed(self.sessions[-12:]):
            r = s["result"]
            c = SUIT_COLORS["c"] if r >= 0 else SUIT_COLORS["h"]
            sign = "+" if r >= 0 else ""
            lines.append(
                f"<span style='color:{COLORS['muted']}'>{s['ts']}  [{s.get('mode','')}]</span>  "
                f"<span style='color:{c}; font-weight:700'>{sign}{r:.2f} $</span>"
            )
        self.history_area.setHtml("<br>".join(lines) if lines else
                                  f"<span style='color:{COLORS['muted']}'>Brak zapisanych sesji.</span>")

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
