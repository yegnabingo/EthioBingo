from fastapi import APIRouter, BackgroundTasks
import psycopg2

router = APIRouter()

# 1. የድሮው Render DB (ዳታው ያለበት)
RENDER_DB = "postgresql://dop:co6pCP2KqkcxjRlmSs4GrT1ljdTAfkQi@dpg-d9p7gb142hec739b9mhg-a.oregon-postgres.render.com/yegnabingo"

# 2. የአዲሱ Neon DB (በአዲሱ አድራሻህ የተስተካከለ)
NEON_DB = "postgresql://neondb_owner:npg_JSOjKIfw4y5b@ep-tiny-dawn-b58l5km4.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require"

def perform_migration():
    try:
        print("የዳታ ማዛወር ሂደት ተጀምሯል...")
        src_conn = psycopg2.connect(RENDER_DB)
        src_cur = src_conn.cursor()
        src_cur.execute("SELECT * FROM users;")
        rows = src_cur.fetchall()
        colnames = [desc[0] for desc in src_cur.description]
        src_conn.close()

        dst_conn = psycopg2.connect(NEON_DB)
        dst_cur = dst_conn.cursor()
        
        dst_cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
        
        cols_str = ", ".join(colnames)
        vals_str = ", ".join(["%s"] * len(colnames))
        insert_query = f"INSERT INTO users ({cols_str}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;"
        
        # በየ 1000 ከፍሎ ማስገባት (Timeout እንዳይመጣ)
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            dst_cur.executemany(insert_query, batch)
            dst_conn.commit()
            print(f"{i + len(batch)} / {len(rows)} ተጫዋቾች ተዛውረዋል...")

        dst_conn.close()
        print("ዳታው ሙሉ በሙሉ ተዛውሮ አልቋል!")
    except Exception as e:
        print(f"ስህተት ተከሰተ፦ {e}")

@router.get("/restore-users-now")
def restore_users_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(perform_migration)
    return {
        "status": "started",
        "message": "የ 11,483 ተጫዋቾች ዳታ በ Background እየተጫነ ነው። ከ 30-60 ሰከንድ በኋላ TablePlus ላይ Refresh አድርገው ይመልከቱ!"
    }
