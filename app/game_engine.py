import random
import asyncio

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Game, Setting


class GameEngine:

    def __init__(self):

        self.running = False

        self.called_numbers = []

        self.current_game = None

    async def start_game(self):

        if self.running:
            return

        self.running = True

        db: Session = SessionLocal()

        settings = db.query(Setting).first()

        game = Game(status="running")

        db.add(game)

        db.commit()

        db.refresh(game)

        self.current_game = game

        db.close()

        await self.countdown(settings.countdown_seconds)

        await self.draw_numbers(settings.draw_interval)

    async def countdown(self, seconds):

        while seconds > 0:

            print(f"Countdown: {seconds}")

            await asyncio.sleep(1)

            seconds -= 1

    async def draw_numbers(self, interval):

        numbers = list(range(1, 76))

        random.shuffle(numbers)

        self.called_numbers = []

        for number in numbers:

            self.called_numbers.append(number)

            print("CALL:", number)

            await asyncio.sleep(interval)

        self.running = False


engine = GameEngine()
