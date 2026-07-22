import random
import asyncio
import json
import inspect
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.websocket_manager import manager
from app.database import SessionLocal
from app.models import Game, Setting, User, AdminStats, PlayerCard, Card

BOT_NAMES = [
   "user_454567", "user_3561655", "user_998767", "user_6578866", "user_765465", "user_436688",  
    "user_3456856", "user_564888", "user_8654519", "user_988786", "user_213456", "user_654321",
    "user_4325677", "user_789646", "user_35567655", "user_456787", "user_344565", "user_3243567",
]

SUPPORTED_FEES = [10.0, 20.0, 50.0]

class GameEngine:

    def __init__(self):
        self.running = False
        self.called_numbers = []
        self.current_game = None
        # 📌 ለእያንዳንዱ ክፍል የቤት (House) ማሸነፊያ ቆጣሪ
        self.house_counters = {10.0: 0, 20.0: 0, 50.0: 0}

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

                countdown_seconds = settings.countdown_seconds if (settings and hasattr(settings, 'countdown_seconds')) else 30
                
                # ⏱️ 🔴 የጥሪው ፍጥነት በየ 3 ሰከንድ እንዲሆን ነባሪው እሴት 3.0 ተደርጓል
                draw_interval = settings.draw_interval if (settings and hasattr(settings, 'draw_interval')) else 3.0

                game = Game(
                    status="running",
                    started_at=datetime.now(timezone.utc),
                    taken_cards="[]",
                    drawn_balls="[]"
                )
                db.add(game)
                db.commit()
                db.refresh(game)
                
                saved_game_id = game.id
                self.current_game = game
                game_display_no = str(100000 + saved_game_id)
                
                # 📌 ቢያንስ 3 ካርዶች ከተሸጡ ብቻ ነው ወደ draw_numbers የሚሸጋገረው
                has_bought_cards = await self.countdown(countdown_seconds, game_display_no, saved_game_id)

                if self.running and has_bought_cards:
                    await self.draw_numbers(draw_interval, game_display_no, saved_game_id)
                else:
                    print(f"🔄 Game {game_display_no} ላይ አስፈላጊው የካርድ ብዛት አልተሟላም። ዑደቱ እንደገና ይጀምራል።")
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
        initial_seconds = seconds
        has_bought_cards = False
        
        while seconds >= 0 and self.running:
            current_taken_list = []
            comm_percent = 20.0
            player_counts = {fee: 0 for fee in SUPPORTED_FEES}
            total_cards_sold = 0
            unique_users_count = 0
            
            db: Session = None
            try:
                db = SessionLocal()
                taken_cards = db.query(Card.card_number).filter(Card.is_taken == True).all()
                current_taken_list = [c[0] for c in taken_cards]
                
                settings = db.query(Setting).first()
                if settings and hasattr(settings, 'game_commission_percent'):
                    comm_percent = settings.game_commission_percent

                for fee in SUPPORTED_FEES:
                    count = db.query(PlayerCard).filter(
                        PlayerCard.game_id == saved_game_id, 
                        PlayerCard.bet_amount == fee
                    ).count()
                    player_counts[fee] = count

                total_cards_sold = db.query(PlayerCard).filter(PlayerCard.game_id == saved_game_id).count()
                unique_users_count = db.query(PlayerCard.user_id).filter(PlayerCard.game_id == saved_game_id).distinct().count()

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

            # 📌 ቢያንስ 3 ካርድ ከተለያየ user ካልተሸጠ ቆጣሪውን ዳግም ማስጀመር
            if seconds == 0:
                if total_cards_sold < 3 or unique_users_count < 1:
                    print(f"⏳ ካርድ አልተሟላም (የተሸጡ፡ {total_cards_sold}/3)። ቆጣሪው እንደገና ወደ {initial_seconds}s ይመለሳል።")
                    seconds = initial_seconds
                    
                    await self.safe_broadcast({
                        "type": "countdown",
                        "seconds": seconds,
                        "time": seconds,
                        "phase": "PICK",
                        "game_no": game_display_no,
                        "game_id": saved_game_id,
                        "taken_cards": current_taken_list,
                        "derash_rooms": {}, 
                        "player_counts": player_counts,
                        "player_count": total_cards_sold,
                        "message": "⚠️ ቢያንስ 3 ካርዶች መሸጥ አለባቸው! ጨዋታው ተራዝሟል።"
                    })
                    await asyncio.sleep(1)
                    continue
                else:
                    has_bought_cards = True

            derash_amounts = {}
            total_players_all_rooms = 0
            for fee, count in player_counts.items():
                total_players_all_rooms += count
                total_pool = count * fee
                derash_ratio = (100.0 - comm_percent) / 100.0
                derash_amounts[str(int(fee))] = int(total_pool * derash_ratio)

            payload = {
                "type": "countdown",
                "seconds": seconds,
                "time": seconds,
                "phase": "PICK",
                "game_no": game_display_no,
                "game_id": saved_game_id,
                "taken_cards": current_taken_list,
                "derash_rooms": derash_amounts, 
                "player_counts": player_counts,
                "player_count": total_players_all_rooms
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
            bought_cards = {}
            for pc in db.query(PlayerCard).filter(PlayerCard.game_id == saved_game_id).all():
                bought_cards[pc.card_number] = {"user_id": pc.user_id, "bet_amount": pc.bet_amount}

            all_200_cards = {}
            for c in db.query(Card).all():
                card_data = json.loads(c.data) if isinstance(c.data, str) else c.data
                all_200_cards[str(c.card_number)] = card_data

            settings = db.query(Setting).first()
            comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0
            
            target_house_wins = settings.house_win_ratio if (settings and hasattr(settings, 'house_win_ratio')) else 3

            pools_by_fee = {}
            derash_by_fee = {}
            active_rooms = []
            
            for fee in SUPPORTED_FEES:
                count = sum(1 for c in bought_cards.values() if c["bet_amount"] == fee)
                pools_by_fee[fee] = count * fee
                derash_by_fee[str(int(fee))] = int(pools_by_fee[fee] * ((100.0 - comm_percent) / 100.0))
                if count > 0:
                    active_rooms.append(fee)

            room_status = {}
            force_all = True
            
            # 🎯 🔴 የጥንቁቅ ማሸነፊያ ሎጂክ እና የኳስ መገደቢያ
            if target_house_wins == 0:
                # Setting ላይ 0 ከተደረገ ሁልጊዜ ተጫዋች (USER) ብቻ እንዲያሸንፍ ይፈቀዳል (ተጫዋች ቢንጎ እስኪል ጥሪው ይ ቀጥላል)
                for fee in SUPPORTED_FEES:
                    room_status[fee] = "ALLOW_PLAYER"
                max_draw_balls = 75 
            else:
                # Setting ላይ 1, 2, 3... ከተደረገ ኳሱ በምንም ተአምር ከ 20 አይበልጥም!
                for fee in SUPPORTED_FEES:
                    if self.house_counters.get(fee, 0) >= target_house_wins:
                        room_status[fee] = "ALLOW_PLAYER"
                        force_all = False
                    else:
                        room_status[fee] = "FORCE_HOUSE"

                # 📌 በከፍተኛው 20 ኳስ ብቻ ይገደባል (ከ 12 እስከ 20)
                max_draw_balls = random.randint(12, 20)

            winner_detected = False

            await self.safe_broadcast({
                "type": "phase_change",
                "phase": "DRAW",
                "game_no": game_display_no,
                "derash_rooms": derash_by_fee
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
                   "derash_rooms": derash_by_fee
                })

                result = self.process_drawn_ball_and_check_winner_v3(
                    db, saved_game_id, self.called_numbers, pools_by_fee, bought_cards, all_200_cards, room_status
                )

                if result["status"] == "WINNER_FOUND":
                    winners_list = result["winners"]
                    
                    for w in winners_list:
                        fee = w["bet_amount"]
                        self.house_counters[fee] = 0
                        print(f"🎉 እውነተኛ ተጫዋች በ {fee} ብር ክፍል አሸንፏል! ቆጣሪው ጸድቷል።")

                    winners_data = []
                    for w in winners_list:
                        user_record = db.query(User).filter(User.id == w["winner_id"]).first()
                        telegram_name = user_record.telegram_name if user_record and user_record.telegram_name else f"User_{w['winner_id']}"
                        
                        winners_data.append({
                            "winner_id": w["winner_id"],
                            "telegram_name": telegram_name,
                            "card_number": w["card_number"],
                            "room_fee": w["bet_amount"],
                            "prize": round(w["prize_share"], 2),
                            "winning_numbers": w["winning_numbers"],
                            "card_numbers": w["card_numbers"],
                            "winning_reason": w["winning_pattern"]
                        })

                    primary_winner = winners_data[0]

                    await self.safe_broadcast({
                        "type": "game_over",
                        "status": "WINNER_FOUND",
                        "result": "BINGO",
                        "winner_name": primary_winner["telegram_name"],
                        "winning_card": primary_winner["card_number"],
                        "prize": primary_winner["prize"],
                        "room_fee": primary_winner["room_fee"],
                        "message": f"🎉 በዙሩ {len(winners_data)} አሸናፊዎች ተገኝተው የየክፍላቸውን ሽልማት ተካፍለዋል!",
                        "card_number": primary_winner["card_number"],
                        "winner_id": primary_winner["winner_id"],
                        "winning_numbers": primary_winner["winning_numbers"], 
                        "card_numbers": primary_winner["card_numbers"],       
                        "winning_reason": primary_winner["winning_reason"],
                        "winners": winners_data
                    })
                    winner_detected = True
                    break

                if call_count >= max_draw_balls:
                    break

                # ⏱️ በየ 3 ሰከንዱ እንዲጠራ የተደረገበት ቦታ
                await asyncio.sleep(interval)

            # 🤖 3. የሀውስ/ቦት ማሸነፊያ ክፍል (የሚሰራው target_house_wins > 0 ሆኖ እውነተኛ ተጫዋች ካላሸነፈ ብቻ ነው)
            if not winner_detected and self.running and target_house_wins > 0:
                result = self.force_house_win(db, saved_game_id, self.called_numbers, pools_by_fee, bought_cards, all_200_cards)
                winner_name = random.choice(BOT_NAMES)

                for fee in active_rooms:
                    self.house_counters[fee] = self.house_counters.get(fee, 0) + 1
                    print(f"🤖 House Win በ {fee} ብር ክፍል! የአሁኑ ቆጣሪ፦ {self.house_counters[fee]}/{target_house_wins}")

                primary_bot_fee = active_rooms[0] if active_rooms else 10.0
                bot_prize_display = derash_by_fee.get(str(int(primary_bot_fee)), 0)

                await self.safe_broadcast({
                    "type": "game_over",
                    "status": "WINNER_FOUND",
                    "result": "BINGO",
                    "winner_name": winner_name,
                    "winning_card": result["card_number"],
                    "prize": round(bot_prize_display, 2),
                    "message": f"🎉 ካርድ #{result['card_number']} ({winner_name}) በ {int(primary_bot_fee)} ብር ክፍል አሸንፏል!",
                    "card_number": result["card_number"],
                    "winner_id": result["winner_id"],
                    "winning_numbers": result.get("winning_numbers", []),
                    "card_numbers": result.get("card_numbers", []),
                    "winning_reason": result.get("winning_pattern", "ቢንጎ"),
                    "winners": [{
                        "winner_id": result["winner_id"],
                        "telegram_name": winner_name,
                        "card_number": result["card_number"],
                        "room_fee": primary_bot_fee,
                        "prize": round(bot_prize_display, 2),
                        "winning_numbers": result.get("winning_numbers", []),
                        "card_numbers": result.get("card_numbers", []),
                        "winning_reason": result.get("winning_pattern", "ቢንጎ")
                    }]
                })
        except Exception as e:
            print(f"❌ Error in draw_numbers execution tracking: {e}")
        finally:
            if db:
                db.close()

    def check_bingo_patterns(self, matrix, drawn_balls):
        if not matrix or len(matrix) != 5 or any(len(row) != 5 for row in matrix):
            return False, [], ""

        drawn_set = set(drawn_balls)
        drawn_set.add("FREE")
        drawn_set.add(None)

        for r in range(5):
            if all(matrix[r][c] in drawn_set for c in range(5)):
                return True, [matrix[r][c] for c in range(5)], "Horizontal Row"
        for c in range(5):
            if all(matrix[r][c] in drawn_set for r in range(5)):
                return True, [matrix[r][c] for r in range(5)], "Vertical Column"
        if all(matrix[i][i] in drawn_set for i in range(5)):
            return True, [matrix[i][i] for i in range(5)], "Diagonal Down"
        if all(matrix[i][4 - i] in drawn_set for i in range(5)):
            return True, [matrix[i][4 - i] for i in range(5)], "Diagonal Up"
        corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
        if all(matrix[r][c] in drawn_set for r, c in corners):
            return True, [matrix[r][c] for r, c in corners], "4 Corners"

        return False, [], ""

    def process_drawn_ball_and_check_winner_v3(self, db, game_id, current_drawn_balls, pools_by_fee, bought_cards, all_200_cards, room_status):
        detected_winners = []
        
        for card_num, card_info in bought_cards.items():
            fee = card_info["bet_amount"]
            
            if room_status.get(fee) == "FORCE_HOUSE":
                continue

            card_matrix = all_200_cards.get(str(card_num))
            if card_matrix:
                is_win, win_nums, pattern = self.check_bingo_patterns(card_matrix, current_drawn_balls)
                if is_win:
                    flat_card = [item for sublist in card_matrix for item in sublist]
                    detected_winners.append({
                        "winner_id": card_info["user_id"],
                        "card_number": card_num,
                        "bet_amount": fee,
                        "winning_numbers": win_nums,
                        "card_numbers": flat_card,
                        "winning_pattern": pattern
                    })
        
        if detected_winners:
            room_winner_counts = {}
            for w in detected_winners:
                f = w["bet_amount"]
                room_winner_counts[f] = room_winner_counts.get(f, 0) + 1
            
            settings = db.query(Setting).first()
            comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0
            
            # 📌 እያንዳንዱ አሸናፊ የሚወስደው የራሱን ክፍል Derash ብቻ ነው!
            for w in detected_winners:
                f = w["bet_amount"]
                room_total_pool = pools_by_fee.get(f, 0)
                
                admin_commission = room_total_pool * (comm_percent / 100.0)
                total_room_player_prize = room_total_pool - admin_commission 
                
                winners_in_this_room = room_winner_counts[f]
                w["prize_share"] = total_room_player_prize / winners_in_this_room

            self.distribute_multi_room_prize_v2(db, game_id, pools_by_fee, detected_winners)
            
            return {
                "status": "WINNER_FOUND",
                "winners": detected_winners
            }
            
        return {"status": "CONTINUE"}

    def distribute_multi_room_prize_v2(self, db, game_id, pools_by_fee, detected_winners):
        settings = db.query(Setting).first()
        comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0

        admin_stats = db.query(AdminStats).first()
        if not admin_stats:
            admin_stats = AdminStats(house_balance=0.0, total_commission=0.0)
            db.add(admin_stats)

        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.status = "finished"
            game.winning_card = ",".join([str(w["card_number"]) for w in detected_winners])
            game.finished_at = datetime.now(timezone.utc)
            game.winner_id = detected_winners[0]["winner_id"]
            game.prize = sum([w["prize_share"] for w in detected_winners])

        winning_fees = set([w["bet_amount"] for w in detected_winners])
        
        # 📌 1. አሸናፊዎች የየክፍላቸውን ደራሽ ብቻ ወደ ባላንሳቸው ያስገባሉ
        for w in detected_winners:
            user = db.query(User).filter(User.id == w["winner_id"]).first()
            if user:
                user.balance += w["prize_share"]
                
        # 📌 2. የአድሚን ኮሚሽን እና ያልተሸነፉ ክፍሎች (House Balance) ስሌት
        for fee, room_pool in pools_by_fee.items():
            if room_pool <= 0:
                continue
            admin_commission = room_pool * (comm_percent / 100.0)
            admin_stats.total_commission += admin_commission

            # በዚያ ክፍል አሸናፊ ከሌለ ገቢው ሙሉ በሙሉ ወደ House ገቢ ይሄዳል
            if fee not in winning_fees:
                admin_stats.house_balance += (room_pool - admin_commission)

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Error committing prize distribution: {e}")

    def force_house_win(self, db, game_id, current_drawn_balls, pools_by_fee, bought_cards, all_200_cards):
        available_ids = [idx for idx in range(1, 201) if idx not in bought_cards]
        winning_card_num = random.choice(available_ids) if available_ids else 1
        card_matrix = all_200_cards.get(str(winning_card_num), [[0]*5 for _ in range(5)])
        
        possible_patterns = []
        if len(card_matrix) == 5:
            for r in range(5):
                possible_patterns.append(([card_matrix[r][c] for c in range(5)], f"Horizontal Row {r+1}"))
            for c in range(5):
                possible_patterns.append(([card_matrix[r][c] for r in range(5)], f"Vertical Column {c+1}"))
            possible_patterns.append(([card_matrix[i][i] for i in range(5)], "Diagonal Down"))
            possible_patterns.append(([card_matrix[i][4-i] for i in range(5)], "Diagonal Up"))
            corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
            possible_patterns.append(([card_matrix[r][c] for r, c in corners], "4 Corners"))

        drawn_set = set(current_drawn_balls)
        if possible_patterns:
            best_pattern_nums, best_pattern_name = max(
                possible_patterns, 
                key=lambda p: sum(1 for n in p[0] if n in drawn_set or n in ["FREE", None])
            )
        else:
            best_pattern_nums, best_pattern_name = [], "ቢንጎ"
        
        for num in best_pattern_nums:
            if num and num != "FREE" and num not in self.called_numbers:
                self.called_numbers.append(num)

        game_record = db.query(Game).filter(Game.id == game_id).first()
        if game_record:
            game_record.drawn_balls = json.dumps(self.called_numbers)

        win_nums = [n for n in best_pattern_nums if n and n != "FREE"]
        pattern = best_pattern_name

        flat_card = [item for sublist in card_matrix for item in sublist] if len(card_matrix) == 5 else []
        
        self.distribute_multi_room_prize(db, game_id, pools_by_fee, winner_user_id=None, winning_card=winning_card_num)

        return {     
            "status": "HOUSE_WIN",
            "winner_id": 0,
            "card_number": winning_card_num,
            "winning_numbers": win_nums,
            "card_numbers": flat_card,
            "winning_pattern": pattern
        }

    def distribute_multi_room_prize(self, db, game_id, pools_by_fee, winner_user_id=None, winning_card=None, winning_fee=None):
        settings = db.query(Setting).first()
        comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0

        admin_stats = db.query(AdminStats).first()
        if not admin_stats:
            admin_stats = AdminStats(house_balance=0.0, total_commission=0.0)
            db.add(admin_stats)

        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.status = "finished"
            game.winning_card = str(winning_card)
            game.finished_at = datetime.now(timezone.utc)

        for fee, total_pool_money in pools_by_fee.items():
            if total_pool_money <= 0:
                continue

            admin_commission = total_pool_money * (comm_percent / 100.0)
            player_prize = total_pool_money - admin_commission

            if winner_user_id and fee == winning_fee:
                admin_stats.total_commission += admin_commission
                user = db.query(User).filter(User.id == winner_user_id).first()
                if user:
                    user.balance += player_prize
                
                if game:
                    game.winner_id = winner_user_id
                    game.prize = player_prize
            else:
                admin_stats.total_commission += admin_commission
                admin_stats.house_balance += player_prize
                
                if not winner_user_id and game:
                    game.winner_id = 0
                    game.prize = sum(pools_by_fee.values())

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Error committing prize distribution: {e}")

engine = GameEngine()
