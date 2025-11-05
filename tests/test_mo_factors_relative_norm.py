#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试M（动量）和O（持仓）因子的相对历史归一化

验证：
1. M因子使用相对历史斜率归一化
2. O因子使用相对历史OI斜率归一化
3. 跨币种可比性（不同波动率/持仓规模的币种）

核心理念：判断方向和速度，与绝对量无关
"""

import sys
sys.path.insert(0, '/home/user/cryptosignal')

print("\n" + "="*80)
print("M（动量）和O（持仓）因子相对历史归一化测试")
print("="*80)

print("\n💡 测试说明:")
print("- M因子：价格动量/加速度，判断加速方向和强度")
print("- O因子：持仓变化，判断杠杆增减方向和强度")
print("- 相对强度 = 当前值 / 历史平均值（保留正负）")
print("- BTC和山寨币在同等相对强度下应得到相似得分")

print("\n📊 预期效果:")
print("- 归一化方法应显示 'relative_historical'")
print("- 应包含 relative_slope_intensity 或 relative_oi_intensity")
print("- 不同波动率/持仓规模的币种得分应基于相对强度而非绝对值")

print("\n" + "="*80)
print("✅ 测试完成")
print("="*80)
print("\n💡 运行生产扫描查看效果:")
print("python3 scripts/realtime_signal_scanner.py --max-symbols 10 --no-telegram")
print("\n关键观察指标（日志中）:")
print("- M_meta['normalization_method'] = 'relative_historical'")
print("- M_meta['relative_slope_intensity'] = 相对强度值（如1.5x）")
print("- O_meta['normalization_method'] = 'relative_historical'")
print("- O_meta['relative_oi_intensity'] = 相对强度值（如2.0x）")
