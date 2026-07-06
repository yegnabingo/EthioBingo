from app.database import Base, engine, SessionLocal
from app.models import Setting
from app.seed_cards import seed_cards


def initialize_database():

    # 1. የዳታቤዝ ቴብሎችን መፍጠር
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # 2. መነሻ ሴቲንጎችን በዳታቤዝ ውስጥ መፍጠር (ከአዲሱ የኮሚሽን ዓምድ ጋር)
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
                game_commission_percent=20.0,  # 🆕 [የተስተካከለ] የካሲኖው 20% ኮሚሽን እዚህ መነሻ ላይ ተካቷል
                is_registration_open=True
            )
        )
        db.commit()

    db.close()

    # 3. ጨዋታው የሚነሳባቸውን 200 ካርዶች በዳታቤዝ ውስጥ መዝራት (Seed)
    seed_cards()
