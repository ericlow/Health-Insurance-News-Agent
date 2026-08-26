"""Conversation persistence — Neon Postgres CRUD for the analyst agent."""
import json
import os

import psycopg2
from psycopg2.extras import Json


def conn():
    """Open a Neon Postgres connection using DATABASE_URL from the environment."""
    return psycopg2.connect(os.environ["DATABASE_URL"])


def create_conversation(db, messages: list) -> int:
    """Insert a new conversation row and return its auto-assigned ID."""
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO conversations (messages) VALUES (%s) RETURNING id",
            (Json(messages),),
        )
        row = cur.fetchone()
    db.commit()
    return row[0]


def load_conversation(db, conv_id: int) -> list | None:
    """Load the message history for an existing conversation, or None if not found."""
    with db.cursor() as cur:
        cur.execute("SELECT messages FROM conversations WHERE id = %s", (conv_id,))
        row = cur.fetchone()
    if not row:
        return None
    raw = row[0]
    return raw if isinstance(raw, list) else json.loads(raw)


def update_conversation(db, conv_id: int, messages: list):
    """Persist the updated message history back to Neon after the tool loop completes."""
    with db.cursor() as cur:
        cur.execute(
            "UPDATE conversations SET messages = %s, updated_at = now() WHERE id = %s",
            (Json(messages), conv_id),
        )
    db.commit()
