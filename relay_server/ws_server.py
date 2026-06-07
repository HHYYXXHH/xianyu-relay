"""WebSocket 实时推送服务。

架构:
- WebSocket 服务器运行在独立线程 + 独立 asyncio event loop
- 线程安全: 通过 asyncio.run_coroutine_threadsafe 跨线程调度
- 广播: 存储 event loop 引用，HTTP 线程通过它调度发送
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import sys
import threading
import time
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection

HOST = os.environ.get("RELAY_HOST", "0.0.0.0")
WS_PORT = int(os.environ.get("RELAY_WS_PORT", "9007"))
HEARTBEAT_INTERVAL = 30

# 线程安全的状态
_loop: asyncio.AbstractEventLoop | None = None
_client_count = 0
_count_lock = threading.Lock()
_send_queue: queue.Queue[dict[str, Any]] = queue.Queue()

# WebSocket 连接集合（仅在事件循环线程内访问）
_ws_connections: set[ServerConnection] = set()


def get_connection_count() -> int:
    with _count_lock:
        return _client_count


def get_active_clients() -> list[str]:
    return []


async def _handler(websocket: ServerConnection) -> None:
    """处理单个 WebSocket 客户端。"""
    global _client_count
    with _count_lock:
        _client_count += 1

    client_id = f"client_{id(websocket)}_{int(time.time())}"

    try:
        _ws_connections.add(websocket)
        await websocket.send(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "message": "已连接到中转服务器",
        }, ensure_ascii=False))

        async for raw_message in websocket:
            try:
                msg = json.loads(raw_message)
                if msg.get("type") == "pong":
                    pass
                elif msg.get("type") == "ack":
                    event_id = msg.get("event_id", "")
                    if event_id:
                        from relay_server.storage.local_store import ack_event
                        ack_event(event_id)
                        await websocket.send(json.dumps({"type": "ack_ok", "event_id": event_id}))
            except json.JSONDecodeError:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        _ws_connections.discard(websocket)
        with _count_lock:
            _client_count -= 1


async def _process_send_queue() -> None:
    """从发送队列取消息并广播到所有客户端。"""
    while True:
        try:
            event = _send_queue.get(timeout=0.1)
        except queue.Empty:
            await asyncio.sleep(0.05)
            continue

        message = json.dumps({
            "type": "event",
            "event": event,
        }, ensure_ascii=False)

        dead: list[ServerConnection] = []
        for ws in list(_ws_connections):
            try:
                await ws.send(message)
            except (websockets.exceptions.ConnectionClosed, Exception):
                dead.append(ws)

        for ws in dead:
            _ws_connections.discard(ws)


def broadcast_event(event: dict[str, Any]) -> bool:
    """向所有客户端广播事件（非阻塞，线程安全）。"""
    global _loop
    if _loop is None or _loop.is_closed():
        return False

    _send_queue.put(event)
    return True


async def _serve() -> None:
    """启动 WebSocket 服务器 + 发送队列处理器。"""
    global _loop
    _loop = asyncio.get_event_loop()

    async with websockets.serve(_handler, HOST, WS_PORT):
        # 同时启动队列处理器
        queue_task = asyncio.create_task(_process_send_queue())
        try:
            await asyncio.Future()
        finally:
            queue_task.cancel()


def _run_ws_server() -> None:
    """在新线程中运行 WebSocket 事件循环。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_serve())
    except OSError as e:
        print(f"[WS] 端口 {WS_PORT} 被占用，WebSocket 服务未能启动: {e}", file=sys.stderr)
        print(f"[WS] HTTP 服务仍正常运行，可用环境变量 RELAY_WS_PORT 更换端口", file=sys.stderr)
    except Exception as e:
        print(f"[WS] 未知错误: {e}", file=sys.stderr)
    finally:
        loop.close()


def start_ws_server() -> threading.Thread:
    """启动 WebSocket 服务器线程。"""
    thread = threading.Thread(target=_run_ws_server, daemon=True, name="ws-server")
    thread.start()
    return thread
