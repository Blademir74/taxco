import psycopg2

passwords = [
    'postgres',
    'postgres123', 
    'admin',
    'root',
    # Agrega aquí otros passwords que creas que puede ser
]

for pwd in passwords:
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='postgres',
            user='postgres',
            password=pwd
        )
        print(f"✓ PASSWORD CORRECTO: {pwd}")
        conn.close()
        break
    except Exception as e:
        print(f"✗ {pwd}: {str(e)[:50]}")
