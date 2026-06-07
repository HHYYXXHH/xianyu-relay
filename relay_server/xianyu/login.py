"""
闲鱼扫码登录脚本（独立于 MCP）。
在 headless 模式下将二维码保存为图片，用户扫码后保存 Cookie。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

COOKIE_DIR = Path.home() / ".xianyu-mcp" / "browser_data"
COOKIE_FILE = COOKIE_DIR / "cookies.json"

# 二维码输出到 data/uploaded_images，可通过 HTTP 服务直接访问
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = Path(os.environ.get("RELAY_DATA_DIR", str(_PROJECT_ROOT / "data")))
QRCODE_OUTPUT = _DATA_DIR / "uploaded_images" / "xianyu_qrcode.png"

XIANYU_URL = "https://www.goofish.com"
LOGIN_IFRAME = "#alibaba-login-box"
LOGIN_BTN = ".btn--LjnfPVtt"
QRCODE_CANVAS = ".qrcode-img canvas"
LOGGED_IN_INDICATOR = ".nick--RyNYtDXM"


async def main():
    from playwright.async_api import async_playwright

    print("启动浏览器（headless）...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = await context.new_page()

        # 1. 打开闲鱼首页
        print("打开闲鱼首页...")
        await page.goto(XIANYU_URL, timeout=30000)
        await page.wait_for_load_state("networkidle")

        # 2. 检查是否已登录
        logged_in = await page.locator(LOGGED_IN_INDICATOR).count()
        if logged_in > 0:
            text = await page.locator(LOGGED_IN_INDICATOR).first.text_content()
            print(f"已登录: {text.strip()}")
            await _save_cookies(context)
            await browser.close()
            return

        # 3. 点击登录按钮
        print("点击登录按钮...")
        try:
            await page.wait_for_selector(LOGIN_BTN, timeout=10000)
            await page.click(LOGIN_BTN)
        except Exception:
            print("未找到登录按钮，可能页面结构已变或已登录")
            # 再试一次检查
            logged_in = await page.locator(LOGGED_IN_INDICATOR).count()
            if logged_in > 0:
                text = await page.locator(LOGGED_IN_INDICATOR).first.text_content()
                print(f"已登录: {text.strip()}")
                await _save_cookies(context)
            await browser.close()
            return

        # 4. 等待 iframe 出现
        print("等待登录 iframe...")
        await page.wait_for_selector(LOGIN_IFRAME, timeout=15000)
        frame = page.frame_locator(LOGIN_IFRAME)

        # 5. 等待二维码 canvas
        print("等待二维码...")
        await frame.locator(QRCODE_CANVAS).wait_for(timeout=15000)
        await asyncio.sleep(2)

        # 6. 截图二维码
        canvas = frame.locator(QRCODE_CANVAS).first
        screenshot = await canvas.screenshot()
        QRCODE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        QRCODE_OUTPUT.write_bytes(screenshot)
        print(f"二维码已保存: {QRCODE_OUTPUT}")
        print()
        print("=" * 50)
        print(f"请用闲鱼 App 扫描二维码")
        print(f"图片地址: http://139.199.11.252:9006/images/xianyu_qrcode.png")
        print("=" * 50)
        print()

        # 7. 轮询等待登录成功（最多 5 分钟）
        print("等待扫码登录（最长 5 分钟）...")
        deadline = time.time() + 300
        while time.time() < deadline:
            await asyncio.sleep(3)
            try:
                # 检查 iframe 是否消失（登录成功标志）
                iframe_count = await page.locator(LOGIN_IFRAME).count()
                if iframe_count == 0:
                    print("iframe 已消失，检查登录状态...")
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    logged_in = await page.locator(LOGGED_IN_INDICATOR).count()
                    if logged_in > 0:
                        text = await page.locator(LOGGED_IN_INDICATOR).first.text_content()
                        print(f"登录成功: {text.strip()}")
                        await _save_cookies(context)
                        await browser.close()
                        return
                    else:
                        print("iframe 消失但未检测到登录状态，继续等待...")
                        continue

                # 检查人脸验证
                face_qr = await frame.locator("#J_Qrcode canvas").count()
                if face_qr > 0:
                    face_screenshot = await frame.locator("#J_Qrcode canvas").first.screenshot()
                    QRCODE_OUTPUT.write_bytes(face_screenshot)
                    print("⚠️ 需要人脸验证，二维码已更新")
                    print(f"请重新扫码: http://139.199.11.252:9006/images/xianyu_qrcode.png")

                # 检查二维码是否还存在
                qr_count = await frame.locator(QRCODE_CANVAS).count()
                if qr_count > 0:
                    remaining = int(deadline - time.time())
                    if remaining % 10 == 0:
                        print(f"  等待中... ({remaining}s)")
            except Exception as e:
                print(f"  检查状态异常: {e}")
                continue

        print("登录超时（5分钟）")
        await browser.close()


async def _save_cookies(context):
    cookies = await context.cookies()
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存 {len(cookies)} 个 Cookie 到 {COOKIE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
