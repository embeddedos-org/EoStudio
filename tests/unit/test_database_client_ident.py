"""SQL identifier validation in DatabaseClient (bandit B608 hardening)."""

import json
import os
import tempfile
import unittest

from eostudio.core.devtools.database_client import (
    DatabaseClient,
    DatabaseConfig,
    DatabaseType,
    QueryResult,
    _ident,
)


class TestIdentValidator(unittest.TestCase):
    def test_accepts_plain_identifiers(self):
        for name in ("users", "_private", "Table_2", "a"):
            self.assertEqual(_ident(name), name)

    def test_rejects_injection_and_non_identifiers(self):
        for name in ("users; DROP TABLE x", "", "1users", "a-b", "a b", 'x"', "x'", "x`", "a.b", "users\n"):
            with self.assertRaises(ValueError, msg=repr(name)):
                _ident(name)


class TestDatabaseClientUsesValidator(unittest.TestCase):
    def setUp(self):
        self.client = DatabaseClient(DatabaseConfig(db_type=DatabaseType.SQLITE, database=":memory:"))
        self.client.connect()
        self.client.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        self.client.execute("INSERT INTO users (name) VALUES (?)", ("alice",))

    def tearDown(self):
        self.client.disconnect()

    def _tmp(self, text, suffix):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_get_table_info_valid(self):
        info = self.client.get_table_info("users")
        self.assertEqual([c.name for c in info.columns], ["id", "name"])
        self.assertEqual(info.row_count, 1)

    def test_get_table_info_rejects_injection(self):
        with self.assertRaises(ValueError):
            self.client.get_table_info("users; DROP TABLE users")
        self.assertIn("users", self.client.get_tables())

    def test_import_csv_valid_and_rejects_bad_names(self):
        path = self._tmp("name\nbob\ncarol\n", ".csv")
        self.assertEqual(self.client.import_data("users", path), 2)
        self.assertEqual(self.client.get_table_info("users").row_count, 3)
        with self.assertRaises(ValueError):
            self.client.import_data("users; DROP TABLE users", path)
        bad_header = self._tmp("name) VALUES ('x'); DROP TABLE users; --\nbob\n", ".csv")
        with self.assertRaises(ValueError):
            self.client.import_data("users", bad_header)
        self.assertIn("users", self.client.get_tables())

    def test_import_json_rejects_bad_key(self):
        good = self._tmp(json.dumps([{"name": "dave"}]), ".json")
        self.assertEqual(self.client.import_data("users", good, fmt="json"), 1)
        bad = self._tmp(json.dumps([{"name; DROP TABLE users": "x"}]), ".json")
        with self.assertRaises(ValueError):
            self.client.import_data("users", bad, fmt="json")

    def test_export_sql_validates_columns_and_escapes_values(self):
        res = QueryResult(columns=["id", "name"], rows=[[1, "o'brien"], [2, None]])
        out = self.client.export_results(res, fmt="sql")
        self.assertEqual(
            out.splitlines(),
            [
                "INSERT INTO exported_data (id, name) VALUES (1, 'o''brien');",
                "INSERT INTO exported_data (id, name) VALUES (2, NULL);",
            ],
        )
        with self.assertRaises(ValueError):
            self.client.export_results(QueryResult(columns=["x; DROP"], rows=[[1]]), fmt="sql")


if __name__ == "__main__":
    unittest.main()
