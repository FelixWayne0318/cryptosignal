#!/bin/bash
# ========================================
# CryptoSignal v6.6 仓库重构执行脚本
# 生成日期: 2025-11-03
# 用途: 自动执行REPOSITORY_REFACTORING_PLAN.md中的重构操作
# ========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "🔧 CryptoSignal v6.6 仓库重构"
echo "========================================"
echo ""

# 检查是否在项目根目录
if [ ! -f "config/params.json" ]; then
    echo -e "${RED}❌ 错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 询问用户确认
echo -e "${YELLOW}⚠️  警告: 此脚本将重组整个仓库结构${NC}"
echo ""
echo "📋 将执行的操作:"
echo "  1. 删除8个冗余部署脚本"
echo "  2. 合并3个archive目录为1个"
echo "  3. 重组standards/目录"
echo "  4. 重组tests/目录"
echo "  5. 删除deprecated/目录"
echo "  6. 更新文档到v6.6"
echo ""
echo -e "${YELLOW}建议: 先运行 git add -A && git commit -m 'chore: 重构前备份'${NC}"
echo ""
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消重构"
    exit 1
fi

echo ""

# ========================================
# Phase 1: 立即清理
# ========================================
echo "📋 Phase 1: 立即清理"
echo "========================================"

# 1.1 备份冗余文件
echo "1️⃣ 备份冗余文件..."
mkdir -p archive_temp/root_scripts
mkdir -p archive_temp/deprecated

# 备份即将删除的脚本
[ -f "deploy_v6.1.sh" ] && cp deploy_v6.1.sh archive_temp/root_scripts/
[ -f "run_background.sh" ] && cp run_background.sh archive_temp/root_scripts/
[ -f "run_production.sh" ] && cp run_production.sh archive_temp/root_scripts/
[ -f "run_with_screen.sh" ] && cp run_with_screen.sh archive_temp/root_scripts/
[ -f "start_production.sh" ] && cp start_production.sh archive_temp/root_scripts/

# 备份deprecated
if [ -d "deprecated" ]; then
    cp -r deprecated/* archive_temp/deprecated/
fi

echo -e "  ${GREEN}✅ 备份完成 → archive_temp/${NC}"

# 1.2 删除冗余部署脚本
echo ""
echo "2️⃣ 删除冗余部署脚本..."

deleted_count=0

for script in deploy_v6.1.sh run_background.sh run_production.sh run_with_screen.sh start_production.sh; do
    if [ -f "$script" ]; then
        rm "$script"
        echo "  ✅ 删除 $script"
        ((deleted_count++))
    fi
done

echo -e "  ${GREEN}✅ 删除了 $deleted_count 个冗余脚本${NC}"

# 1.3 合并archive目录
echo ""
echo "3️⃣ 合并archive目录..."

if [ ! -d "docs/archive" ]; then
    mkdir -p docs/archive
fi

# 合并archive_2025-11-02
if [ -d "docs/archive_2025-11-02" ]; then
    mkdir -p docs/archive/2025-11-02
    mv docs/archive_2025-11-02/* docs/archive/2025-11-02/ 2>/dev/null || true
    rm -rf docs/archive_2025-11-02
    echo "  ✅ 合并 archive_2025-11-02/"
fi

# 合并archived
if [ -d "docs/archived" ]; then
    mkdir -p docs/archive/older
    mv docs/archived/* docs/archive/older/ 2>/dev/null || true
    rm -rf docs/archived
    echo "  ✅ 合并 archived/"
fi

echo -e "  ${GREEN}✅ archive目录已统一${NC}"

# 1.4 删除deprecated目录
echo ""
echo "4️⃣ 删除deprecated目录..."

if [ -d "deprecated" ]; then
    rm -rf deprecated
    echo -e "  ${GREEN}✅ deprecated/目录已删除${NC}"
else
    echo "  ⏭️  deprecated/目录不存在，跳过"
fi

echo ""

# ========================================
# Phase 2: 文档重组
# ========================================
echo "📋 Phase 2: 文档重组"
echo "========================================"

# 2.1 创建新子目录
echo "1️⃣ 创建新子目录..."

mkdir -p standards/configuration
mkdir -p standards/development
mkdir -p standards/deployment
mkdir -p standards/specifications

echo "  ✅ 子目录创建完成"

# 2.2 移动配置文档
echo ""
echo "2️⃣ 移动和重组standards/文档..."

moved_count=0

# 移动配置文档
if [ -f "standards/CONFIGURATION_GUIDE.md" ]; then
    mv standards/CONFIGURATION_GUIDE.md standards/configuration/PARAMS_SPEC.md
    echo "  ✅ CONFIGURATION_GUIDE.md → configuration/PARAMS_SPEC.md"
    ((moved_count++))
fi

# 移动开发文档
if [ -f "standards/DEVELOPMENT_WORKFLOW.md" ]; then
    mv standards/DEVELOPMENT_WORKFLOW.md standards/development/WORKFLOW.md
    echo "  ✅ DEVELOPMENT_WORKFLOW.md → development/WORKFLOW.md"
    ((moved_count++))
fi

if [ -f "standards/MODIFICATION_RULES.md" ]; then
    mv standards/MODIFICATION_RULES.md standards/development/MODIFICATION_RULES.md
    echo "  ✅ MODIFICATION_RULES.md → development/"
    ((moved_count++))
fi

if [ -f "standards/DOCUMENTATION_RULES.md" ]; then
    mv standards/DOCUMENTATION_RULES.md standards/development/DOCUMENTATION_RULES.md
    echo "  ✅ DOCUMENTATION_RULES.md → development/"
    ((moved_count++))
fi

# 移动部署文档
if [ -f "standards/SERVER_OPERATIONS.md" ]; then
    mv standards/SERVER_OPERATIONS.md standards/deployment/SERVER_OPERATIONS.md
    echo "  ✅ SERVER_OPERATIONS.md → deployment/"
    ((moved_count++))
fi

if [ -f "standards/TELEGRAM_SETUP.md" ]; then
    mv standards/TELEGRAM_SETUP.md standards/deployment/TELEGRAM_SETUP.md
    echo "  ✅ TELEGRAM_SETUP.md → deployment/"
    ((moved_count++))
fi

echo -e "  ${GREEN}✅ 移动了 $moved_count 个文档${NC}"

# 2.3 删除重复文档
echo ""
echo "3️⃣ 删除重复文档..."

deleted_docs=0

for doc in ARCHITECTURE.md DEPLOYMENT.md DEPLOYMENT_STANDARD.md QUICK_DEPLOY.md CORE_STANDARDS.md STANDARDIZATION_REPORT.md; do
    if [ -f "standards/$doc" ]; then
        # 先移至archive
        mkdir -p docs/archive/standards_old
        mv "standards/$doc" "docs/archive/standards_old/"
        echo "  ✅ 归档 $doc"
        ((deleted_docs++))
    fi
done

echo -e "  ${GREEN}✅ 归档了 $deleted_docs 个重复文档${NC}"

# 2.4 更新specifications/
echo ""
echo "4️⃣ 更新specifications/..."

if [ -f "standards/specifications/FACTOR_SYSTEM_v6.6_UPDATED.md" ]; then
    # 备份旧版本
    if [ -f "standards/specifications/FACTOR_SYSTEM.md" ]; then
        mv standards/specifications/FACTOR_SYSTEM.md \
           docs/archive/standards_old/FACTOR_SYSTEM_v6.4.md
        echo "  ✅ 备份旧版 FACTOR_SYSTEM.md (v6.4)"
    fi

    # 使用新版本
    mv standards/specifications/FACTOR_SYSTEM_v6.6_UPDATED.md \
       standards/specifications/FACTOR_SYSTEM.md
    echo "  ✅ 更新 FACTOR_SYSTEM.md 到 v6.6"
fi

# 2.5 修复MODULATORS.md
if [ -L "standards/specifications/MODULATORS.md" ] || [ ! -f "standards/specifications/MODULATORS.md" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  MODULATORS.md 需要手动修复${NC}"
    echo "    请创建真实文件: standards/specifications/MODULATORS.md"
fi

echo ""

# ========================================
# Phase 3: 测试重组
# ========================================
echo "📋 Phase 3: 测试重组"
echo "========================================"

# 3.1 创建测试目录结构
echo "1️⃣ 创建测试目录结构..."

mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/e2e
mkdir -p tests/diagnostic
mkdir -p tests/archive

echo "  ✅ 测试子目录创建完成"

# 3.2 归档临时测试
echo ""
echo "2️⃣ 归档临时测试文件..."

archived_tests=0

for test in tests/test_phase1_*.py tests/test_5_coins_old.py; do
    if [ -f "$test" ]; then
        mv "$test" tests/archive/
        basename_test=$(basename "$test")
        echo "  ✅ 归档 $basename_test"
        ((archived_tests++))
    fi
done

echo -e "  ${GREEN}✅ 归档了 $archived_tests 个临时测试${NC}"

# 3.3 移动诊断工具
echo ""
echo "3️⃣ 移动诊断工具..."

diagnostic_moved=0

if [ -f "tests/diagnose_v66.py" ]; then
    mv tests/diagnose_v66.py tests/diagnostic/
    echo "  ✅ diagnose_v66.py → diagnostic/"
    ((diagnostic_moved++))
fi

if [ -f "tests/verify_standardization_imports.py" ]; then
    mv tests/verify_standardization_imports.py tests/diagnostic/verify_imports.py
    echo "  ✅ verify_standardization_imports.py → diagnostic/verify_imports.py"
    ((diagnostic_moved++))
fi

echo -e "  ${GREEN}✅ 移动了 $diagnostic_moved 个诊断工具${NC}"

# 3.4 移动集成测试
echo ""
echo "4️⃣ 移动集成测试..."

if [ -f "tests/test_auto_trader.py" ]; then
    mv tests/test_auto_trader.py tests/integration/
    echo "  ✅ test_auto_trader.py → integration/"
fi

echo ""

# ========================================
# Phase 4: 清理和验证
# ========================================
echo "📋 Phase 4: 清理和验证"
echo "========================================"

# 4.1 创建README文件
echo "1️⃣ 创建README文件..."

# standards/configuration/README.md
cat > standards/configuration/README.md <<'EOF'
# Configuration Documentation

This directory contains all configuration-related documentation.

## Files

- `PARAMS_SPEC.md` - Parameters configuration specification

Refer to parent INDEX for more information.
EOF

# standards/development/README.md
cat > standards/development/README.md <<'EOF'
# Development Documentation

This directory contains all development-related documentation.

## Files

- `WORKFLOW.md` - Development workflow
- `MODIFICATION_RULES.md` - Code modification rules
- `DOCUMENTATION_RULES.md` - Documentation writing rules

Refer to parent INDEX for more information.
EOF

# tests/archive/README.md
cat > tests/archive/README.md <<'EOF'
# Archived Tests

This directory contains old or temporary test files that are no longer actively used.

Files here are kept for historical reference but are not part of the regular test suite.
EOF

echo "  ✅ README文件创建完成"

# 4.2 统计结果
echo ""
echo "2️⃣ 统计重构结果..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ 重构完成统计${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 文件操作:"
echo "  • 删除冗余脚本: $deleted_count 个"
echo "  • 归档重复文档: $deleted_docs 个"
echo "  • 归档临时测试: $archived_tests 个"
echo "  • 移动重组文档: $moved_count 个"
echo "  • 移动诊断工具: $diagnostic_moved 个"
echo ""
echo "🗂️  目录结构:"
echo "  • 合并archive: 3 → 1"
echo "  • standards/子目录: 新增 configuration/, development/"
echo "  • tests/子目录: 新增 unit/, integration/, e2e/, diagnostic/, archive/"
echo ""
echo "📁 备份位置:"
echo "  • archive_temp/root_scripts/ - 删除的脚本"
echo "  • archive_temp/deprecated/ - deprecated目录"
echo "  • docs/archive/standards_old/ - 重复文档"
echo "  • tests/archive/ - 临时测试"
echo ""

# 4.3 验证关键文件
echo "3️⃣ 验证关键文件..."

critical_files_ok=true

# 检查核心脚本
if [ ! -f "deploy_and_run.sh" ]; then
    echo -e "  ${RED}❌ deploy_and_run.sh 丢失${NC}"
    critical_files_ok=false
else
    echo "  ✅ deploy_and_run.sh"
fi

if [ ! -f "start.sh" ]; then
    echo -e "  ${RED}❌ start.sh 丢失${NC}"
    critical_files_ok=false
else
    echo "  ✅ start.sh"
fi

# 检查主配置文件
if [ ! -f "config/params.json" ]; then
    echo -e "  ${RED}❌ config/params.json 丢失${NC}"
    critical_files_ok=false
else
    echo "  ✅ config/params.json"
fi

# 检查主文件
if [ ! -f "scripts/realtime_signal_scanner.py" ]; then
    echo -e "  ${RED}❌ realtime_signal_scanner.py 丢失${NC}"
    critical_files_ok=false
else
    echo "  ✅ realtime_signal_scanner.py"
fi

echo ""

if [ "$critical_files_ok" = true ]; then
    echo -e "${GREEN}✅ 所有关键文件验证通过${NC}"
else
    echo -e "${RED}❌ 部分关键文件丢失，请检查${NC}"
    exit 1
fi

echo ""

# ========================================
# 完成
# ========================================
echo "========================================"
echo -e "${GREEN}✅ 仓库重构完成！${NC}"
echo "========================================"
echo ""
echo "📋 后续步骤:"
echo "  1. 检查重构结果: git status"
echo "  2. 运行验证脚本: ./verify_refactoring.sh"
echo "  3. 提交变更: git add -A && git commit -m 'refactor: 全仓库重组'"
echo "  4. 推送到远程: git push"
echo ""
echo "🔄 如需回滚:"
echo "  • 临时备份在: archive_temp/"
echo "  • Git回滚: git reset --hard HEAD"
echo ""
echo "📖 详细报告: REPOSITORY_REFACTORING_PLAN.md"
echo ""
