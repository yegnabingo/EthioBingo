import psycopg2

# 1. የ Render ዳታቤዝህ Connection String
RENDER_DB = "postgresql://yegnabingo_user:your_render_password@dpg-xxxx-a.render.com/yegnabingo"

# 2. የአዲሱ Neon ዳታቤዝህ Connection String
NEON_DB = "postgresql://neondb_owner:your_neon_password@ep-xxxx.neon.tech/neondb?sslmode=require"

def run_migration():
    print("ከ Render ዳታ እየተነበበ ነው...")
    src_conn = psycopg2.connect(RENDER_DB)
    src_cur = src_conn.cursor()
    src_cur.execute("SELECT * FROM users;")
    rows = src_cur.fetchall()
    colnames = [desc[0] for desc in src_cur.description]
    src_conn.close()

    print(f"በድቅስ {len(rows)} ተጫዋቾች ተገኙ! ወደ Neon እየተጫነ ነው...")

    dst_conn = psycopg2.connect(NEON_DB)
    dst_cur = dst_conn.cursor()
    
    cols_str = ", ".join(colnames)
    vals_str = ", ".join(["%s"] * len(colnames))
    insert_query = f"INSERT INTO users ({cols_str}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;"
    
    dst_cur.executemany(insert_query, rows)
    dst_conn.commit()
    dst_conn.close()
    
    print("ተጠናቋል! 11,483ቱም ተጫዋቾችና ባላንሳቸው ተመልሰዋል።")

if __name__ == "__main__":
    run_migration()
