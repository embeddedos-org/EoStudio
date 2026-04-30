"""Multi-database client with schema introspection and query management."""
from __future__ import annotations

import csv
import enum
import io
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class DatabaseType(enum.Enum):
    """Supported database backends."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"
    DYNAMODB = "dynamodb"


@dataclass
class DatabaseConfig:
    """Connection configuration for a database."""
    db_type: DatabaseType = DatabaseType.SQLITE
    host: str = "localhost"
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_port(self) -> int:
        if self.port:
            return self.port
        defaults = {
            DatabaseType.SQLITE: 0,
            DatabaseType.POSTGRESQL: 5432,
            DatabaseType.MYSQL: 3306,
            DatabaseType.MONGODB: 27017,
            DatabaseType.REDIS: 6379,
            DatabaseType.DYNAMODB: 8000,
        }
        return defaults.get(self.db_type, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_type": self.db_type.value,
            "host": self.host,
            "port": self.effective_port,
            "database": self.database,
            "username": self.username,
            "options": self.options,
        }


@dataclass
class ColumnInfo:
    """Metadata about a table column."""
    name: str = ""
    data_type: str = ""
    nullable: bool = True
    primary_key: bool = False
    default: Any = None
    max_length: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "default": self.default,
            "max_length": self.max_length,
        }


@dataclass
class TableInfo:
    """Metadata about a database table."""
    name: str = ""
    columns: list[ColumnInfo] = field(default_factory=list)
    row_count: int | None = None
    size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": [c.to_dict() for c in self.columns],
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
        }


@dataclass
class QueryResult:
    """Result of a database query."""
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    affected_rows: int = 0
    elapsed_ms: float = 0.0
    query: str = ""
    error: str = ""

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def is_error(self) -> bool:
        return bool(self.error)

    def to_dicts(self) -> list[dict[str, Any]]:
        """Return rows as a list of dictionaries."""
        return [dict(zip(self.columns, row)) for row in self.rows]

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "affected_rows": self.affected_rows,
            "elapsed_ms": self.elapsed_ms,
            "row_count": self.row_count,
            "query": self.query,
            "error": self.error,
        }


@dataclass
class _SavedQuery:
    id: str = ""
    name: str = ""
    query: str = ""
    db_type: str = ""
    description: str = ""


class DatabaseClient:
    """Multi-database client with introspection and history."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self._conn: Any = None
        self._history: list[QueryResult] = []
        self._saved_queries: list[_SavedQuery] = []

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open a connection to the configured database."""
        if self._conn is not None:
            return

        db = self.config.db_type

        if db == DatabaseType.SQLITE:
            self._conn = sqlite3.connect(self.config.database or ":memory:")
            self._conn.row_factory = None
            return

        if db == DatabaseType.POSTGRESQL:
            psycopg2 = _lazy_import("psycopg2", "psycopg2-binary")
            self._conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.effective_port,
                dbname=self.config.database,
                user=self.config.username,
                password=self.config.password,
                **self.config.options,
            )
            return

        if db == DatabaseType.MYSQL:
            mysql = _lazy_import("mysql.connector", "mysql-connector-python")
            self._conn = mysql.connect(
                host=self.config.host,
                port=self.config.effective_port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                **self.config.options,
            )
            return

        if db == DatabaseType.MONGODB:
            pymongo = _lazy_import("pymongo", "pymongo")
            client = pymongo.MongoClient(
                host=self.config.host,
                port=self.config.effective_port,
                username=self.config.username or None,
                password=self.config.password or None,
                **self.config.options,
            )
            self._conn = client[self.config.database or "test"]
            return

        if db == DatabaseType.REDIS:
            redis = _lazy_import("redis", "redis")
            self._conn = redis.Redis(
                host=self.config.host,
                port=self.config.effective_port,
                password=self.config.password or None,
                db=int(self.config.database or 0),
                decode_responses=True,
                **self.config.options,
            )
            return

        if db == DatabaseType.DYNAMODB:
            boto3 = _lazy_import("boto3", "boto3")
            kwargs: dict[str, Any] = {"region_name": self.config.options.get("region", "us-east-1")}
            if self.config.host not in ("localhost", ""):
                kwargs["endpoint_url"] = f"http://{self.config.host}:{self.config.effective_port}"
            self._conn = boto3.resource("dynamodb", **kwargs)
            return

        raise ValueError(f"Unsupported database type: {db}")

    def disconnect(self) -> None:
        """Close the current connection."""
        if self._conn is None:
            return
        db = self.config.db_type
        if db in (DatabaseType.SQLITE, DatabaseType.POSTGRESQL, DatabaseType.MYSQL):
            self._conn.close()
        elif db == DatabaseType.MONGODB:
            self._conn.client.close()
        elif db == DatabaseType.REDIS:
            self._conn.close()
        self._conn = None

    def is_connected(self) -> bool:
        """Check whether the client holds an open connection."""
        if self._conn is None:
            return False
        db = self.config.db_type
        if db == DatabaseType.SQLITE:
            try:
                self._conn.execute("SELECT 1")
                return True
            except Exception:
                return False
        if db == DatabaseType.POSTGRESQL:
            return not getattr(self._conn, "closed", True)
        if db == DatabaseType.MYSQL:
            return getattr(self._conn, "is_connected", lambda: False)()
        if db == DatabaseType.REDIS:
            try:
                self._conn.ping()
                return True
            except Exception:
                return False
        return self._conn is not None

    def __enter__(self) -> DatabaseClient:
        self.connect()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] | dict[str, Any] | None = None) -> QueryResult:
        """Execute a query/command and return results."""
        if self._conn is None:
            raise RuntimeError("Not connected. Call connect() first.")

        db = self.config.db_type
        start = time.monotonic()
        result = QueryResult(query=query)

        try:
            if db in (DatabaseType.SQLITE, DatabaseType.POSTGRESQL, DatabaseType.MYSQL):
                result = self._exec_sql(query, params)
            elif db == DatabaseType.MONGODB:
                result = self._exec_mongo(query)
            elif db == DatabaseType.REDIS:
                result = self._exec_redis(query)
            elif db == DatabaseType.DYNAMODB:
                result = self._exec_dynamo(query)
        except Exception as exc:
            result.error = str(exc)

        result.elapsed_ms = round((time.monotonic() - start) * 1000.0, 2)
        result.query = query
        self._history.append(result)
        return result

    def _exec_sql(self, query: str, params: Any) -> QueryResult:
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = QueryResult()
        if cursor.description:
            result.columns = [desc[0] for desc in cursor.description]
            result.rows = [list(row) for row in cursor.fetchall()]
        result.affected_rows = cursor.rowcount if cursor.rowcount >= 0 else 0
        if self.config.db_type != DatabaseType.SQLITE:
            self._conn.commit()
        return result

    def _exec_mongo(self, query: str) -> QueryResult:
        """Execute a simplified MongoDB command as JSON string."""
        cmd = json.loads(query)
        collection_name = cmd.get("collection", "")
        operation = cmd.get("operation", "find")
        filter_doc = cmd.get("filter", {})
        projection = cmd.get("projection")
        data = cmd.get("data")

        col = self._conn[collection_name]
        result = QueryResult()

        if operation == "find":
            cursor = col.find(filter_doc, projection)
            docs = list(cursor)
            if docs:
                result.columns = list(docs[0].keys())
                result.rows = [[doc.get(k) for k in result.columns] for doc in docs]
        elif operation == "insert_one":
            col.insert_one(data or {})
            result.affected_rows = 1
        elif operation == "insert_many":
            res = col.insert_many(data or [])
            result.affected_rows = len(res.inserted_ids)
        elif operation == "update":
            update = cmd.get("update", {})
            res = col.update_many(filter_doc, update)
            result.affected_rows = res.modified_count
        elif operation == "delete":
            res = col.delete_many(filter_doc)
            result.affected_rows = res.deleted_count
        elif operation == "count":
            cnt = col.count_documents(filter_doc)
            result.columns = ["count"]
            result.rows = [[cnt]]
        return result

    def _exec_redis(self, query: str) -> QueryResult:
        """Execute a Redis command expressed as space-separated tokens."""
        parts = query.strip().split()
        if not parts:
            return QueryResult(error="Empty command")
        cmd = parts[0].upper()
        args = parts[1:]
        raw = self._conn.execute_command(cmd, *args)
        result = QueryResult(columns=["result"])
        if isinstance(raw, list):
            result.rows = [[item] for item in raw]
        else:
            result.rows = [[raw]]
        return result

    def _exec_dynamo(self, query: str) -> QueryResult:
        """Execute a DynamoDB operation expressed as JSON."""
        cmd = json.loads(query)
        table_name = cmd.get("table", "")
        operation = cmd.get("operation", "scan")
        table = self._conn.Table(table_name)
        result = QueryResult()

        if operation == "scan":
            resp = table.scan(**cmd.get("params", {}))
            items = resp.get("Items", [])
            if items:
                result.columns = list(items[0].keys())
                result.rows = [[item.get(k) for k in result.columns] for item in items]
        elif operation == "get_item":
            resp = table.get_item(Key=cmd.get("key", {}))
            item = resp.get("Item")
            if item:
                result.columns = list(item.keys())
                result.rows = [[item.get(k) for k in result.columns]]
        elif operation == "put_item":
            table.put_item(Item=cmd.get("item", {}))
            result.affected_rows = 1
        elif operation == "delete_item":
            table.delete_item(Key=cmd.get("key", {}))
            result.affected_rows = 1
        elif operation == "query":
            resp = table.query(**cmd.get("params", {}))
            items = resp.get("Items", [])
            if items:
                result.columns = list(items[0].keys())
                result.rows = [[item.get(k) for k in result.columns] for item in items]
        return result

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    def get_tables(self) -> list[str]:
        """List all table/collection names."""
        db = self.config.db_type
        if db == DatabaseType.SQLITE:
            res = self.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            return [row[0] for row in res.rows]
        if db == DatabaseType.POSTGRESQL:
            res = self.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            return [row[0] for row in res.rows]
        if db == DatabaseType.MYSQL:
            res = self.execute("SHOW TABLES")
            return [row[0] for row in res.rows]
        if db == DatabaseType.MONGODB:
            return sorted(self._conn.list_collection_names())
        if db == DatabaseType.REDIS:
            keys = self._conn.keys("*")
            return sorted(keys) if keys else []
        if db == DatabaseType.DYNAMODB:
            client = self._conn.meta.client
            resp = client.list_tables()
            return resp.get("TableNames", [])
        return []

    def get_table_info(self, table: str) -> TableInfo:
        """Get detailed metadata for a table."""
        db = self.config.db_type
        info = TableInfo(name=table)

        if db == DatabaseType.SQLITE:
            res = self.execute(f"PRAGMA table_info('{table}')")
            for row in res.rows:
                info.columns.append(
                    ColumnInfo(
                        name=row[1],
                        data_type=row[2],
                        nullable=not bool(row[3]),
                        primary_key=bool(row[5]),
                        default=row[4],
                    )
                )
            cnt = self.execute(f"SELECT COUNT(*) FROM '{table}'")
            if cnt.rows:
                info.row_count = cnt.rows[0][0]

        elif db == DatabaseType.POSTGRESQL:
            res = self.execute(
                "SELECT column_name, data_type, is_nullable, column_default, character_maximum_length "
                "FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                (table,),
            )
            pk_res = self.execute(
                "SELECT a.attname FROM pg_index i "
                "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
                "WHERE i.indrelid = %s::regclass AND i.indisprimary",
                (table,),
            )
            pk_cols = {row[0] for row in pk_res.rows}
            for row in res.rows:
                info.columns.append(
                    ColumnInfo(
                        name=row[0],
                        data_type=row[1],
                        nullable=row[2] == "YES",
                        primary_key=row[0] in pk_cols,
                        default=row[3],
                        max_length=row[4],
                    )
                )
            cnt = self.execute(f'SELECT COUNT(*) FROM "{table}"')
            if cnt.rows:
                info.row_count = cnt.rows[0][0]

        elif db == DatabaseType.MYSQL:
            res = self.execute(f"DESCRIBE `{table}`")
            for row in res.rows:
                info.columns.append(
                    ColumnInfo(
                        name=row[0],
                        data_type=row[1],
                        nullable=row[2] == "YES",
                        primary_key=row[3] == "PRI",
                        default=row[4],
                    )
                )
            cnt = self.execute(f"SELECT COUNT(*) FROM `{table}`")
            if cnt.rows:
                info.row_count = cnt.rows[0][0]

        elif db == DatabaseType.MONGODB:
            sample = self._conn[table].find_one()
            if sample:
                for key, val in sample.items():
                    info.columns.append(ColumnInfo(name=key, data_type=type(val).__name__))
            info.row_count = self._conn[table].estimated_document_count()

        return info

    def get_schema(self) -> list[TableInfo]:
        """Get schema information for all tables."""
        return [self.get_table_info(t) for t in self.get_tables()]

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_results(self, result: QueryResult, fmt: str = "csv") -> str:
        """Export query results to a string in the given format (csv, json, sql)."""
        if fmt == "json":
            return json.dumps(result.to_dicts(), indent=2, default=str)

        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(result.columns)
            writer.writerows(result.rows)
            return buf.getvalue()

        if fmt == "sql":
            if not result.columns or not result.rows:
                return ""
            lines: list[str] = []
            table = "exported_data"
            for row in result.rows:
                vals = ", ".join(
                    f"'{v}'" if isinstance(v, str) else "NULL" if v is None else str(v)
                    for v in row
                )
                cols = ", ".join(result.columns)
                lines.append(f"INSERT INTO {table} ({cols}) VALUES ({vals});")
            return "\n".join(lines)

        raise ValueError(f"Unsupported format: {fmt}")

    def import_data(self, table: str, path: str, fmt: str = "csv") -> int:
        """Import data from a file into a table. Returns number of rows imported."""
        content = Path(path).read_text()

        if fmt == "csv":
            reader = csv.reader(io.StringIO(content))
            headers = next(reader, None)
            if not headers:
                return 0
            count = 0
            for row in reader:
                placeholders = ", ".join(["?" if self.config.db_type == DatabaseType.SQLITE else "%s"] * len(row))
                cols = ", ".join(headers)
                self.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(row))
                count += 1
            if self.config.db_type == DatabaseType.SQLITE:
                self._conn.commit()
            return count

        if fmt == "json":
            records = json.loads(content)
            if not isinstance(records, list):
                records = [records]
            count = 0
            for rec in records:
                keys = list(rec.keys())
                vals = [rec[k] for k in keys]
                placeholders = ", ".join(["?" if self.config.db_type == DatabaseType.SQLITE else "%s"] * len(keys))
                cols = ", ".join(keys)
                self.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(vals))
                count += 1
            if self.config.db_type == DatabaseType.SQLITE:
                self._conn.commit()
            return count

        raise ValueError(f"Unsupported import format: {fmt}")

    # ------------------------------------------------------------------
    # History & saved queries
    # ------------------------------------------------------------------

    def get_history(self) -> list[dict[str, Any]]:
        """Return all past query results."""
        return [r.to_dict() for r in self._history]

    def clear_history(self) -> None:
        self._history.clear()

    def save_query(self, name: str, query: str, description: str = "") -> str:
        """Save a query for later use. Returns the saved query ID."""
        qid = uuid.uuid4().hex[:12]
        self._saved_queries.append(
            _SavedQuery(
                id=qid,
                name=name,
                query=query,
                db_type=self.config.db_type.value,
                description=description,
            )
        )
        return qid

    def get_saved_queries(self) -> list[dict[str, str]]:
        """List all saved queries."""
        return [
            {"id": sq.id, "name": sq.name, "query": sq.query, "db_type": sq.db_type, "description": sq.description}
            for sq in self._saved_queries
        ]

    def delete_saved_query(self, query_id: str) -> bool:
        """Delete a saved query by ID."""
        for i, sq in enumerate(self._saved_queries):
            if sq.id == query_id:
                self._saved_queries.pop(i)
                return True
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lazy_import(module_name: str, pip_name: str) -> Any:
    """Import a module, raising a helpful error if it's missing."""
    import importlib
    try:
        return importlib.import_module(module_name)
    except ImportError:
        raise ImportError(
            f"{module_name} is required for this database backend. "
            f"Install it with: pip install {pip_name}"
        )
