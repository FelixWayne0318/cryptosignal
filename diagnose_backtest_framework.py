#!/usr/bin/env python3
# coding: utf-8
"""
CryptoSignal 回测框架全面诊断工具

功能：
1. 检测HTTP 403 API认证问题
2. 检测API调用速率限制风险
3. 检测四步系统集成问题
4. 检测配置完整性
5. 检测K线格式兼容性
6. 提供详细修复建议

使用方法：
    python3 diagnose_backtest_framework.py

输出：
    - 详细诊断报告（终端）
    - 问题清单（JSON文件）
    - 修复建议（Markdown文件）
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI颜色
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'  # No Color


class BacktestDiagnostic:
    """回测框架诊断器"""

    def __init__(self):
        self.root = Path(__file__).parent
        self.issues = []
        self.warnings = []
        self.info = []

    def run(self):
        """运行完整诊断"""
        print(f"\n{'='*70}")
        print(f"🔍 CryptoSignal 回测框架诊断工具")
        print(f"{'='*70}\n")

        # 1. 环境检查
        self.check_environment()

        # 2. API认证逻辑检查
        self.check_api_auth_logic()

        # 3. 回测引擎集成检查
        self.check_backtest_engine()

        # 4. 四步系统集成检查
        self.check_four_step_integration()

        # 5. 配置完整性检查
        self.check_configuration()

        # 6. K线格式兼容性检查
        self.check_kline_compatibility()

        # 7. API调用优化检查
        self.check_api_optimization()

        # 8. 生成报告
        self.generate_report()

    def check_environment(self):
        """检查环境变量"""
        print(f"{BLUE}[1/7] 环境变量检查{NC}")
        print("-" * 70)

        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")

        if api_key or api_secret:
            self.issues.append({
                "id": "ENV-001",
                "severity": "P0",
                "title": "回测不应设置BINANCE_API_KEY环境变量",
                "description": "检测到BINANCE_API_KEY环境变量，这会导致HTTP 403错误",
                "reason": "公开API端点（如/fapi/v1/klines）不需要认证，发送空认证头会被拒绝",
                "fix": "执行: unset BINANCE_API_KEY && unset BINANCE_API_SECRET"
            })
            print(f"  {RED}✗ BINANCE_API_KEY已设置 → 会导致HTTP 403错误{NC}")
        else:
            print(f"  {GREEN}✓ BINANCE_API_KEY未设置（正确）{NC}")

        print()

    def check_api_auth_logic(self):
        """检查API认证逻辑"""
        print(f"{BLUE}[2/7] API认证逻辑检查{NC}")
        print("-" * 70)

        binance_file = self.root / "ats_core/sources/binance.py"
        if not binance_file.exists():
            self.issues.append({
                "id": "API-001",
                "severity": "P0",
                "title": "binance.py文件缺失",
                "description": f"找不到文件: {binance_file}"
            })
            print(f"  {RED}✗ binance.py文件缺失{NC}\n")
            return

        content = binance_file.read_text(encoding='utf-8')

        # 检查_get_signed函数
        if '"X-MBX-APIKEY": API_KEY' in content:
            # 检查是否有条件判断
            pattern = r'if\s+API_KEY\s*:.*"X-MBX-APIKEY"'
            if not re.search(pattern, content, re.DOTALL):
                self.issues.append({
                    "id": "API-002",
                    "severity": "P0",
                    "title": "API认证头无条件发送（导致HTTP 403）",
                    "description": "_get_signed函数中，无论API_KEY是否为空都发送X-MBX-APIKEY头",
                    "location": "ats_core/sources/binance.py:99-109",
                    "reason": "发送空的X-MBX-APIKEY头会触发Binance 403 Forbidden",
                    "fix": "在发送认证头前检查API_KEY是否存在"
                })
                print(f"  {RED}✗ API认证头逻辑错误 → HTTP 403根因{NC}")
            else:
                print(f"  {GREEN}✓ API认证头有条件检查{NC}")
        else:
            print(f"  {YELLOW}? 未找到API认证头代码{NC}")

        print()

    def check_backtest_engine(self):
        """检查回测引擎集成"""
        print(f"{BLUE}[3/7] 回测引擎集成检查{NC}")
        print("-" * 70)

        engine_file = self.root / "ats_core/backtest/engine.py"
        if not engine_file.exists():
            self.issues.append({
                "id": "ENGINE-001",
                "severity": "P0",
                "title": "engine.py文件缺失"
            })
            print(f"  {RED}✗ engine.py文件缺失{NC}\n")
            return

        content = engine_file.read_text(encoding='utf-8')

        # 检查1: BTC K线加载
        if 'load_btc_klines' in content:
            print(f"  {GREEN}✓ 包含BTC K线加载逻辑{NC}")
        else:
            self.issues.append({
                "id": "ENGINE-002",
                "severity": "P0",
                "title": "回测引擎未加载BTC K线",
                "description": "四步系统Step1需要BTC K线进行对齐检测，但引擎未加载",
                "location": "ats_core/backtest/engine.py:~310",
                "impact": "Step1的BTC对齐检测无法工作，信号质量下降",
                "fix": "在主循环中添加btc_klines加载并传递给analyze_symbol"
            })
            print(f"  {RED}✗ 未加载BTC K线 → Step1对齐检测失败{NC}")

        # 检查2: 四步系统决策判定
        if 'four_step_decision' in content and 'ACCEPT' in content:
            print(f"  {GREEN}✓ 包含四步系统决策判定{NC}")
        else:
            self.issues.append({
                "id": "ENGINE-003",
                "severity": "P0",
                "title": "信号判定逻辑未适配四步系统",
                "description": "仍使用is_prime判定信号，未检查four_step_decision结果",
                "location": "ats_core/backtest/engine.py:343-346",
                "impact": "fusion_mode启用时，可能使用错误的决策结果",
                "fix": "根据配置选择四步系统或旧系统的决策字段"
            })
            print(f"  {RED}✗ 信号判定逻辑未适配四步系统{NC}")

        # 检查3: 价格提取逻辑
        if 'step3' in content and 'entry_price' in content:
            print(f"  {GREEN}✓ 包含四步系统价格提取{NC}")
        else:
            self.issues.append({
                "id": "ENGINE-004",
                "severity": "P1",
                "title": "价格提取逻辑未适配四步系统",
                "description": "未从four_step_decision.step3提取Entry/SL/TP价格",
                "location": "ats_core/backtest/engine.py:354-357",
                "impact": "四步系统启用时使用错误的价格，回测结果偏差",
                "fix": "根据配置从step3或pricing字段提取价格"
            })
            print(f"  {YELLOW}⚠ 价格提取逻辑未适配四步系统{NC}")

        print()

    def check_four_step_integration(self):
        """检查四步系统集成"""
        print(f"{BLUE}[4/7] 四步系统集成检查{NC}")
        print("-" * 70)

        analyze_file = self.root / "ats_core/pipeline/analyze_symbol.py"
        if not analyze_file.exists():
            print(f"  {RED}✗ analyze_symbol.py文件缺失{NC}\n")
            return

        content = analyze_file.read_text(encoding='utf-8')

        # 检查1: _get_kline_field兼容函数
        if '_get_kline_field' in content:
            print(f"  {GREEN}✓ K线格式兼容函数存在{NC}")
        else:
            self.issues.append({
                "id": "INTEGRATE-001",
                "severity": "P0",
                "title": "缺少K线格式兼容函数",
                "description": "_get_kline_field函数缺失，无法兼容字典和列表格式"
            })
            print(f"  {RED}✗ 缺少_get_kline_field函数{NC}")

        # 检查2: 四步系统调用
        if 'run_four_step_decision' in content:
            print(f"  {GREEN}✓ 包含四步系统调用{NC}")
        else:
            self.warnings.append({
                "id": "INTEGRATE-002",
                "severity": "P1",
                "title": "可能缺少四步系统调用",
                "description": "未在analyze_symbol中找到run_four_step_decision调用"
            })
            print(f"  {YELLOW}⚠ 未找到四步系统调用（可能已集成到其他位置）{NC}")

        print()

    def check_configuration(self):
        """检查配置完整性"""
        print(f"{BLUE}[5/7] 配置完整性检查{NC}")
        print("-" * 70)

        config_file = self.root / "config/params.json"
        if not config_file.exists():
            self.issues.append({
                "id": "CONFIG-001",
                "severity": "P0",
                "title": "config/params.json缺失"
            })
            print(f"  {RED}✗ params.json文件缺失{NC}\n")
            return

        try:
            config = json.loads(config_file.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            self.issues.append({
                "id": "CONFIG-002",
                "severity": "P0",
                "title": "config/params.json格式错误",
                "description": str(e)
            })
            print(f"  {RED}✗ JSON格式错误: {e}{NC}\n")
            return

        # 检查回测配置
        if 'backtest' not in config:
            self.issues.append({
                "id": "CONFIG-003",
                "severity": "P0",
                "title": "缺少backtest配置块"
            })
            print(f"  {RED}✗ 缺少backtest配置块{NC}")
        else:
            print(f"  {GREEN}✓ backtest配置块存在{NC}")

            # 检查data_loader配置
            if 'data_loader' in config['backtest']:
                print(f"  {GREEN}✓ data_loader配置存在{NC}")
            else:
                self.warnings.append({
                    "id": "CONFIG-004",
                    "severity": "P2",
                    "title": "缺少data_loader配置"
                })
                print(f"  {YELLOW}⚠ 缺少data_loader配置{NC}")

            # 检查engine配置
            if 'engine' in config['backtest']:
                engine_cfg = config['backtest']['engine']

                # 检查v1.5 P0修复参数
                required = ['max_entry_bars', 'taker_fee_rate', 'slippage_percent']
                missing = [k for k in required if k not in engine_cfg]
                if missing:
                    self.warnings.append({
                        "id": "CONFIG-005",
                        "severity": "P1",
                        "title": "缺少v1.5 P0修复参数",
                        "description": f"缺少参数: {', '.join(missing)}"
                    })
                    print(f"  {YELLOW}⚠ 缺少v1.5参数: {', '.join(missing)}{NC}")
                else:
                    print(f"  {GREEN}✓ v1.5 P0修复参数完整{NC}")
            else:
                self.warnings.append({
                    "id": "CONFIG-006",
                    "severity": "P1",
                    "title": "缺少engine配置"
                })
                print(f"  {YELLOW}⚠ 缺少engine配置{NC}")

        # 检查四步系统配置
        if 'four_step_system' not in config:
            self.warnings.append({
                "id": "CONFIG-007",
                "severity": "P2",
                "title": "缺少four_step_system配置",
                "description": "回测时无法启用/禁用四步系统"
            })
            print(f"  {YELLOW}⚠ 缺少four_step_system配置{NC}")
        else:
            four_step = config['four_step_system']
            enabled = four_step.get('enabled', False)
            fusion = four_step.get('fusion_mode', {}).get('enabled', False)
            print(f"  {GREEN}✓ four_step_system配置存在{NC}")
            print(f"    - enabled: {enabled}")
            print(f"    - fusion_mode.enabled: {fusion}")

            if enabled and fusion:
                self.info.append({
                    "id": "INFO-001",
                    "title": "四步系统融合模式已启用",
                    "description": "回测将使用四步系统决策"
                })

        print()

    def check_kline_compatibility(self):
        """检查K线格式兼容性"""
        print(f"{BLUE}[6/7] K线格式兼容性检查{NC}")
        print("-" * 70)

        analyze_file = self.root / "ats_core/pipeline/analyze_symbol.py"
        if not analyze_file.exists():
            print(f"  {RED}✗ analyze_symbol.py文件缺失{NC}\n")
            return

        content = analyze_file.read_text(encoding='utf-8')

        # 检查OHLCV字段提取
        issues_found = []
        patterns = [
            (r'\br\[2\]', 'high字段硬编码索引'),
            (r'\br\[3\]', 'low字段硬编码索引'),
            (r'\br\[4\]', 'close字段硬编码索引'),
            (r'\br\[5\]', 'volume字段硬编码索引'),
            (r'\br\[7\]', 'quote_volume字段硬编码索引'),
        ]

        for pattern, desc in patterns:
            if re.search(pattern, content):
                # 检查附近是否有_get_kline_field
                # 简化检查：如果有硬编码索引但也有_get_kline_field，认为可能已修复
                if '_get_kline_field' not in content:
                    issues_found.append(desc)

        if issues_found:
            self.issues.append({
                "id": "COMPAT-001",
                "severity": "P0",
                "title": "存在硬编码K线索引访问",
                "description": f"发现{len(issues_found)}处硬编码索引: " + ", ".join(issues_found),
                "location": "ats_core/pipeline/analyze_symbol.py",
                "impact": "字典格式K线会导致KeyError崩溃",
                "fix": "使用_get_kline_field()替代所有硬编码索引访问"
            })
            print(f"  {RED}✗ 存在{len(issues_found)}处硬编码索引{NC}")
            for desc in issues_found:
                print(f"    - {desc}")
        else:
            print(f"  {GREEN}✓ 未发现硬编码K线索引访问{NC}")

        print()

    def check_api_optimization(self):
        """检查API调用优化"""
        print(f"{BLUE}[7/7] API调用优化检查{NC}")
        print("-" * 70)

        engine_file = self.root / "ats_core/backtest/engine.py"
        if not engine_file.exists():
            print(f"  {RED}✗ engine.py文件缺失{NC}\n")
            return

        content = engine_file.read_text(encoding='utf-8')

        # 检查重复API调用
        load_klines_count = len(re.findall(r'self\.data_loader\.load_klines\(', content))

        if load_klines_count > 2:
            self.issues.append({
                "id": "OPTIM-001",
                "severity": "P0",
                "title": "存在重复API调用",
                "description": f"发现{load_klines_count}处load_klines调用",
                "location": "ats_core/backtest/engine.py",
                "impact": "每小时重复加载K线，可能触发速率限制或IP封禁",
                "reason": "限价单检查和头寸监控都会重新加载K线",
                "fix": "实现K线缓存机制，在主循环开始时批量加载"
            })
            print(f"  {RED}✗ 发现{load_klines_count}处load_klines调用 → 速率限制风险{NC}")
        else:
            print(f"  {GREEN}✓ API调用次数合理（{load_klines_count}处）{NC}")

        # 检查是否有缓存机制
        if 'klines_cache' in content or 'current_klines_cache' in content:
            print(f"  {GREEN}✓ 存在K线缓存机制{NC}")
        else:
            self.warnings.append({
                "id": "OPTIM-002",
                "severity": "P1",
                "title": "缺少K线缓存机制",
                "description": "建议在主循环中实现批量加载和缓存"
            })
            print(f"  {YELLOW}⚠ 缺少K线缓存机制{NC}")

        print()

    def generate_report(self):
        """生成诊断报告"""
        print(f"\n{'='*70}")
        print(f"📊 诊断报告")
        print(f"{'='*70}\n")

        # 统计
        p0_count = len([i for i in self.issues if i.get('severity') == 'P0'])
        p1_count = len([i for i in self.issues if i.get('severity') == 'P1'])
        p2_count = len([i for i in self.issues if i.get('severity') == 'P2'])
        warning_count = len(self.warnings)

        print(f"问题统计:")
        print(f"  {RED}P0 (Critical): {p0_count}个{NC}")
        print(f"  {YELLOW}P1 (High): {p1_count}个{NC}")
        print(f"  {YELLOW}P2 (Medium): {p2_count}个{NC}")
        print(f"  {BLUE}警告: {warning_count}个{NC}")
        print()

        # P0问题列表
        if p0_count > 0:
            print(f"{RED}【P0级严重问题】必须立即修复：{NC}")
            print("-" * 70)
            for issue in self.issues:
                if issue.get('severity') == 'P0':
                    print(f"\n{RED}▸ [{issue['id']}] {issue['title']}{NC}")
                    print(f"  描述: {issue.get('description', 'N/A')}")
                    if 'location' in issue:
                        print(f"  位置: {issue['location']}")
                    if 'impact' in issue:
                        print(f"  影响: {issue['impact']}")
                    if 'reason' in issue:
                        print(f"  原因: {issue['reason']}")
                    if 'fix' in issue:
                        print(f"  {GREEN}修复: {issue['fix']}{NC}")
            print()

        # P1问题列表
        if p1_count > 0:
            print(f"{YELLOW}【P1级问题】建议优先修复：{NC}")
            print("-" * 70)
            for issue in self.issues:
                if issue.get('severity') == 'P1':
                    print(f"\n{YELLOW}▸ [{issue['id']}] {issue['title']}{NC}")
                    print(f"  描述: {issue.get('description', 'N/A')}")
                    if 'fix' in issue:
                        print(f"  {GREEN}修复: {issue['fix']}{NC}")
            print()

        # 修复建议
        print(f"{GREEN}【修复建议】{NC}")
        print("-" * 70)

        if p0_count > 0:
            print("\n第一步：立即修复P0问题（预计1-2小时）")
            print("  1. 取消API认证环境变量:")
            print("     unset BINANCE_API_KEY")
            print("     unset BINANCE_API_SECRET")
            print()
            print("  2. 修复binance.py API认证逻辑:")
            print("     在ats_core/sources/binance.py的_get_signed函数中")
            print("     添加API_KEY存在性检查")
            print()
            print("  3. 修复回测引擎集成:")
            print("     - 添加BTC K线加载")
            print("     - 实现K线缓存机制")
            print("     - 适配四步系统决策和价格提取")
            print()

        print("\n第二步：验证修复（预计30分钟）")
        print("  运行短期回测验证:")
        print("  python3 scripts/backtest_four_step.py \\")
        print("      --symbols ETHUSDT \\")
        print("      --start 2024-11-01 \\")
        print("      --end 2024-11-03 \\")
        print("      --output reports/test_backtest.json")
        print()

        # 保存报告
        report_data = {
            "timestamp": "2025-11-18",
            "summary": {
                "p0_issues": p0_count,
                "p1_issues": p1_count,
                "p2_issues": p2_count,
                "warnings": warning_count
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info
        }

        report_file = self.root / "diagnose/backtest_diagnostic_report.json"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding='utf-8')

        print(f"\n详细报告已保存: {report_file}")
        print(f"{'='*70}\n")

        # 返回状态码
        if p0_count > 0:
            return 1  # 有P0问题
        elif p1_count > 0:
            return 2  # 有P1问题
        else:
            return 0  # 正常


def main():
    """主函数"""
    diagnostic = BacktestDiagnostic()
    exit_code = diagnostic.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
