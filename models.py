import sqlite3
from datetime import datetime

DB_NAME = "database.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users table 
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)

    # Knowledge items table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        author_id INTEGER,
        tags TEXT,
        project_link TEXT,
        filename TEXT,
        status TEXT DEFAULT 'submitted',
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(author_id) REFERENCES users(id)
    );
    """)

    # Validation records table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS validation_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        validator_id INTEGER,
        decision TEXT,
        comments TEXT,
        timestamp TEXT,
        FOREIGN KEY(item_id) REFERENCES knowledge_items(id),
        FOREIGN KEY(validator_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()



# User functions

def create_user(username, password, role):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, role))
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid

def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def verify_user(username, password):
    """Return user row if username/password match; else None."""
    user = get_user_by_username(username)
    if user and user["password"] == password:
        return user
    return None


# Knowledge item & validation functions

def add_knowledge_item(title, description, author_id, tags, project_link, filename):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO knowledge_items 
        (title, description, author_id, tags, project_link, filename, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?)
    """, (title, description, author_id, tags, project_link, filename, now, now))
    conn.commit()
    conn.close()

def add_validation_record(item_id, validator_id, decision, comments):
    conn = get_connection()
    cur = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO validation_records (item_id, validator_id, decision, comments, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (item_id, validator_id, decision, comments, timestamp))
    conn.commit()
    conn.close()
