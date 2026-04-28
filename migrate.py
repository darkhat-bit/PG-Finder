import psycopg

DATABASE_URL = "postgresql://postgres:124_%40RIsHI@localhost:5432/pgfind"

def run_migration():
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Add password column to users if not exists
        cur.execute("""
            ALTER TABLE app_users 
            ADD COLUMN IF NOT EXISTS password VARCHAR(100) DEFAULT 'password123';
        """)
        
        # Add role column to users if not exists
        cur.execute("""
            ALTER TABLE app_users 
            ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';
        """)
        
        # Add owner_id column to pgs if not exists
        cur.execute("""
            ALTER TABLE app_pgs 
            ADD COLUMN IF NOT EXISTS owner_id INTEGER DEFAULT 0;
        """)
        
        conn.commit()
        print('Migration complete!')
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run_migration()
