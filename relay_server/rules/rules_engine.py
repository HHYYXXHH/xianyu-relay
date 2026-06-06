"""
规则引擎：加载 YAML 规则文件，匹配用户消息，返回预设回复。
不依赖 LLM，纯规则匹配。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

RULES_FILE = Path(__file__).resolve().parent / "rules.yaml"


class RulesEngine:
    """规则引擎，单例。"""

    _instance: Optional["RulesEngine"] = None

    def __new__(cls) -> "RulesEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self._data: dict = {}
        self.reload()

    # ---- 公开 API ----

    def reload(self) -> None:
        """重新加载规则文件（修改 rules.yaml 后调用）。"""
        if RULES_FILE.exists():
            raw = RULES_FILE.read_text(encoding="utf-8")
            self._data = yaml.safe_load(raw) or {}
        else:
            self._data = {}

    def match(self, product_id: str, message: str) -> Optional[dict]:
        """根据商品ID和用户消息，返回匹配到的规则。

        Returns:
            None 表示未命中任何规则，需要 LLM 兜底。
            dict 格式: {"reply": str, "priority": "must"|"normal", "matched_keyword": str}
        """
        if not message or not message.strip():
            return None

        msg = message.strip()

        # 1. 先匹配指定商品的规则
        products = self._data.get("products", {})
        product_rules = products.get(product_id, {})
        if product_rules.get("enabled", True):
            for rule in product_rules.get("rules", []):
                result = self._try_rule(rule, msg)
                if result:
                    return result

        # 2. 再匹配全局规则
        for rule in self._data.get("global_rules", []):
            result = self._try_rule(rule, msg)
            if result:
                return result

        return None

    def get_product_ids(self) -> list[str]:
        """获取所有已配置的商品 ID。"""
        return list(self._data.get("products", {}).keys())

    def get_product_rules(self, product_id: str) -> list[dict]:
        """获取指定商品的所有规则（用于管理后台展示）。"""
        product = self._data.get("products", {}).get(product_id, {})
        return product.get("rules", [])

    def get_global_rules(self) -> list[dict]:
        """获取所有全局规则。"""
        return self._data.get("global_rules", [])

    def get_llm_constraints(self) -> list[str]:
        """获取 LLM 硬性约束列表。"""
        return self._data.get("llm_constraints", [])

    def get_constraints_text(self) -> str:
        """获取拼接好的 LLM 约束文本。"""
        constraints = self.get_llm_constraints()
        if not constraints:
            return ""
        lines = ["【以下规则必须严格遵守，不得违反】"]
        for i, c in enumerate(constraints, 1):
            lines.append(f"{i}. {c}")
        return "\n".join(lines)

    def get_templates(self) -> dict:
        """获取所有预设模板。"""
        return self._data.get("templates", {})

    def apply_template(self, template_name: str) -> list[dict] | None:
        """返回指定模板的规则列表（深拷贝），不存在返回 None。"""
        templates = self.get_templates()
        template = templates.get(template_name)
        if template is None:
            return None
        import copy
        return copy.deepcopy(template.get("rules", []))

    # ---- 内部 ----

    def _try_rule(self, rule: dict, msg: str) -> Optional[dict]:
        """尝试匹配单条规则。"""
        keywords = rule.get("trigger", [])
        if not keywords:
            return None

        for kw in keywords:
            if kw in msg:  # 简单子串匹配，无需分词
                return {
                    "reply": rule.get("reply", ""),
                    "priority": rule.get("priority", "normal"),
                    "matched_keyword": kw,
                }
        return None


def get_rules_engine() -> RulesEngine:
    """获取单例规则引擎。"""
    return RulesEngine()
