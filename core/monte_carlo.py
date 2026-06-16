from treys import Card, Evaluator, Deck
from typing import List, Dict
import random

class MonteCarloSimulator:
    def __init__(self, simulations: int = 100000):
        self.simulations = simulations
        self.evaluator = Evaluator()

    def run(self, hand: List[str], board: List[str]) -> Dict[str, float]:
        """Przeprowadza N symulacji przeciwko pojedynczemu przeciwnikowi."""
        if not hand:
            return {"win": 0.0, "tie": 0.0, "lose": 0.0}

        hero_ints = [Card.new(c) for c in hand]
        board_ints = [Card.new(c) for c in board]

        wins, ties, losses = 0, 0, 0

        # Pełna talia jako inty Treys dla szybkości
        full_deck = Deck().GetFullDeck()
        for c in hero_ints + board_ints:
            if c in full_deck:
                full_deck.remove(c)

        for _ in range(self.simulations):
            # Używamy random.sample dla najwyższej wydajności w czystym Pythonie
            cards_needed = 5 - len(board_ints)
            drawn_cards = random.sample(full_deck, cards_needed + 2)

            sim_board = board_ints + drawn_cards[:cards_needed]
            villain_hand = drawn_cards[cards_needed:]

            hero_score = self.evaluator.evaluate(sim_board, hero_ints)
            villain_score = self.evaluator.evaluate(sim_board, villain_hand)

            if hero_score < villain_score: wins += 1
            elif hero_score == villain_score: ties += 1
            else: losses += 1

        return {
            "win": round((wins / self.simulations) * 100, 2),
            "tie": round((ties / self.simulations) * 100, 2),
            "lose": round((losses / self.simulations) * 100, 2)
        }