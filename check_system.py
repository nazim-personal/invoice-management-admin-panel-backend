import os
import sys
from dotenv import load_dotenv
import pymysql

def check_environment():
    print("🔍 Checking Environment Variables...")
    load_dotenv()

    required_vars = [
        'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME',
        'JWT_SECRET_KEY', 'SECRET_KEY'
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            masked = value if var not in ['DB_PASSWORD', 'JWT_SECRET_KEY', 'SECRET_KEY'] else '********'
            print(f"  ✅ {var}: {masked}")

    if missing:
        print(f"  ❌ Missing variables: {', '.join(missing)}")
        return False
    return True

def check_database():
    print("\n🔍 Checking Database Connection...")
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            connect_timeout=5
        )
        print("  ✅ Connection Successful!")

        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"  ✅ Database Version: {version[0]}")

            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            print(f"  ✅ Tables Found: {', '.join(table_names)}")

        conn.close()
        return True
    except pymysql.MySQLError as e:
        print(f"  ❌ Database Connection Failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected Error: {e}")
        return False

if __name__ == "__main__":
    print("=== System Diagnostic Tool ===\n")
    env_ok = check_environment()
    db_ok = check_database()

    if env_ok and db_ok:
        print("\n✅ System is ready to run!")
        sys.exit(0)
    else:
        print("\n❌ System has issues. Please fix them before running the app.")
        sys.exit(1)
