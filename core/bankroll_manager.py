from typing import Any, Dict, List, Optional, Tuple

# Standardowe poziomy stawek (online, stack 100bb => buy-in == kwota NL)
CASH_LEVELS: List[Tuple[str, float]] = [
    ("NL2", 2), ("NL5", 5), ("NL10", 10), ("NL25", 25), ("NL50", 50),
    ("NL100", 100), ("NL200", 200), ("NL400", 400), ("NL500", 500), ("NL1000", 1000),
]

# Typowe buy-iny turniejowe (MTT)
MTT_LEVELS: List[float] = [1, 2, 5, 11, 22, 33, 55, 109, 215, 530, 1050, 2100, 5200]


class BankrollManager:
    """Zarządzanie kapitałem: sugestie stawek + ocena ryzyka zaangażowania puli."""

    # Liczba buy-inów wg klasycznych zasad bankroll managementu
    CASH_AGGRO = 30      # agresywnie
    CASH_SAFE = 50       # standard
    CASH_NIT = 100       # ostrożnie

    MTT_AGGRO = 50       # agresywnie
    MTT_SAFE = 100       # standard
    MTT_NIT = 200        # ostrożnie

    # ---------- Sugestie stawek ----------
    @staticmethod
    def _best_cash(max_buyin: float) -> Optional[Tuple[str, float]]:
        best: Optional[Tuple[str, float]] = None
        for name, buyin in CASH_LEVELS:
            if buyin <= max_buyin:
                best = (name, buyin)
        return best

    @staticmethod
    def _best_mtt(max_buyin: float) -> float:
        best = 0.0
        for buyin in MTT_LEVELS:
            if buyin <= max_buyin:
                best = buyin
        return best

    @classmethod
    def suggest(cls, bankroll: float, mode: str = "CASH") -> Dict[str, Any]:
        """Zwraca rekomendowane stawki dla podanego bankrolla i trybu gry."""
        bankroll = max(0.0, bankroll)

        if mode.upper() == "MTT":
            safe = cls._best_mtt(bankroll / cls.MTT_SAFE)
            nit = cls._best_mtt(bankroll / cls.MTT_NIT)
            aggro = cls._best_mtt(bankroll / cls.MTT_AGGRO)
            return {
                "mode": "MTT",
                "headline": f"MTT do ${safe:g}" if safe else "Za mały bankroll na MTT $1",
                "ok": bool(safe),
                "aggressive": (f"${aggro:g}" if aggro else "—"),
                "standard": (f"${safe:g}" if safe else "—"),
                "conservative": (f"${nit:g}" if nit else "—"),
                "rule": f"{cls.MTT_SAFE} buy-inów (standard) · {cls.MTT_NIT} (ostrożnie)",
                "next_target": cls._next_cash_or_mtt(bankroll, "MTT", safe),
            }

        safe = cls._best_cash(bankroll / cls.CASH_SAFE)
        nit = cls._best_cash(bankroll / cls.CASH_NIT)
        aggro = cls._best_cash(bankroll / cls.CASH_AGGRO)
        return {
            "mode": "CASH",
            "headline": (safe[0] if safe else "Za mały bankroll na NL2"),
            "ok": bool(safe),
            "aggressive": (aggro[0] if aggro else "—"),
            "standard": (safe[0] if safe else "—"),
            "conservative": (nit[0] if nit else "—"),
            "rule": f"{cls.CASH_SAFE} buy-inów (standard) · {cls.CASH_NIT} (ostrożnie)",
            "next_target": cls._next_cash_or_mtt(bankroll, "CASH", safe),
        }

    @classmethod
    def _next_cash_or_mtt(cls, bankroll: float, mode: str, current) -> str:
        """Ile brakuje do następnego poziomu (motywacja do grindu)."""
        if mode == "MTT":
            cur = current if current else 0.0
            for buyin in MTT_LEVELS:
                if buyin > cur:
                    needed = buyin * cls.MTT_SAFE - bankroll
                    if needed > 0:
                        return f"Do MTT ${buyin:g}: jeszcze ${needed:,.0f}"
            return "Maksymalny poziom osiągnięty"
        cur_name = current[0] if current else None
        passed = bool(cur_name is None)
        for name, buyin in CASH_LEVELS:
            if passed:
                needed = buyin * cls.CASH_SAFE - bankroll
                if needed > 0:
                    return f"Do {name}: jeszcze ${needed:,.0f}"
            if name == cur_name:
                passed = True
        return "Maksymalny poziom osiągnięty"

    # ---------- Ocena ryzyka zaangażowania puli (używane przez analizator) ----------
    @staticmethod
    def analyze(bankroll: float, buy_in: float, current_stack: float) -> Dict[str, Any]:
        if bankroll <= 0:
            return {"risk_level": "HIGH", "engaged_pct": 0.0, "suggested_buyin": 0.0}

        engaged_pct = (current_stack / bankroll) * 100
        suggested_stake = bankroll / 100  # zasada 100 buy-inów dla bezpieczeństwa

        risk = "LOW"
        if engaged_pct > 5.0:
            risk = "MEDIUM"
        if engaged_pct > 10.0:
            risk = "HIGH"

        return {
            "engaged_pct": round(engaged_pct, 2),
            "suggested_buyin": round(suggested_stake, 2),
            "risk_level": risk,
        }
