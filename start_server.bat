@echo off
chcp 65001 >nul
title 闲鱼消息中转服务器

:: 切到脚本所在目录（解决跨盘符问题）
cd /d "%~dp0"

echo ============================================
echo   闲鱼消息转发 - 中转服务器
echo   HTTP:       0.0.0.0:9006
echo   WS:         0.0.0.0:9007
echo   规则管理后台: http://localhost:9006/admin
echo ============================================

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/3] 安装依赖...
pip install websockets Pillow pyyaml -q

:: 初始化目录
echo [2/3] 初始化目录...
if not exist "data" mkdir "data"
if not exist "data\uploaded_images" mkdir "data\uploaded_images"
if not exist "data\image_cache" mkdir "data\image_cache"

:: 启动
echo [3/3] 启动中转服务器...
echo.
python -c "import sys; sys.path.insert(0, '.'); from relay_server.demo_server import main; main()"

pause
