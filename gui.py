import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QPushButton, QLabel, QGroupBox, QLineEdit, QTextEdit,
                             QComboBox, QCheckBox)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect

from core.utils import get_all_deck_cards, determine_street, treys_to_filename
from core.hand_evaluator import HandEvaluator
from core.monte_carlo import MonteCarloSimulator
from core.pot_odds import PotOddsCalculator
from core.equity_calculator import EquityCalculator
from core.bankroll_manager import BankrollManager
from core.decision_engine import DecisionEngine

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
        except Exception as e:
            self.result_ready.emit({"error": str(e)})


class PokerAssistantGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poker Assistant - Analytics Engine PRO")
        self.resize(1300, 850)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI', Arial;")

        self.deck = get_all_deck_cards()
        self.hero_cards = []
        self.board_cards = []
        self.current_scale = 1.0
        self.animations_list = [] # Referencje do animacji (zapobiega garbage collection)

        # Moduły logiki
        self.evaluator = HandEvaluator()
        self.pot_odds_calc = PotOddsCalculator()
        self.equity_calc = EquityCalculator()
        self.bankroll_mgr = BankrollManager()
        self.engine = DecisionEngine()

        self.worker = None
        self.analyze_timer = QTimer()
        self.analyze_timer.setSingleShot(True)
        self.analyze_timer.timeout.connect(self.run_analysis_logic)

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        left_panel.addWidget(self.create_top_controls())
        left_panel.addWidget(self.create_card_selector())
        left_panel.addWidget(self.create_graphical_board_view())
        left_panel.addWidget(self.create_inputs_view())

        btn_clear = QPushButton("Clear All Cards")
        btn_clear.setStyleSheet("background-color: #cc0000; padding: 10px; font-weight: bold; font-size: 14px;")
        btn_clear.clicked.connect(self.clear_all)
        left_panel.addWidget(btn_clear)
        left_panel.addStretch()

        right_panel = QVBoxLayout()
        right_panel.addWidget(self.create_dashboard_view())

        main_layout.addLayout(left_panel, 5)
        main_layout.addLayout(right_panel, 4)
        self.setLayout(main_layout)

    def create_top_controls(self) -> QGroupBox:
        group = QGroupBox("Configuration & Settings")
        layout = QHBoxLayout()

        # Opcje symulacji
        self.cb_sims = QComboBox()
        self.cb_sims.addItems(["10000", "30000", "50000", "100000"])
        self.cb_sims.setCurrentText("30000")
        self.cb_sims.setStyleSheet("background: #333; padding: 5px;")
        self.cb_sims.currentIndexChanged.connect(self.check_sim_warning)

        self.lbl_warning = QLabel("")
        self.lbl_warning.setStyleSheet("color: #ffaa00; font-weight: bold;")

        # Pozycja i Gracze
        self.cb_position = QComboBox()
        self.cb_position.addItems(["BTN", "CO", "MP", "UTG", "SB", "BB"])
        self.cb_position.setStyleSheet("background: #333; padding: 5px;")
        self.cb_position.currentIndexChanged.connect(self.trigger_analysis)

        self.cb_players = QComboBox()
        self.cb_players.addItems([str(i) for i in range(9, 1, -1)])
        self.cb_players.setCurrentText("6")
        self.cb_players.setStyleSheet("background: #333; padding: 5px;")
        self.cb_players.currentIndexChanged.connect(self.trigger_analysis)

        # UI Scale & Animacje
        self.cb_scale = QComboBox()
        self.cb_scale.addItems(["100%", "125%", "150%", "175%", "200%"])
        self.cb_scale.setStyleSheet("background: #333; padding: 5px;")
        self.cb_scale.currentIndexChanged.connect(self.apply_scaling)

        self.chk_anim = QCheckBox("Enable UI Animations")
        self.chk_anim.setChecked(True)

        # Składanie layoutu
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Simulations:"))
        col1.addWidget(self.cb_sims)
        col1.addWidget(self.lbl_warning)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Position:"))
        col2.addWidget(self.cb_position)
        col2.addWidget(QLabel("Players:"))
        col2.addWidget(self.cb_players)

        col3 = QVBoxLayout()
        col3.addWidget(QLabel("UI Scale:"))
        col3.addWidget(self.cb_scale)
        col3.addWidget(self.chk_anim)

        layout.addLayout(col1)
        layout.addLayout(col2)
        layout.addLayout(col3)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_card_selector(self) -> QGroupBox:
        group = QGroupBox("Deck Selector")
        layout = QGridLayout()
        self.card_buttons = {}

        row, col = 0, 0
        for card in self.deck:
            btn = QPushButton()
            btn.setFixedSize(65, 90)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            filename = treys_to_filename(card)
            img_path = f"cards/{filename}"

            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                scaled_pixmap = pixmap.scaled(60, 84, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                btn.setIcon(QIcon(scaled_pixmap))
                btn.setIconSize(QSize(60, 84))
            else:
                btn.setText(card)

            btn.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px;")
            btn.clicked.connect(lambda checked, c=card: self.on_card_clicked(c))

            layout.addWidget(btn, row, col)
            self.card_buttons[card] = btn

            col += 1
            if col > 12:
                col = 0
                row += 1

        group.setLayout(layout)
        return group

    def create_graphical_board_view(self) -> QGroupBox:
        """Nowy system graficznego wyświetlania kart na żywo."""
        group = QGroupBox("Current Hand & Board")
        layout = QHBoxLayout()

        self.hero_labels = []
        self.board_labels = []

        # Ręka gracza
        hero_layout = QVBoxLayout()
        hero_layout.addWidget(QLabel("<b>HERO:</b>"))
        h_cards_layout = QHBoxLayout()
        for _ in range(2):
            lbl = QLabel()
            lbl.setFixedSize(65, 90)
            lbl.setStyleSheet("border: 2px dashed #444; border-radius: 5px; background: #222;")
            h_cards_layout.addWidget(lbl)
            self.hero_labels.append(lbl)
        hero_layout.addLayout(h_cards_layout)

        # Karty na stole
        board_layout = QVBoxLayout()
        board_layout.addWidget(QLabel("<b>BOARD:</b>"))
        b_cards_layout = QHBoxLayout()
        for _ in range(5):
            lbl = QLabel()
            lbl.setFixedSize(65, 90)
            lbl.setStyleSheet("border: 2px dashed #444; border-radius: 5px; background: #222;")
            b_cards_layout.addWidget(lbl)
            self.board_labels.append(lbl)
        board_layout.addLayout(b_cards_layout)

        layout.addLayout(hero_layout)
        layout.addSpacing(30)
        layout.addLayout(board_layout)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_inputs_view(self) -> QGroupBox:
        group = QGroupBox("Pot & Bankroll Details")
        layout = QGridLayout()

        self.in_pot = QLineEdit("100")
        self.in_call = QLineEdit("0") # Zmieniono domyślnie na 0, nie wywołuje już crasha
        self.in_bankroll = QLineEdit("1000")
        self.in_stack = QLineEdit("200")

        for in_field in [self.in_pot, self.in_call, self.in_bankroll, self.in_stack]:
            in_field.setStyleSheet("background: #333; padding: 5px; font-size: 14px;")
            in_field.textChanged.connect(self.trigger_analysis)

        layout.addWidget(QLabel("Pot Size:"), 0, 0)
        layout.addWidget(self.in_pot, 0, 1)
        layout.addWidget(QLabel("Amount to Call:"), 1, 0)
        layout.addWidget(self.in_call, 1, 1)
        layout.addWidget(QLabel("Bankroll:"), 0, 2)
        layout.addWidget(self.in_bankroll, 0, 3)
        layout.addWidget(QLabel("Current Stack:"), 1, 2)
        layout.addWidget(self.in_stack, 1, 3)

        group.setLayout(layout)
        return group

    def create_dashboard_view(self) -> QGroupBox:
        group = QGroupBox("Analytics Dashboard")
        layout = QVBoxLayout()

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #0d0d0d; color: #00ff00; font-family: Consolas, monospace; font-size: 15px;")

        layout.addWidget(self.log_area)
        group.setLayout(layout)
        return group

    def check_sim_warning(self):
        """Ostrzega przed zamrażaniem GUI przy dużych liczbach symulacji."""
        sims = int(self.cb_sims.currentText())
        if sims >= 50000:
            self.lbl_warning.setText("⚠️ Warning: May cause UI lag")
        else:
            self.lbl_warning.setText("")
        self.trigger_analysis()

    def apply_scaling(self):
        scale_str = self.cb_scale.currentText()
        self.current_scale = int(scale_str.replace("%", "")) / 100.0

        base_w, base_h = 65, 90
        icon_w, icon_h = 60, 84

        for card, btn in self.card_buttons.items():
            btn.setFixedSize(int(base_w * self.current_scale), int(base_h * self.current_scale))

            filename = treys_to_filename(card)
            img_path = f"cards/{filename}"
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                scaled_pixmap = pixmap.scaled(
                    int(icon_w * self.current_scale), int(icon_h * self.current_scale),
                    Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                btn.setIcon(QIcon(scaled_pixmap))
                btn.setIconSize(QSize(int(icon_w * self.current_scale), int(icon_h * self.current_scale)))

    def apply_fade_animation(self, widget):
        """Płynnie pojawia kartę używając modyfikatora Opacity."""
        if not self.chk_anim.isChecked():
            return

        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(400) # Czas w ms
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()

        self.animations_list.append(anim) # Utrzymuje referencję do animacji

    def set_card_image(self, target_label: QLabel, card_str: str):
        """Ustawia grafikę karty w panelu Board/Hero."""
        filename = treys_to_filename(card_str)
        img_path = f"cards/{filename}"

        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            # Lekkie skalowanie w górę dla obszaru widoku względem Deck Selectora
            scaled_pixmap = pixmap.scaled(65, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            target_label.setPixmap(scaled_pixmap)
            target_label.setStyleSheet("border: none; background: transparent;")
        else:
            target_label.setText(card_str)

    def on_card_clicked(self, card: str):
        target_label = None

        if len(self.hero_cards) < 2:
            self.hero_cards.append(card)
            target_label = self.hero_labels[len(self.hero_cards) - 1]
        elif len(self.board_cards) < 5:
            self.board_cards.append(card)
            target_label = self.board_labels[len(self.board_cards) - 1]
        else:
            return

            # Wyłączanie w decku
        self.card_buttons[card].setDisabled(True)
        self.card_buttons[card].setStyleSheet("background-color: #111; opacity: 0.3; border-radius: 4px;")

        # Render i animacja
        self.set_card_image(target_label, card)
        self.apply_fade_animation(target_label)

        self.trigger_analysis()

    def clear_all(self):
        self.hero_cards.clear()
        self.board_cards.clear()

        # Resetowanie Deck Selectora
        for btn in self.card_buttons.values():
            btn.setDisabled(False)
            btn.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px;")

        # Resetowanie grafik Hero i Board
        for lbl in self.hero_labels + self.board_labels:
            lbl.clear()
            lbl.setStyleSheet("border: 2px dashed #444; border-radius: 5px; background: #222;")
            lbl.setGraphicsEffect(None)

        self.log_area.clear()
        self.animations_list.clear()

    def safe_float(self, text: str) -> float:
        try:
            val = float(text.strip())
            return val if val >= 0 else 0.0
        except ValueError:
            return 0.0

    def trigger_analysis(self):
        self.analyze_timer.start(500)

    def run_analysis_logic(self):
        if len(self.hero_cards) < 2:
            return

        if len(self.board_cards) in [1, 2]:
            self.log_area.clear()
            self.log(f"Selected {len(self.board_cards)}/3 flop cards. Waiting for full flop...")
            return

        self.log_area.clear()
        phase = determine_street(self.board_cards)
        self.log(f"--- PHASE: {phase} ---")

        preflop_str = "UNKNOWN"
        if phase == "PREFLOP":
            strength, action = self.evaluator.evaluate_preflop(self.hero_cards)
            preflop_str = strength
            self.log(f"Hand Rank: {strength}")
        else:
            current_hand, pct = self.evaluator.evaluate_postflop(self.hero_cards, self.board_cards)
            self.log(f"Current Hand: {current_hand} (Relative Strength: {pct}%)")

            draw_data = self.equity_calc.calculate_draws(self.hero_cards, self.board_cards)
            if draw_data['outs'] > 0:
                self.log(f"Outs: {draw_data['outs']} | Hit Chance: {draw_data['hit_chance']}%")
                self.log(f"Draws: {', '.join(draw_data['draw_types'])}")

        pot = self.safe_float(self.in_pot.text())
        call_amt = self.safe_float(self.in_call.text())
        br = self.safe_float(self.in_bankroll.text())
        stack = self.safe_float(self.in_stack.text())

        odds_data = self.pot_odds_calc.calculate(pot, call_amt)
        self.log(f"\nPot Odds: 1 : {odds_data['pot_odds_ratio']} (Req Equity: {odds_data['req_equity']}%)")

        br_data = self.bankroll_mgr.analyze(br, pot, stack)
        self.log(f"Bankroll Risk: {br_data['risk_level']} ({br_data['engaged_pct']}% engaged)")

        sims = int(self.cb_sims.currentText())
        self.log(f"\nRunning {sims} Monte Carlo Simulations...")
        self.log("Please wait...")

        self.analysis_data_cache = {
            "phase": phase,
            "preflop_strength": preflop_str,
            "req_equity": odds_data['req_equity'],
            "position": self.cb_position.currentText(),
            "players": int(self.cb_players.currentText())
        }

        if self.worker is not None and self.worker.isRunning():
            try:
                self.worker.result_ready.disconnect()
            except TypeError:
                pass

        self.worker = SimulationWorker(self.hero_cards.copy(), self.board_cards.copy(), simulations=sims)
        self.worker.result_ready.connect(self.on_simulation_complete)
        self.worker.start()

    def on_simulation_complete(self, mc_results: dict):
        if "error" in mc_results:
            self.log(f"\n[!] CRITICAL ERROR IN SIMULATION: {mc_results['error']}")
            return

        self.log(f"MC Win: {mc_results['win']}% | Tie: {mc_results['tie']}% | Lose: {mc_results['lose']}%")

        self.analysis_data_cache["equity"] = mc_results['win']
        decision = self.engine.get_recommendation(self.analysis_data_cache)

        self.log("\n>>> DECISION ENGINE OUTPUT <<<")
        self.log(json.dumps(decision, indent=4))

    def log(self, text: str):
        self.log_area.append(text)