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
import threading
import time
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Generator

DATABASE_FILE = "chat_history.db"


class DatabaseConnection:
    """ACID-compliant database connection with explicit transaction management."""
    
    def __init__(self, isolation_level: str = "SERIALIZABLE", timeout: int = 30):
        self.conn = None
        self.isolation_level = isolation_level
        self.timeout = timeout
        self._lock = threading.Lock()
        self._transaction_started = False

    def __enter__(self):
        try:
            with self._lock:
                self.conn = sqlite3.connect(
                    DATABASE_FILE, 
                    timeout=self.timeout,
                    isolation_level=None  # We'll manage transactions manually
                )
                
                # Configure SQLite for ACID compliance
                self.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                self.conn.execute("PRAGMA synchronous=FULL")  # Full synchronization
                self.conn.execute("PRAGMA foreign_keys=ON")   # Enable foreign key constraints
                self.conn.execute("PRAGMA temp_store=MEMORY") # Store temp tables in memory
                
                # Set isolation level
                if self.isolation_level == "READ_UNCOMMITTED":
                    self.conn.execute("PRAGMA read_uncommitted=1")
                else:  # SERIALIZABLE (default)
                    self.conn.execute("PRAGMA read_uncommitted=0")
                
                # Start explicit transaction
                self.conn.execute("BEGIN IMMEDIATE TRANSACTION")
                self._transaction_started = True
                
                return self.conn.cursor()
                
        except sqlite3.Error as e:
            if self.conn:
                self.conn.close()
            print(f"Database connection error: {e}")
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn and self._transaction_started:
            try:
                with self._lock:
                    if exc_type is None:
                        # Success - commit transaction
                        self.conn.execute("COMMIT")
                        print("Transaction committed successfully")
                    else:
                        # Exception occurred - rollback transaction
                        self.conn.execute("ROLLBACK")
                        print(f"Transaction rolled back due to: {exc_type.__name__}")
                        
            except sqlite3.Error as e:
                print(f"Database error during transaction cleanup: {e}")
                # Force rollback if commit/rollback fails
                try:
                    self.conn.execute("ROLLBACK")
                except:
                    pass
            finally:
                self.conn.close()
                self._transaction_started = False


@contextmanager
def database_transaction(isolation_level: str = "SERIALIZABLE", timeout: int = 30) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for ACID-compliant database transactions with retry logic."""
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            with DatabaseConnection(isolation_level, timeout) as cursor:
                yield cursor
                return  # Success, exit retry loop
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                print(f"Database locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"Database operational error: {e}")
                raise e
        except Exception as e:
            print(f"Unexpected database error: {e}")
            raise e
    
    raise sqlite3.OperationalError("Max retries exceeded for database transaction")


def initialize_database():
    """Initializes the SQLite database and creates tables if they don't exist."""
    try:
        with database_transaction() as cursor:
            # Create tables if they don't exist
            tables = [
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS roles (
                    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    start_time DATETIME NOT NULL,
                    role_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE SET NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id) ON DELETE CASCADE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT
                )
                """
            ]
            
            for table_sql in tables:
                cursor.execute(table_sql)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_roles_user_id ON roles(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_start_time ON conversations(start_time)",
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)",
                "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            print("Database initialized successfully with ACID compliance")
            
    except Exception as e:
        print(f"Error during database initialization: {e}")
        raise e


def create_role(user_id: int, name: str, description: str) -> int:
    """Creates a new role for the user and returns the role_id."""
    # Input validation
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    if not isinstance(description, str):
        raise ValueError("description must be a string")
    
    try:
        with database_transaction() as cursor:
            # Check if user exists with row-level locking
            cursor.execute("SELECT user_id FROM users WHERE user_id = ? FOR UPDATE", (user_id,))
            if not cursor.fetchone():
                raise ValueError(f"User with ID {user_id} does not exist")
            
            # Insert role with proper locking
            cursor.execute("INSERT INTO roles (user_id, name, description) VALUES (?, ?, ?)", 
                          (user_id, name.strip(), description))
            role_id = cursor.lastrowid
            
            if role_id is None:
                raise sqlite3.Error("Failed to create role - no ID returned")
            
            print(f"Role created successfully with ID: {role_id}")
            return role_id
            
    except Exception as e:
        print(f"Error creating role: {e}")
        raise e

def get_roles_by_user(user_id: int):
    """Returns a list of roles (dict) for a given user."""
    # Input validation
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    
    try:
        with database_transaction(isolation_level="READ_UNCOMMITTED") as cursor:
            cursor.execute("SELECT role_id, name, description FROM roles WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            return [
                {"role_id": row[0], "name": row[1], "description": row[2]} for row in rows
            ]
    except Exception as e:
        print(f"Error getting roles by user: {e}")
        raise e

def get_role_by_id(role_id: int):
    """Returns a role (dict) by its ID."""
    # Input validation
    if not isinstance(role_id, int) or role_id <= 0:
        raise ValueError("role_id must be a positive integer")
    
    try:
        with database_transaction(isolation_level="READ_UNCOMMITTED") as cursor:
            cursor.execute("SELECT role_id, name, description FROM roles WHERE role_id = ?", (role_id,))
            row = cursor.fetchone()
            if row:
                return {"role_id": row[0], "name": row[1], "description": row[2]}
            return None
    except Exception as e:
        print(f"Error getting role by ID: {e}")
        raise e

def assign_role_to_conversation(conversation_id: int, role_id: int):
    """Assigns a role to a conversation."""
    # Input validation
    if not isinstance(conversation_id, int) or conversation_id <= 0:
        raise ValueError("conversation_id must be a positive integer")
    if not isinstance(role_id, int) or role_id <= 0:
        raise ValueError("role_id must be a positive integer")
    
    try:
        with database_transaction() as cursor:
            # Check if conversation exists with row-level locking
            cursor.execute("SELECT conversation_id FROM conversations WHERE conversation_id = ? FOR UPDATE", (conversation_id,))
            if not cursor.fetchone():
                raise ValueError(f"Conversation with ID {conversation_id} does not exist")
            
            # Check if role exists with row-level locking
            cursor.execute("SELECT role_id FROM roles WHERE role_id = ? FOR UPDATE", (role_id,))
            if not cursor.fetchone():
                raise ValueError(f"Role with ID {role_id} does not exist")
            
            cursor.execute("UPDATE conversations SET role_id = ? WHERE conversation_id = ?", (role_id, conversation_id))
            
            # Check if any rows were affected
            if cursor.rowcount == 0:
                raise ValueError(f"No conversation was updated. Conversation ID {conversation_id} may not exist")
            
            print(f"Role {role_id} assigned to conversation {conversation_id} successfully")
            
    except Exception as e:
        print(f"Error assigning role to conversation: {e}")
        raise e


def get_user_id(username: str) -> int:
    """Gets or creates a user and returns the user ID."""
    # Input validation
    if not isinstance(username, str) or not username.strip():
        raise ValueError("username must be a non-empty string")
    
    try:
        with database_transaction() as cursor:
            # Use row-level locking to prevent race conditions
            cursor.execute("SELECT user_id FROM users WHERE username = ? FOR UPDATE", (username.strip(),))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                cursor.execute("INSERT INTO users (username) VALUES (?)", (username.strip(),))
                user_id = cursor.lastrowid
                
                if user_id is None:
                    raise sqlite3.Error("Failed to create user - no ID returned")
                
                log_action("User created", f"Username: {username}, User ID: {user_id}", cursor)
                print(f"User created successfully with ID: {user_id}")
                return user_id
                
    except Exception as e:
        print(f"Error getting/creating user: {e}")
        raise e






def create_conversation(user_id: int) -> int:
    """Creates a new conversation and returns the conversation ID."""
    # Input validation
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    
    now = datetime.now().isoformat()
    
    try:
        with database_transaction() as cursor:
            # Check if user exists with row-level locking
            cursor.execute("SELECT user_id FROM users WHERE user_id = ? FOR UPDATE", (user_id,))
            if not cursor.fetchone():
                raise ValueError(f"User with ID {user_id} does not exist")
            
            cursor.execute("INSERT INTO conversations (user_id, start_time) VALUES (?, ?)", (user_id, now))
            conversation_id = cursor.lastrowid
            
            if conversation_id is None:
                raise sqlite3.Error("Failed to create conversation - no ID returned")
            
            log_action("Conversation started", f"User ID: {user_id}, Conversation ID: {conversation_id}", cursor)
            print(f"Conversation created successfully with ID: {conversation_id}")
            return conversation_id
            
    except Exception as e:
        print(f"Error creating conversation: {e}")
        raise e



def add_message(conversation_id: int, role: str, content: str, model: str) -> int:
    """Adds a message to a conversation."""
    # Input validation
    if not isinstance(conversation_id, int) or conversation_id <= 0:
        raise ValueError("conversation_id must be a positive integer")
    if not isinstance(role, str) or not role.strip():
        raise ValueError("role must be a non-empty string")
    if not isinstance(content, str):
        raise ValueError("content must be a string")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")
    
    now = datetime.now().isoformat()
    
    try:
        with database_transaction() as cursor:
            # Check if conversation exists with row-level locking
            cursor.execute("SELECT conversation_id FROM conversations WHERE conversation_id = ? FOR UPDATE", (conversation_id,))
            if not cursor.fetchone():
                raise ValueError(f"Conversation with ID {conversation_id} does not exist")
            
            cursor.execute("INSERT INTO messages (conversation_id, role, content, model, timestamp) VALUES (?, ?, ?, ?, ?)", 
                          (conversation_id, role.strip(), content, model.strip(), now))
            
            message_id = cursor.lastrowid
            if message_id is None:
                raise sqlite3.Error("Failed to add message - no ID returned")
            
            log_action("Message added", f"Conversation ID: {conversation_id}, Role: {role}, Model: {model}, Content: {content[:50]}...", cursor)
            print(f"Message added successfully with ID: {message_id}")
            return message_id
            
    except Exception as e:
        print(f"Error adding message: {e}")
        raise e



def log_action(action: str, details: str, cursor=None) -> int:
    """Logs an action to the logs table."""
    # Input validation
    if not isinstance(action, str) or not action.strip():
        raise ValueError("action must be a non-empty string")
    if not isinstance(details, str):
        raise ValueError("details must be a string")
    
    now = datetime.now().isoformat()
    
    if cursor is not None:
        # Using provided cursor (within existing transaction)
        cursor.execute("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", 
                      (now, action.strip(), details))
        
        log_id = cursor.lastrowid
        if log_id is None:
            raise sqlite3.Error("Failed to log action - no ID returned")
        return log_id
    else:
        # Create new transaction
        try:
            with database_transaction() as cur:
                cur.execute("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", 
                           (now, action.strip(), details))
                
                log_id = cur.lastrowid
                if log_id is None:
                    raise sqlite3.Error("Failed to log action - no ID returned")
                
                print(f"Action logged successfully with ID: {log_id}")
                return log_id
                
        except Exception as e:
            print(f"Error logging action: {e}")
            raise e


def get_conversations_by_user(user_id: int):
    """Returns a list of conversations (dict) for a given user, ordered by date descending."""
    # Input validation
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    
    try:
        with database_transaction(isolation_level="READ_UNCOMMITTED") as cursor:
            cursor.execute("SELECT conversation_id, start_time FROM conversations WHERE user_id = ? ORDER BY start_time DESC", (user_id,))
            rows = cursor.fetchall()
            return [
                {"conversation_id": row[0], "start_time": row[1]} for row in rows
            ]
    except Exception as e:
        print(f"Error getting conversations by user: {e}")
        raise e

def get_messages_by_conversation(conversation_id: int):
    """Returns a list of messages (dict) for a given conversation, ordered by timestamp ascending."""
    # Input validation
    if not isinstance(conversation_id, int) or conversation_id <= 0:
        raise ValueError("conversation_id must be a positive integer")
    
    try:
        with database_transaction(isolation_level="READ_UNCOMMITTED") as cursor:
            cursor.execute("SELECT role, content, model, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,))
            rows = cursor.fetchall()
            return [
                {"role": row[0], "content": row[1], "model": row[2], "timestamp": row[3]} for row in rows
            ]
    except Exception as e:
        print(f"Error getting messages by conversation: {e}")
        raise e


def create_conversation_with_message(user_id: int, role: str, content: str, model: str) -> tuple[int, int]:
    """Creates a conversation and adds the first message in a single ACID transaction."""
    # Input validation
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    if not isinstance(role, str) or not role.strip():
        raise ValueError("role must be a non-empty string")
    if not isinstance(content, str):
        raise ValueError("content must be a string")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")
    
    try:
        with database_transaction() as cursor:
            # Check if user exists with row-level locking
            cursor.execute("SELECT user_id FROM users WHERE user_id = ? FOR UPDATE", (user_id,))
            if not cursor.fetchone():
                raise ValueError(f"User with ID {user_id} does not exist")
            
            # Create conversation
            now = datetime.now().isoformat()
            cursor.execute("INSERT INTO conversations (user_id, start_time) VALUES (?, ?)", (user_id, now))
            conversation_id = cursor.lastrowid
            
            if conversation_id is None:
                raise sqlite3.Error("Failed to create conversation - no ID returned")
            
            # Add first message
            cursor.execute("INSERT INTO messages (conversation_id, role, content, model, timestamp) VALUES (?, ?, ?, ?, ?)", 
                          (conversation_id, role.strip(), content, model.strip(), now))
            
            message_id = cursor.lastrowid
            if message_id is None:
                raise sqlite3.Error("Failed to add message - no ID returned")
            
            # Log the action
            log_action("Conversation with message created", 
                      f"User ID: {user_id}, Conversation ID: {conversation_id}, Message ID: {message_id}", 
                      cursor)
            
            print(f"Conversation with message created successfully - Conversation ID: {conversation_id}, Message ID: {message_id}")
            return conversation_id, message_id
            
    except Exception as e:
        print(f"Error creating conversation with message: {e}")
        raise e