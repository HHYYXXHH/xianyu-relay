"""
轻量闲鱼 API 客户端。
复用 xianyu-mcp 登录后的 Cookie 文件（~/.xianyu-mcp/browser_data/cookies.json），
查询"我发布的"商品列表。
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import httpx

# xianyu-mcp 的 Cookie 存储位置
COOKIE_STORE_PATH = Path.home() / ".xianyu-mcp" / "browser_data" / "cookies.json"

APP_KEY = "34839810"
BASE_URL = "https://h5api.m.goofish.com/h5"

HEADERS = {
    "accept": "application/json",
    "accept-language": "zh-CN,zh;q=0.9",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.goofish.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


def _load_cookies() -> dict[str, str]:
    """从 xianyu-mcp cookie 文件加载有效 cookie。"""
    if not COOKIE_STORE_PATH.exists():
        return {}

    try:
        raw = json.loads(COOKIE_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    # 过滤过期 cookie
    now = time.time()
    cookies: dict[str, str] = {}
    for c in raw:
        name = c.get("name", "")
        value = c.get("value", "")
        expires = c.get("expires")
        if not name or not value:
            continue
        if expires is not None:
            try:
                exp = float(expires)
                if 0 < exp <= now:
                    continue
            except (TypeError, ValueError):
                pass
        cookies[name] = value
    return cookies


def _extract_token(m_h5_tk: str) -> str:
    """从 _m_h5_tk cookie 值提取 token（下划线前的部分）。"""
    pos = m_h5_tk.find("_")
    if pos > 0:
        return m_h5_tk[:pos]
    raise ValueError(f"无效的 _m_h5_tk 格式: {m_h5_tk}")


def _calculate_sign(token: str, timestamp: int, payload: str) -> str:
    """计算 mtop API 请求签名: MD5(token&timestamp&APP_KEY&payload)。"""
    raw = f"{token}&{timestamp}&{APP_KEY}&{payload}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _build_query_string(api_name: str, sign: str, timestamp: int,
                        extra_params: dict[str, str] | None = None) -> str:
    """构建 API 请求的 query string。"""
    params = {
        "jsv": "2.7.2",
        "appKey": APP_KEY,
        "t": str(timestamp),
        "sign": sign,
        "v": "1.0",
        "type": "originaljson",
        "accountSite": "xianyu",
        "dataType": "json",
        "timeout": "20000",
        "api": api_name,
        "sessionOption": "AutoLoginOnly",
        "spm_cnt": "a21ybx.search.0.0",
    }
    if extra_params:
        params.update(extra_params)
    return urllib.parse.urlencode(params)


async def get_login_user_id() -> dict:
    """获取当前登录用户的 ID。"""
    cookies = _load_cookies()
    m_h5_tk = cookies.get("_m_h5_tk", "")
    if not m_h5_tk:
        return {"success": False, "error": "未登录闲鱼，请先用 xianyu-mcp 登录"}

    try:
        token = _extract_token(m_h5_tk)
    except ValueError as e:
        return {"success": False, "error": f"token 无效: {e}"}

    payload = "{}"
    timestamp = int(time.time() * 1000)
    sign = _calculate_sign(token, timestamp, payload)

    query = _build_query_string(
        "mtop.taobao.idlemessage.pc.loginuser.get",
        sign, timestamp,
        {"spm_cnt": "a21ybx.personal.0.0"},
    )
    url = f"{BASE_URL}/mtop.taobao.idlemessage.pc.loginuser.get/1.0/?{query}"
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                url,
                content=f"data={urllib.parse.quote(payload, safe='')}",
                headers={**HEADERS, "cookie": cookie_header},
            )
            data = resp.json()
            ret = data.get("ret", [])
            if ret and "SUCCESS" in str(ret[0]):
                uid = data.get("data", {}).get("userId", "")
                return {"success": True, "user_id": str(uid) if uid else ""}
            return {"success": False, "error": f"API 返回非成功: {ret}"}
    except Exception as e:
        return {"success": False, "error": f"请求失败: {e}"}


async def get_my_goods_list(page: int = 1, page_size: int = 50) -> dict:
    """获取"我发布的"商品列表。"""
    cookies = _load_cookies()
    m_h5_tk = cookies.get("_m_h5_tk", "")
    if not m_h5_tk:
        return {"success": False, "goods": [], "error": "未登录闲鱼，请先用 xianyu-mcp 登录"}

    try:
        token = _extract_token(m_h5_tk)
    except ValueError as e:
        return {"success": False, "goods": [], "error": f"token 无效: {e}"}

    # 先获取用户 ID
    user_result = await get_login_user_id()
    if not user_result.get("success"):
        return {"success": False, "goods": [], "error": user_result.get("error", "获取用户ID失败")}

    user_id = user_result["user_id"]

    # 查我的商品列表
    api_payload = json.dumps({
        "needGroupInfo": True,
        "pageNumber": page,
        "userId": user_id,
        "pageSize": page_size,
    }, ensure_ascii=False)

    timestamp = int(time.time() * 1000)
    sign = _calculate_sign(token, timestamp, api_payload)

    query = _build_query_string(
        "mtop.idle.web.xyh.item.list",
        sign, timestamp,
        {"spm_cnt": "a21ybx.personal.0.0"},
    )
    url = f"{BASE_URL}/mtop.idle.web.xyh.item.list/1.0/?{query}"
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                url,
                content=f"data={urllib.parse.quote(api_payload, safe='')}",
                headers={**HEADERS, "cookie": cookie_header, "referer": "https://www.goofish.com/personal"},
            )
            data = resp.json()

            ret = data.get("ret", [])
            if not ret or "SUCCESS" not in str(ret[0]):
                return {"success": False, "goods": [],
                        "error": f"API 返回非成功 (可能未登录或风控): {ret}"}

            result_data = data.get("data", {})
            card_list = result_data.get("cardList", [])

            STATUS_MAP = {0: "selling", 1: "sold", 2: "taken_down"}
            goods = []
            for card in card_list:
                cd = card.get("cardData", {})
                item_id = cd.get("id", "")
                if not item_id:
                    continue
                status_code = cd.get("itemStatus", -1)
                price_info = cd.get("priceInfo", {})
                pic_info = cd.get("picInfo", {})
                goods.append({
                    "item_id": str(item_id),
                    "title": cd.get("title", ""),
                    "price": price_info.get("price", ""),
                    "status": STATUS_MAP.get(status_code, f"unknown({status_code})"),
                    "image_url": pic_info.get("picUrl", ""),
                    "url": f"https://www.goofish.com/item?id={item_id}",
                })

            return {
                "success": True,
                "goods": goods,
                "total": len(goods),
                "has_more": result_data.get("nextPage", False),
                "user_id": user_id,
            }
    except Exception as e:
        return {"success": False, "goods": [], "error": f"请求失败: {e}"}
