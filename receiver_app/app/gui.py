"""接收端 GUI —— 系统托盘 + 气泡通知 + 事件管理。

特性:
- 系统托盘: 最小化到托盘，右键菜单（显示窗口/退出）
- 气泡通知: need_receiver_attention 事件到达时弹出 Windows Toast
- 实时事件列表: 红色高亮需关注事件，点击查看详情
- 图片预览: 自动加载缩略图
- 标记已处理: 一键回传状态
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

import websockets.sync.client as ws_sync

from receiver_app.app.config import WS_URL, ATTENTION_STATUS_URL
from receiver_app.app.image_loader import load_thumbnail
from shared.api_client import post as http_post


class EventStore:
    """线程安全的事件存储。"""

    def __init__(self) -> None:
        self._events: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def add(self, event: dict[str, Any]) -> None:
        eid = event.get("event_id", "")
        with self._lock:
            if eid not in self._events:
                self._events[eid] = event
                self._order.append(eid)
            else:
                self._events[eid] = event

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._events.get(event_id)

    def get_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._events[eid] for eid in self._order]

    def mark_handled(self, event_id: str) -> None:
        with self._lock:
            if event_id in self._events:
                self._events[event_id]["_handled"] = True

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._order)


# ═══════════════════════════════════════════
# Windows Toast 通知
# ═══════════════════════════════════════════

def _show_toast(title: str, message: str) -> None:
    """通过 PowerShell 弹出 Windows 原生通知。"""
    try:
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $texts = $template.GetElementsByTagName("text")
        $texts.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
        $texts.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        $appId = "闲鱼消息转发"
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
        '''
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass


def show_attention_notification(event: dict[str, Any]) -> None:
    """弹出需关注事件的通知。"""
    summary = event.get("summary", "需要人工处理")
    error_info = ""
    if event.get("error_code"):
        error_info = f"错误: {event['error_code']}"
    if event.get("ocr_error"):
        error_info = f"OCR错误: {event['ocr_error']}"

    _show_toast("闲鱼消息 - 需要处理", f"{summary}\n{error_info}")


# ═══════════════════════════════════════════
# 系统托盘
# ═══════════════════════════════════════════

def _create_tray_icon(root: tk.Tk, on_show: callable) -> object:
    """创建系统托盘图标。"""
    from PIL import Image, ImageDraw
    import pystray

    # 生成托盘图标 (橙色圆形 + 白色铃铛)
    icon_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon_img)
    draw.ellipse([4, 4, 60, 60], fill=(255, 102, 0), outline=(255, 255, 255), width=2)
    # 简化铃铛符号
    draw.rectangle([26, 14, 38, 38], fill=(255, 255, 255))
    draw.ellipse([24, 36, 40, 50], fill=(255, 255, 255))

    def on_clicked(icon, item):
        if item.text == "显示窗口":
            root.deiconify()
            root.lift()
            root.focus_force()
        elif item.text == "退出":
            icon.stop()
            root.destroy()
            os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("显示窗口", on_clicked, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_clicked),
    )

    icon = pystray.Icon("xianyu_relay", icon_img, "闲鱼消息转发", menu)
    return icon


# ═══════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════

class ReceiverGUI:
    def __init__(self) -> None:
        self.store = EventStore()
        self._running = False
        self._msg_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._tray_icon = None
        self._first_minimize = True

        self.root = tk.Tk()
        self.root.title("闲鱼消息转发 - 接收端")
        self.root.geometry("900x600")
        self.root.minsize(700, 400)

        self._build_ui()
        self._start_ws()

        # 创建托盘
        self._tray_icon = _create_tray_icon(self.root, self._show_window)

        # 窗口关闭 → 最小化到托盘
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 开始轮询消息队列
        self._poll_queue()

        # 托盘图标在独立线程运行
        self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        self._tray_thread.start()

    # ═══════════════════════════════════════
    # UI 构建
    # ═══════════════════════════════════════

    def _build_ui(self) -> None:
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 左侧：事件列表
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        header_frame = ttk.Frame(left)
        header_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(header_frame, text="事件列表", font=("", 11, "bold")).pack(side=tk.LEFT)
        ttk.Button(header_frame, text="清空", width=5, command=self._clear_list).pack(side=tk.RIGHT)

        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self._listbox = tk.Listbox(list_frame, font=("Consolas", 10), activestyle="none")
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # 右侧：事件详情
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        ttk.Label(right, text="事件详情", font=("", 11, "bold")).pack(anchor=tk.W, padx=8, pady=(8, 4))

        detail_frame = ttk.Frame(right)
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=8)

        self._detail_text = tk.Text(detail_frame, wrap=tk.WORD, font=("Microsoft YaHei", 10),
                                     state=tk.DISABLED, height=12)
        self._detail_text.pack(fill=tk.BOTH, expand=True)

        self._img_label = ttk.Label(right, text="点击事件查看图片预览", relief=tk.SUNKEN, anchor=tk.CENTER)
        self._img_label.pack(fill=tk.BOTH, expand=False, padx=8, pady=4)

        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill=tk.X, padx=8, pady=(4, 8))

        self._handle_btn = ttk.Button(btn_frame, text="标记已处理", command=self._on_handle, state=tk.DISABLED)
        self._handle_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._alert_label = ttk.Label(btn_frame, text="", foreground="red", font=("", 9, "bold"))
        self._alert_label.pack(side=tk.LEFT)

        self._connection_label = ttk.Label(btn_frame, text="", foreground="gray")
        self._connection_label.pack(side=tk.RIGHT)

        # 底部状态栏
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self._status_var = tk.StringVar(value="正在连接...")
        ttk.Label(status_frame, textvariable=self._status_var, padding=(8, 3)).pack(side=tk.LEFT)

        self._count_var = tk.StringVar(value="事件: 0")
        ttk.Label(status_frame, textvariable=self._count_var, padding=(8, 3)).pack(side=tk.RIGHT)

    # ═══════════════════════════════════════
    # WebSocket
    # ═══════════════════════════════════════

    def _start_ws(self) -> None:
        self._running = True
        threading.Thread(target=self._ws_loop, daemon=True).start()

    def _ws_loop(self) -> None:
        delay = 1.0
        while self._running:
            try:
                ws = ws_sync.connect(WS_URL, close_timeout=2)
                delay = 1.0
                self._msg_queue.put({"type": "status", "text": f"已连接 {WS_URL}"})
                ws.recv()  # connected

                while self._running:
                    try:
                        raw = ws.recv(timeout=1.0)
                        msg = json.loads(raw)
                        if msg.get("type") == "event":
                            evt = msg["event"]
                            self.store.add(evt)
                            self._msg_queue.put({"type": "event", "event": evt})
                        elif msg.get("type") == "ping":
                            ws.send(json.dumps({"type": "pong"}))
                    except TimeoutError:
                        continue
            except Exception as e:
                self._msg_queue.put({"type": "status", "text": f"断开: {delay:.0f}s 后重连"})
                time.sleep(delay)
                delay = min(delay * 2, 30)

    # ═══════════════════════════════════════
    # 消息处理
    # ═══════════════════════════════════════

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                mtype = msg.get("type", "")
                if mtype == "status":
                    self._status_var.set(msg["text"])
                    self._connection_label.configure(text=msg["text"][:20])
                elif mtype == "event":
                    evt = msg.get("event", {})
                    if evt.get("need_receiver_attention"):
                        show_attention_notification(evt)
                        # 闪烁托盘提示（Windows）
                        try:
                            self.root.bell()
                        except Exception:
                            pass
                    self._refresh_list()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    # ═══════════════════════════════════════
    # 事件列表
    # ═══════════════════════════════════════

    def _refresh_list(self) -> None:
        self._listbox.delete(0, tk.END)
        for evt in self.store.get_all():
            eid = evt.get("event_id", "")
            need_attn = evt.get("need_receiver_attention", False)
            handled = evt.get("_handled", False)
            summary = evt.get("summary", "")[:40]

            prefix = "[!]" if need_attn and not handled else "   "
            label = f"{prefix} {eid}  {summary}"

            idx = self._listbox.size()
            self._listbox.insert(tk.END, label)
            bg = "#fff0f0" if (need_attn and not handled) else "white"
            fg = "#cc0000" if (need_attn and not handled) else "#333333"
            self._listbox.itemconfig(idx, bg=bg, fg=fg)

        self._count_var.set(f"事件: {self.store.count}")

    def _clear_list(self) -> None:
        self._listbox.delete(0, tk.END)

    def _on_select(self, event: tk.Event) -> None:
        selection = self._listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        events = self.store.get_all()
        if idx < len(events):
            self._show_detail(events[idx])

    def _show_detail(self, evt: dict[str, Any]) -> None:
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)

        lines = []
        for key, label in [
            ("event_id", "事件ID"), ("event_type", "事件类型"),
            ("content_type", "内容类型"), ("source", "来源"),
            ("timestamp", "时间"), ("thread_key", "会话"),
            ("message_key", "消息"), ("summary", "摘要"),
            ("ocr_status", "OCR状态"), ("upload_status", "上传状态"),
        ]:
            val = evt.get(key, "")
            if val:
                lines.append(f"{label}: {val}")

        if evt.get("ocr_error"):
            lines.append(f"\n>>> OCR错误: {evt['ocr_error']}")
        if evt.get("error_code"):
            lines.append(f">>> 错误码: {evt['error_code']}")
        if evt.get("error_message"):
            lines.append(f">>> 错误信息: {evt['error_message']}")
        if evt.get("content_text"):
            lines.append(f"\n文本内容:\n{evt['content_text'][:500]}")
        if evt.get("image_ocr_text"):
            lines.append(f"\nOCR文本:\n{evt['image_ocr_text'][:500]}")

        self._detail_text.insert("1.0", "\n".join(lines))
        self._detail_text.configure(state=tk.DISABLED)
        self._show_image(evt)

        need_attn = evt.get("need_receiver_attention", False)
        handled = evt.get("_handled", False)
        if need_attn and not handled:
            self._handle_btn.configure(state=tk.NORMAL)
            self._alert_label.configure(text="需要人工处理！", foreground="red")
        elif handled:
            self._handle_btn.configure(state=tk.DISABLED)
            self._alert_label.configure(text="已处理", foreground="green")
        else:
            self._handle_btn.configure(state=tk.DISABLED)
            self._alert_label.configure(text="")

        self._current_event = evt

    def _show_image(self, evt: dict[str, Any]) -> None:
        image_refs = evt.get("image_refs", [])
        if not image_refs:
            self._img_label.configure(image="", text="无图片")
            return
        result = load_thumbnail(image_refs[0], max_size=280)
        if result.get("ok"):
            try:
                from PIL import Image as PILImage, ImageTk
                path = result.get("thumb_path", result["path"])
                img = PILImage.open(path)
                self._photo = ImageTk.PhotoImage(img)
                self._img_label.configure(image=self._photo, text="")
            except Exception:
                self._img_label.configure(image="", text=f"{result.get('width',0)}x{result.get('height',0)}")
        else:
            self._img_label.configure(image="", text=f"加载失败: {result.get('error', '')}")

    def _on_handle(self) -> None:
        evt = getattr(self, "_current_event", None)
        if not evt:
            return
        eid = evt.get("event_id", "")
        try:
            http_post(ATTENTION_STATUS_URL, {
                "event_id": eid, "attention_status": "handled",
                "handled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception:
            pass
        self.store.mark_handled(eid)
        self._handle_btn.configure(state=tk.DISABLED)
        self._alert_label.configure(text="已处理", foreground="green")
        self._refresh_list()

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_close(self) -> None:
        """最小化到托盘而不是退出。"""
        if self._first_minimize:
            self._first_minimize = False
        self.root.withdraw()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = ReceiverGUI()
    app.run()


if __name__ == "__main__":
    main()
