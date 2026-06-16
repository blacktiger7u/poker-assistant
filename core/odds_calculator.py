from typing import Dict, List

class OddsCalculator:
    """Kalkulator szans i outsów bazujący na heurystykach i kombinatoryce."""

    @staticmethod
    def calculate_draw_odds(outs: int) -> Dict[str, float]:
        """Oblicza szanse trafienia drawu używając Rule of 2 i Rule of 4."""
        return {
            "turn_pct": min(outs * 2.0, 100.0),
            "river_pct": min(outs * 2.0, 100.0),
            "turn_and_river_pct": min(outs * 4.0, 100.0)
        }

    @staticmethod
    def exact_combinatorics(outs: int, cards_known: int = 5) -> float:
        """Dokładne wyliczenie procentowe dla jednej ulicy (turn lub river)."""
        cards_remaining = 52 - cards_known
        if cards_remaining <= 0:
            return 0.0
        probability = outs / cards_remaining
        return round(probability * 100, 2)