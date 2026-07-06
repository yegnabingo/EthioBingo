import random
import asyncio
import json

from sqlalchemy.orm import Session
from app.websocket_manager import manager
from app.database import SessionLocal
from app.models import Game, Setting, User, AdminStats, PlayerCard, Card


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

        # አዲስ ጨዋታ በዳታቤዝ መፍጠር
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
            # ለዌብሶኬት ተጠቃሚዎች የሰዓት ቆጣሪውን መላክ ትችላለህ
            await manager.broadcast({
                "type": "countdown",
                "seconds": seconds
            })
            await asyncio.sleep(1)
            seconds -= 1

    async def draw_numbers(self, interval):
        numbers = list(range(1, 76))
        random.shuffle(numbers)
        self.called_numbers = []

        db: Session = SessionLocal()
        
        # 💡 በዙሩ የተገዙ ካርዶችን እና የሁሉም 200 ካርዶች ማትሪክስ ውሂብ ከዳታቤዝ ማዘጋጀት
        # {'card_number': user_id}
        bought_cards = {pc.card_number: pc.user_id for pc in db.query(PlayerCard).filter(PlayerCard.game_id == self.current_game.id).all()}
        
        # የሁሉም 200 ካርዶች ማትሪክስ ውሂብ {'1': [[...]], '2': [[...]]}
        all_200_cards = {str(c.card_number): json.loads(c.data) if isinstance(c.data, str) else c.data for c in db.query(Card).all()}

        # አጠቃላይ በዙሩ የተሰበሰበውን ብር ማስላት (የተገዙ ካርዶች ብዛት * የጨዋታው መግቢያ ክፍያ)
        settings = db.query(Setting).first()
        game_fee = settings.game_fee if settings else 10
        total_pool_money = len(bought_cards) * game_fee

        winner_detected = False

        for number in numbers:
            if not self.running:
                break

            self.called_numbers.append(number)

            letter = ""
            if number <= 15: letter = "B"
            elif number <= 30: letter = "I"
            elif number <= 45: letter = "N"
            elif number <= 60: letter = "G"
            else: letter = "O"

            # ኳሱን ለሁሉም ተጫዋቾች በዌብሶኬት መላክ
            await manager.broadcast({
               "type": "ball",
               "letter": letter,
               "number": number
            })

            # 🎯 🧠 [አዲሱ ህግ] ኳስ በወደቀ ቁጥር አሸናፊ መኖሩን በሰርቨር ደረጃ መፈተሽ
            result = self.process_drawn_ball_and_check_winner(
                db, 
                self.current_game.id, 
                self.called_numbers, 
                total_pool_money, 
                bought_cards, 
                all_200_cards
            )

            if result["status"] in ["WINNER_FOUND", "HOUSE_WIN"]:
                # አሸናፊ ከተገኘ (እውነተኛ ሰውም ይሁን የቤቱ የሀሰት ስም) መልዕክቱን በዌብሶኬት እንልካለን
                await manager.broadcast({
                    "type": "game_over",
                    "status": result["status"],
                    "message": result["message"],
                    "card_number": result["card_number"],
                    "winner_id": result["winner_id"]
                })
                winner_detected = True
                break # ሉፑን አቁም (የግድ 75 ኳስ መውረድ የለበትም!)

            await asyncio.sleep(interval)

        # 🚨 75ቱም ኳሶች ወርደው ማንም በእውነተኛ ካርድ ካላሸነፈ፣ በቤቱ (Admin) አሸናፊነት እንዲዘጋጅ ማድረጊያ
        if not winner_detected and self.running:
            result = self.force_house_win(db, self.current_game.id, self.called_numbers, total_pool_money, bought_cards, all_200_cards)
            await manager.broadcast({
                "type": "game_over",
                "status": result["status"],
                "message": result["message"],
                "card_number": result["card_number"],
                "winner_id": result["winner_id"]
            })

        self.running = False
        db.close()

    # ==========================================================================
    # 🎯 የቢንጎ ማሸነፊያ 5ቱን ህግጋት መፈተሻ ሎጂክ
    # ==========================================================================
    def check_bingo_patterns(self, matrix, drawn_balls):
        drawn_set = set(drawn_balls)
        
        # 1. ↕ አግድም ቼክ ማድረጊያ (Horizontal Rows)
        for r in range(5):
            if all(matrix[r][c] in drawn_set for c in range(5) if not (r == 2 and c == 2)):
                return True

        # 2. ↔ ቁመት ቼክ ማድረጊያ (Vertical Columns)
        for c in range(5):
            if all(matrix[r][c] in drawn_set for r in range(5) if not (r == 2 and c == 2)):
                return True

        # 3. ↘ ዋና ዲያጎናል (Main Diagonal)
        if all(matrix[i][i] in drawn_set for i in range(5) if i != 2):
            return True

        # 4. ↙ ተቃራኒ ዲያጎናል (Anti-Diagonal)
        if all(matrix[i][4 - i] in drawn_set for i in range(5) if i != 2):
            return True

        # 5. 🔲 4ቱ የዳር እና ዳር ማዕዘናት (Four Corners)
        corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
        if all(matrix[r][c] in drawn_set for r, c in corners):
            return True

        return False

    def process_drawn_ball_and_check_winner(self, db, game_id, current_drawn_balls, total_pool_money, bought_cards, all_200_cards):
        # በእውነተኛ ተጫዋች የተገዙትን ካርዶች ብቻ መፈተሽ
        for card_num, user_id in bought_cards.items():
            card_matrix = all_200_cards.get(str(card_num))
            if card_matrix and self.check_bingo_patterns(card_matrix, current_drawn_balls):
                self.distribute_game_prize(db, game_id, total_pool_money, winner_user_id=user_id, winning_card=card_num)
                return {
                    "status": "WINNER_FOUND",
                    "message": f"🎉 ካርድ #{card_num} አሸንፏል!",
                    "winner_id": user_id,
                    "card_number": card_num
                }
        return {"status": "CONTINUE"}

    def force_house_win(self, db, game_id, current_drawn_balls, total_pool_money, bought_cards, all_200_cards):
        # ማንም ሳይገዛው የቀረውን ካርድ ፈልጎ ማሸነፍ
        winning_card_num = None
        for card_num in range(1, 201):
            if card_num not in bought_cards:
                card_matrix = all_200_cards.get(str(card_num))
                if card_matrix and self.check_bingo_patterns(card_matrix, current_drawn_balls):
                    winning_card_num = card_num
                    break
        
        if not winning_card_num:
            winning_card_num = random.choice([id for id in range(1, 201) if id not in bought_cards])

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
        admin_commission = total_pool_money * 0.20  # 20% ኮሚሽን ለአድሚን
        player_prize = total_pool_money * 0.80      # 80% ለአሸናፊው

        admin_stats = db.query(AdminStats).first()
        if not admin_stats:
            admin_stats = AdminStats(house_balance=0.0, total_commission=0.0)
            db.add(admin_stats)
        
        admin_stats.total_commission += admin_commission

        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.status = "finished"
            game.winning_card = winning_card

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
                
        db.commit()


# ሞተሩን አንድ ጊዜ ብቻ ፈጥረን በሌሎች ፋይሎች እንድንጠራው (Singleton Instance)
engine = GameEngine()
