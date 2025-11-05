#!/bin/bash
# 测试扫描脚本（单次扫描20个币种）

cd /home/user/cryptosignal

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull

# 测试扫描
echo "🧪 测试扫描（20个币种）..."
echo ""

python3 scripts/realtime_signal_scanner.py --max-symbols 20
