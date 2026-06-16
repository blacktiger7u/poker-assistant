from typing import Dict, Any

class DecisionEngine:
    @staticmethod
    def get_recommendation(data: Dict[str, Any]) -> dict:
        eq = data.get("equity", 0.0)
        req_eq = data.get("req_equity", 100.0)
        phase = data.get("phase", "UNKNOWN")
        position = data.get("position", "BTN")
        players = data.get("players", 6)

        reasons = []
        action = "FOLD"
        confidence = 0.0

        # Waga pozycji - im wczesna, tym wyższe wymagania
        early_positions = ["UTG", "MP"]
        is_early = position in early_positions
        is_full_ring = players > 6

        if phase == "PREFLOP":
            strength = data.get("preflop_strength", "TRASH")

            if strength == "PREMIUM":
                action = "RAISE / 3-BET"
                confidence = 95.0
                reasons.append(f"Premium starting hand on {position}")
            elif strength == "STRONG":
                action = "RAISE" if not (is_early and is_full_ring) else "CALL / FOLD"
                confidence = 80.0
                reasons.append(f"Strong hand. Positional adjustment: {position}")
            elif strength == "MEDIUM":
                if position in ["CO", "BTN", "SB"]:
                    action = "RAISE (Steal)" if players <= 6 else "CALL"
                    confidence = 70.0
                    reasons.append(f"Playable from late position ({position})")
                else:
                    action = "FOLD"
                    confidence = 85.0
                    reasons.append(f"Too weak to play from early/mid position ({position})")
            else:
                action = "FOLD"
                confidence = 99.0
                reasons.append("Trash hand")

        else:
            eq_diff = eq - req_eq
            if eq > 80.0:
                action = "ALL-IN / VALUE BET"
                confidence = 95.0
                reasons.append("Monster hand advantage")
            elif eq_diff > 10.0:
                action = "RAISE"
                confidence = 85.0
                reasons.append(f"Positive EV (+{round(eq_diff,1)}% margin)")
            elif eq_diff >= -3.0:
                action = "CALL"
                confidence = 70.0
                reasons.append("Pot odds closely align with equity. Good for drawing.")
            else:
                action = "FOLD"
                confidence = 88.0
                reasons.append(f"Negative EV (Req: {req_eq}%, Have: {eq}%)")

        return {
            "action": action,
            "confidence": confidence,
            "reason": reasons
        }