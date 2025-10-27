#!/bin/bash
# 部署脚本 - 带详细错误日志
# 用途：部署所有修复到服务器并进行测试运行

set -e  # 遇到错误立即停止

echo "=========================================="
echo "🚀 开始部署修复（顶尖量化标准重构）"
echo "=========================================="
echo ""

# 步骤1：验证目录
echo "📁 [步骤1/6] 验证工作目录..."
if [ ! -d "/home/cryptosignal/cryptosignal" ]; then
    echo "❌ 错误：目录 /home/cryptosignal/cryptosignal 不存在"
    exit 1
fi

cd /home/cryptosignal/cryptosignal
echo "✅ 当前目录：$(pwd)"
echo ""

# 步骤2：清理缓存
echo "🧹 [步骤2/6] 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ 缓存已清理"
echo ""

# 步骤3：Git操作
echo "📥 [步骤3/6] 拉取最新代码..."
git fetch origin claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya
git pull origin claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya
echo "✅ 代码已更新到最新版本"
echo ""

# 步骤4：验证关键文件
echo "🔍 [步骤4/6] 验证关键文件完整性..."
critical_files=(
    "ats_core/features/market_regime.py"
    "ats_core/pipeline/analyze_symbol.py"
    "ats_core/outputs/telegram_fmt.py"
    "ats_core/scoring/probability.py"
)

for file in "${critical_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 错误：关键文件 $file 不存在"
        exit 1
    fi
    echo "   ✓ $file"
done
echo "✅ 所有关键文件完整"
echo ""

# 步骤5：验证Python模块导入
echo "🐍 [步骤5/6] 验证Python模块导入..."
python3 << 'PYEOF'
import sys
import traceback

modules_to_test = [
    "ats_core.features.market_regime",
    "ats_core.pipeline.analyze_symbol",
    "ats_core.outputs.telegram_fmt",
    "ats_core.scoring.probability",
]

failed = []
for module in modules_to_test:
    try:
        __import__(module)
        print(f"   ✓ {module}")
    except Exception as e:
        print(f"   ❌ {module}: {e}")
        traceback.print_exc()
        failed.append(module)

if failed:
    print(f"\n❌ 模块导入失败：{', '.join(failed)}")
    sys.exit(1)
else:
    print("\n✅ 所有模块导入成功")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ Python模块导入测试失败"
    exit 1
fi
echo ""

# 步骤6：测试运行
echo "🧪 [步骤6/6] 执行测试运行（限制5个交易对）..."
echo "----------------------------------------"
export PYTHONPATH="/home/cryptosignal/cryptosignal"
python3 -u -m tools.full_run --limit 5 2>&1 | tee /tmp/cryptosignal_test_$(date +%Y%m%d_%H%M%S).log

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 部署成功！所有修复已生效"
    echo "=========================================="
    echo ""
    echo "📋 修复内容摘要："
    echo "  1. ✅ 市场过滤器时间尺度对齐（EMA30→EMA5/20）"
    echo "  2. ✅ 对称奖惩机制（×0.70 至 ×1.20）"
    echo "  3. ✅ F调节器参与方向判断（权重7%）"
    echo "  4. ✅ Prime平滑评分（消除悬崖效应）"
    echo "  5. ✅ 合并惩罚逻辑（避免双重惩罚）"
    echo "  6. ✅ 分离显示F与市场过滤器"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ 测试运行失败"
    echo "=========================================="
    echo "日志已保存至：/tmp/cryptosignal_test_*.log"
    echo "请检查上方错误信息"
    exit 1
fi
