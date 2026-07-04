from app.database import Base, engine, SessionLocal
from app.models import Setting
from app.seed_cards import seed_cards


def initialize_database():

    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Create default settings
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
                is_registration_open=True
            )
        )

        db.commit()

    db.close()

    # Create cards if they don't exist
    seed_cards()
