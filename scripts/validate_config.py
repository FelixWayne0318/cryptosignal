#!/usr/bin/env python3
"""
配置文件格式校验脚本 - v7.3.2

**目的**: 解决P1-2问题 - 手动编辑JSON易出错，缺少格式校验

**功能**:
1. 校验JSON格式正确性（语法检查）
2. 校验必需字段存在性（关键配置文件）
3. 校验因子权重配置（6+4架构）
4. 提供清晰的错误提示

**使用方法**:
    # 校验所有配置文件
    python3 scripts/validate_config.py

    # 集成到Git pre-commit hook
    # .git/hooks/pre-commit
    #!/bin/bash
    python3 scripts/validate_config.py || exit 1

**退出码**:
- 0: 所有配置文件验证通过
- 1: 存在格式错误或必需字段缺失

版本: v7.3.2
作者: Claude Code
创建日期: 2025-11-15
参考: /tmp/revised_fix_plan.md#Phase2-4 (任务2.2)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 颜色代码（用于终端输出）
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color


def validate_json_format(file_path: Path) -> bool:
    """
    校验JSON文件格式

    Args:
        file_path: JSON文件路径

    Returns:
        bool: True表示格式正确，False表示格式错误
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"{GREEN}✅ {file_path.name}: JSON格式正确{NC}")
        return True
    except json.JSONDecodeError as e:
        print(f"{RED}❌ {file_path.name}: JSON格式错误{NC}")
        print(f"   错误详情: {e}")
        print(f"   位置: 行{e.lineno} 列{e.colno}")
        return False
    except FileNotFoundError:
        print(f"{RED}❌ {file_path.name}: 文件不存在{NC}")
        return False
    except Exception as e:
        print(f"{RED}❌ {file_path.name}: 读取失败{NC}")
        print(f"   错误: {e}")
        return False


def validate_required_keys(
    config: Dict[str, Any],
    required_keys: List[str],
    file_name: str
) -> bool:
    """
    校验配置文件必需字段

    Args:
        config: 配置字典
        required_keys: 必需字段列表
        file_name: 文件名（用于错误提示）

    Returns:
        bool: True表示所有必需字段存在，False表示缺失字段
    """
    missing = [k for k in required_keys if k not in config]
    if missing:
        print(f"{RED}❌ {file_name}: 缺少必需字段{NC}")
        print(f"   缺失字段: {', '.join(missing)}")
        print(f"   期望字段: {', '.join(required_keys)}")
        return False
    return True


def validate_weights(weights: Dict[str, float], file_name: str) -> bool:
    """
    校验因子权重配置（6+4架构）

    Args:
        weights: 权重配置字典
        file_name: 文件名（用于错误提示）

    Returns:
        bool: True表示权重配置正确，False表示配置错误
    """
    # v7.3.2架构定义
    core_factors = ['T', 'M', 'C', 'V', 'O', 'B']  # A层：6个核心因子，总权重100%
    modulators = ['L', 'S', 'F', 'I']              # B层：4个调制器，权重0%

    all_valid = True

    # 检查核心因子
    missing_core = [f for f in core_factors if f not in weights]
    if missing_core:
        print(f"{RED}❌ {file_name}: 缺少核心因子权重{NC}")
        print(f"   缺失因子: {', '.join(missing_core)}")
        print(f"   期望核心因子(6): T, M, C, V, O, B")
        all_valid = False

    # 检查调制器
    missing_mod = [m for m in modulators if m not in weights]
    if missing_mod:
        print(f"{RED}❌ {file_name}: 缺少调制器权重{NC}")
        print(f"   缺失调制器: {', '.join(missing_mod)}")
        print(f"   期望调制器(4): L, S, F, I")
        all_valid = False

    if not all_valid:
        return False

    # 计算核心因子权重总和
    try:
        core_weights = {k: weights[k] for k in core_factors}
        core_total = sum(core_weights.values())

        # 容差0.01%
        if abs(core_total - 100.0) > 0.01:
            print(f"{RED}❌ {file_name}: 核心因子权重总和错误{NC}")
            print(f"   当前总和: {core_total}%")
            print(f"   期望总和: 100.0%")
            print(f"   核心因子权重: {core_weights}")
            all_valid = False
    except (TypeError, KeyError) as e:
        print(f"{RED}❌ {file_name}: 核心因子权重值格式错误{NC}")
        print(f"   错误: {e}")
        all_valid = False

    # 检查调制器权重必须为0%
    try:
        modulator_weights = {k: weights[k] for k in modulators}
        for mod, wt in modulator_weights.items():
            if abs(wt) > 0.01:
                print(f"{RED}❌ {file_name}: 调制器 {mod} 权重错误{NC}")
                print(f"   当前值: {wt}%")
                print(f"   期望值: 0.0%")
                print(f"   说明: 调制器不参与评分，权重必须为0")
                all_valid = False
    except (TypeError, KeyError) as e:
        print(f"{RED}❌ {file_name}: 调制器权重值格式错误{NC}")
        print(f"   错误: {e}")
        all_valid = False

    return all_valid


def main():
    """主函数：校验所有配置文件"""
    print("==========================================")
    print("🔍 CryptoSignal 配置文件校验")
    print("==========================================")
    print()

    # 获取配置目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    config_dir = project_root / "config"

    if not config_dir.exists():
        print(f"{RED}❌ 配置目录不存在: {config_dir}{NC}")
        sys.exit(1)

    print(f"配置目录: {config_dir}")
    print()

    all_valid = True
    validated_count = 0

    # ========== 第1步: 校验所有JSON文件格式 ==========
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("第1步: 校验JSON格式")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    json_files = list(config_dir.glob("*.json"))
    if not json_files:
        print(f"{YELLOW}⚠️  配置目录中没有JSON文件{NC}")

    for json_file in json_files:
        if not validate_json_format(json_file):
            all_valid = False
        validated_count += 1

    print()

    # ========== 第2步: 校验关键文件必需字段 ==========
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("第2步: 校验必需字段")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # 2.1 params.json
    params_file = config_dir / "params.json"
    if params_file.exists():
        try:
            with open(params_file, 'r', encoding='utf-8') as f:
                params = json.load(f)

            required = ["weights", "trend", "overlay"]
            if validate_required_keys(params, required, "params.json"):
                print(f"{GREEN}✅ params.json: 必需字段完整{NC}")

                # 额外校验：权重配置（6+4架构）
                if 'weights' in params:
                    if validate_weights(params['weights'], "params.json"):
                        print(f"{GREEN}✅ params.json: 权重配置符合6+4架构{NC}")
                    else:
                        all_valid = False
            else:
                all_valid = False
        except Exception as e:
            print(f"{RED}❌ params.json: 读取失败 - {e}{NC}")
            all_valid = False
    else:
        print(f"{YELLOW}⚠️  params.json: 文件不存在{NC}")

    # 2.2 signal_thresholds.json
    thresholds_file = config_dir / "signal_thresholds.json"
    if thresholds_file.exists():
        try:
            with open(thresholds_file, 'r', encoding='utf-8') as f:
                thresholds = json.load(f)

            # v7.2+ 阈值结构
            required = ["v72闸门阈值"]
            if validate_required_keys(thresholds, required, "signal_thresholds.json"):
                print(f"{GREEN}✅ signal_thresholds.json: 必需字段完整{NC}")
            else:
                all_valid = False
        except Exception as e:
            print(f"{RED}❌ signal_thresholds.json: 读取失败 - {e}{NC}")
            all_valid = False
    else:
        print(f"{YELLOW}⚠️  signal_thresholds.json: 文件不存在（可选）{NC}")

    # 2.3 factors_unified.json
    factors_file = config_dir / "factors_unified.json"
    if factors_file.exists():
        try:
            with open(factors_file, 'r', encoding='utf-8') as f:
                factors = json.load(f)

            required = ["factors"]
            if validate_required_keys(factors, required, "factors_unified.json"):
                print(f"{GREEN}✅ factors_unified.json: 必需字段完整{NC}")
            else:
                all_valid = False
        except Exception as e:
            print(f"{RED}❌ factors_unified.json: 读取失败 - {e}{NC}")
            all_valid = False
    else:
        print(f"{YELLOW}⚠️  factors_unified.json: 文件不存在（可选）{NC}")

    # 2.4 numeric_stability.json
    stability_file = config_dir / "numeric_stability.json"
    if stability_file.exists():
        try:
            with open(stability_file, 'r', encoding='utf-8') as f:
                stability = json.load(f)

            required = ["numeric_stability"]
            if validate_required_keys(stability, required, "numeric_stability.json"):
                print(f"{GREEN}✅ numeric_stability.json: 必需字段完整{NC}")
            else:
                all_valid = False
        except Exception as e:
            print(f"{RED}❌ numeric_stability.json: 读取失败 - {e}{NC}")
            all_valid = False
    else:
        print(f"{YELLOW}⚠️  numeric_stability.json: 文件不存在（可选）{NC}")

    print()

    # ========== 总结 ==========
    print("==========================================")
    print("📊 校验结果")
    print("==========================================")
    print()
    print(f"总文件数: {validated_count}")

    if all_valid:
        print(f"{GREEN}✅ 所有配置文件验证通过！{NC}")
        print()
        sys.exit(0)
    else:
        print(f"{RED}❌ 存在配置错误，请修复后重试{NC}")
        print()
        print("常见问题：")
        print("  1. JSON语法错误: 检查括号、逗号、引号是否正确")
        print("  2. 缺少必需字段: 参考上述错误信息添加缺失字段")
        print("  3. 权重配置错误: 确保核心因子总权重=100%，调制器权重=0%")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
