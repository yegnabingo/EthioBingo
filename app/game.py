import random
from datetime import datetime


class GameEngine:

    def __init__(self):

        self.reset()

    def reset(self):

        # Game Status
        self.status = "WAITING"

        # Countdown
        self.countdown = 30

        # Selected Numbers (1-200)
        self.selected_numbers = {}

        # Players
        self.players = {}

        # Current Game
        self.game_id = None

        # Bingo
        self.called_numbers = []

        self.remaining_numbers = list(range(1, 76))

        random.shuffle(self.remaining_numbers)

        self.current_ball = None

        # Winner
        self.winner = None

    def next_ball(self):

        if not self.remaining_numbers:
            return None

        number = self.remaining_numbers.pop(0)

        self.called_numbers.append(number)

        self.current_ball = number

        return number

    def reserve_numbers(self, player_id: str, numbers: list[int]):

        # Check if any number is already reserved
        for number in numbers:
            if number in self.selected_numbers:
                return False, f"Number {number} is already taken."

        # Reserve all numbers
        for number in numbers:
            self.selected_numbers[number] = player_id

        # Save player's numbers
        self.players[player_id] = {
            "numbers": numbers
        }

        return True, "Numbers reserved successfully."


    def release_numbers(self):

        self.selected_numbers.clear()

        self.players.clear()

game = GameEngine()
