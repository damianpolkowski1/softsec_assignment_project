import sqlite3
from pathlib import Path
import json
import shutil
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "resources.db"
RESULTS_DIR = DATA_DIR / "results"


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
        shutil.rmtree(DATA_DIR)

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


def search_documents_for_owner(owner_id: str, query: str):
    connection = get_connection()

    try:
        sql = """
            SELECT id, owner_id, title, content, created_at
            FROM documents
            WHERE owner_id = ?
              AND title LIKE ?
            ORDER BY id
        """

        documents = connection.execute(
            sql,
            (owner_id, f"%{query}%"),
        ).fetchall()

        return [dict(document) for document in documents]
    finally:
        connection.close()


def store_analysis_result(document_id: int, analysis: dict):
    connection = get_connection()

    try:
        document = connection.execute(
            """
            SELECT owner_id
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

        if document is None:
            return None

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        filename = f"analysis_{document_id}_{uuid4().hex}.json"

        result_path = RESULTS_DIR / filename

        with result_path.open("w", encoding="utf-8") as result_file:
            json.dump(
                analysis,
                result_file,
                indent=2,
            )

        cursor = connection.execute(
            """
            INSERT INTO analysis_results (
                document_id,
                owner_id,
                result_filename
            )
            VALUES (?, ?, ?)
            """,
            (
                document_id,
                document["owner_id"],
                filename,
            ),
        )

        connection.commit()

        result = connection.execute(
            """
            SELECT
                id,
                document_id,
                owner_id,
                result_filename,
                created_at
            FROM analysis_results
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

        return dict(result)
    finally:
        connection.close()


def get_analysis_result_by_id(result_id: int):
    connection = get_connection()

    try:
        result = connection.execute(
            """
            SELECT
                id,
                document_id,
                owner_id,
                result_filename,
                created_at
            FROM analysis_results
            WHERE id = ?
            """,
            (result_id,),
        ).fetchone()

        if result is None:
            return None

        return dict(result)
    finally:
        connection.close()


def read_result_file(filename: str):
    result_path = RESULTS_DIR / filename

    if not result_path.is_file():
        return None

    return result_path.read_text(encoding="utf-8")


def list_all_document_metadata():
    connection = get_connection()

    try:
        documents = connection.execute("""
            SELECT id, owner_id, title, created_at
            FROM documents
            ORDER BY id
            """).fetchall()

        return [dict(document) for document in documents]
    finally:
        connection.close()
