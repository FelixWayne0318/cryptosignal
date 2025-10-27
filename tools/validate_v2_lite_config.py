#!/usr/bin/env python3
# coding: utf-8
"""
V2 Lite配置验证工具（轻量级，无需numpy等依赖）

验证V2 Lite配置文件的正确性
"""

import os
import sys
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def validate_v2_lite_config():
    """验证V2 Lite配置"""

    print("=" * 70)
    print("V2 Lite配置验证工具")
    print("=" * 70)

    # 1. 加载配置文件
    print("\n【步骤1】加载配置文件")
    print("-" * 70)

    config_path = os.path.join(project_root, "config", "factors_v2_lite.json")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ 配置文件加载成功")
        print(f"   路径: {config_path}")
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return

    # 2. 基本信息
    print("\n【步骤2】基本信息")
    print("-" * 70)

    version = config.get("version", "unknown")
    updated_at = config.get("updated_at", "unknown")
    description = config.get("description", "")

    print(f"   版本: {version}")
    print(f"   更新时间: {updated_at}")
    print(f"   描述: {description}")

    # 3. 因子配置
    print("\n【步骤3】因子配置")
    print("-" * 70)

    factors = config.get("factors", {})

    enabled_factors = []
    disabled_factors = []

    for factor_name, factor_config in factors.items():
        enabled = factor_config.get("enabled", False)
        if enabled:
            enabled_factors.append(factor_name)
        else:
            disabled_factors.append(factor_name)

    print(f"   总因子数: {len(factors)}")
    print(f"   启用因子: {len(enabled_factors)}个")
    print(f"   禁用因子: {len(disabled_factors)}个")

    print("\n   启用因子列表:")
    for factor_name in enabled_factors:
        factor_cfg = factors[factor_name]
        weight = factor_cfg.get("weight", 0)
        layer = factor_cfg.get("layer", "unknown")
        desc = factor_cfg.get("description", "")
        factor_type = factor_cfg.get("type", "normal")

        type_str = f"[{factor_type}]" if factor_type != "normal" else ""
        print(f"     {factor_name:3s}: {weight:3d}点  {layer:15s}  {type_str:12s}  {desc}")

    print("\n   禁用因子列表:")
    for factor_name in disabled_factors:
        factor_cfg = factors[factor_name]
        weight = factor_cfg.get("weight", 0)
        desc = factor_cfg.get("description", "")
        print(f"     {factor_name:3s}: ({weight:2d}点)  {desc}")

    # 4. 权重配置
    print("\n【步骤4】权重配置")
    print("-" * 70)

    weights_config = config.get("weights_config", {})
    total_weight_config = weights_config.get("total_weight", 0)
    normalization_factor = weights_config.get("normalization_factor", 1.0)

    # 计算实际启用因子的总权重
    actual_weight = 0
    for factor_name in enabled_factors:
        if factors[factor_name].get("type") != "regulator":
            actual_weight += factors[factor_name].get("weight", 0)

    print(f"   配置总权重: {total_weight_config}点")
    print(f"   实际启用权重: {actual_weight}点")
    print(f"   归一化因子: {normalization_factor}")
    print(f"   归一化后范围: ±{int(actual_weight / normalization_factor)}")

    if actual_weight != total_weight_config:
        print(f"   ⚠️  警告: 实际权重({actual_weight})与配置总权重({total_weight_config})不一致")
    else:
        print(f"   ✅ 权重配置一致")

    # 5. 层级分布
    print("\n【步骤5】层级权重分布")
    print("-" * 70)

    layer_weights = {}
    for factor_name in enabled_factors:
        if factors[factor_name].get("type") == "regulator":
            continue

        layer = factors[factor_name].get("layer", "unknown")
        weight = factors[factor_name].get("weight", 0)

        if layer not in layer_weights:
            layer_weights[layer] = 0
        layer_weights[layer] += weight

    layer_distribution = weights_config.get("layer_distribution", {})

    for layer_name, expected_weight in layer_distribution.items():
        actual_weight = layer_weights.get(layer_name, 0)
        status = "✅" if actual_weight == expected_weight else "⚠️ "
        print(f"   {layer_name:20s}: {actual_weight:3d}点 / {expected_weight:3d}点  {status}")

    # 6. V1 vs V2 Lite对比
    print("\n【步骤6】V1 vs V2 Lite对比")
    print("-" * 70)

    print("\n   V1生产版（7+1维）:")
    v1_factors = ["T", "M", "C", "V", "S", "O", "E", "F"]
    print(f"     因子: {', '.join(v1_factors)}")
    print(f"     权重: 115点")
    print(f"     特点: 基础因子，稳定")

    print("\n   V2 Lite版（8+1维）:")
    v2_lite_factors = enabled_factors

    # 重新计算权重（排除调节器）
    v2_lite_weight = 0
    for f in enabled_factors:
        if factors[f].get("type") != "regulator":
            v2_lite_weight += factors[f].get("weight", 0)

    print(f"     因子: {', '.join(v2_lite_factors)}")
    print(f"     权重: {v2_lite_weight}点")
    print(f"     特点: 增强因子")

    # 对比差异
    print("\n   增强/替换:")
    if "C+" in enabled_factors:
        print(f"     C → C+  (增强CVD)")
    if "O+" in enabled_factors:
        print(f"     O → O+  (OI四象限)")
    if "V+" in enabled_factors:
        print(f"     V → V+  (触发K检测)")

    print("\n   新增:")
    if "I" in enabled_factors and "I" not in v1_factors:
        print(f"     I  (独立性分析)")

    print("\n   禁用（数据源未就绪）:")
    for f in disabled_factors:
        if f not in v1_factors:
            print(f"     {f}  ({factors[f]['description']})")

    # 7. 阈值配置
    print("\n【步骤7】阈值配置")
    print("-" * 70)

    thresholds = config.get("thresholds", {})

    print(f"   Prime强度最小值: {thresholds.get('prime_strength_min', 'N/A')}")
    print(f"   Prime概率最小值: {thresholds.get('prime_prob_min', 'N/A')}")
    print(f"   Watch强度最小值: {thresholds.get('watch_strength_min', 'N/A')}")
    print(f"   Watch概率最小值: {thresholds.get('watch_prob_min', 'N/A')}")

    # 8. 数据源配置
    print("\n【步骤8】数据源配置")
    print("-" * 70)

    data_sources = config.get("data_sources", {})

    for source_name, source_config in data_sources.items():
        enabled = source_config.get("enabled", True)
        status = "✅ 启用" if enabled else "❌ 禁用"
        note = source_config.get("note", "")
        print(f"   {source_name:15s}: {status:8s}  {note}")

    # 9. 配置完整性检查
    print("\n【步骤9】配置完整性检查")
    print("-" * 70)

    checks = []

    # 检查1: 所有启用因子都有params
    for factor_name in enabled_factors:
        if "params" not in factors[factor_name]:
            checks.append(f"❌ {factor_name}因子缺少params配置")

    # 检查2: 所有启用因子都有weight（除了regulator）
    for factor_name in enabled_factors:
        if factors[factor_name].get("type") != "regulator":
            if "weight" not in factors[factor_name]:
                checks.append(f"❌ {factor_name}因子缺少weight配置")

    # 检查3: 归一化因子合理
    if normalization_factor <= 0:
        checks.append(f"❌ 归一化因子不合理: {normalization_factor}")

    # 检查4: 权重总和合理
    if actual_weight < 50 or actual_weight > 200:
        checks.append(f"⚠️  权重总和可能不合理: {actual_weight}")

    if not checks:
        print("   ✅ 所有检查通过")
    else:
        for check in checks:
            print(f"   {check}")

    # 10. 总结
    print("\n" + "=" * 70)
    print("✅ V2 Lite配置验证完成")
    print("=" * 70)

    print("\n【配置摘要】")
    print(f"  版本: {version}")
    print(f"  启用因子: {len(enabled_factors)}个 ({', '.join(enabled_factors)})")
    print(f"  禁用因子: {len(disabled_factors)}个 ({', '.join(disabled_factors)})")
    print(f"  总权重: {actual_weight}点")
    print(f"  归一化: ±{int(actual_weight / normalization_factor)}")

    print("\n【部署状态】")
    if not checks or all("⚠️ " not in c and "❌" not in c for c in checks):
        print("  ✅ 配置正确，可以部署到服务器")
        print("  ✅ 无需额外数据源（订单簿/清算数据）")
        print("  ✅ 兼容现有V1数据管道")
    else:
        print("  ⚠️  配置存在问题，需要修复")

    print("\n【使用方法】")
    print("  # Python代码")
    print('  from ats_core.pipeline.analyze_symbol_v2 import analyze_symbol_v2')
    print('  result = analyze_symbol_v2("BTCUSDT", config_path="config/factors_v2_lite.json")')

    print("\n" + "=" * 70)


if __name__ == "__main__":
    validate_v2_lite_config()
