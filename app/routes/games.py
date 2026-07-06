import random
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Game, User, PlayerCard, Setting

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
    
    # ተጠቃሚው በዳታቤዝ እስካሁን ከሌለ በራስ-ሰር እንመዘግበዋለን (Auto-Registration)
    if not user:
        user = User(
            telegram_id=telegram_id,
            balance=0.0,
            gift_coins=0.0,  # አድሚኑ ከሰጠው የሚታይ
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
        game = Game(
            game_no=str(int(game.game_no) + 1),  # የጨዋታውን ቁጥር በ1 መጨመር
            status="running",
            ticket_price=current_ticket_price,
            total_players=0,
            total_pool=0.0
        )
        db.add(game)
        db.commit()
        db.refresh(game)

    # 👥 3. [አዲሱ ሎጂክ] በዚሁ አክቲቭ ዙር ላይ የተገዙ ጠቅላላ የካርዶች ብዛት (Players)
    total_cards_bought = db.query(PlayerCard).filter(PlayerCard.game_id == game.id).count()

    # 💰 4. [አዲሱ ሎጂክ] ጠቅላላ የተሰበሰበው ብር (Pool) እና አሸናፊው የሚደርሰው የብር መጠን (Derash 80%)
    total_pool_money = total_cards_bought * game.ticket_price
    derash_money = total_pool_money * 0.80  # 80% ህግ

    # 🎯 5. ለተጫዋቹ የፊት ገጽ (Frontend) መረጃውን ልክ በፎቶው ስያሜ መሰረት መመለስ
    return {
        "success": True,
        "game_id": game.id,                      # የዳታቤዝ መታወቂያ
        "game_no": game.game_no,                  # Game (ለምሳሌ፡ 100481)
        "status": game.status,
        
        # 📊 ለአኒሜሽን ገጾች የሚያስፈልጉት ሰባቱ ቁልፍ መረጃዎች፡-
        "bet": game.ticket_price,                 # Bet (10, 20, 50...)
        "active_game": 1 if game.status == "running" else 0, # Active Game
        "wallet": user.balance,                   # Wallet - Real User Balance
        "gift": user.gift_coins,                  # Gift Coin (Admin የሰጠው)
        "players": total_cards_bought,            # Players (የተያዘ የካርድ ብዛት)
        "derash": derash_money,                   # Derash (ካሸነፈ የሚደርሰው የ 80% ብር)
        "total_pool": total_pool_money
    }
