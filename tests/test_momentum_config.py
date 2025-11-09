#!/usr/bin/env python
# coding: utf-8
"""
M因子配置系统测试

验证v3.0配置管理系统是否正常工作
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.features.momentum import score_momentum


def test_momentum_with_config():
    """测试M因子使用配置系统"""
    print("=" * 60)
    print("M因子配置系统测试")
    print("=" * 60)

    # 准备测试数据（30个数据点）
    test_h = [100 + i * 0.5 for i in range(30)]
    test_l = [99 + i * 0.5 for i in range(30)]
    test_c = [99.5 + i * 0.5 for i in range(30)]

    print("\n[测试1] 使用配置文件参数")
    print("-" * 60)
    try:
        M, meta = score_momentum(test_h, test_l, test_c)
        print(f"✅ M分数: {M}")
        print(f"   斜率分数: {meta.get('slope_score')}")
        print(f"   加速度分数: {meta.get('accel_score')}")
        print(f"   归一化方法: {meta.get('normalization_method')}")
        print(f"   EMA配置: {meta.get('ema_config')}")
        print(f"   解释: {meta.get('interpretation')}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n[测试2] 传入自定义params（向后兼容测试）")
    print("-" * 60)
    try:
        custom_params = {
            "ema_fast": 5,
            "ema_slow": 10,
            "slope_scale": 3.0
        }
        M, meta = score_momentum(test_h, test_l, test_c, params=custom_params)
        print(f"✅ M分数: {M}")
        print(f"   EMA配置: {meta.get('ema_config')}")
        print(f"   （应该显示EMA5/10，而非配置文件的EMA3/5）")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n[测试3] 数据不足测试（数据质量检查）")
    print("-" * 60)
    try:
        short_h = [100, 101, 102]
        short_l = [99, 100, 101]
        short_c = [99.5, 100.5, 101.5]
        M, meta = score_momentum(short_h, short_l, short_c)
        print(f"✅ M分数: {M} (应该为0)")
        print(f"   降级原因: {meta.get('degradation_reason')}")
        print(f"   最小数据点要求: {meta.get('min_data_required')}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n[测试4] 验证配置文件加载")
    print("-" * 60)
    try:
        from ats_core.config.factor_config import get_factor_config

        config = get_factor_config()

        # 获取M因子配置
        m_params = config.get_factor_params("M")
        print(f"✅ M因子参数:")
        print(f"   ema_fast: {m_params.get('ema_fast')}")
        print(f"   ema_slow: {m_params.get('ema_slow')}")
        print(f"   slope_lookback: {m_params.get('slope_lookback')}")
        print(f"   slope_scale: {m_params.get('slope_scale')}")

        # 获取StandardizationChain配置
        std_params = config.get_standardization_params("M")
        print(f"\n✅ StandardizationChain参数:")
        print(f"   alpha: {std_params.get('alpha')}")
        print(f"   tau: {std_params.get('tau')}")
        print(f"   z0: {std_params.get('z0')}")

        # 获取数据质量阈值
        min_data = config.get_data_quality_threshold("M", "min_data_points")
        print(f"\n✅ 数据质量阈值:")
        print(f"   min_data_points: {min_data}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_momentum_with_config()
