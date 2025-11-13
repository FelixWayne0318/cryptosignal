#!/usr/bin/env python3
"""
系统全面诊断脚本
检测配置、硬编码、因子计算等问题

用法:
    python3 scripts/system_diagnostic.py
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class SystemDiagnostic:
    """系统诊断器"""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []

    def run_all_checks(self):
        """运行所有诊断检查"""
        print("=" * 80)
        print("🔍 CryptoSignal 系统全面诊断")
        print("=" * 80)
        print()

        # 1. 配置文件检查
        self.check_config_files()

        # 2. 硬编码检测
        self.check_hardcoded_values()

        # 3. I因子问题检测
        self.check_i_factor_issue()

        # 4. F因子问题检测
        self.check_f_factor_issue()

        # 5. 置信度计算检测
        self.check_confidence_calculation()

        # 6. 阈值配置检测
        self.check_threshold_config()

        # 7. 默认值一致性检测
        self.check_default_consistency()

        # 8. 模块导入检测
        self.check_module_imports()

        # 输出诊断报告
        self.print_report()

    def check_config_files(self):
        """检查配置文件完整性和一致性"""
        print("📋 1. 配置文件完整性检查")
        print("-" * 80)

        config_files = {
            "signal_thresholds.json": "config/signal_thresholds.json",
            "params.json": "config/params.json",
            "factors_unified.json": "config/factors_unified.json"
        }

        for name, path in config_files.items():
            if not os.path.exists(path):
                self.issues.append(f"❌ 配置文件缺失: {path}")
                continue

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.info.append(f"✅ {name} 存在且有效")

                # 检查关键字段
                if name == "signal_thresholds.json":
                    self._check_signal_thresholds(data)
                elif name == "params.json":
                    self._check_params(data)

            except json.JSONDecodeError as e:
                self.issues.append(f"❌ {name} JSON格式错误: {e}")
            except Exception as e:
                self.issues.append(f"❌ {name} 读取失败: {e}")

        # 检查配置冲突
        self._check_config_conflicts()
        print()

    def _check_signal_thresholds(self, data: Dict):
        """检查signal_thresholds.json内容"""
        required_sections = ["基础分析阈值", "FI调制器参数", "v72闸门阈值"]

        for section in required_sections:
            if section not in data:
                self.warnings.append(f"⚠️  signal_thresholds.json 缺少: {section}")

        # 检查FI调制器参数
        if "FI调制器参数" in data:
            fi_params = data["FI调制器参数"]
            if "p0_base" not in fi_params:
                self.issues.append("❌ FI调制器参数缺少 p0_base")
            else:
                p0 = fi_params["p0_base"]
                if p0 == 0.58:
                    self.issues.append(f"❌ p0_base={p0}，仍是硬编码值，应为0.45")
                elif p0 == 0.45:
                    self.info.append(f"✅ p0_base={p0} 正确")

        # 检查mature_coin阈值
        if "基础分析阈值" in data and "mature_coin" in data["基础分析阈值"]:
            mature = data["基础分析阈值"]["mature_coin"]
            checks = {
                "prime_prob_min": 0.45,
                "prime_strength_min": 35,
                "confidence_min": 20,
                "edge_min": 0.15
            }
            for key, expected in checks.items():
                if key in mature:
                    actual = mature[key]
                    if actual != expected:
                        self.warnings.append(
                            f"⚠️  {key}={actual}, 预期={expected}"
                        )
                else:
                    self.warnings.append(f"⚠️  缺少配置: {key}")

    def _check_params(self, data: Dict):
        """检查params.json内容"""
        # 检查new_coin配置
        if "new_coin" in data:
            new_coin = data["new_coin"]
            required_fields = [
                "ultra_new_prime_dim_threshold",
                "ultra_new_watch_prob_min",
                "phaseA_watch_prob_min",
                "phaseB_watch_prob_min"
            ]
            for field in required_fields:
                if field not in new_coin:
                    self.warnings.append(f"⚠️  params.json new_coin缺少: {field}")

    def _check_config_conflicts(self):
        """检查配置文件冲突"""
        try:
            # 检查prime_prob_min是否在多个文件中定义
            params_path = "config/params.json"
            signal_path = "config/signal_thresholds.json"

            if os.path.exists(params_path) and os.path.exists(signal_path):
                with open(params_path, 'r') as f:
                    params = json.load(f)
                with open(signal_path, 'r') as f:
                    signal = json.load(f)

                # 检查params.json中的publish配置
                if "publish" in params:
                    publish = params["publish"]
                    if "prime_prob_min" in publish:
                        params_prob = publish["prime_prob_min"]

                        # 检查signal_thresholds.json
                        if "基础分析阈值" in signal and "mature_coin" in signal["基础分析阈值"]:
                            signal_prob = signal["基础分析阈值"]["mature_coin"].get("prime_prob_min")

                            if params_prob != signal_prob:
                                self.issues.append(
                                    f"❌ 配置冲突: params.json prime_prob_min={params_prob} "
                                    f"vs signal_thresholds.json={signal_prob}"
                                )
        except Exception as e:
            self.warnings.append(f"⚠️  配置冲突检测失败: {e}")

    def check_hardcoded_values(self):
        """检测硬编码值"""
        print("🔍 2. 硬编码检测")
        print("-" * 80)

        hardcode_patterns = [
            # 概率阈值
            (r"if.*prob.*[<>=].*0\.[5-9][0-9]", "概率阈值硬编码"),
            (r"prime_prob.*=.*0\.[5-9][0-9]", "prime_prob硬编码"),
            (r"p0\s*=\s*0\.[5-9][0-9]", "p0硬编码"),
            # 强度阈值
            (r"strength.*[<>=].*[2-7][0-9](?![0-9])", "strength阈值硬编码"),
            (r"confidence.*[<>=].*[1-6][0-9](?![0-9])", "confidence阈值硬编码"),
            # 新币阈值
            (r"watch_prob_min\s*=\s*0\.[56][0-9]", "watch_prob_min硬编码"),
            (r"prime_dim_threshold\s*=\s*[67][0-9]", "prime_dim_threshold硬编码"),
        ]

        files_to_check = [
            "ats_core/pipeline/analyze_symbol.py",
            "ats_core/modulators/fi_modulators.py",
            "ats_core/config/threshold_config.py",
        ]

        import re

        found_issues = False
        for filepath in files_to_check:
            if not os.path.exists(filepath):
                continue

            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # 跳过注释
                if line.strip().startswith('#'):
                    continue

                for pattern, desc in hardcode_patterns:
                    if re.search(pattern, line):
                        # 排除config.get()的情况
                        if 'config.get' not in line and '.get(' not in line:
                            self.issues.append(
                                f"❌ {desc}: {filepath}:{i}\n   {line.strip()}"
                            )
                            found_issues = True

        if not found_issues:
            self.info.append("✅ 未发现明显的硬编码问题")
        print()

    def check_i_factor_issue(self):
        """检测I因子异常（所有值都是50.0）"""
        print("🔍 3. I因子计算检测")
        print("-" * 80)

        # 检查I因子计算代码
        i_factor_file = "ats_core/features/independence.py"
        if not os.path.exists(i_factor_file):
            self.warnings.append(f"⚠️  找不到I因子文件: {i_factor_file}")
            print()
            return

        with open(i_factor_file, 'r') as f:
            content = f.read()

        # 检查是否返回固定值50
        if 'return 50' in content or 'return 50.0' in content:
            self.issues.append(
                f"❌ I因子返回固定值50 ({i_factor_file})\n"
                "   这导致所有币种I因子都是50.0，没有分布"
            )

        # 检查是否有正确的计算逻辑
        if 'correlation' not in content.lower() and 'corr' not in content.lower():
            self.warnings.append(
                f"⚠️  I因子代码中缺少相关性计算逻辑"
            )

        # 检查analyze_symbol.py中的I因子调用
        analyze_file = "ats_core/pipeline/analyze_symbol.py"
        if os.path.exists(analyze_file):
            with open(analyze_file, 'r') as f:
                lines = f.readlines()

            # 查找I因子计算相关代码
            for i, line in enumerate(lines, 1):
                if 'calculate_independence' in line:
                    # 检查是否有双重映射
                    if i + 5 < len(lines):
                        context = ''.join(lines[i:i+5])
                        if '* 2 - 100' in context or '(I_score - 50) * 2' in context:
                            self.issues.append(
                                f"❌ I因子存在双重归一化 ({analyze_file}:{i})\n"
                                "   calculate_independence已返回±100，不应再映射"
                            )

        print()

    def check_f_factor_issue(self):
        """检测F因子异常（极值饱和）"""
        print("🔍 4. F因子计算检测")
        print("-" * 80)

        # 检查FI调制器配置
        try:
            with open("config/signal_thresholds.json", 'r') as f:
                config = json.load(f)

            if "FI调制器参数" in config:
                fi_params = config["FI调制器参数"]
                p0 = fi_params.get("p0_base")

                if p0 == 0.58:
                    self.issues.append(
                        "❌ FI调制器 p0_base=0.58 (硬编码值)\n"
                        "   应该是0.45，这会导致概率阈值过高"
                    )
                elif p0 != 0.45:
                    self.warnings.append(f"⚠️  p0_base={p0}, 预期0.45")
        except Exception as e:
            self.warnings.append(f"⚠️  无法检查FI调制器配置: {e}")

        # 检查F因子计算
        fund_leading_file = "ats_core/features/fund_leading.py"
        if os.path.exists(fund_leading_file):
            with open(fund_leading_file, 'r') as f:
                content = f.read()

            # 检查是否有tanh软化
            if 'tanh' in content:
                self.info.append("✅ F因子使用tanh软化，避免硬截断")
            else:
                self.warnings.append(
                    "⚠️  F因子未使用tanh软化，可能出现±100极值饱和"
                )

        print()

    def check_confidence_calculation(self):
        """检测置信度计算（中位数只有8）"""
        print("🔍 5. 置信度计算检测")
        print("-" * 80)

        analyze_file = "ats_core/pipeline/analyze_symbol.py"
        if not os.path.exists(analyze_file):
            self.warnings.append(f"⚠️  找不到: {analyze_file}")
            print()
            return

        with open(analyze_file, 'r') as f:
            content = f.read()

        # 检查置信度计算逻辑
        if 'confidence =' in content:
            self.info.append("✅ 存在置信度计算代码")

            # 检查是否受I因子影响
            if 'I_score' in content and 'confidence' in content:
                # I因子如果都是50，会严重影响置信度
                self.warnings.append(
                    "⚠️  置信度计算可能受I因子影响\n"
                    "   如果I因子都是50（中性），会降低置信度"
                )
        else:
            self.warnings.append("⚠️  未找到置信度计算代码")

        print()

    def check_threshold_config(self):
        """检查阈值配置是否合理"""
        print("🔍 6. 阈值配置检查")
        print("-" * 80)

        try:
            with open("config/signal_thresholds.json", 'r') as f:
                config = json.load(f)

            if "基础分析阈值" in config and "mature_coin" in config["基础分析阈值"]:
                mature = config["基础分析阈值"]["mature_coin"]

                # 检查关键阈值
                thresholds = {
                    "prime_prob_min": (0.40, 0.50, "Prime概率最小值"),
                    "prime_strength_min": (25, 40, "Prime强度最小值"),
                    "confidence_min": (15, 30, "置信度最小值"),
                    "edge_min": (0.10, 0.20, "Edge最小值"),
                }

                for key, (min_val, max_val, desc) in thresholds.items():
                    if key in mature:
                        val = mature[key]
                        if val < min_val or val > max_val:
                            self.warnings.append(
                                f"⚠️  {desc}: {val} (合理范围: {min_val}-{max_val})"
                            )
                        else:
                            self.info.append(f"✅ {desc}: {val} (合理)")
        except Exception as e:
            self.warnings.append(f"⚠️  阈值配置检查失败: {e}")

        print()

    def check_default_consistency(self):
        """检查默认值一致性"""
        print("🔍 7. 默认值一致性检查")
        print("-" * 80)

        try:
            # 读取signal_thresholds.json
            with open("config/signal_thresholds.json", 'r') as f:
                signal_config = json.load(f)

            # 读取threshold_config.py中的默认值
            threshold_config_file = "ats_core/config/threshold_config.py"
            if not os.path.exists(threshold_config_file):
                self.warnings.append(f"⚠️  找不到: {threshold_config_file}")
                print()
                return

            with open(threshold_config_file, 'r') as f:
                code_content = f.read()

            # 检查几个关键默认值
            if "基础分析阈值" in signal_config and "mature_coin" in signal_config["基础分析阈值"]:
                config_values = signal_config["基础分析阈值"]["mature_coin"]

                # 简单的模式匹配检查
                checks = [
                    ("prime_strength_min", 35),
                    ("confidence_min", 20),
                    ("edge_min", 0.15),
                    ("prime_prob_min", 0.45),
                ]

                for key, expected in checks:
                    if key in config_values:
                        config_val = config_values[key]

                        # 检查代码中是否有不一致的默认值
                        if isinstance(expected, float):
                            # 检查常见的错误默认值
                            wrong_values = [0.68, 0.48, 60, 54]
                            for wrong in wrong_values:
                                if f'"{key}": {wrong}' in code_content or f"'{key}': {wrong}" in code_content:
                                    self.issues.append(
                                        f"❌ 默认值不一致: {key}\n"
                                        f"   配置文件: {config_val}, 代码默认: {wrong}"
                                    )
                                    break
        except Exception as e:
            self.warnings.append(f"⚠️  默认值一致性检查失败: {e}")

        print()

    def check_module_imports(self):
        """检查模块导入是否正常"""
        print("🔍 8. 模块导入检查")
        print("-" * 80)

        critical_modules = [
            ("ats_core.features.independence", "I因子计算"),
            ("ats_core.features.fund_leading", "F因子计算"),
            ("ats_core.modulators.fi_modulators", "FI调制器"),
            ("ats_core.config.threshold_config", "阈值配置"),
        ]

        for module_name, desc in critical_modules:
            try:
                __import__(module_name)
                self.info.append(f"✅ {desc} 模块导入成功")
            except ImportError as e:
                self.issues.append(f"❌ {desc} 导入失败: {e}")
            except Exception as e:
                self.warnings.append(f"⚠️  {desc} 导入异常: {e}")

        print()

    def print_report(self):
        """输出诊断报告"""
        print()
        print("=" * 80)
        print("📊 诊断报告汇总")
        print("=" * 80)
        print()

        # 严重问题
        if self.issues:
            print(f"❌ 发现 {len(self.issues)} 个严重问题:")
            print("-" * 80)
            for issue in self.issues:
                print(issue)
                print()

        # 警告
        if self.warnings:
            print(f"⚠️  发现 {len(self.warnings)} 个警告:")
            print("-" * 80)
            for warning in self.warnings:
                print(warning)
            print()

        # 正常信息
        if self.info:
            print(f"✅ 正常检查 ({len(self.info)} 项):")
            print("-" * 80)
            for info in self.info:
                print(info)
            print()

        # 总结
        print("=" * 80)
        print("📋 诊断总结")
        print("=" * 80)
        total_issues = len(self.issues) + len(self.warnings)

        if total_issues == 0:
            print("✅ 系统配置正常，未发现问题")
        else:
            print(f"发现问题: {len(self.issues)} 个严重问题, {len(self.warnings)} 个警告")
            print()
            print("📌 建议优先修复的问题:")

            # 按优先级列出问题
            priority_issues = []

            # P0: I因子固定值50
            for issue in self.issues:
                if "I因子返回固定值50" in issue:
                    priority_issues.append(("P0", "I因子固定值50导致无分布", issue))

            # P0: 配置冲突
            for issue in self.issues:
                if "配置冲突" in issue:
                    priority_issues.append(("P0", "配置文件冲突", issue))

            # P1: 硬编码
            for issue in self.issues:
                if "硬编码" in issue:
                    priority_issues.append(("P1", "存在硬编码值", issue))

            # P1: 双重归一化
            for issue in self.issues:
                if "双重归一化" in issue:
                    priority_issues.append(("P1", "I因子双重归一化", issue))

            if priority_issues:
                for priority, title, detail in priority_issues[:5]:  # 只显示前5个
                    print(f"\n[{priority}] {title}")
                    print(f"    {detail.split(chr(10))[0]}")  # 只显示第一行

        print()
        print("=" * 80)

        # 返回退出码
        return 1 if self.issues else 0


def main():
    """主函数"""
    diagnostic = SystemDiagnostic()
    exit_code = diagnostic.run_all_checks()

    print("\n💡 提示: 请将诊断结果反馈给开发者进行修复")
    print("    诊断报告已完成\n")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
