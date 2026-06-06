# 闲鱼消息中转服务器 - PowerShell 启动脚本
# 用法: .\start_server.ps1

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

Write-Host "============================================"
Write-Host "  闲鱼消息转发 - 中转服务器"
Write-Host "  HTTP:       0.0.0.0:9006"
Write-Host "  WS:         0.0.0.0:9007"
Write-Host "  规则管理后台: http://localhost:9006/admin"
Write-Host "============================================"

# 安装依赖
Write-Host "[1/3] 安装依赖..."
pip install websockets Pillow pyyaml httpx -q

# 初始化目录
Write-Host "[2/3] 初始化目录..."
@(
    "data",
    "data\uploaded_images",
    "data\image_cache"
) | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

# 启动
Write-Host "[3/3] 启动中转服务器..."
Write-Host ""
python -c "import sys; sys.path.insert(0, '.'); from relay_server.demo_server import main; main()"

Write-Host "服务器已停止."
