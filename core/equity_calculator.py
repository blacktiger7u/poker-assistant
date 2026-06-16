from treys import Evaluator, Card, Deck
from typing import Dict, List
from core.utils import determine_street

class EquityCalculator:
    def __init__(self):
        self.evaluator = Evaluator()

    def calculate_draws(self, hero_cards: List[str], board_cards: List[str]) -> Dict[str, any]:
        """Oblicza dokładne outsy i szanse trafienia (Rule of 2/4)."""
        phase = determine_street(board_cards)
        if phase in ["PREFLOP", "UNKNOWN", "RIVER"]:
            return {"outs": 0, "hit_chance": 0.0, "draw_types": []}

        hero_ints = [Card.new(c) for c in hero_cards]
        board_ints = [Card.new(c) for c in board_cards]

        current_score = self.evaluator.evaluate(board_ints, hero_ints)
        current_class = self.evaluator.get_rank_class(current_score)

        outs = 0
        draw_types = set()

        full_deck = Deck().GetFullDeck()
        known_cards = hero_ints + board_ints
        remaining_cards = [c for c in full_deck if c not in known_cards]

        # Symulacja każdej karty z talii
        for card in remaining_cards:
            sim_board = board_ints + [card]
            new_score = self.evaluator.evaluate(sim_board, hero_ints)
            new_class = self.evaluator.get_rank_class(new_score)

            # W Treys niższy wynik i niższa klasa oznaczają mocniejszy układ
            if new_class < current_class:
                outs += 1
                if new_class == 5: draw_types.add("Straight Draw")
                if new_class == 4: draw_types.add("Flush Draw")
                if new_class == 3: draw_types.add("Full House Draw")

        multiplier = 4 if phase == "FLOP" else 2
        hit_chance = min(outs * multiplier, 100.0)

        return {
            "outs": outs,
            "hit_chance": round(hit_chance, 2),
            "draw_types": list(draw_types) if draw_types else ["Overcards / Pair Improvement"]
        }