from typing import Dict

class BankrollManager:
    @staticmethod
    def analyze(bankroll: float, buy_in: float, current_stack: float) -> Dict[str, any]:
        if bankroll <= 0: return {"risk": "HIGH", "engaged_pct": 0.0}

        engaged_pct = (current_stack / bankroll) * 100
        suggested_stake = bankroll / 100  # Zasada 100 buy-inów dla bezpieczeństwa

        risk = "LOW"
        if engaged_pct > 5.0: risk = "MEDIUM"
        if engaged_pct > 10.0: risk = "HIGH"

        return {
            "engaged_pct": round(engaged_pct, 2),
            "suggested_buyin": round(suggested_stake, 2),
            "risk_level": risk
        }