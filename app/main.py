import asyncio
import random
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.websocket_manager import manager
from app.database import Base, engine as db_engine, SessionLocal
from app.init_db import initialize_database
from app.models import User, Game, Card, PlayerCard

# 1. የዳታቤዝ ቴብሎችን መፍጠር
Base.metadata.create_all(bind=db_engine)


# -----------------------------------------------------------------------
# 🏆 የቢንጎ አሸናፊነት መቆጣጠሪያ ረዳት ፈንክሽኖች (Winning Checker Logic)
# -----------------------------------------------------------------------

def check_bingo_winning_patterns(matrix, drawn_numbers):
    """የተጫዋቹን 5x5 ማትሪክስ እና የወረዱትን ኳሶች በማነጻጸር ማሸነፉን ያረጋግጣል"""
    if not matrix or len(matrix) != 5:
        return False

    marked = [[False for _ in range(5)] for _ in range(5)]
    for r in range(5):
        for c in range(5):
            val = matrix[r][c]
            if val == "FREE" or val in drawn_numbers:
                marked[r][c] = True

    # ✅ ሀ. አግድም ፍተሻ (Horizontal Lines)
    for r in range(5):
        if all(marked[r]):
            return True

    # ✅ ለ. ቁመት ፍተሻ (Vertical Lines)
    for c in range(5):
        if all(marked[r][c] for r in range(5)):
            return True

    # ✅ ሐ. ዋና ዲያጎናል ፍተሻ (↘)
    if all(marked[i][i] for i in range(5)):
        return True

    # ✅ መ. ተቃራኒ ዲያጎናል ፍተሻ (↙)
    if all(marked[i][4 - i] for i in range(5)):
        return True

    return False


def get_bingo_letter(ball_number):
    """ቁጥሩ በየትኛው የቢንጎ ፊደል ስር እንዳለ ለይቶ ይሰጣል"""
    if 1 <= ball_number <= 15:
        return "B"
    elif 16 <= ball_number <= 30:
        return "I"
    elif 31 <= ball_number <= 45:
        return "N"
    elif 46 <= ball_number <= 60:
        return "G"
    elif 61 <= ball_number <= 75:
        return "O"
    return ""


# -----------------------------------------------------------------------
# 🔄 ዋናው አውቶማቲክ የጨዋታ ሉፕ ሞተር (Automated Game Loop Engine)
# -----------------------------------------------------------------------

async def run_automated_game_loop():
    print("🎯 የቢንጎ ሰዓት መቁጠሪያ ሞተር በጀርባ ስራ ጀምሯል...")
    
    while True:
        db = SessionLocal()
        current_game_id = None
        game_display_no = "000000"
        
        try:
            active_game = db.query(Game).filter(Game.status == "running").first()
            if not active_game:
                active_game = Game(
                    status="running",
                    started_at=datetime.utcnow()
                )
                db.add(active_game)
                db.commit()
                db.refresh(active_game)
            
            current_game_id = active_game.id
            game_display_no = str(100000 + active_game.id)
            
        except Exception as e:
            print(f"❌ Database game session error: {e}")
        finally:
            db.close()

        # --- ምዕራፍ 1፦ PICK PHASE (30 ሰከንድ መቁጠሪያ) ---
        for seconds_left in range(30, -1, -1):
            await manager.broadcast({
                "type": "time_update",
                "time": seconds_left,
                "phase": "PICK",
                "game_no": game_display_no
            })
            await asyncio.sleep(1)
        
        # --- ምዕራፍ 2፦ DRAW PHASE ---
        await manager.broadcast({
            "type": "phase_change",
            "phase": "DRAW",
            "game_no": game_display_no
        })
        
        bingo_balls = list(range(1, 76))
        random.shuffle(bingo_balls)
        
        drawn_numbers = []
        call_count = 0
        winners_found = []
        
        # --- ምዕራፍ 3፦ ኳስ መጣል እና አሸናፊ መፈለግ ---
        for ball in bingo_balls:
            call_count += 1
            drawn_numbers.append(ball)
            
            letter = get_bingo_letter(ball)
            ball_label = f"{letter}{ball}"
            
            await manager.broadcast({
                "type": "ball",
                "number": ball,
                "label": ball_label,
                "call_count": call_count,
                "game_no": game_display_no
            })
            
            db = SessionLocal()
            try:
                active_player_cards = db.query(PlayerCard).filter(PlayerCard.game_id == current_game_id).all()
                
                for p_card in active_player_cards:
                    card_info = db.query(Card).filter(Card.card_number == p_card.card_number).first()
                    if card_info and card_info.data:
                        try:
                            matrix = json.loads(card_info.data)
                        except Exception:
                            continue
                        
                        if check_bingo_winning_patterns(matrix, drawn_numbers):
                            winners_found.append(p_card)
                
                if winners_found:
                    print(f"🎉 🎉 BINGO! {len(winners_found)} አሸናፊ(ዎች) ተገኝተዋል!")
                    db.close()
                    break
            except Exception as e:
                print(f"❌ Winning check error: {e}")
            finally:
                db.close()
                
            await asyncio.sleep(2)

        # --- ምዕራፍ 4፦ ሂሳብ ማውራረድ እና 20% ኮሚሽን መቁረጥ (Payout Phase) ---
        db = SessionLocal()
        winner_names = []  # 💡 [ማስተካከያ] ሁልጊዜ መጀመሪያ 'winner_names' መፈጠር አለበት (ሎግ ላይ የነበረውን Error ይፈታል)
        
        try:
            game_obj = db.query(Game).filter(Game.id == current_game_id).first()
            
            if winners_found:
                total_cards_count = db.query(PlayerCard).filter(PlayerCard.game_id == current_game_id).count()
                total_pool = total_cards_count * 10.0 
                
                house_commission = total_pool * 0.20
                prize_pool = total_pool * 0.80
                per_winner_prize = prize_pool / len(winners_found)
                
                for winner_card in winners_found:
                    user_acc = db.query(User).filter(User.id == winner_card.user_id).first()
                    if user_acc:
                        user_acc.balance += per_winner_prize
                        winner_names.append(user_acc.telegram_name or f"User_{user_acc.telegram_id[:4]}")
                    else:
                        winner_names.append("የማይታወቅ ተጫዋች")
                    
                    winner_card.is_winner = True
                
                if game_obj:
                    game_obj.status = "finished"
                    game_obj.finished_at = datetime.utcnow()
                    game_obj.prize = prize_pool
                    game_obj.winner_id = winners_found[0].user_id
                    game_obj.winning_card = winners_found[0].card_number
                
                db.commit()
                
                # 🏆 አሸናፊውን ፖፕ-አፕ የሚያሳየው መረጃ ወደ ዌብሶኬት ተላከ
                await manager.broadcast({
                    "type": "game_over",
                    "result": "BINGO",
                    "winner_name": ", ".join(winner_names),
                    "winning_card": winners_found[0].card_number,
                    "prize": round(per_winner_prize, 2),
                    "message": f"🎉 እንኳን ደስ አላችሁ! {', '.join(winner_names)} በካርድ ቁጥር #{winners_found[0].card_number} ቢንጎ በልቷል!"
                })
                print(f"🏁 Game ID {current_game_id} በአሸናፊዎች ተዘጋ።")
            else:
                if game_obj:
                    game_obj.status = "finished"
                    game_obj.finished_at = datetime.utcnow()
                db.commit()
                
                await manager.broadcast({
                    "type": "game_over",
                    "result": "NO_WINNER",
                    "message": "ምንም አሸናፊ ሳይገኝ በዚህ ዙር ኳስ አልቋል።"
                })
                print(f"🏁 Game ID {current_game_id} ያለምንም አሸናፊ ተጠናቋል።")
                
        except Exception as e:
            print(f"❌ Error during payout processing: {e}")
        finally:
            db.close()

        await asyncio.sleep(5)


# -----------------------------------------------------------------------
# 🚀 የ Lifespan እና የ FastAPI መነሻ መዋቅር
# -----------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 40)
    print(" 🎯 Pick & Win V3 Starting...")
    print("=" * 40)
    try:
        initialize_database()
        print("✅ Database Initialization Complete.")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")
        
    game_loop_task = asyncio.create_task(run_automated_game_loop())
    yield
    game_loop_task.cancel()
    print("🛑 Server Stopped")


app = FastAPI(title="Pick & Win V3", version="3.0.0", lifespan=lifespan)

# 📡 ዌብሶኬት ማገናኛ ሎጂክ - [ትክክለኛው ማስተካከያ]
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # 💡 እዚህ ላይ የነበረው 'await websocket.accept()' ተነስቷል!
    # ምክንያቱም 'manager.connect(websocket)' በውስጡ በራሱ አክሴፕት ያደርጋል።
    await manager.connect(websocket)
    try:
        while True:
            # ከብሮውዘሩ የሚላክ ዳታ ካለ ዝም ብሎ መቀበል (ግንኙነቱ እንዳይዘጋ)
            await websocket.receive_text()
    except Exception as e:
        print(f"Websocket disconnected: {e}")
    finally:
        manager.disconnect(websocket)

# የራውተሮች ማገናኛ
from app.routes.cards import router as cards_router
from app.routes.users import router as users_router
from app.routes.deposit import router as deposit_router
from app.routes.admin import router as admin_router
from app.routes.withdraw import router as withdraw_router
from app.routes.games import router as games_router

app.include_router(cards_router)
app.include_router(users_router)
app.include_router(deposit_router)
app.include_router(admin_router)
app.include_router(withdraw_router)
app.include_router(games_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root(): return FileResponse("static/index.html")

@app.get("/health")
async def health(): return {"status": "OK"}
