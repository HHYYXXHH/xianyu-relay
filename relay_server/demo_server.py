"""最小可运行的本地中转服务 Demo。

端点:
  GET  /health            - 健康检查
  GET  /stats             - 数据库统计
  GET  /images/<filename> - 获取已上传的图片
  GET  /events/next       - 获取下一条待消费事件
  GET  /events/pending    - 获取所有待消费事件
  POST /events            - 接收事件
  POST /events/ack        - 确认消费完成
  POST /images            - 上传图片（multipart/form-data）
  POST /attention-status  - 处理状态回传
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# 确保 PYTHONPATH 也包含项目根（解决跨目录启动问题）
import os as _os
if str(ROOT) not in _os.environ.get("PYTHONPATH", ""):
    _os.environ["PYTHONPATH"] = str(ROOT)

from relay_server.api.attention_status import update_attention_status
from relay_server.api.events import create_event
from relay_server.storage.db import init_db
from relay_server.storage.local_store import (
    ack_event, dequeue_event, get_store_stats,
    load_events, load_pending_events, save_image_record,
)
from relay_server.api.rules_api import handle_rules_request
from relay_server.xianyu import get_my_goods_list
from relay_server.ws_server import start_ws_server, get_connection_count

# 通过环境变量覆盖端口，方便服务器部署
HOST = _os.environ.get("RELAY_HOST", "0.0.0.0")
PORT = int(_os.environ.get("RELAY_PORT", "9006"))
WS_PORT = int(_os.environ.get("RELAY_WS_PORT", "9007"))
IMAGES_DIR = Path(_os.environ.get("RELAY_DATA_DIR", str(ROOT / "data"))) / "uploaded_images"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


def _ensure_images_dir() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


ADMIN_HTML = (ROOT / "relay_server" / "admin" / "index.html").read_text(encoding="utf-8")


class DemoHandler(BaseHTTPRequestHandler):
    """简化版 HTTP 处理器。"""

    server_version = "RelayDemo/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    # ── GET ──────────────────────────────────────

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "ws_clients": get_connection_count()})
            return

        if self.path == "/stats":
            self._send_json(200, get_store_stats())
            return

        if self.path == "/ws/status":
            self._send_json(200, {
                "ws_port": WS_PORT,
                "ws_clients": get_connection_count(),
                "http_port": PORT,
            })
            return

        if self.path == "/admin" or self.path == "/":
            self._serve_admin()
            return

        if self.path.startswith("/api/rules"):
            code, payload = handle_rules_request("GET", self.path, None)
            self._send_json(code, payload)
            return

        if self.path == "/api/xianyu/my_goods":
            self._handle_xianyu_my_goods()
            return

        if self.path.startswith("/images/"):
            self._serve_image(self.path[len("/images/"):])
            return

        if self.path == "/events/next":
            event_id = dequeue_event()
            event = load_events().get(event_id) if event_id else None
            self._send_json(200, {"event": event})
            return

        if self.path == "/events/pending":
            self._send_json(200, {"events": load_pending_events()})
            return

        self._send_json(404, {"status": "not_found"})

    # ── POST ─────────────────────────────────────

    def do_POST(self) -> None:
        content_type = self.headers.get("Content-Type", "")

        if self.path == "/images":
            self._handle_image_upload(content_type)
            return

        if self.path.startswith("/api/rules"):
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) if length else None
            code, payload = handle_rules_request("POST", self.path, raw_body)
            self._send_json(code, payload)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)

        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"status": "invalid_json"})
            return

        if self.path == "/events":
            response = create_event(payload)
            self._send_json(200, response)
            return

        if self.path == "/events/ack":
            event_id = payload.get("event_id")
            if not event_id:
                self._send_json(400, {"status": "missing_event_id"})
                return
            ack_event(event_id)
            self._send_json(200, {"event_id": event_id, "acked": True})
            return

        if self.path == "/attention-status":
            response = update_attention_status(payload)
            self._send_json(200, response)
            return

        self._send_json(404, {"status": "not_found"})

    # ── 图片上传 ─────────────────────────────────

    def _handle_image_upload(self, content_type: str) -> None:
        """处理 multipart/form-data 图片上传。"""
        if "multipart/form-data" not in content_type:
            self._send_json(400, {"status": "bad_request", "error": "需要 multipart/form-data"})
            return

        boundary = self._extract_boundary(content_type)
        if not boundary:
            self._send_json(400, {"status": "bad_request", "error": "缺少 boundary"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_UPLOAD_SIZE:
            self._send_json(413, {"status": "too_large", "error": f"图片最大 {MAX_UPLOAD_SIZE // 1024 // 1024}MB"})
            return

        raw_body = self.rfile.read(length)
        file_data = self._parse_multipart(raw_body, boundary)
        if file_data is None:
            self._send_json(400, {"status": "bad_request", "error": "无法解析图片数据"})
            return

        file_name, file_bytes = file_data
        sha = hashlib.sha256(file_bytes).hexdigest()[:12]
        ext = Path(file_name).suffix or ".jpg"
        stored_name = f"{int(time.time())}_{sha}{ext}"

        _ensure_images_dir()
        dest = IMAGES_DIR / stored_name
        dest.write_bytes(file_bytes)

        url = f"http://{HOST}:{PORT}/images/{stored_name}"
        save_image_record(url, str(dest), sha)

        self._send_json(200, {
            "status": "ok",
            "url": url,
            "filename": stored_name,
            "size": len(file_bytes),
            "checksum": sha,
        })

    # ── 图片获取 ─────────────────────────────────

    def _serve_image(self, filename: str) -> None:
        """返回已上传的图片文件。"""
        if ".." in filename or "/" in filename or "\\" in filename:
            self._send_json(403, {"status": "forbidden"})
            return

        _ensure_images_dir()
        path = IMAGES_DIR / filename
        if not path.exists():
            self._send_json(404, {"status": "not_found", "error": "图片不存在"})
            return

        content = path.read_bytes()
        suffix = path.suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
        mime = mime_map.get(suffix, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(content)

    # ── 工具方法 ─────────────────────────────────

    def _extract_boundary(self, content_type: str) -> str | None:
        """从 Content-Type 头提取 boundary。"""
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                return part[len("boundary="):]
        return None

    def _parse_multipart(self, body: bytes, boundary: str) -> tuple[str, bytes] | None:
        """解析 multipart/form-data 中的第一个文件字段。"""
        delimiter = b"--" + boundary.encode("utf-8")
        end_delimiter = delimiter + b"--"

        # 在 delimiter 处分割 body
        parts = body.split(delimiter)
        for part in parts:
            # 跳过空片段和结束片段
            part = part.lstrip(b"\r\n")
            if not part or part.startswith(b"--"):
                continue

            # 找到 header 和 body 的分界
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue

            headers_raw = part[:header_end].decode("utf-8", errors="replace")
            file_content = part[header_end + 4:]

            # 去掉尾部结束标记
            if end_delimiter in file_content:
                idx = file_content.rfind(end_delimiter)
                file_content = file_content[:idx]

            file_content = file_content.rstrip(b"\r\n-")

            # 提取文件名
            file_name = "upload.jpg"
            for line in headers_raw.split("\r\n"):
                if "filename=" in line:
                    name_start = line.find('filename="')
                    if name_start != -1:
                        name_start += len('filename="')
                        name_end = line.find('"', name_start)
                        if name_end != -1:
                            file_name = line[name_start:name_end]
                        break

            if file_content:
                return file_name, file_content

        return None

    def _handle_xianyu_my_goods(self) -> None:
        """获取闲鱼"我发布的"商品列表（异步调用）。"""
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(get_my_goods_list())
            loop.close()
        except Exception as e:
            result = {"success": False, "goods": [], "error": str(e)}
        self._send_json(200, result)

    def _serve_admin(self) -> None:
        """返回规则管理后台页面。"""
        html = ADMIN_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    _ensure_images_dir()
    init_db()
    ws_thread = start_ws_server()
    server = ThreadingHTTPServer((HOST, PORT), DemoHandler)
    from relay_server.config import DB_PATH as _DB_PATH, DATA_DIR
    print(f"HTTP 服务:       http://{HOST}:{PORT}")
    print(f"WebSocket 服务:   ws://{HOST}:{WS_PORT}")
    print(f"规则管理后台:     http://{HOST}:{PORT}/admin")
    print(f"数据目录:         {DATA_DIR}")
    print(f"  SQLite:         {_DB_PATH}")
    print(f"  图片上传: POST {HOST}:{PORT}/images")
    print(f"  图片获取: GET  {HOST}:{PORT}/images/<filename>")
    server.serve_forever()


if __name__ == "__main__":
    main()
