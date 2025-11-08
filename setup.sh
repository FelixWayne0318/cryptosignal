#!/bin/bash
# ==========================================
# CryptoSignal v7.2 一键部署脚本
# 用途：拉取代码、检测环境、安装依赖、启动系统
# 特点：自动更新代码、清理缓存、验证结构
# ==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo "🚀 CryptoSignal v7.2 一键部署"
echo "=============================================="
echo ""

# 检测项目目录
cd ~/cryptosignal 2>/dev/null || {
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    echo "请先克隆仓库："
    echo "  git clone https://github.com/FelixWayne0318/cryptosignal.git"
    exit 1
}

# 自动检测当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}✅ 当前分支: $CURRENT_BRANCH${NC}"
echo ""

# ==========================================
# 第0步：拉取最新代码
# ==========================================
echo "📥 拉取最新代码..."
echo "=============================================="

# 0.1 保存本地修改（如果有）
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  检测到本地修改，正在保存...${NC}"
    BACKUP_NAME="自动备份_$(date +%Y%m%d_%H%M%S)"
    git stash save "$BACKUP_NAME" 2>/dev/null || true
    echo -e "${GREEN}✅ 本地修改已备份: $BACKUP_NAME${NC}"
    echo "   恢复方法: git stash pop"
fi

# 0.2 拉取远程代码
echo "正在从远程拉取最新代码..."
if git fetch origin && git pull origin "$CURRENT_BRANCH" 2>/dev/null; then
    echo -e "${GREEN}✅ 代码已更新到最新版本${NC}"
else
    echo -e "${YELLOW}⚠️  代码拉取失败（可能网络问题），继续使用本地版本...${NC}"
fi

# 0.3 清理Python缓存（重要！确保新代码生效）
echo ""
echo "🧹 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Python缓存已清理${NC}"

# 0.4 验证重组后的目录结构（v7.2特性）
echo ""
echo "🔍 验证v7.2目录结构..."
TEST_FILES=$(ls tests/*.py 2>/dev/null | wc -l)
DIAGNOSE_FILES=$(ls diagnose/*.py 2>/dev/null | wc -l)
DOC_FILES=$(ls docs/*.md 2>/dev/null | wc -l)

if [ "$TEST_FILES" -gt 0 ] && [ "$DIAGNOSE_FILES" -gt 0 ]; then
    echo -e "${GREEN}✅ v7.2目录结构正确${NC}"
    echo "   - tests/: $TEST_FILES 个测试文件"
    echo "   - diagnose/: $DIAGNOSE_FILES 个诊断文件"
    echo "   - docs/: $DOC_FILES 个文档文件"
else
    echo -e "${YELLOW}⚠️  目录结构可能不是v7.2版本${NC}"
fi

echo ""
echo "=============================================="
echo ""

# 检测Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装，请先安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3: $(python3 --version 2>&1 | awk '{print $2}')${NC}"

# 检测pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip3 未安装，尝试安装...${NC}"
    sudo apt-get update && sudo apt-get install -y python3-pip || {
        echo -e "${RED}❌ pip3 安装失败${NC}"
        exit 1
    }
fi
echo -e "${GREEN}✅ pip3 已安装${NC}"

# 安装依赖（静默，快速）
echo ""
echo "📦 检查并安装依赖..."
pip3 install -r requirements.txt --quiet 2>&1 | grep -v "Requirement already satisfied" || true
echo -e "${GREEN}✅ 依赖已就绪${NC}"

# 检查配置文件
echo ""
echo "🔧 检查配置文件..."

# 检查Binance配置
if [ ! -f "config/binance_credentials.json" ]; then
    echo -e "${YELLOW}⚠️  Binance配置不存在${NC}"
    echo "请创建: config/binance_credentials.json"
    echo "参考: config/binance_credentials.json.example"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅ Binance配置存在${NC}"

# 检查Telegram配置
if [ ! -f "config/telegram.json" ]; then
    echo -e "${YELLOW}⚠️  Telegram配置不存在，创建默认配置（禁用）${NC}"
    cat > config/telegram.json <<EOF
{
  "enabled": false,
  "bot_token": "",
  "chat_id": "",
  "_comment": "Telegram通知已禁用，如需启用请参考 telegram.json.example"
}
EOF
fi
echo -e "${GREEN}✅ Telegram配置存在${NC}"

# 配置crontab（如果未配置）
echo ""
echo "⏰ 配置定时任务..."
if crontab -l 2>/dev/null | grep -q "auto_restart.sh"; then
    echo -e "${GREEN}✅ 定时任务已配置${NC}"
else
    (crontab -l 2>/dev/null; echo "0 */2 * * * ~/cryptosignal/auto_restart.sh"; echo "0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete") | crontab -
    echo -e "${GREEN}✅ 定时任务已添加（每2小时重启）${NC}"
fi

# 添加执行权限
chmod +x auto_restart.sh deploy_and_run.sh setup.sh scripts/init_databases.py start_live.sh 2>/dev/null || true

# 初始化数据库
echo ""
echo "🗄️  初始化数据库..."
echo "=============================================="
python3 scripts/init_databases.py || {
    echo -e "${RED}❌ 数据库初始化失败${NC}"
    echo "这不会影响系统运行，数据库会在首次使用时自动创建"
}

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 环境准备完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🚀 正在启动 v7.2 扫描器（后台模式 + 实时日志）..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 停止旧进程
pkill -f realtime_signal_scanner_v72.py 2>/dev/null || true
sleep 1

# 创建日志文件名
LOG_FILE=~/cryptosignal_$(date +%Y%m%d_%H%M%S).log

# 后台启动扫描器
echo "📝 后台启动扫描器..."
nohup python3 scripts/realtime_signal_scanner_v72.py --interval 300 > "$LOG_FILE" 2>&1 &
PID=$!

sleep 2

# 验证启动
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 扫描器已启动（PID: $PID）${NC}"
    echo "   日志文件: $LOG_FILE"
    echo "   ✅ SSH断开后继续运行"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 管理命令:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  查看状态: ~/cryptosignal/check_v72_status.sh"
    echo "  重新启动: ~/cryptosignal/auto_restart.sh"
    echo "  停止程序: pkill -f realtime_signal_scanner_v72.py"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚙️  v7.2 新特性:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  环境变量控制自动提交："
    echo "    - 默认启用自动提交（服务器运行）"
    echo "    - 手动测试禁用: export AUTO_COMMIT_REPORTS=false"
    echo ""
    echo "  目录结构已重组："
    echo "    - tests/     测试文件"
    echo "    - diagnose/  诊断文件"
    echo "    - docs/      文档文件"
    echo ""
    echo "  详细文档："
    echo "    - REORGANIZATION_SUMMARY.md  重组总结"
    echo "    - standards/00_INDEX.md      规范索引"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}🟢 正在显示实时日志（按 Ctrl+C 退出查看，程序继续运行）${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # 等待日志文件生成
    sleep 2

    # 显示实时日志（用户按Ctrl+C只是退出查看，不影响后台程序）
    tail -f "$LOG_FILE"
else
    echo -e "${RED}❌ 启动失败${NC}"
    echo "请查看日志: cat $LOG_FILE"
    exit 1
fi
