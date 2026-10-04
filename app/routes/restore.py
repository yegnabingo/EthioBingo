from fastapi import APIRouter
import psycopg2

router = APIRouter()

# 1. የድሮው Render DB (የተስተካከለ External URL)
RENDER_DB = "postgresql://dop:co6pCP2KqkcxjRlmSs4GrT1ljdTAfkQi@dpg-d9p7gb142hec739b9mhg-a.oregon-postgres.render.com/yegnabingo"

# 2. የአዲሱ Neon DB
NEON_DB = "postgresql://neondb_owner:npg_JSOjKIfw4y5b@ep-tiny-dawn-b58l5km4.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require"

@router.get("/restore-users-now")
def restore_users_data():
    try:
        # ከ Render ዳታ ማንበብ
        src_conn = psycopg2.connect(RENDER_DB)
        src_cur = src_conn.cursor()
        src_cur.execute("SELECT * FROM users;")
        rows = src_cur.fetchall()
        colnames = [desc[0] for desc in src_cur.description]
        src_conn.close()

        # ወደ Neon ዳታ ማስገባት
        dst_conn = psycopg2.connect(NEON_DB)
        dst_cur = dst_conn.cursor()
        
        dst_cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
        
        cols_str = ", ".join(colnames)
        vals_str = ", ".join(["%s"] * len(colnames))
        insert_query = f"INSERT INTO users ({cols_str}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;"
        
        dst_cur.executemany(insert_query, rows)
        dst_conn.commit()
        dst_conn.close()
        
        return {"status": "success", "message": f"Successfully restored {len(rows)} users to Neon!"}
    except Exception as e:
        return {"status": "error", "details": str(e)}
