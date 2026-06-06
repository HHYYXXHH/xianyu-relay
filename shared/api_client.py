"""统一的 HTTP 客户端骨架。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from shared.constants import DEFAULT_TIMEOUT


def post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """向指定 URL 发送 POST 请求。"""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            body = response.read().decode("utf-8")
            return {"ok": True, "status": response.status, "body": json.loads(body) if body else {}}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "body": {"error": exc.reason}}
    except Exception as exc:
        return {"ok": False, "status": 500, "body": {"error": str(exc)}}
