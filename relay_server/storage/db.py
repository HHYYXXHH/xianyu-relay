"""SQLite 数据库连接管理与表结构初始化。

表结构:
- events:       事件主表
- event_images: 图片引用
- event_delivery: 推送投递记录
- image_index:  上传图片索引
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from relay_server.config import DB_PATH

_connections: dict[int, sqlite3.Connection] = {}
_lock = threading.Lock()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    TEXT NOT NULL UNIQUE,
    event_type  TEXT NOT NULL,
    content_type TEXT NOT NULL,
    source      TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    thread_key  TEXT NOT NULL,
    message_key TEXT NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    ocr_status  TEXT NOT NULL DEFAULT 'not_needed',
    upload_status TEXT NOT NULL DEFAULT 'pending',
    need_receiver_attention INTEGER NOT NULL DEFAULT 0,
    notify_receiver INTEGER NOT NULL DEFAULT 0,
    checksum    TEXT NOT NULL DEFAULT '',
    content_text TEXT DEFAULT '',
    image_ocr_text TEXT DEFAULT '',
    ocr_error   TEXT DEFAULT '',
    error_code  TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    retry_count INTEGER NOT NULL DEFAULT 0,
    attention_status TEXT DEFAULT '',
    handled_at  TEXT DEFAULT '',
    received_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS event_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    TEXT NOT NULL,
    image_ref   TEXT NOT NULL,
    storage_uri TEXT NOT NULL DEFAULT '',
    checksum    TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);

CREATE TABLE IF NOT EXISTS event_delivery (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    TEXT NOT NULL,
    receiver_id TEXT NOT NULL DEFAULT '',
    push_status TEXT NOT NULL DEFAULT 'pending',
    pushed_at   TEXT DEFAULT '',
    delivered_at TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS image_index (
    checksum    TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    local_path  TEXT NOT NULL,
    stored_at   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_thread_key ON events(thread_key);
CREATE INDEX IF NOT EXISTS idx_events_message_key ON events(message_key);
CREATE INDEX IF NOT EXISTS idx_events_checksum ON events(checksum);
CREATE INDEX IF NOT EXISTS idx_event_images_event_id ON event_images(event_id);
CREATE INDEX IF NOT EXISTS idx_event_delivery_event_id ON event_delivery(event_id);
"""


def _get_conn() -> sqlite3.Connection:
    """获取当前线程的数据库连接（线程安全）。"""
    tid = threading.get_ident()
    with _lock:
        if tid not in _connections:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            _connections[tid] = conn
        return _connections[tid]


def init_db() -> None:
    """初始化数据库表结构（幂等）。"""
    conn = _get_conn()
    conn.executescript(SCHEMA_SQL)
    # 迁移：为已有数据库添加 received_at 字段
    try:
        conn.execute("ALTER TABLE events ADD COLUMN received_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))")
    except sqlite3.OperationalError:
        pass  # 字段已存在
    conn.commit()


def get_db() -> sqlite3.Connection:
    """获取数据库连接，自动初始化。"""
    conn = _get_conn()
    # 检查表是否已创建
    try:
        conn.execute("SELECT 1 FROM events LIMIT 0")
    except sqlite3.OperationalError:
        init_db()
    return conn
