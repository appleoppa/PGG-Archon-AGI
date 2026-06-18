"""Regression tests for keeping tool payloads out of SessionDB FTS indexes."""

import sqlite3


def _make_db(tmp_path):
    from hermes_state import SessionDB

    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session(session_id="s1", source="test", model="test-model")
    return db


def _fts_counts(db):
    with db._lock:
        row = db._conn.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM messages_fts) AS unicode_count, "
            "(SELECT COUNT(*) FROM messages_fts_trigram) AS trigram_count"
        ).fetchone()
    return tuple(row)


def _install_unfiltered_legacy_triggers(db_path):
    """Simulate a v15 DB whose FTS triggers index tool messages."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            DROP TRIGGER IF EXISTS messages_fts_insert;
            DROP TRIGGER IF EXISTS messages_fts_update;
            DROP TRIGGER IF EXISTS messages_fts_trigram_insert;
            DROP TRIGGER IF EXISTS messages_fts_trigram_update;

            CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content) VALUES (
                    new.id,
                    COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
                );
            END;

            CREATE TRIGGER messages_fts_update AFTER UPDATE ON messages BEGIN
                DELETE FROM messages_fts WHERE rowid = old.id;
                INSERT INTO messages_fts(rowid, content) VALUES (
                    new.id,
                    COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
                );
            END;

            CREATE TRIGGER messages_fts_trigram_insert AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts_trigram(rowid, content) VALUES (
                    new.id,
                    COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
                );
            END;

            CREATE TRIGGER messages_fts_trigram_update AFTER UPDATE ON messages BEGIN
                DELETE FROM messages_fts_trigram WHERE rowid = old.id;
                INSERT INTO messages_fts_trigram(rowid, content) VALUES (
                    new.id,
                    COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
                );
            END;

            UPDATE schema_version SET version = 15;
            DELETE FROM messages_fts;
            DELETE FROM messages_fts_trigram;
            INSERT INTO messages_fts(rowid, content)
                SELECT id, COALESCE(content, '') || ' ' || COALESCE(tool_name, '') || ' ' || COALESCE(tool_calls, '')
                FROM messages;
            INSERT INTO messages_fts_trigram(rowid, content)
                SELECT id, COALESCE(content, '') || ' ' || COALESCE(tool_name, '') || ' ' || COALESCE(tool_calls, '')
                FROM messages;
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_tool_messages_do_not_enter_either_fts_index_on_insert(tmp_path):
    db = _make_db(tmp_path)
    try:
        user_id = db.append_message("s1", "user", content="visible alpha needle")
        tool_id = db.append_message(
            "s1",
            "tool",
            content="hidden omega needle",
            tool_name="secret_tool",
            tool_call_id="call-1",
        )

        assert user_id != tool_id
        assert _fts_counts(db) == (1, 1)
        assert db.search_messages("visible")
        assert db.search_messages("hidden") == []
    finally:
        db.close()


def test_tool_role_update_removes_message_from_both_fts_indexes(tmp_path):
    db = _make_db(tmp_path)
    try:
        msg_id = db.append_message("s1", "assistant", content="convertible beta needle")
        assert _fts_counts(db) == (1, 1)

        with db._lock:
            assert db._conn is not None
            db._conn.execute("UPDATE messages SET role = 'tool' WHERE id = ?", (msg_id,))
            db._conn.commit()

        assert _fts_counts(db) == (0, 0)
        assert db.search_messages("convertible") == []
    finally:
        db.close()


def test_legacy_unfiltered_fts_triggers_are_repaired_and_rebuilt(tmp_path):
    db_path = tmp_path / "state.db"
    db = _make_db(tmp_path)
    try:
        db.append_message("s1", "user", content="visible gamma needle")
        db.append_message(
            "s1",
            "tool",
            content="hidden legacy needle",
            tool_name="legacy_tool",
            tool_call_id="call-legacy",
        )
    finally:
        db.close()

    _install_unfiltered_legacy_triggers(db_path)

    # Reopening SessionDB should migrate v15 triggers to role-filtered v16
    # triggers and rebuild FTS from non-tool messages only.
    from hermes_state import SessionDB

    repaired = SessionDB(db_path=db_path)
    try:
        assert _fts_counts(repaired) == (1, 1)
        assert repaired.search_messages("visible")
        assert repaired.search_messages("hidden") == []
        with repaired._lock:
            assert repaired._conn is not None
            trigger_sql = "\n".join(
                row[0]
                for row in repaired._conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'messages_fts%' ORDER BY name"
                ).fetchall()
                if row[0]
            )
        assert "WHEN new.role != 'tool'" in trigger_sql
    finally:
        repaired.close()
