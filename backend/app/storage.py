"""
SQLite storage.

Public interface used by chat.py: create_session, load_session,
append_message, mark_session_closed, get_or_create_profile,
authenticate_profile, load_profile, update_profile_summary.

People are identified by username + password (hashed with
PBKDF2-HMAC-SHA256 and a salt, never stored in plain text).
"""

import hashlib
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from .config import DB_PATH

_USERNAME_SAFE = re.compile(r"[^a-z0-9_\-]")

PBKDF2_ITERATIONS = 260_000


class WrongPasswordError(Exception):
    """Raised when the username exists but the password doesn't match."""


def normalize_username(username: str) -> str:
    slug = username.strip().lower().replace(" ", "-")
    slug = _USERNAME_SAFE.sub("", slug)
    return slug[:64]


def _hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
    _, computed_hash = _hash_password(password, salt_hex)
    return secrets.compare_digest(computed_hash, expected_hash_hex)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            city TEXT,
            profile_summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            username TEXT REFERENCES profiles(username),
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            city TEXT,
            created_at TEXT NOT NULL,
            closed INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(session_id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id);
        """
    )
    conn.commit()
    conn.close()


init_db()


# ---------- Profiles ----------


def get_or_create_profile(
    username: str, password: str, name: str, age: int, city: Optional[str]
) -> dict:
    """
    Creates a new profile, or if the username already exists, verifies
    the password and updates name/age/city with the latest submitted
    values (can change between visits) while preserving the accumulated
    profile_summary. Used by the signup flow.
    """
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM profiles WHERE username = ?", (username,)
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()

    if row:
        if not _verify_password(password, row["password_salt"], row["password_hash"]):
            conn.close()
            raise WrongPasswordError()
        conn.execute(
            "UPDATE profiles SET name=?, age=?, city=?, updated_at=? WHERE username=?",
            (name, age, city, now, username),
        )
        conn.commit()
        profile = dict(row)
        profile.update(name=name, age=age, city=city, updated_at=now)
    else:
        salt_hex, hash_hex = _hash_password(password)
        conn.execute(
            """INSERT INTO profiles
               (username, password_salt, password_hash, name, age, city,
                profile_summary, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, '', ?, ?)""",
            (username, salt_hex, hash_hex, name, age, city, now, now),
        )
        conn.commit()
        profile = {
            "username": username,
            "password_salt": salt_hex,
            "password_hash": hash_hex,
            "name": name,
            "age": age,
            "city": city,
            "profile_summary": "",
            "created_at": now,
            "updated_at": now,
        }

    conn.close()
    return profile


def authenticate_profile(username: str, password: str) -> Optional[dict]:
    """
    Verifies username + password WITHOUT creating or modifying anything
    (unlike get_or_create_profile, which also creates new profiles).
    Returns the profile if the password matches, or None if the user
    doesn't exist or the password is wrong. Used by the login flow.
    """
    profile = load_profile(username)
    if profile is None:
        return None
    if not _verify_password(password, profile["password_salt"], profile["password_hash"]):
        return None
    return profile


def load_profile(username: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM profiles WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_profile_summary(username: str, new_summary: str) -> None:
    conn = _connect()
    cur = conn.execute(
        "UPDATE profiles SET profile_summary=?, updated_at=? WHERE username=?",
        (new_summary, datetime.now(timezone.utc).isoformat(), username),
    )
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise ValueError(f"Profile not found: {username}")
    conn.close()


# ---------- Sessions ----------


def create_session(
    name: str, age: int, city: Optional[str], username: Optional[str] = None
) -> str:
    session_id = uuid.uuid4().hex
    conn = _connect()
    conn.execute(
        """INSERT INTO sessions
           (session_id, username, name, age, city, created_at, closed)
           VALUES (?, ?, ?, ?, ?, ?, 0)""",
        (session_id, username, name, age, city, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return session_id


def load_session(session_id: str) -> Optional[dict]:
    conn = _connect()
    session_row = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if session_row is None:
        conn.close()
        return None

    message_rows = conn.execute(
        "SELECT role, content, ts FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    conn.close()

    data = dict(session_row)
    data["closed"] = bool(data["closed"])
    data["messages"] = [dict(m) for m in message_rows]
    return data


def append_message(session_id: str, role: str, content: str) -> None:
    conn = _connect()
    exists = conn.execute(
        "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not exists:
        conn.close()
        raise ValueError(f"Session not found: {session_id}")
    conn.execute(
        "INSERT INTO messages (session_id, role, content, ts) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def mark_session_closed(session_id: str) -> None:
    conn = _connect()
    cur = conn.execute(
        "UPDATE sessions SET closed = 1 WHERE session_id = ?", (session_id,)
    )
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise ValueError(f"Session not found: {session_id}")
    conn.close()