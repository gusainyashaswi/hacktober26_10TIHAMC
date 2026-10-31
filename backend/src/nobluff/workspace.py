"""Durable single-user repository and investigation metadata; no credentials stored."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class Workspace:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY, full_name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL, default_branch TEXT NOT NULL, connected_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY, request_json TEXT NOT NULL, report_json TEXT NOT NULL,
                    context_json TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
        self.path.chmod(0o600)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def connect(self, metadata):
        with self.db() as db:
            db.execute(
                "INSERT INTO repositories(full_name,url,default_branch,connected_at) VALUES(?,?,?,?) ON CONFLICT(full_name) DO UPDATE SET url=excluded.url,default_branch=excluded.default_branch",
                (
                    metadata["full_name"],
                    metadata["html_url"],
                    metadata["default_branch"],
                    datetime.now(UTC).isoformat(),
                ),
            )
            return dict(
                db.execute(
                    "SELECT * FROM repositories WHERE full_name=?",
                    (metadata["full_name"],),
                ).fetchone()
            )

    def repositories(self):
        with self.db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM repositories ORDER BY connected_at DESC"
                )
            ]

    def repository(self, identifier):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM repositories WHERE id=?", (identifier,)
            ).fetchone()
            return dict(row) if row else None

    def disconnect(self, identifier):
        with self.db() as db:
            db.execute("DELETE FROM repositories WHERE id=?", (identifier,))

    def save(self, request, report, context=None):
        with self.db() as db:
            db.execute(
                "INSERT INTO investigations VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET report_json=excluded.report_json",
                (
                    report.id,
                    request.model_dump_json(),
                    report.model_dump_json(),
                    json.dumps(context or {}),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def context(self, identifier, context):
        with self.db() as db:
            db.execute(
                "UPDATE investigations SET context_json=? WHERE id=?",
                (json.dumps(context), identifier),
            )

    def investigation(self, identifier):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM investigations WHERE id=?", (identifier,)
            ).fetchone()
            return dict(row) if row else None

    def history(self, repository=None, limit=50):
        with self.db() as db:
            rows = db.execute(
                "SELECT * FROM investigations ORDER BY created_at DESC LIMIT 500"
            ).fetchall()
        items = []
        for row in rows:
            report = json.loads(row["report_json"])
            context = json.loads(row["context_json"])
            if repository and report["repository"] != repository:
                continue
            items.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "repository": report["repository"],
                    "revision": report["revision"],
                    "comparison_revision": report.get("comparison_revision"),
                    "stage": report["stage"],
                    "context": context,
                }
            )
            if len(items) >= limit:
                break
        return items
