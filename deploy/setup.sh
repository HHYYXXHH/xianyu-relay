#!/bin/bash
# ============================================================
# 闲鱼消息转发 - 服务器一键部署脚本
# 用法: 在项目根目录下执行 bash deploy/setup.sh
# ============================================================
set -e

APP_DIR="/opt/relay-server"
SERVICE_NAME="relay-server"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 必须以 root 运行
if [ "$(id -u)" != "0" ]; then
    echo -e "${RED}请用 root 执行: sudo bash deploy/setup.sh${NC}"
    exit 1
fi

# 找到项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -f "$PROJECT_DIR/relay_server/demo_server.py" ]; then
    echo -e "${RED}错误: 未找到 relay_server/demo_server.py${NC}"
    echo "请在项目根目录下执行: bash deploy/setup.sh"
    exit 1
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  闲鱼消息转发 - 服务器部署${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# ---------- 1. Python 环境 ----------
echo "[1/5] 检查 Python 环境..."
PYTHON_BIN=$(which python3 || which python)
if ! $PYTHON_BIN --version &>/dev/null; then
    echo "  安装 Python3..."
    apt update -qq && apt install -y -qq python3 python3-pip
    PYTHON_BIN=$(which python3)
fi
echo "  $($PYTHON_BIN --version)"

# ---------- 2. 复制文件 ----------
echo "[2/5] 复制项目文件到 $APP_DIR..."
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"

# 只复制需要的文件
cp -r "$PROJECT_DIR/relay_server" "$APP_DIR/relay_server"
cp -r "$PROJECT_DIR/shared" "$APP_DIR/shared"
cp -r "$PROJECT_DIR/deploy" "$APP_DIR/deploy"

# 清理 __pycache__
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true

# ---------- 3. 安装依赖 ----------
echo "[3/5] 安装 Python 依赖..."
$PYTHON_BIN -m pip install --upgrade pip -q 2>/dev/null
$PYTHON_BIN -m pip install -r "$APP_DIR/deploy/requirements-server.txt" -q
echo "  完成"

# ---------- 4. systemd ----------
echo "[4/5] 注册 systemd 服务..."
cp "$APP_DIR/deploy/relay-server.service" /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload
systemctl enable $SERVICE_NAME
echo "  已注册为系统服务"

# ---------- 5. 启动 ----------
echo "[5/5] 启动服务..."
systemctl restart $SERVICE_NAME
sleep 2

if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}  服务运行中 ✓${NC}"
else
    echo -e "${RED}  服务启动失败，查看日志: journalctl -u $SERVICE_NAME -n 20${NC}"
    exit 1
fi

# ---------- 完成 ----------
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  访问地址:"
echo "    健康检查:  http://${SERVER_IP}:9006/health"
echo "    规则管理:  http://${SERVER_IP}:9006/admin"
echo "    WebSocket: ws://${SERVER_IP}:9007"
echo ""
echo "  常用命令:"
echo "    sudo systemctl status $SERVICE_NAME   状态"
echo "    sudo systemctl restart $SERVICE_NAME  重启"
echo "    sudo systemctl stop $SERVICE_NAME     停止"
echo "    sudo journalctl -u $SERVICE_NAME -f   实时日志"
echo ""
echo "  编辑规则:"
echo "    vim $APP_DIR/relay_server/rules/rules.yaml"
echo "    或访问 http://${SERVER_IP}:9006/admin"
echo ""
echo "  数据目录: $APP_DIR/data/"
echo ""
