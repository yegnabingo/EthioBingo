import random


def generate_card():

    columns = [

        random.sample(range(1, 16), 5),

        random.sample(range(16, 31), 5),

        random.sample(range(31, 46), 5),

        random.sample(range(46, 61), 5),

        random.sample(range(61, 76), 5),

    ]

    card = []

    for row in range(5):

        card.append([

            columns[0][row],

            columns[1][row],

            columns[2][row],

            columns[3][row],

            columns[4][row]

        ])

    card[2][2] = "FREE"

    return card


def generate_all_cards():

    cards = []

    used = set()

    while len(cards) < 200:

        card = generate_card()

        key = str(card)

        if key in used:
            continue

        used.add(key)

        cards.append(card)

    return cards
