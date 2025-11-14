#!/usr/bin/env python3
# coding: utf-8
"""
CryptoSignal v7.2 - Claude Project 导入分析工具

分析整个仓库，识别：
1. 核心文件（必须导入Claude Project）
2. 辅助文件（只需要知道接口）
3. 文件依赖关系
4. 模块接口规范
"""

from pathlib import Path
import ast
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class ClaudeProjectAnalyzer:
    """分析仓库，生成Claude Project导入指南"""

    def __init__(self, root_dir: str = None):
        if root_dir is None:
            script_path = Path(__file__).resolve()
            self.root_dir = script_path.parent
        else:
            self.root_dir = Path(root_dir)

        # 核心文件分类
        self.core_files = []  # 必须导入
        self.interface_files = []  # 只需要知道接口
        self.config_files = []  # 配置文件

        # 统计信息
        self.file_stats = defaultdict(dict)

    def analyze_file_size(self, file_path: Path) -> Tuple[int, int]:
        """分析文件大小和行数"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = len(content.splitlines())
            size_kb = file_path.stat().st_size / 1024
            return lines, size_kb
        except:
            return 0, 0

    def extract_public_api(self, file_path: Path) -> List[str]:
        """提取文件的公共API（函数、类）"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))

            public_api = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):
                        # 获取函数签名
                        args = [arg.arg for arg in node.args.args]
                        public_api.append(f"def {node.name}({', '.join(args)})")
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith('_'):
                        public_api.append(f"class {node.name}")

            return public_api
        except:
            return []

    def classify_files(self):
        """分类所有Python文件"""
        all_py_files = sorted(self.root_dir.glob('**/*.py'))

        # 核心入口文件
        entry_files = [
            'setup.sh',
            'scripts/realtime_signal_scanner.py',
            'scripts/batch_scan_test.py'
        ]

        # 核心配置层（必须理解）
        core_config = [
            'ats_core/cfg.py',
            'ats_core/config/threshold_config.py',
            'ats_core/config/factor_config.py',
            'ats_core/config/anti_jitter_config.py'
        ]

        # 核心流程层（必须理解）
        core_pipeline = [
            'ats_core/pipeline/analyze_symbol.py',
            'ats_core/pipeline/analyze_symbol_v72.py',
            'ats_core/pipeline/batch_scan_optimized.py'
        ]

        # 核心输出层（必须理解）
        core_output = [
            'ats_core/outputs/telegram_fmt.py',
            'ats_core/publishing/anti_jitter.py'
        ]

        # 核心数据层（必须理解）
        core_data = [
            'ats_core/data/analysis_db.py',
            'ats_core/data/trade_recorder.py'
        ]

        # 辅助模块（只需要知道接口）
        interface_modules = {
            'features': 'ats_core/features',
            'sources': 'ats_core/sources',
            'scoring': 'ats_core/scoring',
            'factors_v2': 'ats_core/factors_v2',
            'calibration': 'ats_core/calibration',
            'utils': 'ats_core/utils',
            'modulators': 'ats_core/modulators',
            'execution': 'ats_core/execution',
            'analysis': 'ats_core/analysis'
        }

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔍 分析所有Python文件...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()

        for py_file in all_py_files:
            rel_path = py_file.relative_to(self.root_dir)
            rel_path_str = str(rel_path)

            # 跳过分析工具本身
            if 'analyze_dependencies' in rel_path_str or 'analyze_for_claude' in rel_path_str:
                continue

            lines, size_kb = self.analyze_file_size(py_file)

            # 分类文件
            is_core = False
            category = "其他"

            if rel_path_str in core_config:
                self.core_files.append((rel_path_str, '核心配置', lines, size_kb))
                is_core = True
                category = "核心配置"
            elif rel_path_str in core_pipeline:
                self.core_files.append((rel_path_str, '核心流程', lines, size_kb))
                is_core = True
                category = "核心流程"
            elif rel_path_str in core_output:
                self.core_files.append((rel_path_str, '核心输出', lines, size_kb))
                is_core = True
                category = "核心输出"
            elif rel_path_str in core_data:
                self.core_files.append((rel_path_str, '核心数据', lines, size_kb))
                is_core = True
                category = "核心数据"
            elif rel_path_str.startswith('ats_core/logging'):
                self.core_files.append((rel_path_str, '核心工具', lines, size_kb))
                is_core = True
                category = "核心工具"
            else:
                # 检查是否属于辅助模块
                for module_name, module_path in interface_modules.items():
                    if rel_path_str.startswith(module_path):
                        api = self.extract_public_api(py_file)
                        self.interface_files.append((rel_path_str, module_name, lines, size_kb, api))
                        category = f"接口模块-{module_name}"
                        break

            self.file_stats[rel_path_str] = {
                'lines': lines,
                'size_kb': size_kb,
                'is_core': is_core,
                'category': category
            }

        print(f"  ✓ 分析了 {len(all_py_files)} 个Python文件")
        print(f"  ✓ 核心文件: {len(self.core_files)} 个")
        print(f"  ✓ 接口文件: {len(self.interface_files)} 个")
        print()

    def generate_report(self) -> str:
        """生成Claude Project导入指南"""
        report = []

        report.append("# CryptoSignal v7.2 - Claude Project 导入指南")
        report.append("")
        report.append("生成时间：2025-11-14")
        report.append("")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("## 📋 导入策略")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("")
        report.append("### 🎯 核心理念")
        report.append("- **核心文件**：必须完整导入Claude Project，需要深入理解和修改")
        report.append("- **接口文件**：只需要知道函数签名和返回值，无需导入完整代码")
        report.append("- **配置文件**：导入JSON配置文件，理解参数含义")
        report.append("")
        report.append("### 📊 统计")
        total_lines = sum(info['lines'] for info in self.file_stats.values())
        total_size = sum(info['size_kb'] for info in self.file_stats.values())
        core_lines = sum(item[2] for item in self.core_files)
        core_size = sum(item[3] for item in self.core_files)

        report.append(f"- **仓库总计**：{len(self.file_stats)} 个Python文件，{total_lines:,} 行代码，{total_size:.1f}KB")
        report.append(f"- **核心文件**：{len(self.core_files)} 个文件，{core_lines:,} 行代码，{core_size:.1f}KB")
        report.append(f"- **压缩率**：{core_lines/total_lines*100:.1f}% 的代码量，覆盖 100% 的功能理解")
        report.append("")

        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("## ⭐ 第一部分：核心文件（必须导入）")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("")
        report.append("这些文件是系统的骨架，必须完整理解：")
        report.append("")

        # 按类别分组核心文件
        core_by_category = defaultdict(list)
        for file_path, category, lines, size_kb in self.core_files:
            core_by_category[category].append((file_path, lines, size_kb))

        for category in ['核心配置', '核心流程', '核心输出', '核心数据', '核心工具']:
            if category in core_by_category:
                report.append(f"### {category}")
                report.append("")
                for file_path, lines, size_kb in core_by_category[category]:
                    report.append(f"- `{file_path}` ({lines} 行, {size_kb:.1f}KB)")
                report.append("")

        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("## 📚 第二部分：接口模块（只需要知道API）")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("")
        report.append("这些模块的实现细节可以不导入，只需要在Claude Project中记录接口规范：")
        report.append("")

        # 按模块分组接口文件
        interface_by_module = defaultdict(list)
        for file_path, module_name, lines, size_kb, api in self.interface_files:
            interface_by_module[module_name].append((file_path, lines, size_kb, api))

        for module_name in sorted(interface_by_module.keys()):
            files = interface_by_module[module_name]
            total_module_lines = sum(item[1] for item in files)
            total_module_size = sum(item[2] for item in files)

            report.append(f"### {module_name.upper()} 模块")
            report.append("")
            report.append(f"**统计**：{len(files)} 个文件，{total_module_lines:,} 行代码，{total_module_size:.1f}KB")
            report.append("")

            for file_path, lines, size_kb, api in files[:3]:  # 只显示前3个主要文件
                report.append(f"#### `{file_path}`")
                report.append("")
                if api:
                    report.append("**主要API**：")
                    for api_item in api[:5]:  # 只显示前5个API
                        report.append(f"- `{api_item}`")
                    if len(api) > 5:
                        report.append(f"- ... 还有 {len(api)-5} 个API")
                else:
                    report.append("（内部实现细节）")
                report.append("")

            if len(files) > 3:
                report.append(f"... 还有 {len(files)-3} 个文件")
                report.append("")

        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("## 🔗 第三部分：模块接口规范")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("")
        report.append("在Claude Project中，只需要记录这些模块的接口约定：")
        report.append("")

        report.append("### 1. Features模块（因子计算）")
        report.append("```python")
        report.append("# 接口规范：所有因子计算函数返回 float 或 Dict[str, float]")
        report.append("from ats_core.features.trend import analyze_trend")
        report.append("from ats_core.features.momentum import calc_momentum")
        report.append("from ats_core.features.liquidity import calc_liquidity_score")
        report.append("")
        report.append("# 示例：")
        report.append("trend_score = analyze_trend(klines)  # 返回 Dict[str, float]")
        report.append("momentum = calc_momentum(klines)      # 返回 float")
        report.append("```")
        report.append("")

        report.append("### 2. Sources模块（数据源）")
        report.append("```python")
        report.append("# 接口规范：获取市场数据")
        report.append("from ats_core.sources.klines import get_klines")
        report.append("from ats_core.sources.oi import fetch_oi_history")
        report.append("")
        report.append("# 示例：")
        report.append("klines = get_klines(symbol, interval, limit)  # 返回 List[Dict]")
        report.append("oi_data = fetch_oi_history(symbol)             # 返回 List[float]")
        report.append("```")
        report.append("")

        report.append("### 3. Scoring模块（评分系统）")
        report.append("```python")
        report.append("# 接口规范：标准化和评分")
        report.append("from ats_core.scoring.scoring_utils import StandardizationChain")
        report.append("")
        report.append("# 示例：")
        report.append("chain = StandardizationChain()")
        report.append("normalized = chain.standardize(value, method='robust')  # 返回 float")
        report.append("```")
        report.append("")

        report.append("### 4. Factors_v2模块（v7.2因子）")
        report.append("```python")
        report.append("# 接口规范：v7.2版本的因子计算")
        report.append("from ats_core.factors_v2.funding_v2 import calc_F_v2")
        report.append("")
        report.append("# 示例：")
        report.append("F_score = calc_F_v2(funding_rate, oi_change)  # 返回 float")
        report.append("```")
        report.append("")

        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("## 🎯 第四部分：Claude Project 导入清单")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("")
        report.append("### 必须导入的文件（按优先级）")
        report.append("")
        report.append("#### 第一优先级：理解系统入口和主流程")
        report.append("```")
        report.append("scripts/realtime_signal_scanner.py   # 主入口")
        report.append("ats_core/pipeline/analyze_symbol.py  # 核心分析流程")
        report.append("ats_core/pipeline/analyze_symbol_v72.py  # v7.2增强")
        report.append("```")
        report.append("")

        report.append("#### 第二优先级：理解配置和阈值")
        report.append("```")
        report.append("config/signal_thresholds.json        # 信号阈值配置")
        report.append("config/factor_weights.json           # 因子权重配置")
        report.append("ats_core/config/threshold_config.py  # 阈值读取")
        report.append("ats_core/config/factor_config.py     # 因子配置")
        report.append("```")
        report.append("")

        report.append("#### 第三优先级：理解输出和发布")
        report.append("```")
        report.append("ats_core/outputs/telegram_fmt.py     # Telegram格式化")
        report.append("ats_core/publishing/anti_jitter.py   # 防抖动")
        report.append("```")
        report.append("")

        report.append("#### 第四优先级：理解数据存储")
        report.append("```")
        report.append("ats_core/data/analysis_db.py         # 分析结果数据库")
        report.append("ats_core/data/trade_recorder.py      # 交易记录")
        report.append("```")
        report.append("")

        report.append("### 只需要记录接口的模块")
        report.append("")
        report.append("创建一个 `INTERFACES.md` 文件，记录以下模块的接口规范：")
        report.append("")
        report.append("```markdown")
        report.append("# CryptoSignal 模块接口规范")
        report.append("")
        report.append("## Features模块")
        report.append("- `analyze_trend(klines) -> Dict[str, float]`")
        report.append("- `calc_momentum(klines) -> float`")
        report.append("- `calc_liquidity_score(volume, trades) -> float`")
        report.append("")
        report.append("## Sources模块")
        report.append("- `get_klines(symbol, interval, limit) -> List[Dict]`")
        report.append("- `fetch_oi_history(symbol) -> List[float]`")
        report.append("")
        report.append("## Scoring模块")
        report.append("- `StandardizationChain.standardize(value, method) -> float`")
        report.append("```")
        report.append("")

        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("## 🚀 第五部分：使用建议")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("")
        report.append("### 在Claude Project中的工作流程")
        report.append("")
        report.append("1. **导入核心文件**（约15个文件，3000-4000行代码）")
        report.append("   - 完整理解系统架构和主流程")
        report.append("   - 可以修改配置、阈值、流程逻辑")
        report.append("")
        report.append("2. **创建接口文档** `INTERFACES.md`")
        report.append("   - 记录所有辅助模块的API")
        report.append("   - 无需导入实现细节（节省tokens）")
        report.append("")
        report.append("3. **修改代码时**")
        report.append("   - 修改核心文件：直接在Claude Project中修改")
        report.append("   - 修改接口文件：回到仓库修改，然后更新 `INTERFACES.md`")
        report.append("")
        report.append("4. **理解系统运行**")
        report.append("   - 主入口 → 批量扫描 → 单币分析 → v7.2增强 → 输出格式化")
        report.append("   - 配置层控制所有阈值和权重")
        report.append("   - 辅助模块提供计算能力（只需要知道输入输出）")
        report.append("")

        report.append("### 优势")
        report.append("")
        report.append(f"- ✅ **Token使用减少 {100-core_lines/total_lines*100:.0f}%**")
        report.append("- ✅ **聚焦核心逻辑**，避免陷入实现细节")
        report.append("- ✅ **快速定位问题**，所有关键代码都在Claude Project中")
        report.append("- ✅ **接口清晰**，模块之间的调用关系一目了然")
        report.append("")

        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("## 📝 附录：完整文件清单")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append("")

        report.append("### 核心文件详细列表")
        report.append("")
        for file_path, category, lines, size_kb in sorted(self.core_files, key=lambda x: x[1]):
            report.append(f"- `{file_path}` - {category} ({lines} 行, {size_kb:.1f}KB)")
        report.append("")

        report.append(f"**核心文件总计**：{len(self.core_files)} 个文件，{core_lines:,} 行代码")
        report.append("")

        return "\n".join(report)

    def run(self):
        """执行完整分析"""
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🚀 CryptoSignal v7.2 - Claude Project 导入分析")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()

        # 分类文件
        self.classify_files()

        # 生成报告
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📝 生成导入指南...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()

        report = self.generate_report()

        # 保存报告
        report_path = self.root_dir / 'CLAUDE_PROJECT_IMPORT_GUIDE.md'
        report_path.write_text(report, encoding='utf-8')

        print(f"✅ 导入指南已保存到: {report_path}")
        print()

        # 输出摘要
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📊 分析摘要")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()

        total_lines = sum(info['lines'] for info in self.file_stats.values())
        core_lines = sum(item[2] for item in self.core_files)

        print(f"  📁 仓库文件数: {len(self.file_stats)} 个")
        print(f"  📄 仓库总行数: {total_lines:,} 行")
        print()
        print(f"  ⭐ 核心文件数: {len(self.core_files)} 个")
        print(f"  ⭐ 核心代码行: {core_lines:,} 行")
        print()
        print(f"  📚 接口文件数: {len(self.interface_files)} 个")
        print(f"  📚 接口代码行: {total_lines - core_lines:,} 行")
        print()
        print(f"  🎯 压缩率: {core_lines/total_lines*100:.1f}% （导入核心文件即可理解全系统）")
        print()

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ 分析完成")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()
        print("📖 请查看: CLAUDE_PROJECT_IMPORT_GUIDE.md")
        print()

if __name__ == '__main__':
    analyzer = ClaudeProjectAnalyzer()
    analyzer.run()
