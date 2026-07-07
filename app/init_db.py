from sqlalchemy import text
from app.database import Base, engine, SessionLocal
from app.models import Setting
from app.seed_cards import seed_cards


def initialize_database():
    # 1. መጀመሪያ ያሉትን ቴብሎች መፍጠር
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # 🛠️ [አዲሱ ማስተካከያ] የ 'game_commission_percent' ዓምድ በዳታቤዙ ውስጥ መኖሩን ማረጋገጥ እና ከሌለ መጨመር
    try:
        # በሴቲንግ ቴብል ውስጥ ዓምዱ መኖሩን ይፈትሻል
        db.execute(text("SELECT game_commission_percent FROM settings LIMIT 1;"))
    except Exception:
        # ዓምዱ ከሌለ (ስህተት ከተፈጠረ) ዳታቤዙን ሮልባክ አድርገን አዲሱን ዓምድ በSQL እንጨምረዋለን
        db.rollback()
        print("⚠️ game_commission_percent column is missing. Adding it to 'settings' table...")
        try:
            db.execute(text("ALTER TABLE settings ADD COLUMN game_commission_percent FLOAT DEFAULT 20.0;"))
            db.commit()
            print("✅ Successfully added game_commission_percent column.")
        except Exception as e:
            print(f"❌ Failed to alter table: {e}")
            db.rollback()

    # 2. መነሻ ሴቲንጎችን በዳታቤዝ ውስጥ መፍጠር (ቴብሉ ሙሉ በሙሉ ባዶ ከሆነ)
    if db.query(Setting).count() == 0:
        db.add(
            Setting(
                game_fee=10,
                countdown_seconds=30,
                draw_interval=2,
                max_cards=5,
                min_deposit=20,
                min_withdraw=50,
                jackpot_percent=10,
                game_commission_percent=20.0,
                is_registration_open=True
            )
        )
        db.commit()
    else:
        # ቴብሉ ቀድሞውኑ ካለ ግን ዓምዱ ባዶ ከሆነ ዲፎልት 20% መሙላት
        db.execute(text("UPDATE settings SET game_commission_percent = 20.0 WHERE game_commission_percent IS NULL;"))
        db.commit()

    # ---- Ensure schema compatibility for new columns ----
    # Ensure users.gift_coin exists
    try:
        db.execute(text("SELECT gift_coin FROM users LIMIT 1;"))
    except Exception:
        db.rollback()
        print("⚠️ users.gift_coin column is missing. Adding it to 'users' table...")
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS gift_coin FLOAT DEFAULT 0.0;"))
            db.commit()
            print("✅ Successfully added users.gift_coin column.")
        except Exception as e:
            print(f"❌ Failed to alter users table: {e}")
            db.rollback()

    # Ensure player_cards.bet_amount exists
    try:
        db.execute(text("SELECT bet_amount FROM player_cards LIMIT 1;"))
    except Exception:
        db.rollback()
        print("⚠️ player_cards.bet_amount column is missing. Adding it to 'player_cards' table...")
        try:
            db.execute(text("ALTER TABLE player_cards ADD COLUMN IF NOT EXISTS bet_amount FLOAT DEFAULT 0.0;"))
            db.commit()
            print("✅ Successfully added player_cards.bet_amount column.")
        except Exception as e:
            print(f"❌ Failed to alter player_cards table: {e}")
            db.rollback()

    # Ensure games.total_players and games.total_pool exist
    try:
        db.execute(text("SELECT total_players FROM games LIMIT 1;"))
    except Exception:
        db.rollback()
        print("⚠️ games.total_players column is missing. Adding it to 'games' table...")
        try:
            db.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS total_players INTEGER DEFAULT 0;"))
            db.commit()
            print("✅ Successfully added games.total_players column.")
        except Exception as e:
            print(f"❌ Failed to alter games table (total_players): {e}")
            db.rollback()

    try:
        db.execute(text("SELECT total_pool FROM games LIMIT 1;"))
    except Exception:
        db.rollback()
        print("⚠️ games.total_pool column is missing. Adding it to 'games' table...")
        try:
            db.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS total_pool FLOAT DEFAULT 0.0;"))
            db.commit()
            print("✅ Successfully added games.total_pool column.")
        except Exception as e:
            print(f"❌ Failed to alter games table (total_pool): {e}")
            db.rollback()

    # Ensure games.taken_cards and games.drawn_balls exist
    try:
        db.execute(text("SELECT taken_cards FROM games LIMIT 1;"))
    except Exception:
        db.rollback()
        print("⚠️ games.taken_cards column is missing. Adding it to 'games' table...")
        try:
            db.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS taken_cards TEXT DEFAULT '[]';"))
            db.commit()
            print("✅ Successfully added games.taken_cards column.")
        except Exception as e:
            print(f"❌ Failed to alter games table (taken_cards): {e}")
            db.rollback()

    try:
        db.execute(text("SELECT drawn_balls FROM games LIMIT 1;"))
    except Exception:
        db.rollback()
        print("⚠️ games.drawn_balls column is missing. Adding it to 'games' table...")
        try:
            db.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS drawn_balls TEXT DEFAULT '[]';"))
            db.commit()
            print("✅ Successfully added games.drawn_balls column.")
        except Exception as e:
            print(f"❌ Failed to alter games table (drawn_balls): {e}")
            db.rollback()

    db.close()

    # 3. ጨዋታው የሚነሳባቸውን 200 ካርዶች በዳታቤዝ ውስጥ መዝራት
    seed_cards()
