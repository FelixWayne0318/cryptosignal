#!/usr/bin/env python3
"""
依赖树分析工具
从指定的入口文件递归分析所有内部导入依赖
"""

import ast
import json
import sys
from pathlib import Path
from collections import defaultdict, deque
from typing import Set, Dict, List, Tuple


class DependencyAnalyzer:
    """依赖分析器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.dependency_tree = {}
        self.visited = set()
        self.all_project_files = set()

        # 项目内部的包前缀
        self.internal_prefixes = ['ats_core', 'scripts', 'config', 'tests']

        # 标准库模块（部分常见的，用于过滤）
        self.stdlib_modules = {
            'os', 'sys', 'asyncio', 'argparse', 'signal', 'json', 'pathlib',
            'datetime', 'time', 'logging', 'traceback', 'collections',
            'typing', 'dataclasses', 'enum', 'functools', 'itertools',
            're', 'math', 'random', 'io', 'contextlib', 'copy', 'pickle',
            'urllib', 'http', 'hashlib', 'hmac', 'base64', 'uuid',
            'threading', 'multiprocessing', 'subprocess', 'shutil', 'tempfile',
            'warnings', 'abc', 'inspect', 'importlib'
        }

        # 已知的第三方库
        self.third_party_modules = {
            'requests', 'pandas', 'numpy', 'matplotlib', 'seaborn',
            'aiohttp', 'websockets', 'ccxt', 'binance', 'ta', 'talib',
            'scipy', 'sklearn', 'joblib', 'pytz', 'tqdm'
        }

    def is_internal_module(self, module_name: str) -> bool:
        """判断是否为项目内部模块"""
        if not module_name:
            return False

        # 检查是否以内部包前缀开头
        for prefix in self.internal_prefixes:
            if module_name.startswith(prefix):
                return True

        return False

    def is_stdlib_or_third_party(self, module_name: str) -> bool:
        """判断是否为标准库或第三方库"""
        if not module_name:
            return False

        # 获取顶层模块名
        top_level = module_name.split('.')[0]

        # 检查是否为标准库或已知第三方库
        if top_level in self.stdlib_modules or top_level in self.third_party_modules:
            return True

        return False

    def module_to_path(self, module_name: str) -> Path:
        """将模块名转换为文件路径"""
        # 例如: ats_core.pipeline.batch_scan -> ats_core/pipeline/batch_scan.py
        parts = module_name.split('.')

        # 尝试作为文件
        file_path = self.project_root / '/'.join(parts)
        if file_path.with_suffix('.py').exists():
            return file_path.with_suffix('.py')

        # 尝试作为包（__init__.py）
        init_path = file_path / '__init__.py'
        if init_path.exists():
            return init_path

        return None

    def path_to_module(self, file_path: Path) -> str:
        """将文件路径转换为模块名"""
        try:
            rel_path = file_path.relative_to(self.project_root)

            # 移除 .py 后缀
            if rel_path.name == '__init__.py':
                # __init__.py -> 使用父目录作为模块名
                parts = rel_path.parent.parts
            else:
                # 普通文件 -> 移除 .py
                parts = rel_path.with_suffix('').parts

            return '/'.join(parts)
        except ValueError:
            # 文件不在项目根目录下
            return str(file_path)

    def extract_imports(self, file_path: Path) -> List[str]:
        """从Python文件中提取所有import语句"""
        imports = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    # import xxx
                    for alias in node.names:
                        imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    # from xxx import yyy
                    if node.module:
                        imports.append(node.module)

        except SyntaxError as e:
            print(f"⚠️  语法错误 {file_path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  解析失败 {file_path}: {e}", file=sys.stderr)

        return imports

    def analyze_file(self, file_path: Path, depth: int = 0) -> None:
        """递归分析文件的依赖关系"""
        # 转换为相对路径的模块名
        module_name = self.path_to_module(file_path)

        # 检查是否已访问
        if module_name in self.visited:
            return

        self.visited.add(module_name)

        # 提取导入
        raw_imports = self.extract_imports(file_path)

        # 过滤出项目内部的导入
        internal_imports = []
        for imp in raw_imports:
            if self.is_internal_module(imp) and not self.is_stdlib_or_third_party(imp):
                # 转换为文件路径
                imp_path = self.module_to_path(imp)
                if imp_path and imp_path.exists():
                    imp_module = self.path_to_module(imp_path)
                    internal_imports.append(imp_module)

        # 记录到依赖树
        self.dependency_tree[module_name] = {
            'imports': sorted(internal_imports),
            'depth': depth
        }

        # 递归分析导入的模块
        for imp_module in internal_imports:
            imp_path = self.project_root / imp_module.replace('/', '/')
            if imp_module.endswith('__init__'):
                imp_path = self.project_root / imp_module.replace('__init__', '__init__.py')
            else:
                imp_path = self.project_root / (imp_module + '.py')

            if imp_path.exists():
                self.analyze_file(imp_path, depth + 1)

    def analyze_from_entry(self, entry_file: Path) -> Dict:
        """从入口文件开始分析依赖树"""
        print(f"🔍 开始分析依赖树...")
        print(f"   入口文件: {entry_file}")
        print(f"   项目根目录: {self.project_root}")
        print()

        # 分析入口文件
        self.analyze_file(entry_file, depth=0)

        print(f"✅ 分析完成")
        print(f"   已分析文件数: {len(self.dependency_tree)}")
        print()

        return self.dependency_tree

    def get_all_python_files(self) -> Set[str]:
        """获取项目中所有Python文件"""
        python_files = set()

        # 扫描项目内部目录
        for prefix in self.internal_prefixes:
            prefix_path = self.project_root / prefix
            if prefix_path.exists() and prefix_path.is_dir():
                for py_file in prefix_path.rglob('*.py'):
                    # 排除 __pycache__ 等
                    if '__pycache__' not in str(py_file):
                        module_name = self.path_to_module(py_file)
                        python_files.add(module_name)

        return python_files

    def generate_report(self, entry_file: Path) -> Dict:
        """生成分析报告"""
        # 获取所有项目文件
        all_files = self.get_all_python_files()
        used_files = set(self.dependency_tree.keys())

        # 计算使用率
        total_count = len(all_files)
        used_count = len(used_files)
        usage_rate = (used_count / total_count * 100) if total_count > 0 else 0

        report = {
            'dependency_tree': self.dependency_tree,
            'statistics': {
                'entry_file': self.path_to_module(entry_file),
                'total_python_files': total_count,
                'used_files': used_count,
                'usage_rate': round(usage_rate, 2),
                'all_files': sorted(all_files),
                'used_files_list': sorted(used_files),
                'unused_files': sorted(all_files - used_files)
            }
        }

        return report


def main():
    """主函数"""
    # 项目根目录
    project_root = Path(__file__).parent

    # 入口文件
    entry_file = project_root / 'scripts' / 'realtime_signal_scanner.py'

    if not entry_file.exists():
        print(f"❌ 入口文件不存在: {entry_file}")
        sys.exit(1)

    # 创建分析器
    analyzer = DependencyAnalyzer(project_root)

    # 分析依赖树
    analyzer.analyze_from_entry(entry_file)

    # 生成报告
    report = analyzer.generate_report(entry_file)

    # 保存为JSON
    output_file = project_root / 'dependency_tree.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"📄 依赖树已保存: {output_file}")
    print()

    # 打印统计信息
    stats = report['statistics']
    print("=" * 60)
    print("📊 依赖分析统计")
    print("=" * 60)
    print(f"入口文件: {stats['entry_file']}")
    print(f"所有Python文件总数: {stats['total_python_files']}")
    print(f"实际被使用的文件数: {stats['used_files']}")
    print(f"使用率: {stats['usage_rate']:.2f}%")
    print()

    print("✅ 所有被使用的文件列表（按路径排序）:")
    print("-" * 60)
    for i, file in enumerate(stats['used_files_list'], 1):
        depth = report['dependency_tree'][file]['depth']
        imports_count = len(report['dependency_tree'][file]['imports'])
        print(f"{i:3d}. {file:60s} (depth={depth}, imports={imports_count})")
    print()

    if stats['unused_files']:
        print(f"❌ 未被使用的文件 ({len(stats['unused_files'])}个):")
        print("-" * 60)
        for i, file in enumerate(stats['unused_files'], 1):
            print(f"{i:3d}. {file}")
        print()

    print("=" * 60)


if __name__ == '__main__':
    main()
