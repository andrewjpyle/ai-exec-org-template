import sqlite3

from exec_org.readers import basic


class _FakeConn:
    def __init__(self, row):
        self.row = row
        self.closed = False
        self.queries = []

    def cursor(self):
        return self

    def execute(self, query):
        self.queries.append(query)

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


def test_sql_connect_callable_is_used_and_closed():
    conn = _FakeConn((42,))
    out = basic.sql("leads", "SELECT 1", connect=lambda: conn)()
    assert out == {"leads": 42}
    assert conn.queries == ["SELECT 1"]
    assert conn.closed is True


def test_sql_no_database_configured_is_unavailable(monkeypatch):
    monkeypatch.delenv("EXEC_SQLITE_PATH", raising=False)
    out = basic.sql("leads", "SELECT 1")()
    assert out == {"unavailable": "no database configured"}


def test_sql_sqlite_path_from_env(monkeypatch, tmp_path):
    db = tmp_path / "d.db"
    c = sqlite3.connect(db)
    c.execute("create table t (n integer)")
    c.execute("insert into t values (7)")
    c.commit()
    c.close()
    monkeypatch.setenv("EXEC_SQLITE_PATH", str(db))
    assert basic.sql("n", "select n from t")() == {"n": 7}


def test_sql_empty_result_is_unavailable_not_zero():
    conn = _FakeConn(None)
    out = basic.sql("leads", "SELECT 1", connect=lambda: conn)()
    assert out == {"unavailable": "leads: query returned no value"}
    assert conn.closed is True


def test_sql_null_value_is_unavailable_but_zero_is_kept():
    null = basic.sql("k", "SELECT 1", connect=lambda: _FakeConn((None,)))()
    assert "unavailable" in null and "k" not in null
    zero = basic.sql("k", "SELECT 1", connect=lambda: _FakeConn((0,)))()
    assert zero == {"k": 0}
