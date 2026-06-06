"""接收端配置。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ATTENTION_STATUS_URL = "http://127.0.0.1:8000/attention-status"
EVENT_NEXT_URL = "http://127.0.0.1:8000/events/next"
EVENT_ACK_URL = "http://127.0.0.1:8000/events/ack"
WS_URL = "ws://127.0.0.1:8001"
DEFAULT_CONSUMER_CONFIG_PATH = Path(__file__).with_name("consumer_strategy.json")
IMAGE_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "image_cache"


@dataclass(frozen=True)
class ConsumerStrategy:
    """接收端消费策略。"""

    poll_interval_seconds: float = 2
    max_cycles: int | None = None
    fetch_timeout_seconds: float = 10
    ack_timeout_seconds: float = 10
    ack_retry_count: int = 2
    ack_retry_delay_seconds: float = 0.5
    stop_when_empty: bool = False


DEFAULT_CONSUMER_STRATEGY = ConsumerStrategy()


def _coerce_env_value(name: str, raw_value: str):
    """把环境变量转换为对应类型。"""
    lower = raw_value.strip().lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if lower in {"none", "null"}:
        return None
    try:
        if "." in lower:
            return float(raw_value)
        return int(raw_value)
    except ValueError:
        return raw_value


def _load_strategy_file(path: Path | None) -> dict[str, object]:
    """从配置文件读取策略。"""
    file_path = path or DEFAULT_CONSUMER_CONFIG_PATH
    if not file_path.exists():
        return {}

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def _load_strategy_env() -> dict[str, object]:
    """从环境变量读取策略覆盖。"""
    env_keys = {
        "poll_interval_seconds": "RECEIVER_CONSUMER_POLL_INTERVAL_SECONDS",
        "max_cycles": "RECEIVER_CONSUMER_MAX_CYCLES",
        "fetch_timeout_seconds": "RECEIVER_CONSUMER_FETCH_TIMEOUT_SECONDS",
        "ack_timeout_seconds": "RECEIVER_CONSUMER_ACK_TIMEOUT_SECONDS",
        "ack_retry_count": "RECEIVER_CONSUMER_ACK_RETRY_COUNT",
        "ack_retry_delay_seconds": "RECEIVER_CONSUMER_ACK_RETRY_DELAY_SECONDS",
        "stop_when_empty": "RECEIVER_CONSUMER_STOP_WHEN_EMPTY",
    }

    overrides: dict[str, object] = {}
    for field_name, env_name in env_keys.items():
        raw = os.getenv(env_name)
        if raw is None:
            continue
        overrides[field_name] = _coerce_env_value(field_name, raw)
    return overrides


def load_consumer_strategy(config_path: str | Path | None = None) -> ConsumerStrategy:
    """加载消费策略，配置文件为基础，环境变量覆盖。"""
    file_payload = _load_strategy_file(Path(config_path) if config_path else None)
    env_payload = _load_strategy_env()
    merged = {
        "poll_interval_seconds": DEFAULT_CONSUMER_STRATEGY.poll_interval_seconds,
        "max_cycles": DEFAULT_CONSUMER_STRATEGY.max_cycles,
        "fetch_timeout_seconds": DEFAULT_CONSUMER_STRATEGY.fetch_timeout_seconds,
        "ack_timeout_seconds": DEFAULT_CONSUMER_STRATEGY.ack_timeout_seconds,
        "ack_retry_count": DEFAULT_CONSUMER_STRATEGY.ack_retry_count,
        "ack_retry_delay_seconds": DEFAULT_CONSUMER_STRATEGY.ack_retry_delay_seconds,
        "stop_when_empty": DEFAULT_CONSUMER_STRATEGY.stop_when_empty,
    }
    merged.update(file_payload)
    merged.update(env_payload)
    return ConsumerStrategy(**merged)


def make_consumer_strategy(**overrides) -> ConsumerStrategy:
    """根据覆盖项生成消费策略。"""
    strategy = load_consumer_strategy()
    data = strategy.__dict__.copy()
    data.update(overrides)
    return ConsumerStrategy(**data)
