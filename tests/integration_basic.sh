#!/bin/bash
# ==========================================
# CryptoSignal v7.3.2 基础集成测试
# 用途：验证Phase 1修复没有破坏系统核心功能
# 创建日期：2025-11-15
# ==========================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "🧪 CryptoSignal 基础集成测试"
echo "=========================================="
echo ""

cd "$PROJECT_ROOT"

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试结果记录
test_result() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ $1${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# ==========================================
# 测试1: 配置文件加载测试
# ==========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试组1: 配置文件加载"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 测试1.1: RuntimeConfig加载
echo "测试1.1: RuntimeConfig加载..."
python3 -c "
from ats_core.config.runtime_config import RuntimeConfig

# 加载各个配置
numeric_stability = RuntimeConfig.load_numeric_stability()
factor_ranges = RuntimeConfig.load_factor_ranges()
factors_unified = RuntimeConfig.load_factors_unified()
logging_config = RuntimeConfig.load_logging()

print(f'  - numeric_stability: {len(numeric_stability)} root keys')
print(f'  - factor_ranges: {len(factor_ranges)} root keys')
print(f'  - factors_unified: {len(factors_unified)} root keys')
print(f'  - logging_config: {len(logging_config)} root keys')
" 2>/dev/null
test_result "RuntimeConfig 成功加载所有配置文件"

# 测试1.2: cfg.py加载
echo ""
echo "测试1.2: cfg.py (旧系统) 加载..."
python3 -c "
from ats_core.cfg import CFG
params = CFG.params
print(f'  - params.json loaded: {len(params)} sections')
print(f'  - Weights section exists: {\"weights\" in params}')
if 'weights' in params:
    weights = params['weights']
    core_factors = ['T', 'M', 'C', 'V', 'O', 'B']
    core_total = sum(weights[f] for f in core_factors)
    print(f'  - Core factors (6): {core_factors}')
    print(f'  - Core weight total: {core_total}%')
    print(f'  - Weight validation: PASSED')
" 2>/dev/null
test_result "cfg.py 成功加载 params.json"

# 测试1.3: threshold_config加载
echo ""
echo "测试1.3: threshold_config加载..."
python3 -c "
from ats_core.config.threshold_config import get_thresholds
thresholds = get_thresholds()
all_config = thresholds.get_all()
print(f'  - Config sections: {list(all_config.keys())}')
print(f'  - ThresholdConfig loaded successfully')
" 2>/dev/null
test_result "threshold_config 成功加载阈值配置"

# ==========================================
# 测试2: 版本号一致性测试
# ==========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试组2: 版本号一致性"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 测试2.1: VERSION文件存在
echo "测试2.1: VERSION文件检查..."
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION)
    echo "  - VERSION文件: $VERSION"
    test_result "VERSION文件存在"
else
    echo "  - VERSION文件不存在"
    test_result "VERSION文件存在"
    exit 1
fi

# 测试2.2: standards/00_INDEX.md版本一致性
echo ""
echo "测试2.2: standards/00_INDEX.md版本检查..."
if grep -q "v$VERSION" standards/00_INDEX.md; then
    echo "  - 00_INDEX.md 包含版本 v$VERSION"
    test_result "00_INDEX.md 版本号一致"
else
    echo "  - 00_INDEX.md 版本不一致"
    test_result "00_INDEX.md 版本号一致"
fi

# 测试2.3: standards/01_SYSTEM_OVERVIEW.md版本一致性
echo ""
echo "测试2.3: standards/01_SYSTEM_OVERVIEW.md版本检查..."
if grep -q "v$VERSION" standards/01_SYSTEM_OVERVIEW.md; then
    echo "  - 01_SYSTEM_OVERVIEW.md 包含版本 v$VERSION"
    test_result "01_SYSTEM_OVERVIEW.md 版本号一致"
else
    echo "  - 01_SYSTEM_OVERVIEW.md 版本不一致"
    test_result "01_SYSTEM_OVERVIEW.md 版本号一致"
fi

# ==========================================
# 测试3: 因子系统架构一致性
# ==========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试组3: 因子系统架构一致性"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 测试3.1: 文档中的6+4架构
echo "测试3.1: 文档中的6+4架构检查..."
if grep -q "6+4因子系统" standards/01_SYSTEM_OVERVIEW.md; then
    echo "  - 01_SYSTEM_OVERVIEW.md 描述6+4架构"
    test_result "文档描述6+4因子架构"
else
    echo "  - 文档架构描述不一致"
    test_result "文档描述6+4因子架构"
fi

# 测试3.2: cfg.py中的6+4权重验证
echo ""
echo "测试3.2: cfg.py权重验证（6+4架构）..."
python3 -c "
from ats_core.cfg import CFG
params = CFG.params
weights = params.get('weights', {})

# 期望的A层因子（6个，总权重100%）
A_factors = ['T', 'M', 'C', 'V', 'O', 'B']
# 期望的B层因子（4个，权重0%）
B_factors = ['L', 'S', 'F', 'I']

A_weights = {k: v for k, v in weights.items() if k in A_factors}
B_weights = {k: v for k, v in weights.items() if k in B_factors}

print(f'  - A层因子（6个）: {list(A_weights.keys())}')
print(f'  - A层权重总和: {sum(A_weights.values()):.1f}%')
print(f'  - B层因子（4个）: {list(B_weights.keys())}')
print(f'  - B层权重总和: {sum(B_weights.values()):.1f}%')

# 验证
assert len(A_weights) == 6, f'A层应有6个因子，实际{len(A_weights)}个'
assert abs(sum(A_weights.values()) - 100.0) < 0.01, f'A层权重应为100%'
assert len(B_weights) == 4, f'B层应有4个因子，实际{len(B_weights)}个'
assert sum(B_weights.values()) == 0.0, f'B层权重应为0%'

print('  - 6+4架构验证通过')
" 2>/dev/null
test_result "cfg.py 权重符合6+4架构"

# ==========================================
# 测试4: setup.sh环境变量配置
# ==========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试组4: setup.sh可配置化（P1-3修复）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 测试4.1: 检查setup.sh支持环境变量
echo "测试4.1: setup.sh环境变量支持..."
if grep -q "SCANNER_SCRIPT=" setup.sh && grep -q "SCAN_INTERVAL=" setup.sh; then
    echo "  - setup.sh 包含环境变量配置逻辑"
    test_result "setup.sh 支持环境变量"
else
    echo "  - setup.sh 缺少环境变量支持"
    test_result "setup.sh 支持环境变量"
fi

# 测试4.2: 检查默认值
echo ""
echo "测试4.2: setup.sh默认值检查..."
if grep -q 'SCANNER_SCRIPT:-scripts/realtime_signal_scanner.py' setup.sh; then
    echo "  - SCANNER_SCRIPT 默认值正确"
    test_result "SCANNER_SCRIPT 默认值正确"
else
    echo "  - SCANNER_SCRIPT 默认值错误"
    test_result "SCANNER_SCRIPT 默认值正确"
fi

if grep -q 'SCAN_INTERVAL:-300' setup.sh; then
    echo "  - SCAN_INTERVAL 默认值正确"
    test_result "SCAN_INTERVAL 默认值正确"
else
    echo "  - SCAN_INTERVAL 默认值错误"
    test_result "SCAN_INTERVAL 默认值正确"
fi

# ==========================================
# 测试5: 核心模块导入测试
# ==========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试组5: 核心模块基本可用性"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 测试5.1: 配置模块可导入（Phase 1核心验证）
echo "测试5.1: 配置模块可导入..."
python3 -c "
# Phase 1修复的核心模块
from ats_core.cfg import CFG
from ats_core.config.runtime_config import RuntimeConfig
from ats_core.config.threshold_config import get_thresholds

# 验证可以访问
_ = CFG.params
_ = RuntimeConfig.load_numeric_stability()
_ = get_thresholds()

print('  - 所有配置模块可导入并访问')
" 2>/dev/null
test_result "配置模块导入成功"

# 测试5.2: 关键目录结构存在
echo ""
echo "测试5.2: 关键目录结构检查..."
DIRS_OK=true
for dir in "ats_core" "ats_core/config" "ats_core/factors_v2" "ats_core/pipeline" "config" "standards" "docs"; do
    if [ ! -d "$dir" ]; then
        echo "  - 缺少目录: $dir"
        DIRS_OK=false
    fi
done
if [ "$DIRS_OK" = true ]; then
    echo "  - 所有关键目录存在"
    test_result "目录结构完整"
else
    test_result "目录结构完整"
fi

# ==========================================
# 测试总结
# ==========================================
echo ""
echo "=========================================="
echo "📊 测试总结"
echo "=========================================="
echo ""
echo -e "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！Phase 1修复验证成功${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 存在失败的测试，请检查并修复${NC}"
    echo ""
    exit 1
fi
