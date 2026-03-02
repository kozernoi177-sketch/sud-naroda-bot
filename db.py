import sqlite3

conn = sqlite3.connect("game.db")
cursor = conn.cursor()


def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            language TEXT DEFAULT 'ru',
            money INTEGER DEFAULT 100,
            diamonds INTEGER DEFAULT 0,
            exp INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 1000,
            win_streak INTEGER DEFAULT 0
        )
    """)
    conn.commit()


def register_user(user_id, username):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()


def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()


def update_money(user_id, amount):
    cursor.execute(
        "UPDATE users SET money = money + ? WHERE user_id=?",
        (amount, user_id)
    )
    conn.commit()


def update_exp(user_id, amount):
    cursor.execute(
        "UPDATE users SET exp = exp + ? WHERE user_id=?",
        (amount, user_id)
    )
    conn.commit()


def add_win(user_id):
    cursor.execute(
        "UPDATE users SET wins = wins + 1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def add_game(user_id):
    cursor.execute(
        "UPDATE users SET games_played = games_played + 1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def update_language(user_id, lang):
    cursor.execute(
        "UPDATE users SET language=? WHERE user_id=?",
        (lang, user_id)
    )
    conn.commit()


