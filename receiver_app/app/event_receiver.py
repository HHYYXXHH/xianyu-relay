"""接收端事件接收 —— WebSocket 实时推送 + HTTP 轮询回退。

WebSocket 模式（默认）: 连接 ws://127.0.0.1:8001，事件实时送达
轮询模式（回退）: WebSocket 不可用时自动回退到 HTTP 轮询
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import Any

import websockets

from shared.constants import DEFAULT_ENCODING
from shared.event_schema import normalize_event, validate_event
from receiver_app.app.config import ConsumerStrategy, WS_URL, load_consumer_strategy
from receiver_app.app.reminder_manager import evaluate
from receiver_app.app.status_reporter import report_handled
from receiver_app.app.ui_renderer import render_event


# ── HTTP 轮询回退 ─────────────────────────────

def fetch_next_event(timeout_seconds: float) -> dict[str, Any] | None:
    """从中转服务读取下一个队列事件。"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/events/next", timeout=timeout_seconds) as response:
            body = response.read().decode(DEFAULT_ENCODING)
            payload = json.loads(body)
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None

    event = payload.get("event") if isinstance(payload, dict) else None
    if not isinstance(event, dict):
        return None

    ok, _ = validate_event(event)
    if not ok:
        return None

    return normalize_event(event)


def ack_event(event_id: str, timeout_seconds: float, retry_count: int, retry_delay_seconds: float) -> dict[str, Any]:
    """向中转服务确认队列事件已处理。"""
    payload = json.dumps({"event_id": event_id}).encode(DEFAULT_ENCODING)

    for attempt in range(retry_count + 1):
        request = urllib.request.Request(
            "http://127.0.0.1:8000/events/ack",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode(DEFAULT_ENCODING)
                return json.loads(body) if body else {"event_id": event_id, "acked": True}
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            if attempt == retry_count:
                return {"event_id": event_id, "acked": False}
            time.sleep(retry_delay_seconds)

    return {"event_id": event_id, "acked": False}


# ── WebSocket 实时消费 ────────────────────────

def connect_ws(strategy: ConsumerStrategy | None = None, config_path: str | None = None) -> None:
    """通过 WebSocket 连接中转服务器，实时接收事件。"""
    asyncio.run(_ws_consumer(strategy, config_path))


async def _ws_consumer(strategy: ConsumerStrategy | None = None, config_path: str | None = None) -> None:
    """WebSocket 消费者协程。"""
    effective = load_consumer_strategy(config_path) if strategy is None else strategy
    ws_url = WS_URL
    reconnect_delay = 1.0

    print(f"[接收端] WebSocket 模式: 连接 {ws_url}")

    while effective.max_cycles is None or effective.max_cycles > 0:
        try:
            async with websockets.connect(ws_url) as ws:
                print(f"[接收端] 已连接 WebSocket")
                reconnect_delay = 1.0

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    msg_type = msg.get("type", "")

                    if msg_type == "connected":
                        print(f"[接收端] {msg.get('message', '')} (id={msg.get('client_id', '')})")

                    elif msg_type == "event":
                        event = msg.get("event", {})
                        ok, _ = validate_event(event)
                        if not ok:
                            continue
                        event = normalize_event(event)
                        on_event_received(event, effective)
                        if effective.max_cycles is not None:
                            effective = ConsumerStrategy(
                                poll_interval_seconds=effective.poll_interval_seconds,
                                max_cycles=effective.max_cycles - 1,
                                fetch_timeout_seconds=effective.fetch_timeout_seconds,
                                ack_timeout_seconds=effective.ack_timeout_seconds,
                                ack_retry_count=effective.ack_retry_count,
                                ack_retry_delay_seconds=effective.ack_retry_delay_seconds,
                                stop_when_empty=effective.stop_when_empty,
                            )

                    elif msg_type == "ping":
                        await ws.send(json.dumps({"type": "pong"}))

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as exc:
            print(f"[接收端] WebSocket 断开: {exc}，{reconnect_delay:.0f}s 后重连...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 30)
            if effective.stop_when_empty:
                break

    print("[接收端] WebSocket 消费结束")


# ── 事件处理 ──────────────────────────────────

def on_event_received(event: dict[str, Any], strategy: ConsumerStrategy) -> dict[str, Any]:
    """收到事件后渲染并判断提醒。"""
    render_event(event)
    evaluate(event)
    result = report_handled(event.get("event_id", ""))
    return {"event_id": event.get("event_id"), "received": True, "reported": result}


# ── HTTP 轮询（兼容旧接口）─────────────────────

def connect_push(strategy: ConsumerStrategy | None = None, max_cycles: int | None = None, poll_interval: int | float | None = None, config_path: str | None = None) -> None:
    """HTTP 轮询模式。"""
    effective_strategy = load_consumer_strategy(config_path) if strategy is None else strategy

    if max_cycles is not None:
        effective_strategy = ConsumerStrategy(
            poll_interval_seconds=effective_strategy.poll_interval_seconds,
            max_cycles=max_cycles,
            fetch_timeout_seconds=effective_strategy.fetch_timeout_seconds,
            ack_timeout_seconds=effective_strategy.ack_timeout_seconds,
            ack_retry_count=effective_strategy.ack_retry_count,
            ack_retry_delay_seconds=effective_strategy.ack_retry_delay_seconds,
            stop_when_empty=effective_strategy.stop_when_empty,
        )
    if poll_interval is not None:
        effective_strategy = ConsumerStrategy(
            poll_interval_seconds=poll_interval,
            max_cycles=effective_strategy.max_cycles,
            fetch_timeout_seconds=effective_strategy.fetch_timeout_seconds,
            ack_timeout_seconds=effective_strategy.ack_timeout_seconds,
            ack_retry_count=effective_strategy.ack_retry_count,
            ack_retry_delay_seconds=effective_strategy.ack_retry_delay_seconds,
            stop_when_empty=effective_strategy.stop_when_empty,
        )

    print("[接收端] HTTP 轮询模式")
    cycles = 0
    while effective_strategy.max_cycles is None or cycles < effective_strategy.max_cycles:
        event = fetch_next_event(effective_strategy.fetch_timeout_seconds)
        if event is None:
            if effective_strategy.stop_when_empty:
                break
            time.sleep(effective_strategy.poll_interval_seconds)
            continue

        on_event_received(event, effective_strategy)
        cycles += 1

        if effective_strategy.max_cycles is None:
            time.sleep(effective_strategy.poll_interval_seconds)
