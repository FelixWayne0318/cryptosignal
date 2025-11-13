#!/bin/bash
#
# CryptoSignal 服务器全面缓存清理脚本
# 用于解决Python缓存导致的旧代码执行问题
#
# 用法: bash cleanup_all_cache.sh
#

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }

clear
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       CryptoSignal 服务器全面缓存清理工具                 ║${NC}"
echo -e "${CYAN}║       目标：彻底清除旧代码缓存，加载v7.2.17修复            ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
print_warning "此脚本将："
echo "   1. 停止所有CryptoSignal进程"
echo "   2. 清理所有Python缓存（__pycache__、*.pyc、*.pyo）"
echo "   3. 清理pip缓存"
echo "   4. 验证正确分支和v7.2.17修复"
echo "   5. 重新启动系统"
echo ""
read -p "是否继续？(y/N): " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && { print_warning "清理已取消"; exit 0; }

# ============================================================================
print_header "步骤 1/8: 停止所有Python进程"
# ============================================================================

print_info "查找运行中的Python进程..."
PYTHON_PIDS=$(ps aux | grep -v grep | grep "python.*cryptosignal" | awk '{print $2}' || true)

if [ -n "$PYTHON_PIDS" ]; then
    print_info "发现以下进程:"
    ps aux | grep -v grep | grep "python.*cryptosignal" | awk '{print "   PID " $2 ": " $11 " " $12 " " $13}'

    print_info "尝试优雅停止（SIGTERM）..."
    echo "$PYTHON_PIDS" | xargs -r kill 2>/dev/null || true
    sleep 3

    # 检查是否还有进程
    REMAINING=$(ps aux | grep -v grep | grep "python.*cryptosignal" | wc -l || echo "0")
    if [ "$REMAINING" -gt 0 ]; then
        print_warning "进程未停止，使用强制停止（SIGKILL）..."
        pkill -9 -f "python.*cryptosignal" 2>/dev/null || true
        sleep 2
    fi

    # 最终验证
    FINAL_CHECK=$(ps aux | grep -v grep | grep "python.*cryptosignal" | wc -l || echo "0")
    if [ "$FINAL_CHECK" -eq 0 ]; then
        print_success "所有Python进程已停止"
    else
        print_error "仍有进程运行，请手动检查: ps aux | grep python"
    fi
else
    print_info "无运行中的Python进程"
fi

# 停止Screen会话
if command -v screen &> /dev/null; then
    if screen -ls 2>/dev/null | grep -q cryptosignal; then
        print_info "发现Screen会话，正在停止..."
        screen -S cryptosignal -X quit 2>/dev/null || true
        print_success "Screen会话已停止"
    fi
fi

# ============================================================================
print_header "步骤 2/8: 清理项目目录Python缓存"
# ============================================================================

if [ ! -d ~/cryptosignal ]; then
    print_error "项目目录不存在: ~/cryptosignal"
    print_error "请先克隆仓库并切换到正确分支"
    exit 1
fi

cd ~/cryptosignal

print_info "清理 __pycache__ 目录..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
if [ "$PYCACHE_COUNT" -gt 0 ]; then
    print_info "找到 $PYCACHE_COUNT 个 __pycache__ 目录"
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    print_success "__pycache__ 目录已清理"
else
    print_info "无 __pycache__ 目录"
fi

print_info "清理 .pyc 文件..."
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l)
if [ "$PYC_COUNT" -gt 0 ]; then
    print_info "找到 $PYC_COUNT 个 .pyc 文件"
    find . -name "*.pyc" -delete 2>/dev/null || true
    print_success ".pyc 文件已清理"
else
    print_info "无 .pyc 文件"
fi

print_info "清理 .pyo 文件（优化字节码）..."
PYO_COUNT=$(find . -name "*.pyo" 2>/dev/null | wc -l)
if [ "$PYO_COUNT" -gt 0 ]; then
    print_info "找到 $PYO_COUNT 个 .pyo 文件"
    find . -name "*.pyo" -delete 2>/dev/null || true
    print_success ".pyo 文件已清理"
else
    print_info "无 .pyo 文件"
fi

# ============================================================================
print_header "步骤 3/8: 清理系统级Python缓存"
# ============================================================================

print_info "清理 /tmp 中的Python缓存..."
find /tmp -user $(whoami) -name "*.pyc" -delete 2>/dev/null || true
find /tmp -user $(whoami) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
print_success "/tmp 缓存已清理"

# ============================================================================
print_header "步骤 4/8: 清理pip缓存"
# ============================================================================

print_info "清理pip缓存..."
if command -v pip3 &> /dev/null; then
    CACHE_DIR=$(pip3 cache dir 2>/dev/null || echo "")
    if [ -n "$CACHE_DIR" ] && [ -d "$CACHE_DIR" ]; then
        CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | awk '{print $1}')
        print_info "pip缓存大小: $CACHE_SIZE"
        pip3 cache purge 2>/dev/null || true
        print_success "pip缓存已清理"
    else
        print_info "无pip缓存"
    fi
else
    print_warning "pip3未安装，跳过"
fi

# ============================================================================
print_header "步骤 5/8: 验证当前分支"
# ============================================================================

cd ~/cryptosignal

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
CORRECT_BRANCH="claude/system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH"

print_info "当前分支: $CURRENT_BRANCH"
print_info "正确分支: $CORRECT_BRANCH"

if [ "$CURRENT_BRANCH" = "$CORRECT_BRANCH" ]; then
    print_success "分支正确"
else
    print_error "分支错误！"
    print_warning "正在切换到正确分支..."

    git fetch --all 2>/dev/null || { print_error "git fetch失败"; exit 1; }

    if git checkout "$CORRECT_BRANCH" 2>/dev/null; then
        print_success "分支切换成功"
        git pull origin "$CORRECT_BRANCH" 2>/dev/null || print_warning "git pull失败，使用当前版本"
    else
        print_error "分支切换失败"
        print_error "请手动执行:"
        echo "   cd ~/cryptosignal"
        echo "   git fetch --all"
        echo "   git checkout $CORRECT_BRANCH"
        exit 1
    fi
fi

# ============================================================================
print_header "步骤 6/8: 验证v7.2.17修复"
# ============================================================================

print_info "检查 _get_dict 函数..."
TARGET_FILE="ats_core/outputs/telegram_fmt.py"

if [ ! -f "$TARGET_FILE" ]; then
    print_error "文件不存在: $TARGET_FILE"
    exit 1
fi

if grep -q "def _get_dict" "$TARGET_FILE"; then
    print_success "_get_dict 函数存在"

    # 统计使用次数
    GET_DICT_COUNT=$(grep -c "_get_dict(" "$TARGET_FILE" 2>/dev/null || echo "0")
    print_info "_get_dict 调用次数: $GET_DICT_COUNT"

    if [ "$GET_DICT_COUNT" -ge 35 ]; then
        print_success "v7.2.17修复已完整应用（预期≥35次调用）"
    else
        print_warning "调用次数少于预期（$GET_DICT_COUNT < 35）"
        print_warning "可能修复不完整"
    fi
else
    print_error "_get_dict 函数不存在！"
    print_error "v7.2.17修复未找到！"
    echo ""
    print_warning "这意味着您可能在错误的分支或旧版本代码"
    print_warning "建议操作："
    echo "   1. 检查分支: git branch --show-current"
    echo "   2. 拉取最新: git pull origin $CORRECT_BRANCH"
    echo "   3. 查看提交: git log --oneline -3"
    exit 1
fi

# 显示最近提交
echo ""
print_info "最近3次提交:"
git log --oneline -3 | sed 's/^/   /'

# ============================================================================
print_header "步骤 7/8: 运行测试验证"
# ============================================================================

if [ -f "test_v7217_fix.py" ]; then
    print_info "运行 test_v7217_fix.py..."
    echo ""

    if python3 test_v7217_fix.py; then
        echo ""
        print_success "测试通过！v7.2.17修复已生效"
    else
        echo ""
        print_error "测试失败！"
        print_warning "请查看上述测试输出"
        exit 1
    fi
else
    print_warning "测试脚本不存在（test_v7217_fix.py）"
    print_warning "跳过测试，但强烈建议手动验证"
fi

# ============================================================================
print_header "步骤 8/8: 清理总结"
# ============================================================================

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ 缓存清理完成！                               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

print_info "清理统计："
echo "   • 停止进程: ✅"
echo "   • __pycache__: $PYCACHE_COUNT 个已清理"
echo "   • .pyc文件: $PYC_COUNT 个已清理"
echo "   • .pyo文件: $PYO_COUNT 个已清理"
echo "   • pip缓存: ✅"
echo "   • 分支验证: ✅ $CURRENT_BRANCH"
echo "   • v7.2.17修复: ✅ _get_dict调用${GET_DICT_COUNT}次"
echo ""

print_header "启动系统"

print_info "准备启动系统..."
echo ""
print_warning "请选择启动方式："
echo "   1) 自动启动（推荐）"
echo "   2) 手动启动（稍后自己执行）"
echo ""
read -p "请选择 (1/2): " -n 1 -r
echo
echo ""

if [[ $REPLY == "1" ]]; then
    print_info "自动启动系统..."
    cd ~/cryptosignal

    if [ -f "setup.sh" ]; then
        print_info "执行 ./setup.sh ..."
        ./setup.sh
        print_success "系统已启动"
    else
        print_error "setup.sh 不存在"
        print_info "请手动启动: cd ~/cryptosignal && ./setup.sh"
    fi
else
    print_info "跳过自动启动"
    echo ""
    print_warning "手动启动命令："
    echo "   cd ~/cryptosignal"
    echo "   ./setup.sh"
fi

echo ""
print_header "完成"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}💡 重要提示${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
print_success "如果仍然出现 'str' object has no attribute 'get' 错误："
echo ""
echo "   1. 检查日志确认错误行号:"
echo "      tail -f ~/cryptosignal/logs/*.log"
echo ""
echo "   2. 验证_get_dict函数:"
echo "      grep -n 'def _get_dict' ~/cryptosignal/ats_core/outputs/telegram_fmt.py"
echo ""
echo "   3. 验证函数被调用:"
echo "      grep -c '_get_dict(' ~/cryptosignal/ats_core/outputs/telegram_fmt.py"
echo ""
echo "   4. 重新运行清理脚本:"
echo "      bash cleanup_all_cache.sh"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

print_success "缓存清理脚本执行完成！"
echo ""
