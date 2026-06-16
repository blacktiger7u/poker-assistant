from typing import Dict, Any

class PotOddsCalculator:
    @staticmethod
    def calculate(pot_size: float, call_amount: float) -> Dict[str, Any]:
        # Zabezpieczenie przed wpisaniem 0 (lub wartości ujemnych) - zapobiega crashom
        if call_amount <= 0:
            return {
                "pot_odds_ratio": "N/A (Free Play)",
                "req_equity": 0.0
            }

        total_pot = pot_size + call_amount
        req_equity = (call_amount / total_pot) * 100.0

        # Zabezpieczenie na wypadek pot_size = 0 przy aktywnym call_amount
        ratio = round(pot_size / call_amount, 2) if call_amount > 0 else 0.0

        return {
            "pot_odds_ratio": str(ratio),
            "req_equity": round(req_equity, 2)
        }