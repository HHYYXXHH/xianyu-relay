"""接收端启动入口。

模式:
  (默认)  WebSocket 终端模式
  --gui    Tkinter 图形界面
  --poll   HTTP 轮询回退模式
"""

from __future__ import annotations

import sys


def main() -> None:
    if "--gui" in sys.argv:
        from receiver_app.app.gui import main as gui_main
        gui_main()
    elif "--poll" in sys.argv:
        from receiver_app.app.event_receiver import connect_push
        connect_push()
    else:
        from receiver_app.app.event_receiver import connect_ws
        connect_ws()


if __name__ == "__main__":
    main()
