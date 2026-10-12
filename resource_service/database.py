import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "resources.db"


def get_connection():
    DATA_DIR.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    connection = get_connection()

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                owner_id TEXT NOT NULL,
                result_filename TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE
            );
            """)

        connection.commit()
    finally:
        connection.close()


def reset_database():
    if DB_PATH.exists():
        DB_PATH.unlink()

    initialize_database()


def create_document(owner_id: str, title: str, content: str):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO documents (
                owner_id,
                title,
                content
            )
            VALUES (?, ?, ?)
            """,
            (owner_id, title, content),
        )

        connection.commit()

        document = connection.execute(
            """
            SELECT id, owner_id, title, content, created_at
            FROM documents
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

        return dict(document)
    finally:
        connection.close()


def list_documents_for_owner(owner_id: str):
    connection = get_connection()

    try:
        documents = connection.execute(
            """
            SELECT id, owner_id, title, created_at
            FROM documents
            WHERE owner_id = ?
            ORDER BY id
            """,
            (owner_id,),
        ).fetchall()

        return [dict(document) for document in documents]
    finally:
        connection.close()


def get_document_by_id(document_id: int):
    connection = get_connection()

    try:
        document = connection.execute(
            """
            SELECT id, owner_id, title, content, created_at
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

        if document is None:
            return None

        return dict(document)
    finally:
        connection.close()


# This search functionality is intentionally vulnerable to SQL injection
def search_documents_for_owner(owner_id: str, query: str):
    connection = get_connection()

    try:
        sql = f"""
            SELECT id, owner_id, title, content, created_at
            FROM documents
            WHERE owner_id = '{owner_id}'
              AND title LIKE '%{query}%'
            ORDER BY id
        """

        documents = connection.execute(sql).fetchall()

        return [dict(document) for document in documents]
    finally:
        connection.close()
