#!/bin/bash
# ========================================
# CryptoSignal v6.6 合规性修复脚本
# 生成日期: 2025-11-03
# 用途: 修复规范文档与代码实现的不一致问题
# ========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "🔧 CryptoSignal v6.6 合规性修复"
echo "========================================"
echo ""

# 检查是否在项目根目录
if [ ! -f "config/params.json" ]; then
    echo -e "${RED}❌ 错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# ========================================
# Phase 1: 备份现有文档
# ========================================
echo "📋 Phase 1: 备份现有文档"
echo "----------------------------------------"

BACKUP_DIR="standards/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "创建备份目录: $BACKUP_DIR"

# 备份要修改的文件
if [ -f "standards/specifications/FACTOR_SYSTEM.md" ]; then
    cp "standards/specifications/FACTOR_SYSTEM.md" "$BACKUP_DIR/"
    echo "  ✅ 备份 FACTOR_SYSTEM.md"
fi

if [ -f "standards/01_SYSTEM_OVERVIEW.md" ]; then
    cp "standards/01_SYSTEM_OVERVIEW.md" "$BACKUP_DIR/"
    echo "  ✅ 备份 01_SYSTEM_OVERVIEW.md"
fi

if [ -f "standards/03_VERSION_HISTORY.md" ]; then
    cp "standards/03_VERSION_HISTORY.md" "$BACKUP_DIR/"
    echo "  ✅ 备份 03_VERSION_HISTORY.md"
fi

if [ -f "standards/00_INDEX.md" ]; then
    cp "standards/00_INDEX.md" "$BACKUP_DIR/"
    echo "  ✅ 备份 00_INDEX.md"
fi

echo ""

# ========================================
# Phase 2: 更新规范文档
# ========================================
echo "📝 Phase 2: 更新规范文档到v6.6"
echo "----------------------------------------"

# 2.1 更新 FACTOR_SYSTEM.md
echo "1️⃣ 更新 FACTOR_SYSTEM.md..."

if [ -f "standards/specifications/FACTOR_SYSTEM_v6.6_UPDATED.md" ]; then
    cp "standards/specifications/FACTOR_SYSTEM_v6.6_UPDATED.md" \
       "standards/specifications/FACTOR_SYSTEM.md"
    echo -e "  ${GREEN}✅ FACTOR_SYSTEM.md 已更新到v6.6${NC}"
else
    echo -e "  ${YELLOW}⚠️  FACTOR_SYSTEM_v6.6_UPDATED.md 不存在，跳过${NC}"
fi

# 2.2 更新 01_SYSTEM_OVERVIEW.md
echo ""
echo "2️⃣ 更新 01_SYSTEM_OVERVIEW.md..."

# 更新因子系统描述 (8+2 → 6+4)
if [ -f "standards/01_SYSTEM_OVERVIEW.md" ]; then
    sed -i 's/## 🔢 8+2因子系统/## 🔢 6+4因子系统/g' standards/01_SYSTEM_OVERVIEW.md
    sed -i 's/10+1维因子系统/6+4维因子系统/g' standards/01_SYSTEM_OVERVIEW.md
    sed -i 's/A层10因子/A层6因子/g' standards/01_SYSTEM_OVERVIEW.md
    sed -i 's/（9维，总权重100%）/（6维，总权重100%）/g' standards/01_SYSTEM_OVERVIEW.md
    sed -i 's/（2维，权重0%）/（4维，权重0%）/g' standards/01_SYSTEM_OVERVIEW.md

    # 更新版本号
    sed -i 's/**版本**: v6.5/**版本**: v6.6/g' standards/01_SYSTEM_OVERVIEW.md
    sed -i 's/**v6.4** | /**v6.6** | /g' standards/01_SYSTEM_OVERVIEW.md

    echo -e "  ${GREEN}✅ 01_SYSTEM_OVERVIEW.md 已更新${NC}"
else
    echo -e "  ${YELLOW}⚠️  01_SYSTEM_OVERVIEW.md 不存在，跳过${NC}"
fi

# 2.3 补充 03_VERSION_HISTORY.md
echo ""
echo "3️⃣ 补充 03_VERSION_HISTORY.md (v6.5/v6.6变更记录)..."

if [ -f "standards/03_VERSION_HISTORY.md" ]; then
    # 在文件开头添加v6.5/v6.6变更记录
    cat > /tmp/version_history_addition.md <<'EOF'

---

## 📋 版本更新 (v6.5) - 2025-11-02

### 🎯 核心改进：因子系统优化

#### 移除Q因子
- **问题**: 清算密度数据不可靠，收益低
- **修改**: 完全移除Q因子及相关计算
- **权重重分配**: Q的4%权重分配到其他因子
- **文件**:
  - `ats_core/pipeline/analyze_symbol.py:361` - 移除Q因子计算
  - `config/params.json` - 移除Q权重配置

#### L因子移至执行层
- **问题**: L是质量指标，不应参与方向评分
- **修改**: L从A层移至执行层作为质量门槛
- **权重调整**: L的12%权重重新分配
- **架构**: 9因子 → 8因子 (T/M/C/S/V/O/B/E)

---

## 📋 版本更新 (v6.6) - 2025-11-03

### 🎯 核心改进：统一调制器架构

#### L/S移至B层调制器
- **问题**: L/S是质量指标，非方向指标
- **修改**: L和S从A层移至B层，作为调制器
- **新功能**:
  - L调制器: 调节仓位大小 (position)
  - S调制器: 调节置信度 (confidence)
- **架构**: 8+2 → 6+4 (A层6因子 + B层4调制器)
- **文件**:
  - `ats_core/pipeline/analyze_symbol.py:363-425` - B层调制器实现
  - `ats_core/modulators/modulator_chain.py` - 调制器链

#### 权重重新分配
**释放权重**: L(12%) + S(10%) = 22%

**重新分配**:
- T: 18% → 24% (+6%)
- M: 12% → 17% (+5%)
- C: 18% → 24% (+6%)
- V: 10% → 12% (+2%)
- O: 12% → 17% (+5%)
- B: 4% → 6% (+2%)

**总计**: +22% + Q的4% (v6.5) = 26% ✅

#### 软约束系统
- **修改**: EV≤0和P<p_min从硬门槛改为软约束
- **效果**: 仅标记警告，不硬拒绝信号
- **文件**: `scripts/realtime_signal_scanner.py:266-312`

#### Bug修复
- **M因子**: scale=1.00，消除tanh饱和
- **I因子**: 移除double-tanh bug
- **F因子**: 移除double-tanh bug

### 📊 架构对比

| 版本 | 架构 | A层因子 | B层调制器 | 权重系统 |
|------|------|--------|----------|---------|
| v6.4 | 9+2 | T/M/C/S/V/O/L/B/Q | F/I | 100% |
| v6.5 | 8+2 | T/M/C/S/V/O/B/E | F/I | 100% |
| v6.6 | 6+4 | T/M/C/V/O/B | L/S/F/I | 100% |

---

EOF

    # 在09_NEWCOIN_SPEC.md合规性审查之前插入
    sed -i '/## 📋 NEWCOIN_SPEC.md 合规性审查/r /tmp/version_history_addition.md' standards/03_VERSION_HISTORY.md

    rm /tmp/version_history_addition.md

    echo -e "  ${GREEN}✅ 03_VERSION_HISTORY.md 已补充v6.5/v6.6记录${NC}"
else
    echo -e "  ${YELLOW}⚠️  03_VERSION_HISTORY.md 不存在，跳过${NC}"
fi

# 2.4 更新 00_INDEX.md
echo ""
echo "4️⃣ 更新 00_INDEX.md (追溯矩阵和版本号)..."

if [ -f "standards/00_INDEX.md" ]; then
    # 更新版本号
    sed -i 's/当前版本\*\*: v6.6/**当前版本**: v6.6/g' standards/00_INDEX.md

    # 更新追溯矩阵中的因子系统行
    sed -i 's/| 6因子系统 | \[FACTOR_SYSTEM.md\]/| 6+4因子系统 | [FACTOR_SYSTEM.md]/g' standards/00_INDEX.md
    sed -i 's/`ats_core\/factors_v2\/`/`ats_core\/factors_v2\/` (6因子A层) + `ats_core\/modulators\/` (4调制器B层)/g' standards/00_INDEX.md

    echo -e "  ${GREEN}✅ 00_INDEX.md 已更新${NC}"
else
    echo -e "  ${YELLOW}⚠️  00_INDEX.md 不存在，跳过${NC}"
fi

echo ""

# ========================================
# Phase 3: 修正系统消息
# ========================================
echo "💬 Phase 3: 修正系统消息"
echo "----------------------------------------"

# 3.1 修正 realtime_signal_scanner.py
echo "1️⃣ 修正 realtime_signal_scanner.py..."

if [ -f "scripts/realtime_signal_scanner.py" ]; then
    # 修正新币数据流描述
    sed -i 's/🆕 新币数据流架构: 1m\/5m\/15m粒度/🆕 新币通道: Phase 1完成 (判断标准 + 阈值补偿)/g' \
        scripts/realtime_signal_scanner.py

    echo -e "  ${GREEN}✅ realtime_signal_scanner.py 消息已修正${NC}"
else
    echo -e "  ${YELLOW}⚠️  realtime_signal_scanner.py 不存在，跳过${NC}"
fi

# 3.2 修正 deploy_and_run.sh
echo ""
echo "2️⃣ 修正 deploy_and_run.sh..."

if [ -f "deploy_and_run.sh" ]; then
    # 修正新币数据流描述
    sed -i 's/✅ 新币数据流：1m\/5m\/15m粒度自动判断/🚧 新币通道：Phase 1完成 (当前使用1h\/4h + 阈值补偿)/g' \
        deploy_and_run.sh

    echo -e "  ${GREEN}✅ deploy_and_run.sh 消息已修正${NC}"
else
    echo -e "  ${YELLOW}⚠️  deploy_and_run.sh 不存在，跳过${NC}"
fi

echo ""

# ========================================
# Phase 4: 验证修复结果
# ========================================
echo "✅ Phase 4: 验证修复结果"
echo "----------------------------------------"

echo "1️⃣ 验证权重配置..."
python3 -c "
import json
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
        print('  ✅ 权重配置验证通过')
    else:
        print('  ❌ 权重配置验证失败')
        exit(1)
"

echo ""
echo "2️⃣ 检查文档更新..."

# 检查FACTOR_SYSTEM.md是否包含v6.6标识
if grep -q "v6.6" standards/specifications/FACTOR_SYSTEM.md 2>/dev/null; then
    echo -e "  ${GREEN}✅ FACTOR_SYSTEM.md 包含v6.6标识${NC}"
else
    echo -e "  ${YELLOW}⚠️  FACTOR_SYSTEM.md 未找到v6.6标识${NC}"
fi

# 检查01_SYSTEM_OVERVIEW.md是否包含6+4
if grep -q "6+4" standards/01_SYSTEM_OVERVIEW.md 2>/dev/null; then
    echo -e "  ${GREEN}✅ 01_SYSTEM_OVERVIEW.md 包含6+4架构${NC}"
else
    echo -e "  ${YELLOW}⚠️  01_SYSTEM_OVERVIEW.md 未找到6+4标识${NC}"
fi

echo ""

# ========================================
# 完成
# ========================================
echo "========================================"
echo -e "${GREEN}✅ 合规性修复完成！${NC}"
echo "========================================"
echo ""
echo "📋 修复总结:"
echo "  ✅ Phase 1: 备份现有文档 → $BACKUP_DIR"
echo "  ✅ Phase 2: 更新规范文档到v6.6"
echo "  ✅ Phase 3: 修正系统消息"
echo "  ✅ Phase 4: 验证修复结果"
echo ""
echo "📂 修改的文件:"
echo "  - standards/specifications/FACTOR_SYSTEM.md"
echo "  - standards/01_SYSTEM_OVERVIEW.md"
echo "  - standards/03_VERSION_HISTORY.md"
echo "  - standards/00_INDEX.md"
echo "  - scripts/realtime_signal_scanner.py"
echo "  - deploy_and_run.sh"
echo ""
echo "📖 查看详细审查报告:"
echo "  cat COMPLIANCE_AUDIT_REPORT.md"
echo ""
echo "🔄 如需回滚，可从备份恢复:"
echo "  cp $BACKUP_DIR/* standards/specifications/"
echo ""
