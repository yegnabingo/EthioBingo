from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    telegram_id = Column(String, unique=True, index=True)
    telegram_name = Column(String)
    first_name = Column(String)

    balance = Column(Float, default=0)

    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    amount = Column(Float)

    tx_hash = Column(String)

    status = Column(String, default="Pending")

    approved_by = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    amount = Column(Float)

    wallet = Column(String)

    status = Column(String, default="Pending")

    approved_by = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)

    game_no = Column(Integer, unique=True, index=True)

    status = Column(String, default="WAITING")

    ticket_price = Column(Float, default=0)

    total_players = Column(Integer, default=0)

    total_pool = Column(Float, default=0)

    winner_id = Column(Integer, nullable=True)

    started_at = Column(DateTime)

    ended_at = Column(DateTime)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    game_id = Column(Integer, ForeignKey("games.id"))

    picked_numbers = Column(Text)

    card_data = Column(Text)

    is_winner = Column(Boolean, default=False)

    prize = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class BingoCard(Base):
    __tablename__ = "bingo_cards"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    game_id = Column(Integer, ForeignKey("games.id"))

    card_data = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
