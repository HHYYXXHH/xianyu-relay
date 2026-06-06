"""审计日志模型骨架。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AuditLog:
    """审计日志模型。"""

    action: str
    detail: str
