from resource_service.database import DB_PATH, get_connection, reset_database

SEED_DOCUMENTS = [
    (
        1,
        "alice",
        "Alice private notes",
        "This is Alice's private document used for development and authorization testing.",
    ),
    (
        2,
        "bob",
        "Bob private notes",
        "This is Bob's private document used for development and authorization testing.",
    ),
]


def seed_database():
    reset_database()

    connection = get_connection()

    try:
        connection.executemany(
            """
            INSERT INTO documents (
                id,
                owner_id,
                title,
                content
            )
            VALUES (?, ?, ?, ?)
            """,
            SEED_DOCUMENTS,
        )

        connection.commit()

        documents = connection.execute("""
            SELECT id, owner_id, title
            FROM documents
            ORDER BY id
            """).fetchall()
    finally:
        connection.close()

    print(f"Database ready: {DB_PATH}")

    for document in documents:
        print(
            f"Document {document['id']}: "
            f"{document['owner_id']} - {document['title']}"
        )


if __name__ == "__main__":
    seed_database()
