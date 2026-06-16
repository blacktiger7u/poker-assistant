from treys import Card, Evaluator
from typing import List, Tuple

class HandEvaluator:
    def __init__(self):
        self.evaluator = Evaluator()
        # Prosta heurystyka preflop (format: RankRank np. 'AK', 'JT')
        self.premium_hands = ['AA', 'KK', 'QQ', 'JJ', 'AK']
        self.strong_hands = ['TT', '99', 'AQ', 'AJ', 'KQ']

    def evaluate_preflop(self, hand: List[str]) -> Tuple[str, str]:
        """Zwraca kategorię siły i sugerowaną akcję preflop."""
        if len(hand) != 2:
            return "UNKNOWN", "FOLD"

        r1, r2 = hand[0][0], hand[1][0]
        # Sortowanie dla łatwiejszego porównania (np. AK zamiast KA)
        ranks = sorted([r1, r2], key=lambda x: '23456789TJQKA'.index(x), reverse=True)
        hand_str = f"{ranks[0]}{ranks[1]}"
        is_suited = hand[0][1] == hand[1][1]

        if hand_str in self.premium_hands:
            return "PREMIUM", "3-BET / ALL-IN"
        elif hand_str in self.strong_hands or (is_suited and hand_str == 'AQ'):
            return "STRONG", "RAISE"
        elif r1 == r2 or 'A' in ranks or is_suited:
            return "MEDIUM", "CALL"
        elif '23456789TJQKA'.index(ranks[0]) >= 8: # Najwyższa karta to przynajmniej T
            return "WEAK", "FOLD"
        else:
            return "TRASH", "FOLD"

    def evaluate_postflop(self, hand: List[str], board: List[str]) -> Tuple[str, float]:
        """Ocenia aktualny układ (zwraca nazwę i siłę znormalizowaną do procentów)."""
        hero_cards = [Card.new(c) for c in hand]
        board_cards = [Card.new(c) for c in board]

        score = self.evaluator.evaluate(board_cards, hero_cards)
        rank_class = self.evaluator.get_rank_class(score)
        class_string = self.evaluator.class_to_string(rank_class)

        # Treys score: 1 to najwyższy (Royal Flush), 7462 to najniższy.
        # Konwersja na siłę procentową układu (przybliżona).
        strength_pct = round((1.0 - (score / 7462.0)) * 100, 2)

        return class_string, strength_pct