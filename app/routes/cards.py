import json
import random
import datetime
import asyncio
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models import User, Game, Card, PlayerCard
from app.websocket_manager import manager

router = APIRouter(prefix="/api/cards", tags=["Cards"])

class AdvancedPickCardRequest(BaseModel):
    telegram_id: str
    card_number: int
    bet_amount: float = Field(..., description="የውርርድ መጠን፡ 10, 20, ወይም 50")


# =========================================================
# 🤖 BOT HELPER LOGIC
# =========================================================
def get_bot_user(db):
    """🤖 የቦት ተጫዋች በዳታቤዝ ውስጥ መኖሩን ያረጋግጣል፤ ከሌለ ይፈጥራል።"""
    bot = db.query(User).filter(User.telegram_id == "BOT_VIRTUAL_PLAYER").first()
    if not bot:
        bot = User(
            telegram_id="BOT_VIRTUAL_PLAYER",
            telegram_name="System Bot",
            first_name="Virtual Player",
            balance=9999999.0,
            wallet=0.0,
            gift_coin=0.0,
            is_bot=True
        )
        db.add(bot)
        db.commit()
        db.refresh(bot)
    return bot

def get_target_bot_card_count() -> int:
    """🕒 በውይይታችን መሰረት የተስተካከለ ሰዓትን መሰረት ያደረገ የቦት ካርድ ብዛት (UTC+3)"""
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    hour = now.hour

    # ከጠዋቱ 12:00 እስከ ቀኑ 7:00 (ከ6:00 እስከ 12:59)
    if 6 <= hour < 13:
        return random.randint(20, 30)
    # ከቀኑ 7:00 እስከ ሌሊቱ 6:00 (ከ13:00 እስከ 23:59)
    elif 13 <= hour <= 23:
        return random.randint(30, 50)
    # ከሌሊቱ 6:00 እስከ ጠዋቱ 12:00 (ከ0:00 እስከ 5:59)
    else:
        return random.randint(30, 40)

async def trigger_bot_card_purchases(game_id: int, bet_amount: float = 10.0):
    """
    🤖 ቦቱ በ 10 ETB ክፍል ብቻ በዘፈቀደ ላልተያዙ የካርድ ቁጥሮች ተራ በተራ ግዢ ይፈጽማል።
    ✨ ካርዶቹ እውነተኛ ተጫዋቾች እንደሚገዙት ተራ በተራ በቦርዱ ላይ ቢጫ እየሆኑ ይታያሉ!
    """
    if bet_amount != 10.0:
        return

    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.id == game_id, Game.status.in_(["running", "waiting"])).first()
        if not game:
            return

        bot_user = get_bot_user(db)
        target_count = get_target_bot_card_count()

        taken_cards = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.bet_amount == bet_amount
        ).all()
        taken_numbers = {c.card_number for c in taken_cards}

        bot_current_count = sum(1 for c in taken_cards if c.user_id == bot_user.id)
        needed = target_count - bot_current_count

        if needed <= 0:
            return

        available_numbers = [num for num in range(1, 201) if num not in taken_numbers]
        cards_to_buy_count = min(needed, len(available_numbers))
        
        if cards_to_buy_count <= 0:
            return

        selected_bot_cards = random.sample(available_numbers, cards_to_buy_count)

        # 🎭 እውነተኛ ለማስመሰል ካርዶቹን ተራ በተራ (በጥቂት ሰከንድ ልዩነት) መግዛት
        for card_num in selected_bot_cards:
            active_check = db.query(Game).filter(Game.id == game_id, Game.status.in_(["running", "waiting"])).first()
            if not active_check:
                break

            bot_card = PlayerCard(
                game_id=game.id,
                user_id=bot_user.id,
                card_number=card_num,
                bet_amount=bet_amount
            )
            db.add(bot_card)

            main_card = db.query(Card).filter(Card.card_number == card_num).first()
            if main_card:
                main_card.is_taken = True
                main_card.reserved_by = bot_user.id
                main_card.current_game_id = game.id

            db.commit()

            # 📡 እያንዳንዱ ካርድ በተገዛ ቁጥር ለተጫዋቾች በየተራ ቢጫ ሆኖ እንዲታይ broadcast ማድረግ
            all_taken = db.query(PlayerCard).filter(
                PlayerCard.game_id == game.id,
                PlayerCard.bet_amount == bet_amount
            ).all()
            taken_list = [c.card_number for c in all_taken]

            await manager.broadcast({
                "type": "taken_cards_update",
                "bet_amount": bet_amount,
                "taken_cards": taken_list
            })

            # ⏱️ ተፈጥሮአዊ እንዲመስል በየካርዱ መካከል ከ 0.4 እስከ 1.2 ሰከንድ ማረፍ
            await asyncio.sleep(random.uniform(0.05, 0.15))

    except Exception as e:
        if db:
            db.rollback()
        print(f"⚠️ Bot card purchase error: {e}")
    finally:
        if db:
            db.close()


# =========================================================
# 📌 API ROUTES
# =========================================================

@router.get("/status")
def get_cards_status(
    background_tasks: BackgroundTasks,
    bet_amount: float = Query(10.0, description="የተመረጠው ክፍል ውርርድ መጠን")
):
    db = SessionLocal()
    try:
        active_game = db.query(Game).filter(Game.status.in_(["running", "waiting"])).order_by(Game.id.desc()).first()
        
        if not active_game:
            return []
            
        taken_cards = db.query(PlayerCard).filter(
            PlayerCard.game_id == active_game.id,
            PlayerCard.bet_amount == bet_amount
        ).all()

        bot_user = get_bot_user(db)
        bot_current_count = sum(1 for c in taken_cards if c.user_id == bot_user.id)
        target_count = get_target_bot_card_count()

        # 🤖 የቦቱ ካርድ መጠን ከዒላማው ያነሰ ከሆነ ባክግራውንድ ላይ ገዢ እንዲቀጥል ማነሳሳት
        if bet_amount == 10.0 and bot_current_count < target_count:
            background_tasks.add_task(trigger_bot_card_purchases, active_game.id, bet_amount)

        return [c.card_number for c in taken_cards]
    except Exception:
        return []
    finally:
        db.close()


@router.post("/pick")
async def pick_card(request: AdvancedPickCardRequest, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        if request.bet_amount not in [10.0, 20.0, 50.0]:
            return {"success": False, "message": "ያልተፈቀደ የውርርድ መጠን! እባክህ 10፣ 20 ወይም 50 ይምረጡ።"}

        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            user = User(
                telegram_id=request.telegram_id,
                telegram_name=f"User_{request.telegram_id[:5]}" if request.telegram_id else "Guest",
                first_name="Player",
                balance=0.0,
                wallet=0.0,
                gift_coin=0.0
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        game = db.query(Game).filter(Game.status.in_(["running", "waiting"])).order_by(Game.id.desc()).first()
        if not game:
            return {"success": False, "message": "በአሁኑ ሰዓት ምንም የነቃ ጨዋታ የለም። እባክህ አዲስ ዙር ጠብቅ።"}

        already_bought_count = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.user_id == user.id
        ).count()
        
        if already_bought_count >= 10:
            return {"success": False, "message": "በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርቴላ መጠን 10 ብቻ ነው!"}

        card_taken = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.card_number == request.card_number,
            PlayerCard.bet_amount == request.bet_amount
        ).first()
        if card_taken:
            return {"success": False, "message": f"ካርቴላ ቁጥር {request.card_number} በ {int(request.bet_amount)} ብር ክፍል አስቀድሞ ተይዟል!"}

        total_available = (user.balance or 0.0) + (user.gift_coin or 0.0)
        if total_available < request.bet_amount:
            return {"success": False, "message": f"በቂ ባላንስ የሎትም! የእርሶ ጠቅላላ ባላንስ {total_available} ETB ነው።"}

        if (user.gift_coin or 0.0) >= request.bet_amount:
            user.gift_coin -= request.bet_amount
        else:
            remaining_fee = request.bet_amount - (user.gift_coin or 0.0)
            user.gift_coin = 0.0
            user.balance -= remaining_fee
            user.wallet -= remaining_fee

        new_player_card = PlayerCard(
            game_id=game.id,
            user_id=user.id,
            card_number=request.card_number,
            bet_amount=request.bet_amount
        )
        db.add(new_player_card)

        main_card = db.query(Card).filter(Card.card_number == request.card_number).first()
        if main_card:
            main_card.is_taken = True
            main_card.reserved_by = user.id
            main_card.current_game_id = game.id
        
        user.total_games_played = (user.total_games_played or 0) + 1
        user.weekly_games_played = (user.weekly_games_played or 0) + 1

        db.commit()

        if request.bet_amount == 10.0:
            background_tasks.add_task(trigger_bot_card_purchases, game.id, request.bet_amount)

        try:
            all_taken = db.query(PlayerCard).filter(
                PlayerCard.game_id == game.id,
                PlayerCard.bet_amount == request.bet_amount
            ).all()
            taken_list = [c.card_number for c in all_taken]
            await manager.broadcast({
                "type": "taken_cards_update",
                "bet_amount": request.bet_amount,
                "taken_cards": taken_list
            })
        except Exception as e:
            print(f"⚠️ Live broadcast failed after pick: {e}")

        return {
            "success": True, 
            "message": "ካርቴላው በተሳካ ሁኔታ ተገዝቷል!", 
            "current_balance": user.balance,
            "current_gift": user.gift_coin,
            "card_number": request.card_number,
            "bet_amount": request.bet_amount
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"የቴክኒክ ስህተት አጋጥሟል፡ {str(e)}"}
    finally:
        db.close()


@router.get("/get_matrix")
def get_matrix(card_number: int = Query(...)):
    db = SessionLocal()
    try:
        card_info = db.query(Card).filter(Card.card_number == card_number).first()
        if card_info and card_info.data:
            try:
                matrix_data = json.loads(card_info.data)
                return {"matrix": matrix_data}
            except Exception:
                pass
                
        b = random.sample(range(1, 16), 5)
        i = random.sample(range(16, 31), 5)
        n = random.sample(range(31, 46), 5)
        g = random.sample(range(46, 61), 5)
        o = random.sample(range(61, 76), 5)
        
        generated_matrix = []
        for r_idx in range(5):
            row = [b[r_idx], i[r_idx], n[r_idx], g[r_idx], o[r_idx]]
            generated_matrix.append(row)
            
        generated_matrix[2][2] = "FREE"
        return {"matrix": generated_matrix}
        
    except Exception as e:
        return {"matrix": [[i for i in range(5)] for _ in range(5)]}
    finally:
        db.close()
