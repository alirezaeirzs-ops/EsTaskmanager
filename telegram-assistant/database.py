import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional
import pytz

DB_PATH = os.getenv("DB_PATH", "assistant.db")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tehran")
REMINDER_MINUTES = int(os.getenv("REMINDER_MINUTES", "15"))


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY,
            name          TEXT,
            reminder_minutes INTEGER DEFAULT 15,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            title            TEXT NOT NULL,
            due_datetime     TEXT,
            is_recurring     INTEGER DEFAULT 0,
            recurrence_rule  TEXT,
            reminder_minutes INTEGER DEFAULT 15,
            reminded         INTEGER DEFAULT 0,
            done             INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """)
        self.conn.commit()

    # ── Users ────────────────────────────────────────────
    def upsert_user(self, user_id: int, name: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        self.conn.commit()

    def get_user(self, user_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else {}

    def get_all_users(self) -> list:
        rows = self.conn.execute("SELECT * FROM users").fetchall()
        return [dict(r) for r in rows]

    def update_user_reminder(self, user_id: int, minutes: int):
        self.conn.execute(
            "UPDATE users SET reminder_minutes = ? WHERE user_id = ?",
            (minutes, user_id)
        )
        self.conn.commit()

    # ── Tasks ────────────────────────────────────────────
    def add_task(
        self,
        user_id: int,
        title: str,
        due_datetime: Optional[str] = None,
        is_recurring: bool = False,
        recurrence_rule: Optional[str] = None,
        reminder_minutes: int = REMINDER_MINUTES,
    ) -> int:
        # Get user's personal reminder_minutes if available
        user = self.get_user(user_id)
        rem = user.get("reminder_minutes", reminder_minutes)

        cur = self.conn.execute(
            """INSERT INTO tasks
               (user_id, title, due_datetime, is_recurring, recurrence_rule, reminder_minutes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, title, due_datetime, int(is_recurring), recurrence_rule, rem)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_task(self, task_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else {}

    def get_all_active_tasks(self, user_id: int) -> list:
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND done = 0 ORDER BY due_datetime ASC NULLS LAST",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_tasks_in_range(self, user_id: int, start: datetime, end: datetime) -> list:
        rows = self.conn.execute(
            """SELECT * FROM tasks
               WHERE user_id = ? AND done = 0
               AND due_datetime >= ? AND due_datetime < ?
               ORDER BY due_datetime ASC""",
            (user_id, start.isoformat(), end.isoformat())
        ).fetchall()
        return [dict(r) for r in rows]

    def get_upcoming_tasks_for_reminder(self, now: datetime) -> list:
        """تسک‌هایی که در بازه reminder_minutes دقیقه آینده هستن و هنوز یادآوری نشدن"""
        # We check tasks where due_datetime is between now and now+reminder_minutes
        # and reminded=0 — joining with users to get per-user reminder_minutes
        rows = self.conn.execute(
            """SELECT t.*, u.reminder_minutes as user_reminder
               FROM tasks t
               JOIN users u ON t.user_id = u.user_id
               WHERE t.done = 0 AND t.reminded = 0
               AND t.due_datetime IS NOT NULL""",
        ).fetchall()

        result = []
        tz = pytz.timezone(TIMEZONE)
        for row in rows:
            t = dict(row)
            due = datetime.fromisoformat(t["due_datetime"]).astimezone(tz)
            now_tz = now.astimezone(tz)
            rem_min = t.get("user_reminder") or t.get("reminder_minutes", REMINDER_MINUTES)
            # Remind when we're within [rem_min-1, rem_min] minutes window
            delta = (due - now_tz).total_seconds() / 60
            if rem_min - 1 <= delta <= rem_min:
                result.append(t)
        return result

    def mark_reminded(self, task_id: int):
        self.conn.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (task_id,))
        self.conn.commit()

    def mark_done(self, task_id: int, user_id: int):
        self.conn.execute(
            "UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ?",
            (task_id, user_id)
        )
        self.conn.commit()

    def delete_task(self, task_id: int, user_id: int):
        self.conn.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id)
        )
        self.conn.commit()
