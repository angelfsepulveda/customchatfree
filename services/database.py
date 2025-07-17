# MIT License
#
# Copyright (c) 2025
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sqlite3
import json
from datetime import datetime

DATABASE_FILE = "chat_history.db"


class DatabaseConnection:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(DATABASE_FILE)
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            self.conn.close()


def initialize_database():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE
                )
            """)

    cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    start_time DATETIME,
                    role_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (role_id) REFERENCES roles (role_id)
                )
            """)

    cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    role TEXT,
                    content TEXT,
                    model TEXT,
                    timestamp DATETIME,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                )
            """)

    cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    action TEXT,
                    details TEXT
                )
            """)

    cursor.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    description TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
    conn.commit()
    conn.close()


def create_role(user_id: int, name: str, description: str) -> int:
    """Crea un nuevo rol para el usuario y retorna el role_id."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO roles (user_id, name, description) VALUES (?, ?, ?)", (user_id, name, description))
    role_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return role_id

def get_roles_by_user(user_id: int):
    """Devuelve una lista de roles (dict) para un usuario dado."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role_id, name, description FROM roles WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"role_id": row[0], "name": row[1], "description": row[2]} for row in rows
    ]

def get_role_by_id(role_id: int):
    """Devuelve un rol (dict) por su ID."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role_id, name, description FROM roles WHERE role_id = ?", (role_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"role_id": row[0], "name": row[1], "description": row[2]}
    return None

def assign_role_to_conversation(conversation_id: int, role_id: int):
    """Asigna un rol a una conversación."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE conversations SET role_id = ? WHERE conversation_id = ?", (role_id, conversation_id))
    conn.commit()
    conn.close()


def get_user_id(username: str) -> int:
    """Gets or creates a user and returns the user ID."""
    with DatabaseConnection() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
            user_id = cursor.lastrowid
            log_action("User created", f"Username: {username}, User ID: {user_id}", cursor)
            return user_id






def create_conversation(user_id: int, cursor=None) -> int:
    """Creates a new conversation and returns the conversation ID."""
    now = datetime.now().isoformat()
    if cursor is not None:
        cursor.execute("INSERT INTO conversations (user_id, start_time) VALUES (?, ?)", (user_id, now))
        conversation_id = cursor.lastrowid
        log_action("Conversation started", f"User ID: {user_id}, Conversation ID: {conversation_id}", cursor)
        return conversation_id
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO conversations (user_id, start_time) VALUES (?, ?)", (user_id, now))
        conversation_id = cur.lastrowid
        conn.commit()
        log_action("Conversation started", f"User ID: {user_id}, Conversation ID: {conversation_id}", cur)
        conn.close()
        return conversation_id



def add_message(conversation_id: int, role: str, content: str, model: str, cursor=None):
    """Adds a message to a conversation."""
    now = datetime.now().isoformat()
    if cursor is not None:
        cursor.execute("INSERT INTO messages (conversation_id, role, content, model, timestamp) VALUES (?, ?, ?, ?, ?)", (conversation_id, role, content, model, now))
        log_action("Message added", f"Conversation ID: {conversation_id}, Role: {role}, Model: {model}, Content: {content[:50]}...", cursor)
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (conversation_id, role, content, model, timestamp) VALUES (?, ?, ?, ?, ?)", (conversation_id, role, content, model, now))
        conn.commit()
        log_action("Message added", f"Conversation ID: {conversation_id}, Role: {role}, Model: {model}, Content: {content[:50]}...", cur)
        conn.close()



def log_action(action: str, details: str, cursor=None):
    """Logs an action to the logs table."""
    now = datetime.now().isoformat()
    if cursor is not None:
        cursor.execute("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", (now, action, details))
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", (now, action, details))
        conn.commit()
        conn.close()


def get_conversations_by_user(user_id: int):
    """Devuelve una lista de conversaciones (dict) para un usuario dado, ordenadas por fecha descendente."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_id, start_time FROM conversations WHERE user_id = ? ORDER BY start_time DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"conversation_id": row[0], "start_time": row[1]} for row in rows
    ]

def get_messages_by_conversation(conversation_id: int):
    """Devuelve una lista de mensajes (dict) para una conversación dada, ordenados por timestamp ascendente."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content, model, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"role": row[0], "content": row[1], "model": row[2], "timestamp": row[3]} for row in rows
    ]