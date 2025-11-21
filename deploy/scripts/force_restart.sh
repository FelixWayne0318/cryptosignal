#!/bin/bash
# ============================================== #
# CryptoSignal 强制重启脚本 v7.3.47
# 用途：彻底停止服务 + 清理缓存 + 重新启动
# ============================================== #

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo -e "${YELLOW}🔄 CryptoSignal 强制重启 v7.3.47${NC}"
echo "=============================================="
echo ""

# 进入项目目录
cd ~/cryptosignal || {
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    exit 1
}

# Step 1: 强制停止所有相关进程
echo -e "${YELLOW}Step 1: 强制停止所有运行中的进程...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 查找进程
PIDS=$(ps aux | grep 'realtime_signal_scanner' | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo -e "${GREEN}✅ 没有运行中的进程${NC}"
else
    echo "发现运行中的进程:"
    ps aux | grep 'realtime_signal_scanner' | grep -v grep
    echo ""

    echo "强制终止进程..."
    pkill -9 -f 'realtime_signal_scanner.py'
    sleep 2

    # 再次检查
    PIDS=$(ps aux | grep 'realtime_signal_scanner' | grep -v grep | awk '{print $2}')
    if [ -z "$PIDS" ]; then
        echo -e "${GREEN}✅ 所有进程已停止${NC}"
    else
        echo -e "${RED}❌ 仍有进程运行，请手动停止${NC}"
        ps aux | grep 'realtime_signal_scanner' | grep -v grep
        exit 1
    fi
fi

echo ""

# Step 2: 清理 Python 缓存
echo -e "${YELLOW}Step 2: 清理 Python 字节码缓存...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 统计缓存文件
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l)
CACHE_COUNT=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)

echo "发现 .pyc 文件: $PYC_COUNT 个"
echo "发现 __pycache__ 目录: $CACHE_COUNT 个"

if [ "$PYC_COUNT" -gt 0 ] || [ "$CACHE_COUNT" -gt 0 ]; then
    echo ""
    echo "清理中..."

    # 删除 .pyc 文件
    find . -name "*.pyc" -delete 2>/dev/null

    # 删除 __pycache__ 目录
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

    echo -e "${GREEN}✅ 缓存已清理${NC}"
else
    echo -e "${GREEN}✅ 没有缓存需要清理${NC}"
fi

echo ""

# Step 3: 验证代码修复
echo -e "${YELLOW}Step 3: 验证代码修复...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查关键修复是否存在
if grep -q "factor_config\.config\.get('I因子参数'" ats_core/pipeline/analyze_symbol.py; then
    echo -e "${GREEN}✅ FactorConfig 修复已应用 (factor_config.config.get)${NC}"
else
    echo -e "${RED}❌ FactorConfig 修复未找到！${NC}"
    echo "   请确认代码已更新到最新版本"
    exit 1
fi

# 检查输出配置文件
if [ -f "config/scan_output.json" ]; then
    echo -e "${GREEN}✅ 输出配置文件存在${NC}"

    # 检查配置
    if grep -q '"mode": "full"' config/scan_output.json; then
        echo -e "${GREEN}✅ 输出模式: full (完整)${NC}"
    else
        echo -e "${YELLOW}⚠️  输出模式不是 full${NC}"
    fi
else
    echo -e "${RED}❌ 输出配置文件不存在！${NC}"
    exit 1
fi

echo ""

# Step 4: 运行诊断测试（可选）
echo -e "${YELLOW}Step 4: 运行诊断测试 (可选)...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "diagnose/test_factorconfig_fix.py" ]; then
    echo "运行诊断脚本..."
    python3 diagnose/test_factorconfig_fix.py

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 诊断测试通过${NC}"
    else
        echo -e "${YELLOW}⚠️  诊断测试有警告，但可以继续${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  诊断脚本不存在，跳过${NC}"
fi

echo ""

# Step 5: 重新启动服务
echo -e "${YELLOW}Step 5: 重新启动服务...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "./setup.sh" ]; then
    echo "执行 setup.sh..."
    ./setup.sh
else
    echo -e "${RED}❌ setup.sh 不存在！${NC}"
    exit 1
fi

# 注意：setup.sh 会接管控制台显示日志
# 用户按 Ctrl+C 只是退出查看，不影响后台程序
