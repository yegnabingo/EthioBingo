# app/bingo.py
# Bingo-specific logic placeholder

import random

def generate_card():
    """Generate a simple 5x5 bingo card placeholder."""
    numbers = random.sample(range(1, 76), 25)
    card = [numbers[i*5:(i+1)*5] for i in range(5)]
    return card

# TODO: implement bingo card generation and draw logic
