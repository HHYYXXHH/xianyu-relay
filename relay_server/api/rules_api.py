"""
规则管理 API：提供规则的读取和保存接口，供管理后台页面调用。
"""
from __future__ import annotations

import json
import yaml

from relay_server.rules import get_rules_engine, RULES_FILE


def get_rules_data() -> dict:
    """获取完整规则数据（JSON 格式，给管理后台渲染）。"""
    engine = get_rules_engine()
    engine.reload()  # 确保读到最新文件
    return engine._data


def save_rules_data(payload: dict) -> dict:
    """将前端提交的 JSON 数据写入 rules.yaml。"""
    if not payload:
        return {"success": False, "error": "空数据"}

    try:
        # 先验证：确保 YAML 可序列化
        yaml_text = yaml.dump(
            payload,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        # 写入文件
        RULES_FILE.write_text(yaml_text, encoding="utf-8")
        # 重新加载
        get_rules_engine().reload()
        return {"success": True, "message": "规则已保存并生效"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_rules_request(method: str, path: str, body: bytes | None) -> tuple[int, dict]:
    """处理规则相关请求，返回 (status_code, response_dict)。"""

    if method == "GET" and path == "/api/rules":
        return 200, get_rules_data()

    if method == "POST" and path == "/api/rules/save":
        if not body:
            return 400, {"success": False, "error": "缺少请求体"}
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return 400, {"success": False, "error": "JSON 解析失败"}
        result = save_rules_data(payload)
        return 200, result

    if method == "POST" and path == "/api/rules/reload":
        get_rules_engine().reload()
        return 200, {"success": True, "message": "已重新加载规则"}

    if method == "GET" and path == "/api/rules/match":
        # ?product_id=xxx&message=xxx
        return 200, {"success": False, "error": "需要 body 参数，请用 POST"}

    if method == "POST" and path == "/api/rules/match":
        if not body:
            return 400, {"success": False, "error": "缺少请求体"}
        try:
            params = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return 400, {"success": False, "error": "JSON 解析失败"}
        product_id = params.get("product_id", "")
        message = params.get("message", "")
        engine = get_rules_engine()
        result = engine.match(product_id, message)
        if result:
            return 200, {"matched": True, **result}
        return 200, {"matched": False, "message": "未命中任何规则，需要 LLM 兜底"}

    if method == "GET" and path == "/api/rules/templates":
        engine = get_rules_engine()
        return 200, engine.get_templates()

    if method == "POST" and path == "/api/rules/templates/apply":
        if not body:
            return 400, {"success": False, "error": "缺少请求体"}
        try:
            params = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return 400, {"success": False, "error": "JSON 解析失败"}
        template_name = params.get("template", "")
        engine = get_rules_engine()
        rules = engine.apply_template(template_name)
        if rules is None:
            return 404, {"success": False, "error": f"模板不存在: {template_name}"}
        return 200, {"success": True, "template": template_name, "rules": rules, "message": f"已应用模板「{template_name}」"}

    return 404, {"error": "未知规则 API 路径"}
