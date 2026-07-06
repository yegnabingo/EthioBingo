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

    db.close()

    # 3. ጨዋታው የሚነሳባቸውን 200 ካርዶች በዳታቤዝ ውስጥ መዝራት
    seed_cards()
