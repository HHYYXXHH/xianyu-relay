"""消息监听器 —— ADB 通知监控 + 文件监听 + 轮询。

三种模式（通过 ListenerConfig.mode 切换）:
- adb_bridge:   通过 ADB 监控手机通知栏，筛选闲鱼消息（生产模式）
- file_watcher: 监控本地目录下的 JSON 消息文件（测试模式）
- polling:      定时检查消息源（占位模式）

ADB 模式特性:
- 自动搜索 ADB 路径（PATH / Android SDK / platform-tools）
- 持续监控 dumpsys notification 输出
- 按 package 过滤（com.taobao.idlefish / 闲鱼）
- 增量去重（基于 notification key，最多缓存 500 条）
- ADB 断开自动重连
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from source_app.app.local_storage import save_image_from_file

# ── 数据结构 ────────────────────────────────

@dataclass
class MessageMeta:
    message_key: str
    thread_key: str
    timestamp: str
    source: str = "chat_page"


@dataclass
class ListenerConfig:
    mode: str = "adb_bridge"
    poll_interval: float = 2.0
    watch_dir: str = ""
    max_cycles: int | None = None
    adb_timeout: float = 10.0
    package_filter: str = "idlefish"


# ── 全局状态 ────────────────────────────────

_message_callback: Callable[[dict[str, Any]], None] | None = None
_seen_notifications: set[str] = set()

# ADB 路径缓存
_adb_exe: str | None = None
_ADB_PATHS = [
    "adb",
    os.path.expandvars("%LOCALAPPDATA%/Android/Sdk/platform-tools/adb.exe"),
    "C:/Users/mdjyx/AppData/Local/Android/Sdk/platform-tools/adb.exe",
    "C:/platform-tools/adb.exe",
]


def _get_adb() -> str:
    """获取 ADB 可执行文件路径，自动搜索并缓存。"""
    global _adb_exe
    if _adb_exe:
        return _adb_exe
    for p in _ADB_PATHS:
        try:
            r = subprocess.run([p, "version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                _adb_exe = p
                return p
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    _adb_exe = "adb"
    return "adb"


def _run_adb(args: list[str], timeout: float = 10) -> subprocess.CompletedProcess:
    return subprocess.run([_get_adb()] + args, capture_output=True, text=True, timeout=timeout)


# ── 公共 API ────────────────────────────────

def start_listener(config: ListenerConfig | None = None) -> None:
    if config is None:
        config = ListenerConfig()
    if config.mode == "adb_bridge":
        _run_adb_bridge(config)
    elif config.mode == "file_watcher":
        _run_file_watcher(config)
    else:
        _run_polling_loop(config)


def set_message_handler(handler: Callable[[dict[str, Any]], None]) -> None:
    global _message_callback
    _message_callback = handler


# ── ADB 桥接模式 ────────────────────────────

def check_adb_available() -> tuple[bool, str]:
    try:
        r = _run_adb(["version"], timeout=5)
        if r.returncode == 0:
            v = r.stdout.split("\n")[0] if r.stdout else "unknown"
            return True, v
        return False, r.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "adb 不可用，请安装 Android Platform Tools"


def check_device_connected() -> tuple[bool, str]:
    try:
        r = _run_adb(["devices"], timeout=5)
        lines = r.stdout.strip().split("\n")[1:]
        devices = [l for l in lines if l.strip() and "offline" not in l]
        if not devices:
            return False, "无已授权设备，请检查 USB 连接并在手机上授权调试"
        return True, devices[0].split("\t")[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "adb 不可用"


def _run_adb_bridge(config: ListenerConfig) -> None:
    ok, msg = check_adb_available()
    if not ok:
        print(f"[ADB] {msg}，回退到文件监听模式")
        _run_file_watcher(config)
        return

    print(f"[ADB] {msg}")
    ok, info = check_device_connected()
    if not ok:
        print(f"[ADB] {info}，等待设备连接...")

    cycles = 0
    delay = 2.0
    while config.max_cycles is None or cycles < config.max_cycles:
        if not check_device_connected()[0]:
            print(f"[ADB] 设备断开，{delay:.0f}s 后重试...")
            time.sleep(delay)
            delay = min(delay * 1.5, 30)
            continue
        delay = 2.0

        try:
            raw = _run_adb(["shell", "dumpsys", "notification", "--noredact"], timeout=config.adb_timeout).stdout
            messages = _parse_notifications(raw, config.package_filter)
            for msg in messages:
                result = on_message(msg)
                if _message_callback:
                    _message_callback(result)
            if messages:
                print(f"[ADB] 本轮 {len(messages)} 条新消息")
            cycles += 1
        except subprocess.TimeoutExpired:
            pass
        except Exception as exc:
            print(f"[ADB] 异常: {exc}")

        time.sleep(config.poll_interval)


def _parse_notifications(output: str, pkg_filter: str) -> list[dict[str, Any]]:
    global _seen_notifications
    messages: list[dict[str, Any]] = []

    blocks = re.split(r"(?=  NotificationRecord)", output)
    for block in blocks:
        if not block.strip():
            continue

        pkg_match = re.search(r"pkg=([^\s\n,}]+)", block)
        pkg = pkg_match.group(1) if pkg_match else ""
        if pkg_filter.lower() not in pkg.lower():
            continue

        key_match = re.search(r"key=([^\s\n)]+)", block)
        notif_key = key_match.group(1) if key_match else ""
        if notif_key and notif_key in _seen_notifications:
            continue
        if notif_key:
            _seen_notifications.add(notif_key)
        if len(_seen_notifications) > 500:
            _seen_notifications = set(list(_seen_notifications)[-200:])

        title_match = re.search(r"android\.title=([^\n]+)", block)
        text_match = re.search(r"android\.text=([^\n]+)", block)
        title = title_match.group(1).strip() if title_match else ""
        text = text_match.group(1).strip() if text_match else ""

        big_match = re.search(r"android\.bigText=([^\n]+)", block)
        if big_match and big_match.group(1).strip():
            big = big_match.group(1).strip()
            text = f"{text}\n{big}" if text else big

        when_match = re.search(r"when=(\d+)", block)
        when_ts = int(when_match.group(1)) if when_match else int(time.time() * 1000)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when_ts / 1000))

        image_uris = re.findall(r"uri=([^\s\n]+\.(?:jpg|jpeg|png|webp))", block, re.I)

        short_key = notif_key.split("|")[-1] if notif_key else str(int(time.time() * 1000))
        msg = {
            "message_key": f"notif_{short_key}",
            "thread_key": pkg,
            "timestamp": ts,
            "source": "notification_bar",
            "text": f"{title}\n{text}".strip(),
            "title": title,
            "images": [{"path": uri, "image_ref": uri} for uri in image_uris],
            "image_paths": image_uris,
            "raw_key": notif_key,
        }
        messages.append(msg)

    return messages


# ── 文件监听模式 ────────────────────────────

def _run_file_watcher(config: ListenerConfig) -> None:
    watch_dir = Path(config.watch_dir) if config.watch_dir else Path("data/watch")
    watch_dir.mkdir(parents=True, exist_ok=True)
    print(f"[文件监听] {watch_dir}")

    seen: set[str] = set()
    while config.max_cycles is None or len(seen) < config.max_cycles:
        for p in sorted(watch_dir.glob("*.json")):
            if str(p) in seen:
                continue
            seen.add(str(p))
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                result = on_message(raw)
                if _message_callback:
                    _message_callback(result)
                print(f"[文件监听] {p.name}")
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[文件监听] 失败: {p.name} - {exc}")
        time.sleep(config.poll_interval)


# ── 轮询模式 ────────────────────────────────

def _run_polling_loop(config: ListenerConfig) -> None:
    print(f"[轮询] 间隔 {config.poll_interval}s")
    cycles = 0
    while config.max_cycles is None or cycles < config.max_cycles:
        for msg in _fetch_pending_messages():
            result = on_message(msg)
            if _message_callback:
                _message_callback(result)
        cycles += 1
        time.sleep(config.poll_interval)


def _fetch_pending_messages() -> list[dict[str, Any]]:
    return []


# ── 消息标准化 ──────────────────────────────

def on_message(raw_message: dict[str, Any]) -> dict[str, Any]:
    metadata = extract_message_metadata(raw_message)
    images = extract_images(raw_message)

    saved_image_refs: list[str] = []
    for image in images:
        src_path = image.get("path", "")
        if src_path and os.path.exists(src_path):
            try:
                saved_image_refs.append(save_image_from_file(
                    src_path, message_key=metadata.message_key, timestamp=metadata.timestamp,
                ))
            except (OSError, FileNotFoundError):
                saved_image_refs.append(src_path)
        else:
            saved_image_refs.append(image.get("image_ref", ""))

    return {
        "message_key": metadata.message_key,
        "thread_key": metadata.thread_key,
        "timestamp": metadata.timestamp,
        "source": metadata.source,
        "images": images,
        "image_refs": saved_image_refs or raw_message.get("image_refs", []),
        "text": raw_message.get("text", ""),
    }


def extract_message_metadata(raw_message: dict[str, Any]) -> MessageMeta:
    return MessageMeta(
        message_key=raw_message.get("message_key", f"msg_{int(time.time() * 1000)}"),
        thread_key=raw_message.get("thread_key", "unknown_thread"),
        timestamp=raw_message.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
        source=raw_message.get("source", "chat_page"),
    )


def extract_images(raw_message: dict[str, Any]) -> list[dict[str, Any]]:
    images = raw_message.get("images", [])
    if not images:
        image_paths = raw_message.get("image_paths", [])
        images = [{"path": p} for p in image_paths]
    return images
