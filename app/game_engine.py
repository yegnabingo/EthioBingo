Import random
import asyncio
import json
import inspect
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.websocket_manager import manager
from app.database import SessionLocal
from app.models import Game, Setting, User, AdminStats, PlayerCard, Card

BOT_NAMES = [
    "አቤል_99", "ዮናስ_ቢንጎ", "ሰላም_K", "ሄለን_ፈጣኑ", "ዳዊት_ዘ_ኪንግ", 
    "ማሂ_ባቲ", "ቲጂ_አዲስ", "በርናባስ", "ፋሲካ_ወሎ", "ናቲ_ማን", 
    "ኤልሳ_አልማዝ", "ኬነዲ_ጂ", "ሮቤል_ቶፕ", "ሳሚ_ዲ", "ሊዲያ_የስ"
]

class GameEngine:

    def __init__(self):
        self.running = False
        self.called_numbers = []
        self.current_game = None

    async def safe_broadcast(self, payload):
        try:
            preview = payload if isinstance(payload, dict) else str(payload)
            if isinstance(preview, dict):
                preview = {k: preview.get(k) for k in list(preview)[:5]}
            print(f"⬆️ broadcast attempt: {preview}")

            maybe = None
            try:
                maybe = manager.broadcast(payload)
            except Exception as e:
                print(f"❌ manager.broadcast raised synchronously: {e}")

            try:
                if inspect.isawaitable(maybe):
                    await maybe
                    return True
                if callable(maybe):
                    maybe()
                    return True
            except Exception as e:
                print(f"❌ Error during broadcast invocation: {e}")

            sent = False
            for attr in ("connections", "active_connections", "websockets"):
                conns = getattr(manager, attr, None)
                if conns:
                    for ws in list(conns):
                        try:
                            await ws.send_json(payload)
                            sent = True
                        except Exception as e:
                            print(f"❌ Failed to send to socket: {e}")
                    if sent:
                        return True
            return False
        except Exception as e:
            print(f"❌ safe_broadcast unexpected error: {e}")
            return False

    async def start_game(self):
        if self.running:
            return

        self.running = True
        print("🎯 የቢንጎ ጨዋታ ሞተር በማለቂያ በሌለው ዑደት (Loop) ስራ ጀምሯል...")

        while self.running:
            db: Session = None
            saved_game_id = None
            game_display_no = "0"
            try:
                db = SessionLocal()
                settings = db.query(Setting).first()

                countdown_seconds = settings.countdown_seconds if settings else 30
                draw_interval = settings.draw_interval if settings else 2.0

                game = Game(
                    status="running",
                    started_at=datetime.now(timezone.utc),
                    taken_cards="[]",
                    drawn_balls="[]"
                )
                db.add(game)
                db.commit()
                
                saved_game_id = game.id
                self.current_game = game
                game_display_no = str(100000 + saved_game_id)
                
                has_bought_cards = await self.countdown(countdown_seconds, game_display_no, saved_game_id)

                if self.running and has_bought_cards:
                    await self.draw_numbers(draw_interval, game_display_no, saved_game_id)
                else:
                    print(f"🔄 Game {game_display_no} ላይ ምንም ካርድ አልተሸጠም። ወደ DRAW ሳይሻገር ዑደቱ እንደገና ይጀምራል።")
                    game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                    if game_record:
                        game_record.status = "cancelled"
                        db.commit()

                await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ Error in game loop iteration: {e}")
                await asyncio.sleep(1)
            finally:
                if db:
                    try:
                        # ⚠️ CRITICAL FIX: Only reset cards assigned explicitly to this closed game thread loop!
                        if saved_game_id:
                            db.query(Card).filter(Card.current_game_id == saved_game_id).update({
                                Card.is_taken: False, 
                                Card.reserved_by: None, 
                                Card.current_game_id: None
                            })
                            db.commit()
                            print(f"🏁 Game ID {game_display_no} ተጠናቆ የዚህ ዙር ካርዶች ብቻ ጸድተዋል።")
                        db.close()
                    except Exception as e:
                        print(f"❌ Error resetting context assets: {e}")

    async def countdown(self, seconds, game_display_no, saved_game_id):
        has_bought_cards = False
        while seconds >= 0 and self.running:
            current_taken_list = []
            sold_cards_count = 0
            db: Session = None
            try:
                db = SessionLocal()
                taken_cards = db.query(Card.card_number).filter(Card.is_taken == True).all()
                current_taken_list = [c[0] for c in taken_cards]
                
                sold_cards_count = db.query(PlayerCard).filter(PlayerCard.game_id == saved_game_id).count()

                if saved_game_id:
                    game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                    if game_record:
                        game_record.taken_cards = json.dumps(current_taken_list)
                        db.commit()
            except Exception as e:
                print(f"❌ Error during countdown DB update: {e}")
            finally:
                if db:
                    db.close()

            game_fee = 10.0
            total_pool = sold_cards_count * game_fee
            derash_amount = int(total_pool * 0.80) if sold_cards_count > 0 else 0

            if sold_cards_count > 0:
                has_bought_cards = True

            payload = {
                "type": "countdown",
                "seconds": seconds,
                "time": seconds,
                "phase": "PICK",
                "game_no": game_display_no,
                "game_id": saved_game_id,
                "taken_cards": current_taken_list,
                "derash": derash_amount,
                "player_count": sold_cards_count
            }
            await self.safe_broadcast(payload)
            await asyncio.sleep(1)
            seconds -= 1
            
        return has_bought_cards

    async def draw_numbers(self, interval, game_display_no, saved_game_id):
        if not saved_game_id:
            return

        numbers = list(range(1, 76))
        random.shuffle(numbers)
        self.called_numbers = []

        db: Session = None
        try:
            db = SessionLocal()
            bought_cards = {pc.card_number: pc.user_id for pc in db.query(PlayerCard).filter(PlayerCard.game_id == saved_game_id).all()}
            all_200_cards = {str(c.card_number): json.loads(c.data) if isinstance(c.data, str) else c.data for c in db.query(Card).all()}

            game_fee = 10.0
            total_pool_money = len(bought_cards) * game_fee
            derash_amount = int(total_pool_money * 0.80)
            winner_detected = False

            await self.safe_broadcast({
                "type": "phase_change",
                "phase": "DRAW",
                "game_no": game_display_no,
                "derash": derash_amount
            })

            call_count = 0
            for number in numbers:
                if not self.running:
                    break

                call_count += 1
                self.called_numbers.append(number)

                game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                if game_record:
                    game_record.drawn_balls = json.dumps(self.called_numbers)
                    db.commit()

                letter = "B" if number <= 15 else "I" if number <= 30 else "N" if number <= 45 else "G" if number <= 60 else "O"

                await self.safe_broadcast({
                   "type": "ball",
                   "letter": letter,
                   "number": number,
                   "label": f"{letter}{number}",
                   "call_count": call_count,
                   "game_no": game_display_no,
                   "derash": derash_amount
                })

                result = self.process_drawn_ball_and_check_winner(
                    db, saved_game_id, self.called_numbers, total_pool_money, bought_cards, all_200_cards
                )

                if result["status"] in ["WINNER_FOUND", "HOUSE_WIN"]:
                    prize_display = derash_amount if result["status"] == "WINNER_FOUND" and result["winner_id"] != 0 else total_pool_money
                    
                    if result["status"] == "WINNER_FOUND" and result["winner_id"] != 0:
                        user_record = db.query(User).filter(User.id == result["winner_id"]).first()
                        winner_name = user_record.telegram_name if user_record and user_record.telegram_name else f"ተጫዋች {result['winner_id']}"
                    else:
                        winner_name = random.choice(BOT_NAMES)

                    await self.safe_broadcast({
                        "type": "game_over",
                        "status": "WINNER_FOUND",
                        "result": "BINGO",
                        "winner_name": winner_name,
                        "winning_card": result["card_number"],
                        "prize": round(prize_display, 2),
                        "message": result["message"],
                        "card_number": result["card_number"],
                        "winner_id": result["winner_id"],
                        "winning_numbers": result.get("winning_numbers", []), 
                        "card_numbers": result.get("card_numbers", []),       
                        "winning_reason": result.get("winning_pattern", "ቢንጎ")
                    })
                    winner_detected = True
                    break

                await asyncio.sleep(interval)

            if not winner_detected and self.running:
                result = self.force_house_win(db, saved_game_id, self.called_numbers, total_pool_money, bought_cards, all_200_cards)
                winner_name = random.choice(BOT_NAMES)

                await self.safe_broadcast({
                    "type": "game_over",
                    "status": "WINNER_FOUND",
                    "result": "BINGO",
                    "winner_name": winner_name,
                    "winning_card": result["card_number"],
                    "prize": round(total_pool_money, 2),
                    "message": result["message"],
                    "card_number": result["card_number"],
                    "winner_id": result["winner_id"],
                    "winning_numbers": result.get("winning_numbers", []),
                    "card_numbers": result.get("card_numbers", []),
                    "winning_reason": result.get("winning_pattern", "ቢንጎ")
                })
        except Exception as e:
            print(f"❌ Error in draw_numbers execution tracking: {e}")
        finally:
            if db:
                db.close()

    def check_bingo_patterns(self, matrix, drawn_balls):
        drawn_set = set(drawn_balls)
        drawn_set.add("FREE")
        drawn_set.add(None)

        # Horizontal Check
        for r in range(5):
            if all(matrix[r][c] in drawn_set for c in range(5)):
                return True, [matrix[r][c] for c in range(5)], "Horizontal Row"
        # Vertical Check
        for c in range(5):
            if all(matrix[r][c] in drawn_set for r in range(5)):
                return True, [matrix[r][c] for r in range(5)], "Vertical Column"
        # Diagonal Down Check
        if all(matrix[i][i] in drawn_set for i in range(5)):
            return True, [matrix[i][i] for i in range(5)], "Diagonal Down"
        # Diagonal Up Check
        if all(matrix[i][4 - i] in drawn_set for i in range(5)):
            return True, [matrix[i][4 - i] for i in range(5)], "Diagonal Up"
        # 4 Corners Check
        corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
        if all(matrix[r][c] in drawn_set for r, c in corners):
            return True, [matrix[r][c] for r, c in corners], "4 Corners"

        return False, [], ""

    def process_drawn_ball_and_check_winner(self, db, game_id, current_drawn_balls, total_pool_money, bought_cards, all_200_cards):
        for card_num, user_id in bought_cards.items():
            card_matrix = all_200_cards.get(str(card_num))
            if card_matrix:
                is_win, win_nums, pattern = self.check_bingo_patterns(card_matrix, current_drawn_balls)
                if is_win:
                    self.distribute_game_prize(db, game_id, total_pool_money, winner_user_id=user_id, winning_card=card_num)
                    # Flatten full matrix data for frontend delivery
                    flat_card = [item for sublist in card_matrix for item in sublist]
                    return {
                        "status": "WINNER_FOUND",
                        "message": f"🎉 ካርድ #{card_num} አሸንፏል!",
                        "winner_id": user_id,
                        "card_number": card_num,
                        "winning_numbers": win_nums,
                        "card_numbers": flat_card,
                        "winning_pattern": pattern
                    }

        for card_num in range(1, 201):
            if card_num not in bought_cards:
                card_matrix = all_200_cards.get(str(card_num))
                if card_matrix:
                    is_win, win_nums, pattern = self.check_bingo_patterns(card_matrix, current_drawn_balls)
                    if is_win:
                        self.distribute_game_prize(db, game_id, total_pool_money, winner_user_id=None, winning_card=card_num)
                        flat_card = [item for sublist in card_matrix for item in sublist]
                        return {           
                            "status": "HOUSE_WIN",
                            "message": f"🎉 ካርድ #{card_num} አሸንፏል!",
                            "winner_id": 0,
                            "card_number": card_num,
                            "winning_numbers": win_nums,
                            "card_numbers": flat_card,
                            "winning_pattern": pattern
                        }
        return {"status": "CONTINUE"}

    def force_house_win(self, db, game_id, current_drawn_balls, total_pool_money, bought_cards, all_200_cards):
        winning_card_num = None
        win_nums, pattern = [], "Forced House Win"
        
        for card_num in range(1, 201):
            if card_num not in bought_cards:
                card_matrix = all_200_cards.get(str(card_num))
                if card_matrix:
                    is_win, tmp_nums, tmp_pat = self.check_bingo_patterns(card_matrix, current_drawn_balls)
                    if is_win:
                        winning_card_num = card_num
                        win_nums, pattern = tmp_nums, tmp_pat
                        break

        if not winning_card_num:
            available_ids = [idx for idx in range(1, 201) if idx not in bought_cards]
            winning_card_num = random.choice(available_ids) if available_ids else 1

        card_matrix = all_200_cards.get(str(winning_card_num), [[0]*5]*5)
        flat_card = [item for sublist in card_matrix for item in sublist]
        
        self.distribute_game_prize(db, game_id, total_pool_money, winner_user_id=None, winning_card=winning_card_num)

        return {     
            "status": "HOUSE_WIN",
            "message": f"🎉 ካርድ #{winning_card_num} አሸንፏል!",
            "winner_id": 0,
            "card_number": winning_card_num,
            "winning_numbers": win_nums,
            "card_numbers": flat_card,
            "winning_pattern": pattern
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

        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.status = "finished"
            game.winning_card = winning_card
            game.finished_at = datetime.now(timezone.utc)

        if winner_user_id:
            admin_stats.total_commission += admin_commission
            user = db.query(User).filter(User.id == winner_user_id).first()
            if user:
                user.balance += player_prize
            if game:
                game.winner_id = winner_user_id
                game.prize = player_prize
        else:
            admin_stats.house_balance += total_pool_money
            if game:
                game.winner_id = 0
                game.prize = total_pool_money

        try:
            db.commit()
        except Exception as e:
            print(f"❌ Error committing prize distribution: {e}")

engine = GameEngine()
