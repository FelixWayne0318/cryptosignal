#!/bin/bash
# ========================================
# CryptoSignal v6.6 重构验证脚本
# 生成日期: 2025-11-03
# 用途: 验证REPOSITORY_REFACTORING_PLAN.md执行结果
# ========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "🔍 CryptoSignal v6.6 重构验证"
echo "========================================"
echo ""

passed=0
failed=0
warnings=0

# ========================================
# 1. 验证根目录脚本
# ========================================
echo "📋 1. 验证根目录脚本"
echo "----------------------------------------"

echo "检查核心脚本存在..."
required_scripts=(
    "deploy_and_run.sh"
    "start.sh"
    "stop.sh"
    "check_status.sh"
    "view_logs.sh"
)

for script in "${required_scripts[@]}"; do
    if [ -f "$script" ]; then
        echo -e "  ${GREEN}✅${NC} $script"
        ((passed++))
    else
        echo -e "  ${RED}❌${NC} $script 丢失"
        ((failed++))
    fi
done

echo ""
echo "检查冗余脚本已删除..."
removed_scripts=(
    "deploy_v6.1.sh"
    "run_background.sh"
    "run_production.sh"
    "run_with_screen.sh"
    "start_production.sh"
)

for script in "${removed_scripts[@]}"; do
    if [ ! -f "$script" ]; then
        echo -e "  ${GREEN}✅${NC} $script 已删除"
        ((passed++))
    else
        echo -e "  ${YELLOW}⚠️${NC} $script 仍然存在"
        ((warnings++))
    fi
done

# ========================================
# 2. 验证standards/目录结构
# ========================================
echo ""
echo "📋 2. 验证standards/目录结构"
echo "----------------------------------------"

echo "检查子目录存在..."
required_dirs=(
    "standards/configuration"
    "standards/development"
    "standards/deployment"
    "standards/specifications"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✅${NC} $dir/"
        ((passed++))
    else
        echo -e "  ${RED}❌${NC} $dir/ 丢失"
        ((failed++))
    fi
done

echo ""
echo "检查重复文档已删除..."
removed_docs=(
    "standards/ARCHITECTURE.md"
    "standards/DEPLOYMENT.md"
    "standards/DEPLOYMENT_STANDARD.md"
    "standards/QUICK_DEPLOY.md"
    "standards/CORE_STANDARDS.md"
    "standards/STANDARDIZATION_REPORT.md"
)

for doc in "${removed_docs[@]}"; do
    if [ ! -f "$doc" ]; then
        echo -e "  ${GREEN}✅${NC} $doc 已删除"
        ((passed++))
    else
        echo -e "  ${YELLOW}⚠️${NC} $doc 仍然存在"
        ((warnings++))
    fi
done

echo ""
echo "检查文档已移动..."
moved_docs=(
    "standards/configuration/PARAMS_SPEC.md"
    "standards/development/WORKFLOW.md"
    "standards/development/MODIFICATION_RULES.md"
    "standards/development/DOCUMENTATION_RULES.md"
)

for doc in "${moved_docs[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "  ${GREEN}✅${NC} $doc"
        ((passed++))
    else
        echo -e "  ${RED}❌${NC} $doc 丢失"
        ((failed++))
    fi
done

# ========================================
# 3. 验证docs/目录结构
# ========================================
echo ""
echo "📋 3. 验证docs/目录结构"
echo "----------------------------------------"

echo "检查archive目录统一..."
if [ -d "docs/archive" ]; then
    echo -e "  ${GREEN}✅${NC} docs/archive/"
    ((passed++))
else
    echo -e "  ${RED}❌${NC} docs/archive/ 丢失"
    ((failed++))
fi

if [ ! -d "docs/archive_2025-11-02" ]; then
    echo -e "  ${GREEN}✅${NC} docs/archive_2025-11-02/ 已删除"
    ((passed++))
else
    echo -e "  ${YELLOW}⚠️${NC} docs/archive_2025-11-02/ 仍然存在"
    ((warnings++))
fi

if [ ! -d "docs/archived" ]; then
    echo -e "  ${GREEN}✅${NC} docs/archived/ 已删除"
    ((passed++))
else
    echo -e "  ${YELLOW}⚠️${NC} docs/archived/ 仍然存在"
    ((warnings++))
fi

# ========================================
# 4. 验证tests/目录结构
# ========================================
echo ""
echo "📋 4. 验证tests/目录结构"
echo "----------------------------------------"

echo "检查测试子目录..."
test_dirs=(
    "tests/unit"
    "tests/integration"
    "tests/e2e"
    "tests/diagnostic"
    "tests/archive"
)

for dir in "${test_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✅${NC} $dir/"
        ((passed++))
    else
        echo -e "  ${RED}❌${NC} $dir/ 丢失"
        ((failed++))
    fi
done

echo ""
echo "检查临时测试已归档..."
archived_tests=(
    "tests/test_phase1_code_review.py"
    "tests/test_phase1_data_update.py"
    "tests/test_phase1_e2e.py"
    "tests/test_phase1_quick.py"
    "tests/test_5_coins_old.py"
)

for test in "${archived_tests[@]}"; do
    if [ ! -f "$test" ]; then
        echo -e "  ${GREEN}✅${NC} $(basename $test) 已归档"
        ((passed++))
    else
        echo -e "  ${YELLOW}⚠️${NC} $(basename $test) 未归档"
        ((warnings++))
    fi
done

# ========================================
# 5. 验证deprecated/目录已删除
# ========================================
echo ""
echo "📋 5. 验证deprecated/目录"
echo "----------------------------------------"

if [ ! -d "deprecated" ]; then
    echo -e "  ${GREEN}✅${NC} deprecated/ 已删除"
    ((passed++))
else
    echo -e "  ${YELLOW}⚠️${NC} deprecated/ 仍然存在"
    ((warnings++))
fi

# ========================================
# 6. 验证关键文件完整性
# ========================================
echo ""
echo "📋 6. 验证关键文件完整性"
echo "----------------------------------------"

critical_files=(
    "config/params.json"
    "scripts/realtime_signal_scanner.py"
    "ats_core/pipeline/analyze_symbol.py"
    "ats_core/pipeline/batch_scan_optimized.py"
    "requirements.txt"
    "README.md"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✅${NC} $file"
        ((passed++))
    else
        echo -e "  ${RED}❌${NC} $file 丢失"
        ((failed++))
    fi
done

# ========================================
# 7. 验证权重配置
# ========================================
echo ""
echo "📋 7. 验证权重配置"
echo "----------------------------------------"

python3 -c "
import json
try:
    with open('config/params.json') as f:
        weights = json.load(f)['weights']
        factor_weights = {k: v for k, v in weights.items() if not k.startswith('_')}

        # A层6因子
        a_layer = ['T', 'M', 'C', 'V', 'O', 'B']
        a_total = sum(factor_weights.get(k, 0) for k in a_layer)

        # B层4调制器
        b_layer = ['L', 'S', 'F', 'I']
        b_total = sum(factor_weights.get(k, 0) for k in b_layer)

        print(f'  A层6因子总和: {a_total}%')
        print(f'  B层4调制器总和: {b_total}%')

        if abs(a_total - 100.0) < 0.01 and abs(b_total) < 0.01:
            print('  ✅ 权重配置正确')
            exit(0)
        else:
            print('  ❌ 权重配置错误')
            exit(1)
except Exception as e:
    print(f'  ❌ 验证失败: {e}')
    exit(1)
" && ((passed++)) || ((failed++))

# ========================================
# 8. 统计和总结
# ========================================
echo ""
echo "========================================"
echo "📊 验证结果统计"
echo "========================================"
echo ""
echo -e "  ${GREEN}✅ 通过: $passed${NC}"
echo -e "  ${YELLOW}⚠️  警告: $warnings${NC}"
echo -e "  ${RED}❌ 失败: $failed${NC}"
echo ""

total=$((passed + warnings + failed))
pass_rate=$((passed * 100 / total))

echo "通过率: $pass_rate% ($passed/$total)"
echo ""

if [ $failed -eq 0 ]; then
    if [ $warnings -eq 0 ]; then
        echo -e "${GREEN}✅ 重构验证完美通过！${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  重构验证通过，但有 $warnings 个警告${NC}"
        echo ""
        echo "建议: 检查警告项并手动处理"
        exit 0
    fi
else
    echo -e "${RED}❌ 重构验证失败，发现 $failed 个问题${NC}"
    echo ""
    echo "建议: 检查失败项并重新运行重构脚本"
    exit 1
fi
