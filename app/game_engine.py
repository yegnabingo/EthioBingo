import random
import asyncio
import json
import inspect
from datetime import datetime
from sqlalchemy.orm import Session

from app.websocket_manager import manager
from app.database import SessionLocal
from app.models import Game, Setting, User, AdminStats, PlayerCard, Card


class GameEngine:

    def __init__(self):
        self.running = False
        self.called_numbers = []
        self.current_game = None

    async def safe_broadcast(self, payload):
        """Robust broadcast helper:
        - handles manager.broadcast being awaitable or synchronous callable
        - falls back to sending directly on manager connections if available
        - logs success/errors so we can diagnose why clients aren't receiving frames
        """
        try:
            # Short payload preview for logs
            preview = payload if isinstance(payload, dict) else str(payload)
            if isinstance(preview, dict):
                preview = {k: preview.get(k) for k in list(preview)[:5]}
            print(f"⬆️ broadcast attempt: {preview}")

            maybe = None
            try:
                maybe = manager.broadcast(payload)
            except Exception as e:
                # manager.broadcast itself raised synchronously
                print(f"❌ manager.broadcast raised synchronously: {e}")

            # If manager.broadcast returned an awaitable (common), await it
            try:
                if inspect.isawaitable(maybe):
                    await maybe
                    print("⬆️ broadcast: awaitable completed")
                    return True

                # If manager.broadcast returned a callable (some implementations), call it
                if callable(maybe):
                    try:
                        maybe()
                        print("⬆️ broadcast: callable executed")
                        return True
                    except Exception as e:
                        print(f"❌ manager.broadcast callable failed: {e}")
            except Exception as e:
                print(f"❌ Error while awaiting/calling manager.broadcast result: {e}")

            # Fallback: try to send to sockets directly if manager exposes them
            sent = False
            for attr in ("connections", "active_connections", "websockets"):
                conns = getattr(manager, attr, None)
                if conns:
                    # iterate a copy in case manager mutates list during sends
                    for ws in list(conns):
                        try:
                            # attempt JSON send (works with FastAPI WebSocket)
                            await ws.send_json(payload)
                            sent = True
                        except Exception as e:
                            # remove dead socket if possible
                            print(f"❌ Failed to send to socket, removing: {e}")
                            try:
                                conns.remove(ws)
                            except Exception:
                                pass
                    if sent:
                        print("⬆️ broadcast: fallback per-socket sends succeeded")
                        return True

            # If nothing sent
            print("⚠️ broadcast: no awaitable/callable/fallback succeeded")
            return False

        except Exception as e:
            print(f"❌ safe_broadcast unexpected error: {e}")
            return False

    async def start_game(self):
        if self.running:
            return

        self.running = True
        print("🎯 የቢንጎ ጨዋታ ሞተር በማለቂያ በሌለው ዑደት (Loop) ስራ ጀምሯል...")

        # Main loop: starts immediately
        while self.running:
            db: Session = None
            try:
                db = SessionLocal()
                settings = db.query(Setting).first()

                countdown_seconds = settings.countdown_seconds if settings else 30
                draw_interval = settings.draw_interval if settings else 2.0

                # Create new game record (taken_cards/drawn_balls should now exist)
                game = Game(
                    status="running",
                    started_at=datetime.utcnow(),
                    taken_cards="[]",
                    drawn_balls="[]"
                )
                db.add(game)
                db.commit()
                db.refresh(game)

                self.current_game = game

                # PICK PHASE
                game_display_no = str(100000 + game.id)
                await self.countdown(countdown_seconds, game_display_no)

                # DRAW PHASE
                if self.running:
                    await self.draw_numbers(draw_interval, game_display_no)

                # short rest between rounds
                await asyncio.sleep(5)

            except Exception as e:
                print(f"❌ Error in game loop iteration: {e}")
                # small pause to avoid tight error loop
                await asyncio.sleep(1)

            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass

    async def countdown(self, seconds, game_display_no):
        while seconds >= 0 and self.running:
            current_taken_list = []
            db: Session = None
            try:
                db = SessionLocal()
                taken_cards = db.query(Card.card_number).filter(Card.is_taken == True).all()
                current_taken_list = [c[0] for c in taken_cards]

                if self.current_game:
                    try:
                        game_record = db.query(Game).filter(Game.id == self.current_game.id).first()
                        if game_record:
                            game_record.taken_cards = json.dumps(current_taken_list)
                            db.commit()
                    except Exception as e:
                        # log DB update failure but continue
                        print(f"❌ Failed to update game.taken_cards: {e}")

            except Exception as e:
                print(f"❌ Error during countdown DB fetch: {e}")

            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass

            # Broadcast within its own try so failures won't stop the loop
            payload = {
                "type": "countdown",
                "seconds": seconds,
                "time": seconds,
                "phase": "PICK",
                "game_no": game_display_no,
                "game_id": self.current_game.id if self.current_game else 0,
                "taken_cards": current_taken_list
            }
            await self.safe_broadcast(payload)

            # Debug log so we can see server-side countdown ticks
            print(f"⏱ server countdown tick: {seconds} (game {game_display_no})")

            await asyncio.sleep(1)
            seconds -= 1

    async def draw_numbers(self, interval, game_display_no):
        if not self.current_game:
            return

        numbers = list(range(1, 76))
        random.shuffle(numbers)
        self.called_numbers = []

        db: Session = None
        try:
            db = SessionLocal()

            bought_cards = {pc.card_number: pc.user_id for pc in db.query(PlayerCard).filter(PlayerCard.game_id == self.current_game.id).all()}
            all_200_cards = {str(c.card_number): json.loads(c.data) if isinstance(c.data, str) else c.data for c in db.query(Card).all()}

            settings = db.query(Setting).first()
            game_fee = settings.game_fee if settings else 10
            total_pool_money = len(bought_cards) * game_fee

            winner_detected = False

            await self.safe_broadcast({
                "type": "phase_change",
                "phase": "DRAW",
                "game_no": game_display_no
            })

            call_count = 0
            for number in numbers:
                if not self.running:
                    break

                call_count += 1
                self.called_numbers.append(number)

                # persist drawn balls
                try:
                    game_record = db.query(Game).filter(Game.id == self.current_game.id).first()
                    if game_record:
                        game_record.drawn_balls = json.dumps(self.called_numbers)
                        db.commit()
                except Exception as e:
                    print(f"❌ Error saving drawn ball to DB: {e}")

                # broadcast ball
                letter = ""
                if number <= 15: letter = "B"
                elif number <= 30: letter = "I"
                elif number <= 45: letter = "N"
                elif number <= 60: letter = "G"
                else: letter = "O"

                await self.safe_broadcast({
                   "type": "ball",
                   "letter": letter,
                   "number": number,
                   "label": f"{letter}{number}",
                   "call_count": call_count,
                   "game_no": game_display_no
                })

                # debug print per ball
                print(f"🔔 called ball: {letter}{number} (call #{call_count})")

                result = self.process_drawn_ball_and_check_winner(
                    db,
                    self.current_game.id,
                    self.called_numbers,
                    total_pool_money,
                    bought_cards,
                    all_200_cards
                )

                if result["status"] in ["WINNER_FOUND", "HOUSE_WIN"]:
                    try:
                        user_record = db.query(User).filter(User.id == result["winner_id"]).first()
                        winner_name = user_record.telegram_name if user_record else "የቤቱ ተጫዋች"
                    except Exception:
                        winner_name = "የቤቱ ተጫዋች"

                    prize_amt = total_pool_money * 0.80

                    await self.safe_broadcast({
                        "type": "game_over",
                        "status": result["status"],
                        "result": "BINGO",
                        "winner_name": winner_name,
                        "winning_card": result["card_number"],
                        "prize": round(prize_amt, 2),
                        "message": result["message"],
                        "card_number": result["card_number"],
                        "winner_id": result["winner_id"]
                    })
                    winner_detected = True
                    break

                await asyncio.sleep(interval)

            if not winner_detected and self.running:
                result = self.force_house_win(db, self.current_game.id, self.called_numbers, total_pool_money, bought_cards, all_200_cards)
                prize_amt = total_pool_money * 0.80

                await self.safe_broadcast({
                    "type": "game_over",
                    "status": result["status"],
                    "result": "BINGO",
                    "winner_name": "የቤቱ ተጫዋች",
                    "winning_card": result["card_number"],
                    "prize": round(prize_amt, 2),
                    "message": result["message"],
                    "card_number": result["card_number"],
                    "winner_id": result["winner_id"]
                })

        except Exception as e:
            print(f"❌ Error in draw_numbers: {e}")

        finally:
            # reset all 200 cards
            try:
                if db:
                    db.query(Card).update({Card.is_taken: False, Card.reserved_by: None, Card.current_game_id: None})
                    db.commit()
                    print(f"🏁 Game ID {game_display_no} ተጠናቆ ካርዶች በሙሉ ለቀጣይ ዙር ጸድተዋል።")
            except Exception as e:
                print(f"❌ Error resetting cards at game over: {e}")

            if db:
                try:
                    db.close()
                except Exception:
                    pass

    def check_bingo_patterns(self, matrix, drawn_balls):
        drawn_set = set(drawn_balls)
        drawn_set.add("FREE")
        drawn_set.add(None)

        for r in range(5):
            if all(matrix[r][c] in drawn_set for c in range(5)): return True
        for c in range(5):
            if all(matrix[r][c] in drawn_set for r in range(5)): return True
        if all(matrix[i][i] in drawn_set for i in range(5)): return True
        if all(matrix[i][4 - i] in drawn_set for i in range(5)): return True

        corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
        if all(matrix[r][c] in drawn_set for r, c in corners): return True

        return False

    def process_drawn_ball_and_check_winner(self, db, game_id, current_drawn_balls, total_pool_money, bought_cards, all_200_cards):
        for card_num, user_id in bought_cards.items():
            card_matrix = all_200_cards.get(str(card_num))
            if card_matrix and self.check_bingo_patterns(card_matrix, current_drawn_balls):
                try:
                    self.distribute_game_prize(db, game_id, total_pool_money, winner_user_id=user_id, winning_card=card_num)
                except Exception as e:
                    print(f"❌ Error distributing prize: {e}")
                return {
                    "status": "WINNER_FOUND",
                    "message": f"🎉 ካርድ #{card_num} አሸንፏል!",
                    "winner_id": user_id,
                    "card_number": card_num
                }
        return {"status": "CONTINUE"}

    def force_house_win(self, db, game_id, current_drawn_balls, total_pool_money, bought_cards, all_200_cards):
        winning_card_num = None
        for card_num in range(1, 201):
            if card_num not in bought_cards:
                card_matrix = all_200_cards.get(str(card_num))
                if card_matrix and self.check_bingo_patterns(card_matrix, current_drawn_balls):
                    winning_card_num = card_num
                    break

        if not winning_card_num:
            available_ids = [id for id in range(1, 201) if id not in bought_cards]
            winning_card_num = random.choice(available_ids) if available_ids else 1

        self.distribute_game_prize(db, game_id, total_pool_money, winner_user_id=None, winning_card=winning_card_num)

        fake_names = ["Abebe_99", "Selam_🎰", "Bekele_K", "Aster_B", "Elias_Bingo"]
        random_name = random.choice(fake_names)

        return {
            "status": "HOUSE_WIN",
            "message": f"🎉 ካርድ #{winning_card_num} ({random_name}) አሸንፏል!",
            "winner_id": 0,
            "card_number": winning_card_num
        }

    def distribute_game_prize(self, db, game_id, total_pool_money, winner_user_id=None, winning_card=None):
        settings = db.query(Setting).first()
        comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0

        admin_commission = total_pool_money * (comm_percent / 100.0)
        player_prize = total_pool_money - admin_commission

        admin_stats = db.query(AdminStats).first()
        if not admin_stats:
            admin_stats = AdminStats(house_balance=0.0, total_commission=0.0)
            db.add(admin_stats)

        admin_stats.total_commission += admin_commission

        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.status = "finished"
            game.winning_card = winning_card
            game.finished_at = datetime.utcnow()

        if winner_user_id:
            user = db.query(User).filter(User.id == winner_user_id).first()
            if user:
                user.balance += player_prize
            if game:
                game.winner_id = winner_user_id
                game.prize = player_prize
        else:
            admin_stats.house_balance += player_prize
            if game:
                game.winner_id = 0
                game.prize = player_prize

        try:
            db.commit()
        except Exception as e:
            print(f"❌ Error committing prize distribution: {e}")


# 🎯 🧠 የጌም ሞተሩን ውጭ መጥሪያ
engine = GameEngine()
