import sqlite3
import os

DATABASE_FILE = "users.db"

def create_database():
    """Creates and initializes the SQLite database and tables if they don't exist."""
    if os.path.exists(DATABASE_FILE):
        print("Database already exists.")
        return

    try:
        print("Creating new database...")
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        print("Table 'users' created successfully.")
        
        conn.commit()
        conn.close()
        print("Database initialized.")
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_database()