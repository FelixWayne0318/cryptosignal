#!/usr/bin/env python3
"""
依赖分析工具 - 从setup.sh递归分析所有文件依赖关系
生成txt格式报告，适合发送到电报群

用途：
1. 分析setup.sh引用的所有文件
2. 递归分析Python文件的import依赖
3. 识别未使用的文件
4. 输出依赖关系树和文件列表

作者：Claude Code
版本：v1.0
"""

import os
import re
import json
import ast
from pathlib import Path
from collections import defaultdict
from typing import Set, Dict, List, Tuple

class DependencyAnalyzer:
    """依赖分析器"""

    def __init__(self, root_dir: str = "/home/user/cryptosignal"):
        self.root_dir = Path(root_dir)
        self.analyzed_files = set()
        self.dependencies = defaultdict(set)  # file -> set of dependencies
        self.reverse_deps = defaultdict(set)  # file -> set of files that depend on it
        self.errors = []

        # 忽略的目录和文件
        self.ignore_dirs = {
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            '.venv', 'venv', 'env', 'build', 'dist', '*.egg-info'
        }
        self.ignore_files = {
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib'
        }

    def should_ignore(self, path: Path) -> bool:
        """判断是否应该忽略该路径"""
        # 忽略的目录
        for part in path.parts:
            if part in self.ignore_dirs or part.startswith('.'):
                return True

        # 忽略的文件扩展名
        if path.suffix in self.ignore_files:
            return True

        return False

    def extract_python_imports(self, file_path: Path) -> Set[str]:
        """提取Python文件的import语句"""
        imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用AST解析（更准确）
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
            except SyntaxError:
                # AST解析失败，使用正则表达式
                import_patterns = [
                    r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)',
                    r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import',
                ]
                for pattern in import_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        module = match.group(1).split('.')[0]
                        imports.add(module)

        except Exception as e:
            self.errors.append(f"解析{file_path}失败: {e}")

        return imports

    def extract_bash_references(self, file_path: Path) -> Set[str]:
        """提取Bash脚本中引用的文件"""
        references = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 匹配文件路径引用
            patterns = [
                r'python3?\s+([a-zA-Z0-9_/\.]+\.py)',  # python3 script.py
                r'source\s+([a-zA-Z0-9_/\.]+)',  # source file
                r'\.\s+([a-zA-Z0-9_/\.]+)',  # . file
                r'cat\s+([a-zA-Z0-9_/\.]+)',  # cat file
                r'[\"\']([^\"\']*\.(json|txt|md|py|sh))[\"\']',  # "file.ext"
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    ref = match.group(1)
                    if not ref.startswith('/'):
                        references.add(ref)

        except Exception as e:
            self.errors.append(f"解析{file_path}失败: {e}")

        return references

    def resolve_import_to_file(self, import_name: str) -> List[Path]:
        """将import名称解析为文件路径"""
        files = []

        # ats_core模块
        if import_name.startswith('ats_core') or import_name == 'ats_core':
            module_parts = import_name.split('.')
            module_path = '/'.join(module_parts)
            possible_paths = [
                self.root_dir / module_path / '__init__.py',
                self.root_dir / (module_path + '.py'),
            ]
            for path in possible_paths:
                if path.exists():
                    files.append(path)

        # scripts模块
        elif import_name == 'scripts':
            files.append(self.root_dir / 'scripts')

        return files

    def analyze_python_file(self, file_path: Path):
        """分析Python文件的依赖"""
        if file_path in self.analyzed_files:
            return

        self.analyzed_files.add(file_path)

        imports = self.extract_python_imports(file_path)

        for imp in imports:
            # 只分析项目内的模块
            if imp in ['ats_core', 'scripts'] or imp.startswith('ats_core.'):
                resolved_files = self.resolve_import_to_file(imp)
                for dep_file in resolved_files:
                    if dep_file.exists():
                        rel_path = dep_file.relative_to(self.root_dir)
                        self.dependencies[str(file_path.relative_to(self.root_dir))].add(str(rel_path))
                        self.reverse_deps[str(rel_path)].add(str(file_path.relative_to(self.root_dir)))

                        # 递归分析依赖
                        if dep_file.suffix == '.py' and dep_file not in self.analyzed_files:
                            self.analyze_python_file(dep_file)

    def analyze_bash_file(self, file_path: Path):
        """分析Bash脚本的依赖"""
        if file_path in self.analyzed_files:
            return

        self.analyzed_files.add(file_path)

        references = self.extract_bash_references(file_path)

        for ref in references:
            ref_path = self.root_dir / ref
            if ref_path.exists():
                rel_path = ref_path.relative_to(self.root_dir)
                self.dependencies[str(file_path.relative_to(self.root_dir))].add(str(rel_path))
                self.reverse_deps[str(rel_path)].add(str(file_path.relative_to(self.root_dir)))

                # 递归分析Python文件
                if ref_path.suffix == '.py':
                    self.analyze_python_file(ref_path)

    def scan_all_files(self) -> Dict[str, List[Path]]:
        """扫描所有文件并分类"""
        file_categories = {
            'python': [],
            'bash': [],
            'config': [],
            'docs': [],
            'tests': [],
            'others': []
        }

        for path in self.root_dir.rglob('*'):
            if path.is_file() and not self.should_ignore(path):
                rel_path = path.relative_to(self.root_dir)

                if path.suffix == '.py':
                    if 'test' in str(path).lower():
                        file_categories['tests'].append(path)
                    else:
                        file_categories['python'].append(path)
                elif path.suffix in ['.sh', '.bash']:
                    file_categories['bash'].append(path)
                elif path.suffix in ['.json', '.yaml', '.yml', '.toml', '.ini']:
                    file_categories['config'].append(path)
                elif path.suffix in ['.md', '.txt', '.rst']:
                    file_categories['docs'].append(path)
                else:
                    file_categories['others'].append(path)

        return file_categories

    def find_unused_files(self, all_files: Set[Path]) -> Set[Path]:
        """查找未被引用的文件"""
        used_files = set()

        # 从setup.sh开始的所有依赖
        for file_str in self.analyzed_files:
            if isinstance(file_str, Path):
                used_files.add(file_str)
            else:
                used_files.add(self.root_dir / file_str)

        # 从reverse_deps中获取所有被引用的文件
        for dep_str in self.reverse_deps.keys():
            used_files.add(self.root_dir / dep_str)

        # 未使用的文件 = 所有文件 - 使用的文件
        unused = all_files - used_files

        return unused

    def generate_report(self) -> str:
        """生成文本格式的分析报告"""
        lines = []

        lines.append("=" * 70)
        lines.append("CryptoSignal v7.2 依赖分析报告")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"分析根目录: {self.root_dir}")
        lines.append(f"分析时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 1. 文件分类统计
        lines.append("-" * 70)
        lines.append("📊 文件分类统计")
        lines.append("-" * 70)

        file_categories = self.scan_all_files()
        total_files = sum(len(files) for files in file_categories.values())

        for category, files in sorted(file_categories.items()):
            count = len(files)
            percentage = (count / total_files * 100) if total_files > 0 else 0
            lines.append(f"  {category:12s}: {count:4d} 个文件 ({percentage:5.1f}%)")

        lines.append(f"  {'总计':12s}: {total_files:4d} 个文件")
        lines.append("")

        # 2. 核心入口文件
        lines.append("-" * 70)
        lines.append("🚀 核心入口文件")
        lines.append("-" * 70)

        entry_files = [
            'setup.sh',
            'auto_restart.sh',
            'deploy_and_run.sh',
            'start_live.sh',
            'scripts/realtime_signal_scanner.py',
            'scripts/init_databases.py'
        ]

        for entry in entry_files:
            entry_path = self.root_dir / entry
            if entry_path.exists():
                size = entry_path.stat().st_size
                lines.append(f"  ✓ {entry:45s} ({size:7,d} bytes)")
            else:
                lines.append(f"  ✗ {entry:45s} (不存在)")

        lines.append("")

        # 3. 依赖关系统计
        lines.append("-" * 70)
        lines.append("🔗 依赖关系统计")
        lines.append("-" * 70)

        lines.append(f"  已分析文件: {len(self.analyzed_files)} 个")
        lines.append(f"  依赖关系: {sum(len(deps) for deps in self.dependencies.values())} 条")
        lines.append("")

        # 被引用最多的文件 (Top 20)
        lines.append("  📌 被引用最多的文件 (Top 20):")
        lines.append("")

        sorted_by_refs = sorted(
            self.reverse_deps.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:20]

        for i, (file_str, referrers) in enumerate(sorted_by_refs, 1):
            lines.append(f"    {i:2d}. {file_str:50s} ({len(referrers)} 次引用)")

        lines.append("")

        # 4. 目录结构分析
        lines.append("-" * 70)
        lines.append("📁 目录结构分析")
        lines.append("-" * 70)

        # 统计每个目录的文件数量
        dir_stats = defaultdict(int)
        all_py_files = file_categories['python'] + file_categories['tests']

        for file in all_py_files:
            rel_path = file.relative_to(self.root_dir)
            if len(rel_path.parts) > 1:
                top_dir = rel_path.parts[0]
                dir_stats[top_dir] += 1

        lines.append("")
        for dir_name, count in sorted(dir_stats.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {dir_name:30s}: {count:4d} 个Python文件")

        lines.append("")

        # 5. ats_core模块结构
        lines.append("-" * 70)
        lines.append("🔧 ats_core 模块结构")
        lines.append("-" * 70)

        ats_core_path = self.root_dir / 'ats_core'
        if ats_core_path.exists():
            subdirs = [d for d in ats_core_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

            for subdir in sorted(subdirs):
                py_files = list(subdir.glob('*.py'))
                py_files = [f for f in py_files if f.name != '__init__.py']
                lines.append(f"  ats_core/{subdir.name:20s}: {len(py_files):3d} 个模块")

        lines.append("")

        # 6. 配置文件列表
        lines.append("-" * 70)
        lines.append("⚙️  配置文件列表")
        lines.append("-" * 70)

        config_files = sorted(file_categories['config'])
        for cfg_file in config_files:
            rel_path = cfg_file.relative_to(self.root_dir)
            size = cfg_file.stat().st_size
            lines.append(f"  {str(rel_path):50s} ({size:7,d} bytes)")

        lines.append("")

        # 7. 文档文件列表
        lines.append("-" * 70)
        lines.append("📚 文档文件列表")
        lines.append("-" * 70)

        # 按目录分组
        doc_by_dir = defaultdict(list)
        for doc_file in file_categories['docs']:
            rel_path = doc_file.relative_to(self.root_dir)
            parent = str(rel_path.parent) if rel_path.parent != Path('.') else '根目录'
            doc_by_dir[parent].append(rel_path.name)

        for dir_name in sorted(doc_by_dir.keys()):
            lines.append(f"  {dir_name}:")
            for doc_name in sorted(doc_by_dir[dir_name]):
                lines.append(f"    - {doc_name}")
            lines.append("")

        # 8. 测试文件列表
        lines.append("-" * 70)
        lines.append("🧪 测试文件列表")
        lines.append("-" * 70)

        test_files = sorted(file_categories['tests'])
        if test_files:
            for test_file in test_files:
                rel_path = test_file.relative_to(self.root_dir)
                lines.append(f"  {str(rel_path)}")
        else:
            lines.append("  (无测试文件)")

        lines.append("")

        # 9. 脚本文件列表
        lines.append("-" * 70)
        lines.append("📜 Bash脚本列表")
        lines.append("-" * 70)

        bash_files = sorted(file_categories['bash'])
        for bash_file in bash_files:
            rel_path = bash_file.relative_to(self.root_dir)
            size = bash_file.stat().st_size
            # 检查是否可执行
            is_executable = os.access(bash_file, os.X_OK)
            exec_mark = "✓" if is_executable else "✗"
            lines.append(f"  {exec_mark} {str(rel_path):45s} ({size:7,d} bytes)")

        lines.append("")

        # 10. 关键依赖链
        lines.append("-" * 70)
        lines.append("🔍 关键依赖链 (setup.sh → realtime_signal_scanner.py)")
        lines.append("-" * 70)

        lines.append("")
        lines.append("  setup.sh")
        lines.append("    ├─→ requirements.txt (Python依赖)")
        lines.append("    ├─→ config/binance_credentials.json (交易所配置)")
        lines.append("    ├─→ config/telegram.json (通知配置)")
        lines.append("    ├─→ scripts/init_databases.py (数据库初始化)")
        lines.append("    └─→ scripts/realtime_signal_scanner.py (主扫描器)")
        lines.append("          ├─→ ats_core.cfg (全局配置)")
        lines.append("          ├─→ ats_core.pipeline.analyze_symbol (基础分析)")
        lines.append("          ├─→ ats_core.pipeline.analyze_symbol_v72 (v7.2增强)")
        lines.append("          ├─→ ats_core.outputs.telegram_fmt (Telegram格式化)")
        lines.append("          ├─→ ats_core.sources.binance_futures_client (数据源)")
        lines.append("          └─→ config/signal_thresholds.json (信号阈值)")
        lines.append("")

        # 11. 错误和警告
        if self.errors:
            lines.append("-" * 70)
            lines.append("⚠️  错误和警告")
            lines.append("-" * 70)

            for error in self.errors[:20]:  # 最多显示20个错误
                lines.append(f"  - {error}")

            if len(self.errors) > 20:
                lines.append(f"  ... 还有 {len(self.errors) - 20} 个错误未显示")

            lines.append("")

        # 12. 总结
        lines.append("=" * 70)
        lines.append("📋 分析总结")
        lines.append("=" * 70)

        lines.append(f"  ✓ 总文件数: {total_files} 个")
        lines.append(f"  ✓ Python文件: {len(file_categories['python'])} 个")
        lines.append(f"  ✓ 测试文件: {len(file_categories['tests'])} 个")
        lines.append(f"  ✓ 配置文件: {len(file_categories['config'])} 个")
        lines.append(f"  ✓ 文档文件: {len(file_categories['docs'])} 个")
        lines.append(f"  ✓ 脚本文件: {len(file_categories['bash'])} 个")
        lines.append(f"  ✓ 已分析文件: {len(self.analyzed_files)} 个")
        lines.append(f"  ✓ 依赖关系: {sum(len(deps) for deps in self.dependencies.values())} 条")

        if self.errors:
            lines.append(f"  ⚠ 错误数: {len(self.errors)} 个")

        lines.append("")
        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)

    def run_analysis(self):
        """执行完整分析"""
        print("🔍 开始分析依赖关系...")
        print(f"📁 根目录: {self.root_dir}")
        print("")

        # 从setup.sh开始
        setup_sh = self.root_dir / 'setup.sh'
        if setup_sh.exists():
            print("✓ 分析 setup.sh")
            self.analyze_bash_file(setup_sh)

        # 分析其他入口文件
        entry_files = [
            'auto_restart.sh',
            'deploy_and_run.sh',
            'start_live.sh',
            'scripts/realtime_signal_scanner.py',
            'scripts/init_databases.py'
        ]

        for entry in entry_files:
            entry_path = self.root_dir / entry
            if entry_path.exists():
                print(f"✓ 分析 {entry}")
                if entry_path.suffix == '.py':
                    self.analyze_python_file(entry_path)
                elif entry_path.suffix == '.sh':
                    self.analyze_bash_file(entry_path)

        print("")
        print(f"✓ 分析完成！共分析 {len(self.analyzed_files)} 个文件")
        print("")


def main():
    """主函数"""
    analyzer = DependencyAnalyzer()

    # 执行分析
    analyzer.run_analysis()

    # 生成报告
    report = analyzer.generate_report()

    # 保存到文件
    output_file = analyzer.root_dir / 'DEPENDENCY_ANALYSIS_REPORT.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 报告已保存到: {output_file}")
    print("")
    print("=" * 70)
    print("您可以使用以下命令查看报告:")
    print(f"  cat {output_file}")
    print(f"  less {output_file}")
    print("")
    print("或者直接发送到Telegram群:")
    print(f"  cat {output_file} | xclip -selection clipboard  # 复制到剪贴板")
    print("=" * 70)
    print("")

    # 同时输出到控制台
    print(report)


if __name__ == '__main__':
    main()
