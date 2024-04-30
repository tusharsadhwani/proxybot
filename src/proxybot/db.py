import sqlite3

_conn = None


def setup_db() -> None:
    conn = sqlite3.connect("./forward.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS forwards(
            message_id int PRIMARY KEY,
            user_id int,
            dm_message_id int
        )
        """
    )

    global _conn
    _conn = conn


def get_db() -> sqlite3.Connection:
    assert _conn is not None
    return _conn
