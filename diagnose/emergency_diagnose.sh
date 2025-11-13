#!/bin/bash
#
# 紧急诊断脚本 - 捕获完整错误堆栈
#

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}紧急诊断：捕获ETHUSDT错误的完整堆栈${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd ~/cryptosignal

# 1. 检查最近的日志文件
echo -e "${CYAN}📁 步骤1: 查找最新日志文件${NC}"
LATEST_LOG=$(find . -name "*.log" -type f -printf '%T+ %p\n' 2>/dev/null | sort -r | head -1 | awk '{print $2}')

if [ -n "$LATEST_LOG" ]; then
    echo -e "${GREEN}✅ 找到日志: $LATEST_LOG${NC}"
    echo ""
    echo -e "${CYAN}📄 最后50行日志（包含错误）:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -50 "$LATEST_LOG"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo -e "${RED}❌ 未找到日志文件${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 步骤2: 检查Python导入路径${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

python3 -c "
import sys
print('Python路径:')
for i, p in enumerate(sys.path, 1):
    print(f'  {i}. {p}')

print('\n检查telegram_fmt.py位置:')
try:
    from ats_core.outputs import telegram_fmt
    print(f'  ✅ 已加载: {telegram_fmt.__file__}')

    # 检查_get_dict是否存在
    if hasattr(telegram_fmt, '_get_dict'):
        print(f'  ✅ _get_dict函数存在')
    else:
        print(f'  ❌ _get_dict函数不存在！')
except Exception as e:
    print(f'  ❌ 导入失败: {e}')
"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🔍 步骤3: 检查运行中的进程使用的代码${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if ps aux | grep -v grep | grep "python.*cryptosignal" > /dev/null; then
    echo -e "${GREEN}✅ 发现运行中的进程:${NC}"
    ps aux | grep -v grep | grep "python.*cryptosignal" | while read line; do
        PID=$(echo "$line" | awk '{print $2}')
        CMD=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
        echo "  PID $PID: $CMD"

        # 检查进程的工作目录
        if [ -d "/proc/$PID" ]; then
            CWD=$(readlink /proc/$PID/cwd 2>/dev/null || echo "无法读取")
            echo "    工作目录: $CWD"
        fi
    done
else
    echo -e "${YELLOW}⚠️  无运行中的进程${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🧪 步骤4: 模拟ETHUSDT错误${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

python3 << 'PYEOF'
import sys
import traceback

sys.path.insert(0, '/home/cryptosignal/cryptosignal')

print("尝试重现错误...")

try:
    from ats_core.outputs.telegram_fmt import render_trade_v72

    # 模拟可能导致错误的ETHUSDT数据
    test_signal = {
        "symbol": "ETHUSDT",
        "side_long": False,
        "confidence": 50.0,
        "confidence_adjusted": 50.0,
        "prime_strength": 50,
        "prime_prob": 0.60,
        "edge": 0.20,
        "scores": "string_value",  # 可能的问题数据
        "v72_enhancements": {
            "I_meta": "string_value",
            "independence_market_analysis": "string_value",
            "group_scores": "string_value",
            "gates": "string_value",
        }
    }

    result = render_trade_v72(test_signal)
    print(f"✅ 渲染成功（长度: {len(result)}）")
    print("   这意味着错误可能来自其他位置")

except AttributeError as e:
    print(f"❌ 发现AttributeError错误！")
    print(f"   错误信息: {e}")
    print(f"\n完整堆栈:")
    traceback.print_exc()
except Exception as e:
    print(f"❌ 其他错误: {e}")
    traceback.print_exc()

PYEOF

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📝 步骤5: 检查其他可能的问题文件${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo "搜索所有 'or {}' 模式（可能遗漏的位置）:"
grep -rn "or {}" --include="*.py" ats_core/ scripts/ 2>/dev/null | grep -v "Binary" | head -20

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "✅ 诊断完成"
echo ""
echo -e "${YELLOW}请将以上输出完整发送给我，特别是:${NC}"
echo "  1. 最后50行日志（步骤1）"
echo "  2. Python导入路径（步骤2）"
echo "  3. 模拟错误结果（步骤4）"
echo "  4. 搜索or {}结果（步骤5）"
echo ""
