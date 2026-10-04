from fastapi import APIRouter
import psycopg2

router = APIRouter()

# የድሮው የ Render External DB URL
RENDER_DB = "postgresql://dop:co6pCP2KqkcxjRlmSs4GrT1ljdTAfkQi@dpg-d9p7gb142hec739b9mhg-a.oregon-postgres.render.com/yegnabingo"

# የአዲሱ Neon DB URL
NEON_DB = "postgresql://neondb_owner:npg_JSOjKIfw4y5b@ep-tiny-dawn-b58l5km4.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require"

@router.get("/restore-users-now")
def restore_users_data():
    try:
        # 1. ከ Render በቀጥታ ማንበብ
        src_conn = psycopg2.connect(RENDER_DB)
        src_cur = src_conn.cursor()
        src_cur.execute("SELECT * FROM users;")
        rows = src_cur.fetchall()
        colnames = [desc[0] for desc in src_cur.description]
        src_conn.close()

        if not rows:
            return {"status": "error", "message": "ከ Render ዳታቤዝ ምንም የ users ዳታ አልተገኘም! እባክዎን የ RENDER_DB አድራሻን ያረጋግጡ።"}

        # 2. ወደ Neon ዳታቤዝ ማስገባት
        dst_conn = psycopg2.connect(NEON_DB)
        dst_cur = dst_conn.cursor()
        
        cols_str = ", ".join([f'"{col}"' for col in colnames])
        vals_str = ", ".join(["%s"] * len(colnames))
        insert_query = f'INSERT INTO users ({cols_str}) VALUES ({vals_str}) ON CONFLICT (telegram_id) DO NOTHING;'

        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            dst_cur.executemany(insert_query, batch)
            dst_conn.commit()

        dst_conn.close()
        return {"status": "success", "message": f"በስኬት {len(rows)} ተጫዋቾች ወደ Neon ተዛውረዋል!"}

    except Exception as e:
        return {"status": "error", "details": str(e)}
