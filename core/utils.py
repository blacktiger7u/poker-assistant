from typing import List

# Definicje kart i kolorów
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['s', 'h', 'd', 'c']

def get_all_deck_cards() -> List[str]:
    """Generuje listę 52 kart w formacie treys, np. ['As', 'Kh', ...]."""
    return [f"{r}{s}" for r in RANKS for s in SUITS]

def treys_to_filename(card_str: str) -> str:
    """Mapuje format treys (np. 'Ks') na nazwę pliku (np. 'king_of_spades.png')."""
    rank_map = {
        '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
        '7': '7', '8': '8', '9': '9', 'T': '10',
        'J': 'jack', 'Q': 'queen', 'K': 'king', 'A': 'ace'
    }
    suit_map = {
        's': 'spades', 'h': 'hearts', 'd': 'diamonds', 'c': 'clubs'
    }

    rank = rank_map[card_str[0]]
    suit = suit_map[card_str[1]]
    return f"{rank}_of_{suit}.png"

def determine_street(board_cards: List[str]) -> str:
    """Określa fazę rozdania na podstawie liczby kart na stole."""
    count = len(board_cards)
    if count == 0: return "PREFLOP"
    if count == 3: return "FLOP"
    if count == 4: return "TURN"
    if count == 5: return "RIVER"
    return "UNKNOWN"