"""PyInstaller 一键打包脚本。

生成:
  dist/server.exe   - 中转服务器 (HTTP + WebSocket)
  dist/receiver.exe - 接收端 GUI (托盘 + 通知)
  dist/source.exe   - 发射端 (ADB 消息监听)

用法:
  python build.py          # 打包全部
  python build.py server   # 仅打包服务器
  python build.py receiver # 仅打包接收端
  python build.py source   # 仅打包发射端
"""

import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DATA_TESSDATA = os.path.join(PROJECT_ROOT, "data", "tessdata")

os.chdir(PROJECT_ROOT)

# 公共 PyInstaller 参数
COMMON_FLAGS = [
    "--noconfirm",
    "--clean",
    f"--distpath={DIST_DIR}",
    f"--workpath={BUILD_DIR}",
    "--noconsole",            # GUI 模式默认无控制台
]

# 共享的隐藏导入
HIDDEN_IMPORTS = [
    "websockets", "websockets.sync", "websockets.sync.client",
    "websockets.asyncio", "websockets.asyncio.server",
    "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL.ImageTk", "PIL.ImageEnhance",
    "pystray", "pystray._win32",
    "shared.event_schema", "shared.error_codes", "shared.constants", "shared.api_client",
    "relay_server", "relay_server.config", "relay_server.api", "relay_server.models",
    "relay_server.services", "relay_server.storage",
    "source_app", "source_app.app",
    "receiver_app", "receiver_app.app",
]

ADD_DATA = []
if os.path.isdir(DATA_TESSDATA):
    ADD_DATA = [f"{DATA_TESSDATA}{os.sep}*{os.sep}tessdata"]


def build_server() -> bool:
    """打包中转服务器 (控制台模式)。"""
    print("=" * 50)
    print("  打包: 中转服务器 (server.exe)")
    print("=" * 50)

    flags = [
        "--name=server",
        "--console",
        "--add-data=shared;shared",
        "--add-data=relay_server;relay_server",
    ]
    for imp in HIDDEN_IMPORTS:
        flags.append(f"--hidden-import={imp}")
    for data in ADD_DATA:
        flags.append(f"--add-data={data}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        *COMMON_FLAGS,
        *flags,
        "relay_server/demo_server.py",
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0


def build_receiver() -> bool:
    """打包接收端 GUI。"""
    print("=" * 50)
    print("  打包: 接收端 GUI (receiver.exe)")
    print("=" * 50)

    flags = [
        "--name=receiver",
        "--add-data=shared;shared",
        "--add-data=receiver_app;receiver_app",
        "--add-data=relay_server;relay_server",
    ]
    for imp in HIDDEN_IMPORTS:
        flags.append(f"--hidden-import={imp}")
    for data in ADD_DATA:
        flags.append(f"--add-data={data}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        *COMMON_FLAGS,
        *flags,
        "receiver_app/app/main.py",
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0


def build_source() -> bool:
    """打包发射端 (控制台模式，排除重型 ML 依赖)。"""
    print("=" * 50)
    print("  打包: 发射端 (source.exe)")
    print("=" * 50)

    flags = [
        "--name=source",
        "--console",
        "--add-data=shared;shared",
        "--add-data=source_app;source_app",
        "--add-data=relay_server;relay_server",
        # 排除重型依赖
        "--exclude-module=paddle",
        "--exclude-module=paddleocr",
        "--exclude-module=paddlex",
        "--exclude-module=paddlepaddle",
        "--exclude-module=numpy",
        "--exclude-module=cv2",
        "--exclude-module=opencv",
        "--exclude-module=PIL",
        "--exclude-module=PIL.Image",
        "--exclude-module=PIL.ImageDraw",
        "--exclude-module=PIL.ImageFont",
        "--exclude-module=PIL.ImageEnhance",
        "--exclude-module=pytesseract",
        "--exclude-module=modelscope",
        "--exclude-module=huggingface_hub",
    ]
    for imp in HIDDEN_IMPORTS:
        flags.append(f"--hidden-import={imp}")
    for data in ADD_DATA:
        flags.append(f"--add-data={data}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        *COMMON_FLAGS,
        *flags,
        "source_app/app/main.py",
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0


def main() -> None:
    os.makedirs(DIST_DIR, exist_ok=True)

    targets = sys.argv[1:] if len(sys.argv) > 1 else ["server", "receiver", "source"]
    results = {}

    if "server" in targets:
        results["server"] = build_server()
    if "receiver" in targets:
        results["receiver"] = build_receiver()
    if "source" in targets:
        results["source"] = build_source()

    print()
    print("=" * 50)
    print("  打包结果")
    print("=" * 50)
    all_ok = True
    for name, ok in results.items():
        status = "OK" if ok else "FAIL"
        if not ok: all_ok = False
        exe = f"dist/{name}.exe"
        size = ""
        if os.path.exists(exe):
            size_mb = os.path.getsize(exe) / 1024 / 1024
            size = f" ({size_mb:.1f} MB)"
        print(f"  [{status}] {exe}{size}")

    if all_ok:
        print(f"\n  全部打包成功! 文件在 {os.path.abspath(DIST_DIR)}/")
    else:
        print(f"\n  存在失败项，请检查上方错误信息")


if __name__ == "__main__":
    main()
