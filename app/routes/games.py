import json
import random
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Game, User, PlayerCard, Setting, Card

router = APIRouter(
    prefix="/api/games",
    tags=["Games"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/current")
def current_game(
    telegram_id: str = Query(...),  # 👤 የተጫዋቹን ዋሌት እና ጊፍት ለማወቅ መታወቂያውን እንቀበላለን
    db: Session = Depends(get_db)
):
    # 1. መጀመሪያ የተጫዋቹን መረጃ ከዳታቤዝ መፈለግ
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    # 🎯 ፊክስ፦ ተጫዋቹ በዳታቤዝ ከሌለ እና በራሱ ሰርቨር ሲመዘገብ ከ crud.py እና users.py ጋር እንዲስማማ ማድረግ
    if not user:
        user = User(
            telegram_id=telegram_id,
            telegram_name=f"User_{telegram_id}",
            first_name="Player",
            balance=0.0,
            wallet=0.0,      # ሁለቱንም የሞዴል አማራጮች ለመጠበቅ
            gift_coin=0.0,   # ከቀድሞው ሞዴል 'gift_coin' ጋር ስሙ ተስተካክሏል
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. የመጨረሻውን የነቃ ጨዋታ (Active Game) መፈለግ
    game = db.query(Game).order_by(Game.id.desc()).first()

    # ⚙️ የሲስተሙን የመግቢያ ዋጋ (Setting) ማምጣት (ከሌለ Default 10 ብር)
    settings = db.query(Setting).first()
    current_ticket_price = settings.game_fee if settings else 10.0

    # 💡 ጨዋታ በዳታቤዝ ውስጥ ጨርሶ ከሌለ አዲስ መፍጠር
    if not game:
        game = Game(
            game_no=str(random.randint(100000, 199999)),  # ልክ በፎቶው ላይ እንዳለው (ለምሳሌ፡ 100481)
            status="running",
            ticket_price=current_ticket_price,
            total_players=0,
            total_pool=0.0
        )
        db.add(game)
        db.commit()
        db.refresh(game)

    # 🔄 ጨዋታው ካለቀ አዲስ የነቃ ጨዋታ ማዘጋጀት (Auto-Loop)
    elif game.status == "finished":
        # 🛠 ፊክስ፦ የቁጥር ግጭትን ለመከላከል ቁጥሩ ትክክለኛ ኢንቲጀር መሆኑን ማረጋገጥ
        try:
            next_game_no = str(int(game.game_no) + 1)
        except ValueError:
            next_game_no = str(random.randint(200000, 299999))

        game = Game(
            game_no=next_game_no,  # የጨዋታውን ቁጥር በ1 መጨመር
            status="running",
            ticket_price=current_ticket_price,
            total_players=0,
            total_pool=0.0
        )
        db.add(game)
        db.commit()
        db.refresh(game)

    # 👥 3. በዚሁ አክቲቭ ዙር ላይ የተገዙ ጠቅላላ የካርዶች ብዛት (Players)
    total_cards_bought = db.query(PlayerCard).filter(PlayerCard.game_id == game.id).count()

    # 💰 4. ጠቅላላ የተሰበሰበው ብር (Pool) እና አሸናፊው የሚደርሰው የብር መጠን (Derash 80%)
    total_pool_money = total_cards_bought * game.ticket_price
    derash_money = total_pool_money * 0.80  # 80% ህግ

    # 🎯 5. ለተጫዋቹ የፊት ገጽ (Frontend) እና ለቦቱ መረጃውን መመለስ
    return {
        "success": True,
        "game_id": game.id,                      # የዳታቤዝ መታወቂያ
        "game_no": game.game_no,                  # Game (ለምሳሌ፡ 100481)
        "status": game.status,
        
        # 📊 ለአኒሜሽን ገጾች የሚያስፈልጉት ሰባቱ ቁልፍ መረጃዎች፦
        "bet": game.ticket_price,                 # Bet (10, 20, 50...)
        "active_game": 1 if game.status == "running" else 0, # Active Game
        
        # 🎯 ፊክስ፦ ፍሮንትኤንዱም ሆነ ቴሌግራም ቦቱ በየትኛውም ስም ቢፈልጉት እንዳያጡት ሁለቱንም በአንድ ላይ እንልካለን
        "wallet": user.balance,                   # ለአሮጌው ፍሮንትኤንድ/ቦት ሎጂክ
        "balance": user.balance,                  # ለአዲሱ የተስተካከለው ሎጂክ
        
        "gift": user.gift_coin,                   # Gift Coin (የተስተካከለ)
        "players": total_cards_bought,            # Players (የተያዘ የካርድ ብዛት)
        "derash": round(derash_money, 2),         # Derash (ካሸነፈ የሚደርሰው የ 80% ብር)
        "total_pool": total_pool_money
    }


# 📜 6. ያለፉትን ጨዋታዎች እና የሁሉንም አሸናፊዎች መረጃ የሚመልስ API
@router.get("/history/{telegram_id}")
def get_game_history(telegram_id: str, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {"success": False, "history": []}

    # 1. ያለፉትን 10 ያለቁ ጨዋታዎች ማውጣት
    recent_games = db.query(Game).filter(Game.status == "finished").order_by(Game.id.desc()).limit(10).all()

    history_data = []

    for g in recent_games:
        # ተጫዋቹ በዚህ ጨዋታ የመረጣቸውን/የገዛቸውን ካርዶች መፈለግ
        user_cards = db.query(PlayerCard.card_number).filter(
            PlayerCard.game_id == g.id,
            PlayerCard.user_id == user.id
        ).all()
        user_card_numbers = [c[0] for c in user_cards]

        # 🎯 የሁሉንም አሸናፊዎች መረጃ የሚይዝ List/Array
        winners_list = []
        
        # 🔴 1. በቅድሚያ game_engine.py የፃፈውን winners_info (ባለብዙ አሸናፊዎች) የማንበብ ሎጂክ
        if hasattr(g, 'winners_info') and g.winners_info:
            try:
                raw_winners = json.loads(g.winners_info)
                if isinstance(raw_winners, list) and len(raw_winners) > 0:
                    # 🔄 በዙሩ ያሸነፉትን የሁሉም ተጫዋቾች መረጃ በ Loop መሰብሰብ
                    for w_item in raw_winners:
                        winning_card_grid = None
                        win_card_num = w_item.get("winning_card_number") or w_item.get("card_number")
                        if win_card_num:
                            try:
                                card_obj = db.query(Card).filter(Card.card_number == int(win_card_num)).first()
                                if card_obj and card_obj.data:
                                    winning_card_grid = json.loads(card_obj.data) if isinstance(card_obj.data, str) else card_obj.data
                            except Exception:
                                winning_card_grid = None

                        winners_list.append({
                            "winner_name": w_item.get("winner_name") or w_item.get("telegram_name") or "ተጫዋች",
                            "winner_phone": w_item.get("phone_number", "ያልተመዘገበ"),
                            "winning_card_number": win_card_num or "N/A",
                            "prize": w_item.get("prize", 0.0),
                            "drawn_balls": json.loads(g.drawn_balls) if g.drawn_balls else [],
                            "card_grid": winning_card_grid
                        })
            except Exception as e:
                print("Error parsing winners_info in history route:", e)

        # 🔴 2. winners_info ከሌለ ወይም ባዶ ከሆነ (Fallback)
        if not winners_list and g.winner_id is not None:
            winner_user = db.query(User).filter(User.id == g.winner_id).first()
            w_name = (winner_user.telegram_name or winner_user.first_name) if winner_user else "ተጫዋች"
            w_phone = getattr(winner_user, 'phone_number', "ያልተመዘገበ") if winner_user else "ያልተመዘገበ"

            winning_card_grid = None
            if g.winning_card:
                try:
                    first_win_card_num = int(str(g.winning_card).split(',')[0])
                    card_obj = db.query(Card).filter(Card.card_number == first_win_card_num).first()
                    if card_obj and card_obj.data:
                        winning_card_grid = json.loads(card_obj.data) if isinstance(card_obj.data, str) else card_obj.data
                except Exception:
                    winning_card_grid = None

            winners_list.append({
                "winner_name": w_name,
                "winner_phone": w_phone,
                "winning_card_number": g.winning_card or "N/A",
                "prize": g.prize or 0.0,
                "drawn_balls": json.loads(g.drawn_balls) if g.drawn_balls else [],
                "card_grid": winning_card_grid
            })

        history_data.append({
            "game_id": g.id,
            "game_no": getattr(g, "game_no", str(100000 + g.id)),
            "user_picked_cards": user_card_numbers,
            "winners": winners_list,  # 👈 የሁሉም አሸናፊዎች Array
            "winner": winners_list[0] if winners_list else None # 👈 ለአሮጌ Frontend ተኳሃኝነት
        })

    return {"success": True, "history": history_data}
