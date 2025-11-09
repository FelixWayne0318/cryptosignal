#!/bin/bash
# P0修复脚本：重新启用并优化StandardizationChain

echo "🔧 P0修复：重新启用StandardizationChain（参数已优化）"
echo "修复文件："

# 修复cvd_flow.py
echo "- cvd_flow.py"
sed -i '29s/.*/# P0修复（2025-11-09）：使用新参数（alpha=0.25, tau=5.0, z0=3.0）/' ats_core/features/cvd_flow.py
sed -i '30s/.*/_cvd_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5)/' ats_core/features/cvd_flow.py
sed -i 's/# ⚠️ 2025-11-04紧急修复：禁用StandardizationChain.*/# ✅ P0修复（2025-11-09）：重新启用StandardizationChain（参数已优化）/' ats_core/features/cvd_flow.py
sed -i 's/# C_pub, diagnostics = _cvd_chain.standardize(C_raw)/C_pub, diagnostics = _cvd_chain.standardize(C_raw)/' ats_core/features/cvd_flow.py
sed -i '/C_pub = max(-100, min(100, C_raw))/d' ats_core/features/cvd_flow.py

# 修复open_interest.py
echo "- open_interest.py"
sed -i 's/_oi_chain = StandardizationChain(alpha=0.15, tau=3.0/_oi_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0/' ats_core/features/open_interest.py
sed -i 's/# ⚠️ 2025-11-04紧急修复.*/ # ✅ P0修复（2025-11-09）：重新启用StandardizationChain（参数已优化）/' ats_core/features/open_interest.py
sed -i 's/# O_pub, diagnostics = _oi_chain.standardize(O_raw)/O_pub, diagnostics = _oi_chain.standardize(O_raw)/' ats_core/features/open_interest.py
sed -i '/O_pub = max(-100, min(100, O_raw))/d' ats_core/features/open_interest.py

# 修复trend.py
echo "- trend.py"
sed -i 's/_trend_chain = StandardizationChain(alpha=0.15, tau=3.0/_trend_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0/' ats_core/features/trend.py
sed -i 's/# ⚠️ 2025-11-04紧急修复.*/# ✅ P0修复（2025-11-09）：重新启用StandardizationChain（参数已优化）/' ats_core/features/trend.py
sed -i 's/# T_pub, diagnostics = _trend_chain.standardize(T_raw)/T_pub, diagnostics = _trend_chain.standardize(T_raw)/' ats_core/features/trend.py
sed -i '/T_pub = max(-100, min(100, T_raw))/d' ats_core/features/trend.py

# 修复structure_sq.py
echo "- structure_sq.py"
sed -i 's/_structure_chain = StandardizationChain(alpha=0.15, tau=3.0/_structure_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0/' ats_core/features/structure_sq.py

# 修复fund_leading.py
echo "- fund_leading.py"
sed -i 's/_fund_chain = StandardizationChain(alpha=0.15, tau=3.0/_fund_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0/' ats_core/features/fund_leading.py

echo "✅ P0修复完成！"
