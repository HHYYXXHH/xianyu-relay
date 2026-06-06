"""SQLite 持久化存储 —— 替换原 JSON 文件存储。

所有函数签名与旧版兼容，内部实现全部切换为 SQLite。
"""

from __future__ import annotations

import json
import time
from typing import Any

from relay_server.storage.db import get_db


# ═══════════════════════════════════════════
# 事件管理
# ═══════════════════════════════════════════

def upsert_event(payload: dict[str, Any]) -> None:
    """写入或更新事件。"""
    db = get_db()
    db.execute(
        """INSERT INTO events (
            event_id, event_type, content_type, source, timestamp,
            thread_key, message_key, summary, ocr_status, upload_status,
            need_receiver_attention, notify_receiver, checksum,
            content_text, image_ocr_text, ocr_error, error_code, error_message
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(event_id) DO UPDATE SET
            ocr_status=excluded.ocr_status,
            upload_status=excluded.upload_status,
            need_receiver_attention=excluded.need_receiver_attention,
            notify_receiver=excluded.notify_receiver,
            updated_at=datetime('now','localtime')
        """,
        (
            payload["event_id"], payload["event_type"], payload["content_type"],
            payload.get("source", ""), payload.get("timestamp", ""),
            payload.get("thread_key", ""), payload.get("message_key", ""),
            payload.get("summary", ""), payload.get("ocr_status", "not_needed"),
            payload.get("upload_status", "pending"),
            int(payload.get("need_receiver_attention", False)),
            int(payload.get("notify_receiver", False)),
            payload.get("checksum", ""),
            payload.get("content_text", ""), payload.get("image_ocr_text", ""),
            payload.get("ocr_error", ""), payload.get("error_code", ""),
            payload.get("error_message", ""),
        ),
    )
    db.commit()

    # 需要推送的事件加入投递队列
    if payload.get("notify_receiver"):
        enqueue_event(payload)


def load_events() -> dict[str, dict[str, Any]]:
    """读取所有事件（兼容旧接口，返回 dict 格式）。"""
    db = get_db()
    rows = db.execute("SELECT * FROM events ORDER BY created_at DESC").fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        d = dict(row)
        d["need_receiver_attention"] = bool(d.get("need_receiver_attention", 0))
        d["notify_receiver"] = bool(d.get("notify_receiver", 0))
        # 合并图片引用
        imgs = db.execute(
            "SELECT image_ref FROM event_images WHERE event_id=?", (d["event_id"],)
        ).fetchall()
        d["image_refs"] = [r["image_ref"] for r in imgs]
        result[d["event_id"]] = d
    return result


def has_event_key(key: str) -> bool:
    """判断 event_id 或 checksum 是否已存在。"""
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM events WHERE event_id=? OR checksum=? LIMIT 1",
        (key, key),
    ).fetchone()
    return row is not None


def mark_handled(event_id: str) -> None:
    """标记事件已处理。"""
    db = get_db()
    db.execute(
        "UPDATE events SET attention_status='handled', handled_at=datetime('now','localtime'), updated_at=datetime('now','localtime') WHERE event_id=?",
        (event_id,),
    )
    db.commit()


def update_event_images(event_id: str, image_refs: list[str]) -> None:
    """更新事件的图片引用（先删后插）。"""
    db = get_db()
    db.execute("DELETE FROM event_images WHERE event_id=?", (event_id,))
    for ref in image_refs:
        db.execute(
            "INSERT INTO event_images (event_id, image_ref) VALUES (?,?)",
            (event_id, ref),
        )
    db.commit()


# ═══════════════════════════════════════════
# 已处理状态（兼容旧接口）
# ═══════════════════════════════════════════

def load_handled() -> dict[str, bool]:
    """读取已处理事件集合。"""
    db = get_db()
    rows = db.execute(
        "SELECT event_id FROM events WHERE attention_status='handled'"
    ).fetchall()
    return {r["event_id"]: True for r in rows}


def save_handled(handed: dict[str, bool]) -> None:
    """保存已处理状态（SQLite 下为兼容空操作，实际由 mark_handled 处理）。"""
    pass


# ═══════════════════════════════════════════
# 事件集合批量操作（兼容旧接口）
# ═══════════════════════════════════════════

def save_events(events: dict[str, dict[str, Any]]) -> None:
    """批量保存事件（兼容空操作，实际由 upsert_event 逐条处理）。"""
    pass


# ═══════════════════════════════════════════
# 队列管理
# ═══════════════════════════════════════════

def enqueue_event(payload: dict[str, Any]) -> None:
    """将 `notify_receiver=true` 的事件加入投递队列。"""
    if not payload.get("notify_receiver"):
        return
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO event_delivery (event_id, push_status) VALUES (?, 'pending')",
        (payload["event_id"],),
    )
    db.commit()


def dequeue_event() -> str | None:
    """从队列取出一个待投递事件 ID，标记为 inflight。"""
    db = get_db()
    # 超时回收 inflight (>300s 未确认的)
    db.execute(
        "UPDATE event_delivery SET push_status='pending', pushed_at=NULL "
        "WHERE push_status='inflight' AND pushed_at IS NOT NULL "
        "AND (strftime('%s','now') - strftime('%s', pushed_at)) > 300"
    )
    db.commit()

    row = db.execute(
        "SELECT event_id FROM event_delivery WHERE push_status='pending' ORDER BY id LIMIT 1"
    ).fetchone()
    if not row:
        return None

    event_id = row["event_id"]
    db.execute(
        "UPDATE event_delivery SET push_status='inflight', pushed_at=datetime('now','localtime') WHERE event_id=?",
        (event_id,),
    )
    db.commit()
    return event_id


def ack_event(event_id: str) -> None:
    """确认投递完成，标记为 delivered + handled。"""
    db = get_db()
    db.execute(
        "UPDATE event_delivery SET push_status='delivered', delivered_at=datetime('now','localtime') WHERE event_id=?",
        (event_id,),
    )
    db.commit()
    mark_handled(event_id)


def load_pending_events() -> list[dict[str, Any]]:
    """读取所有待消费事件详情。"""
    db = get_db()
    rows = db.execute(
        """SELECT e.* FROM events e
           INNER JOIN event_delivery d ON e.event_id = d.event_id
           WHERE d.push_status IN ('pending', 'inflight')
           ORDER BY e.created_at ASC"""
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["need_receiver_attention"] = bool(d.get("need_receiver_attention", 0))
        d["notify_receiver"] = bool(d.get("notify_receiver", 0))
        imgs = db.execute(
            "SELECT image_ref FROM event_images WHERE event_id=?", (d["event_id"],)
        ).fetchall()
        d["image_refs"] = [r["image_ref"] for r in imgs]
        result.append(d)
    return result


# ═══════════════════════════════════════════
# 队列持久化（兼容旧接口）
# ═══════════════════════════════════════════

def load_queue() -> dict[str, Any]:
    """读取队列状态（兼容旧接口）。"""
    db = get_db()
    pending = db.execute(
        "SELECT event_id FROM event_delivery WHERE push_status='pending'"
    ).fetchall()
    inflight = db.execute(
        "SELECT event_id, pushed_at FROM event_delivery WHERE push_status='inflight'"
    ).fetchall()
    return {
        "pending": [r["event_id"] for r in pending],
        "inflight": {r["event_id"]: r["pushed_at"] or "" for r in inflight},
    }


def save_queue(queue: dict[str, Any]) -> None:
    """保存队列状态（兼容空操作，由 enqueue_event/dequeue_event/ack_event 处理）。"""
    pass


# ═══════════════════════════════════════════
# 图片记录
# ═══════════════════════════════════════════

def save_image_record(url: str, local_path: str, checksum: str) -> None:
    """记录已上传图片。"""
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO image_index (checksum, url, local_path, stored_at) VALUES (?,?,?,?)",
        (checksum, url, local_path, time.time()),
    )
    db.commit()


def get_image_record(checksum: str) -> dict[str, Any] | None:
    """根据 checksum 查询图片记录。"""
    db = get_db()
    row = db.execute(
        "SELECT * FROM image_index WHERE checksum=?", (checksum,)
    ).fetchone()
    if not row:
        return None
    return dict(row)


# ═══════════════════════════════════════════
# 数据库统计（新增）
# ═══════════════════════════════════════════

def get_store_stats() -> dict[str, int]:
    """返回存储统计信息。"""
    db = get_db()
    return {
        "total_events": db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "pending_delivery": db.execute(
            "SELECT COUNT(*) FROM event_delivery WHERE push_status IN ('pending','inflight')"
        ).fetchone()[0],
        "total_images": db.execute("SELECT COUNT(*) FROM event_images").fetchone()[0],
        "handled": db.execute(
            "SELECT COUNT(*) FROM events WHERE attention_status='handled'"
        ).fetchone()[0],
    }
