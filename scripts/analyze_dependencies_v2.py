#!/usr/bin/env python3
"""
依赖分析工具 v2
从系统入口点开始，分析所有被使用的Python文件和配置文件
"""

import os
import sys
import re
import ast
from pathlib import Path
from typing import Set, Dict, List
import json

class DependencyAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.used_files: Set[Path] = set()
        self.import_graph: Dict[Path, Set[Path]] = {}
        self.config_files: Set[Path] = set()
        self.processed_files: Set[Path] = set()

    def analyze_from_entrypoint(self, entrypoint: str):
        """从入口点开始分析所有依赖"""
        entry_path = self.project_root / entrypoint
        if not entry_path.exists():
            print(f"⚠️  入口文件不存在: {entrypoint}")
            return

        print(f"🔍 从入口点开始分析: {entrypoint}")
        self._analyze_file(entry_path)

    def _analyze_file(self, file_path: Path):
        """递归分析单个文件的依赖"""
        if file_path in self.processed_files:
            return

        self.processed_files.add(file_path)
        self.used_files.add(file_path)

        if file_path.suffix != '.py':
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用AST解析import语句
            try:
                tree = ast.parse(content, filename=str(file_path))
                imports = self._extract_imports(tree, file_path)
                self.import_graph[file_path] = imports

                # 递归分析导入的文件
                for imported_file in imports:
                    if imported_file and imported_file.exists():
                        self._analyze_file(imported_file)
            except SyntaxError as e:
                print(f"⚠️  语法错误 {file_path}: {e}")

            # 分析配置文件引用
            self._extract_config_references(content, file_path)

        except Exception as e:
            print(f"⚠️  无法读取 {file_path}: {e}")

    def _extract_imports(self, tree: ast.AST, current_file: Path) -> Set[Path]:
        """从AST中提取import语句并解析为文件路径"""
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    file_path = self._resolve_module(module_name, current_file)
                    if file_path:
                        imports.add(file_path)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    file_path = self._resolve_module(module_name, current_file)
                    if file_path:
                        imports.add(file_path)

        return imports

    def _resolve_module(self, module_name: str, current_file: Path) -> Path:
        """将模块名解析为文件路径"""
        # 处理相对导入
        if module_name.startswith('.'):
            # 相对当前文件的目录
            current_dir = current_file.parent
            parts = module_name.split('.')
            level = len([p for p in parts if not p])
            module_parts = [p for p in parts if p]

            target_dir = current_dir
            for _ in range(level - 1):
                target_dir = target_dir.parent

            for part in module_parts:
                target_dir = target_dir / part

            # 尝试 __init__.py 或 module.py
            if (target_dir / '__init__.py').exists():
                return target_dir / '__init__.py'
            elif (target_dir.parent / f'{target_dir.name}.py').exists():
                return target_dir.parent / f'{target_dir.name}.py'
        else:
            # 绝对导入
            parts = module_name.split('.')

            # 尝试从项目根目录解析
            target = self.project_root / '/'.join(parts)

            if (target / '__init__.py').exists():
                return target / '__init__.py'
            elif (self.project_root / f"{'/'.join(parts)}.py").exists():
                return self.project_root / f"{'/'.join(parts)}.py"

        return None

    def _extract_config_references(self, content: str, file_path: Path):
        """提取配置文件引用"""
        # 查找常见的配置文件引用模式
        patterns = [
            r'["\']config/([^"\']+\.json)["\']',
            r'["\']config/([^"\']+\.yaml)["\']',
            r'["\']config/([^"\']+\.yml)["\']',
            r'Path\(["\']config/([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                config_path = self.project_root / 'config' / match
                if config_path.exists():
                    self.config_files.add(config_path)
                    self.used_files.add(config_path)

    def find_all_python_files(self) -> Set[Path]:
        """查找项目中所有Python文件"""
        all_files = set()

        for ext in ['*.py']:
            for file in self.project_root.rglob(ext):
                # 排除 __pycache__ 和隐藏目录
                if '__pycache__' not in file.parts and not any(p.startswith('.') for p in file.parts):
                    all_files.add(file)

        return all_files

    def find_all_doc_files(self) -> Dict[str, List[Path]]:
        """查找所有文档文件并分类"""
        doc_files = {
            'standards': [],  # 规范文档
            'docs': [],       # 说明文档
            'tests': [],      # 测试文件
            'diagnose': [],   # 诊断文件
            'other': []       # 其他
        }

        # 查找markdown文件
        for md_file in self.project_root.rglob('*.md'):
            if '__pycache__' in md_file.parts or any(p.startswith('.') for p in md_file.parts):
                continue

            rel_path = md_file.relative_to(self.project_root)

            # 根据内容和位置分类
            if 'standards' in md_file.parts or 'STANDARD' in md_file.name.upper():
                doc_files['standards'].append(md_file)
            elif 'docs' in md_file.parts:
                doc_files['docs'].append(md_file)
            elif 'tests' in md_file.parts or 'test' in md_file.name.lower():
                doc_files['tests'].append(md_file)
            elif 'diagnose' in md_file.parts or 'diagnostic' in md_file.name.lower():
                doc_files['diagnose'].append(md_file)
            elif md_file.parent == self.project_root:
                # 根目录的文档需要进一步分类
                name_lower = md_file.name.lower()
                if any(kw in name_lower for kw in ['standard', 'spec', 'rule', 'convention']):
                    doc_files['standards'].append(md_file)
                elif any(kw in name_lower for kw in ['doc', 'readme', 'guide', 'manual', 'fix', 'report', 'summary']):
                    doc_files['docs'].append(md_file)
                elif any(kw in name_lower for kw in ['test', 'diagnostic', 'diagnose', 'check']):
                    doc_files['diagnose'].append(md_file)
                else:
                    doc_files['other'].append(md_file)
            else:
                doc_files['other'].append(md_file)

        return doc_files

    def generate_report(self) -> Dict:
        """生成分析报告"""
        all_py_files = self.find_all_python_files()
        unused_py_files = all_py_files - self.used_files
        doc_files = self.find_all_doc_files()

        report = {
            'total_python_files': len(all_py_files),
            'used_python_files': len(self.used_files & all_py_files),
            'unused_python_files': len(unused_py_files),
            'config_files': len(self.config_files),
            'unused_files_list': [str(f.relative_to(self.project_root)) for f in sorted(unused_py_files)],
            'doc_files': {
                category: [str(f.relative_to(self.project_root)) for f in files]
                for category, files in doc_files.items()
            }
        }

        return report


def main():
    """主函数"""
    project_root = Path(__file__).parent
    analyzer = DependencyAnalyzer(project_root)

    # 定义系统入口点
    entrypoints = [
        'scripts/realtime_signal_scanner.py',
        'scripts/init_databases.py',
        'setup.sh',  # Shell脚本会分析其中的Python调用
    ]

    print("=" * 60)
    print("🔍 CryptoSignal 依赖分析 v2")
    print("=" * 60)
    print()

    # 从所有入口点分析
    for entry in entrypoints:
        entry_path = project_root / entry
        if entry_path.exists() and entry_path.suffix == '.py':
            analyzer.analyze_from_entrypoint(entry)

    # 生成报告
    print()
    print("=" * 60)
    print("📊 分析报告")
    print("=" * 60)

    report = analyzer.generate_report()

    print(f"\n📁 Python 文件统计:")
    print(f"   总计: {report['total_python_files']} 个")
    print(f"   使用中: {report['used_python_files']} 个")
    print(f"   未使用: {report['unused_python_files']} 个")

    print(f"\n⚙️  配置文件: {report['config_files']} 个")

    print(f"\n📝 文档文件统计:")
    for category, files in report['doc_files'].items():
        if files:
            print(f"   {category}: {len(files)} 个")

    if report['unused_python_files'] > 0:
        print(f"\n❌ 未使用的 Python 文件 ({report['unused_python_files']} 个):")
        for file in report['unused_files_list'][:20]:  # 只显示前20个
            print(f"   - {file}")
        if len(report['unused_files_list']) > 20:
            print(f"   ... 还有 {len(report['unused_files_list']) - 20} 个")

    # 保存详细报告
    output_file = project_root / 'dependency_analysis_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 详细报告已保存: {output_file}")
    print()

    return report


if __name__ == '__main__':
    main()
