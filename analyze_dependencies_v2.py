#!/usr/bin/env python3
"""
依赖分析工具 v2.0 - 深度分析所有文件依赖并识别冗余文件
适合在Termius中运行并发送结果到Telegram

改进：
1. 深度递归分析所有ats_core模块
2. 完整追踪import路径
3. 识别并列出未使用的文件
4. 生成详细的清理建议

作者：Claude Code
版本：v2.0
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict
from typing import Set, Dict, List

class DeepDependencyAnalyzer:
    """深度依赖分析器"""

    def __init__(self, root_dir: str = "/home/user/cryptosignal"):
        self.root_dir = Path(root_dir)
        self.all_python_files = set()  # 所有Python文件
        self.imported_modules = set()  # 被导入的模块
        self.file_imports = defaultdict(set)  # 文件 -> 它导入的模块
        self.module_to_file = {}  # 模块名 -> 文件路径映射
        self.errors = []

    def scan_all_python_files(self):
        """扫描所有Python文件"""
        print("📁 扫描所有Python文件...")

        for path in self.root_dir.rglob('*.py'):
            # 忽略__pycache__
            if '__pycache__' in path.parts:
                continue

            self.all_python_files.add(path)

            # 建立模块名到文件路径的映射
            try:
                rel_path = path.relative_to(self.root_dir)

                # 转换文件路径为模块名
                if rel_path.name == '__init__.py':
                    # ats_core/features/__init__.py -> ats_core.features
                    module_name = '.'.join(rel_path.parts[:-1])
                else:
                    # ats_core/features/trend.py -> ats_core.features.trend
                    parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                    module_name = '.'.join(parts)

                if module_name:
                    self.module_to_file[module_name] = path

            except Exception as e:
                self.errors.append(f"处理{path}时出错: {e}")

        print(f"  ✓ 找到 {len(self.all_python_files)} 个Python文件")
        print(f"  ✓ 建立 {len(self.module_to_file)} 个模块映射")
        print()

    def extract_imports(self, file_path: Path) -> Set[str]:
        """提取文件中的所有import语句（完整路径）"""
        imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            # import ats_core.features.trend
                            imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            # from ats_core.features import trend
                            module = node.module
                            imports.add(module)
                            # 也添加子模块
                            for alias in node.names:
                                if alias.name != '*':
                                    full_name = f"{module}.{alias.name}"
                                    imports.add(full_name)
            except SyntaxError:
                # AST解析失败，使用正则
                patterns = [
                    r'^\s*import\s+([\w\.]+)',
                    r'^\s*from\s+([\w\.]+)\s+import\s+([\w\s,]+)',
                ]
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        imports.add(match.group(1))

        except Exception as e:
            self.errors.append(f"解析{file_path}失败: {e}")

        # 只保留项目内的import
        project_imports = {
            imp for imp in imports
            if imp.startswith('ats_core') or imp == 'scripts'
        }

        return project_imports

    def analyze_all_dependencies(self):
        """分析所有文件的依赖关系"""
        print("🔗 分析文件依赖关系...")

        for file_path in self.all_python_files:
            imports = self.extract_imports(file_path)
            self.file_imports[file_path] = imports

            # 记录被导入的模块
            for imp in imports:
                self.imported_modules.add(imp)
                # 也记录父模块
                parts = imp.split('.')
                for i in range(1, len(parts)):
                    parent = '.'.join(parts[:i])
                    self.imported_modules.add(parent)

        print(f"  ✓ 分析了 {len(self.file_imports)} 个文件")
        print(f"  ✓ 发现 {len(self.imported_modules)} 个被导入的模块")
        print()

    def find_unused_files(self) -> List[Path]:
        """找出未被使用的文件"""
        print("🔍 识别未使用的文件...")

        unused_files = []

        # 入口文件永远被认为是使用的
        entry_files = {
            'scripts/realtime_signal_scanner.py',
            'scripts/init_databases.py',
            'analyze_dependencies.py',
            'analyze_dependencies_v2.py',
        }

        for file_path in self.all_python_files:
            try:
                rel_path = file_path.relative_to(self.root_dir)
                rel_path_str = str(rel_path)

                # 入口文件跳过
                if rel_path_str in entry_files:
                    continue

                # 转换为模块名
                if rel_path.name == '__init__.py':
                    module_name = '.'.join(rel_path.parts[:-1])
                else:
                    parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                    module_name = '.'.join(parts)

                # 检查是否被导入
                is_used = module_name in self.imported_modules

                # __init__.py 特殊处理：如果其父目录下有其他文件被导入，则认为被使用
                if rel_path.name == '__init__.py':
                    parent_module = module_name
                    for imp in self.imported_modules:
                        if imp.startswith(parent_module + '.'):
                            is_used = True
                            break

                if not is_used:
                    unused_files.append(file_path)

            except Exception as e:
                self.errors.append(f"检查{file_path}时出错: {e}")

        print(f"  ✓ 找到 {len(unused_files)} 个未使用的文件")
        print()

        return sorted(unused_files)

    def generate_report(self, unused_files: List[Path]) -> str:
        """生成详细报告"""
        lines = []

        lines.append("=" * 70)
        lines.append("📊 CryptoSignal v7.2 深度依赖分析报告 v2.0")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"📁 分析根目录: {self.root_dir}")
        lines.append(f"🕐 分析时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 1. 总体统计
        lines.append("-" * 70)
        lines.append("📈 总体统计")
        lines.append("-" * 70)
        lines.append(f"  总Python文件数: {len(self.all_python_files)} 个")
        lines.append(f"  被导入的模块数: {len(self.imported_modules)} 个")
        lines.append(f"  未使用的文件数: {len(unused_files)} 个")

        usage_rate = (len(self.all_python_files) - len(unused_files)) / len(self.all_python_files) * 100 if self.all_python_files else 0
        lines.append(f"  代码使用率: {usage_rate:.1f}%")
        lines.append("")

        # 2. 未使用的文件列表（重点）
        lines.append("-" * 70)
        lines.append("🗑️  未使用的文件列表（可安全删除）")
        lines.append("-" * 70)

        if unused_files:
            # 按目录分组
            by_dir = defaultdict(list)
            total_size = 0
            total_lines = 0

            for file_path in unused_files:
                rel_path = file_path.relative_to(self.root_dir)
                parent = str(rel_path.parent) if rel_path.parent != Path('.') else '根目录'

                size = file_path.stat().st_size
                # 统计行数
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_count = len(f.readlines())
                except:
                    line_count = 0

                total_size += size
                total_lines += line_count

                by_dir[parent].append((rel_path, size, line_count))

            for dir_name in sorted(by_dir.keys()):
                lines.append(f"\n  📂 {dir_name}:")
                for rel_path, size, line_count in sorted(by_dir[dir_name]):
                    lines.append(f"    • {rel_path.name:40s}  ({line_count:4d}行, {size:6,d}字节)")

            lines.append("")
            lines.append(f"  💾 总计: {len(unused_files)}个文件, {total_lines:,}行代码, {total_size/1024:.1f}KB")
        else:
            lines.append("  ✅ 没有发现未使用的文件！代码已经非常精简。")

        lines.append("")

        # 3. 高频使用的模块（Top 15）
        lines.append("-" * 70)
        lines.append("🔥 高频使用的模块 (Top 15)")
        lines.append("-" * 70)

        # 统计每个模块被导入的次数
        import_counts = defaultdict(int)
        for imports in self.file_imports.values():
            for imp in imports:
                import_counts[imp] += 1

        sorted_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:15]

        for i, (module, count) in enumerate(sorted_imports, 1):
            # 找到对应的文件
            file_path = self.module_to_file.get(module, '')
            if file_path:
                rel_path = Path(file_path).relative_to(self.root_dir)
                lines.append(f"  {i:2d}. {module:45s} ({count:2d}次) <- {rel_path}")
            else:
                lines.append(f"  {i:2d}. {module:45s} ({count:2d}次)")

        lines.append("")

        # 4. 按目录统计
        lines.append("-" * 70)
        lines.append("📁 按目录统计文件使用情况")
        lines.append("-" * 70)

        dir_stats = defaultdict(lambda: {'total': 0, 'used': 0, 'unused': 0})

        for file_path in self.all_python_files:
            rel_path = file_path.relative_to(self.root_dir)
            if len(rel_path.parts) > 0:
                top_dir = rel_path.parts[0]
                dir_stats[top_dir]['total'] += 1

                if file_path in unused_files:
                    dir_stats[top_dir]['unused'] += 1
                else:
                    dir_stats[top_dir]['used'] += 1

        for dir_name in sorted(dir_stats.keys()):
            stats = dir_stats[dir_name]
            usage = stats['used'] / stats['total'] * 100 if stats['total'] > 0 else 0
            lines.append(f"  {dir_name:20s}: {stats['used']:3d}/{stats['total']:3d} 使用 ({usage:5.1f}%) | {stats['unused']:2d} 未使用")

        lines.append("")

        # 5. 清理建议
        if unused_files:
            lines.append("-" * 70)
            lines.append("💡 清理建议")
            lines.append("-" * 70)
            lines.append("")
            lines.append("  可以安全删除的文件:")
            lines.append("")

            for file_path in unused_files:
                rel_path = file_path.relative_to(self.root_dir)
                lines.append(f"    rm {rel_path}")

            lines.append("")
            lines.append("  或使用以下命令批量删除:")
            lines.append("")

            # 按目录分组删除命令
            by_dir = defaultdict(list)
            for file_path in unused_files:
                rel_path = file_path.relative_to(self.root_dir)
                by_dir[rel_path.parent].append(rel_path.name)

            for parent_dir, filenames in sorted(by_dir.items()):
                if len(filenames) == 1:
                    lines.append(f"    rm {parent_dir}/{filenames[0]}")
                else:
                    files_str = ' '.join(filenames)
                    lines.append(f"    rm {parent_dir}/{{{files_str}}}")

            lines.append("")

        # 6. 错误和警告
        if self.errors:
            lines.append("-" * 70)
            lines.append("⚠️  错误和警告")
            lines.append("-" * 70)

            for error in self.errors[:10]:
                lines.append(f"  - {error}")

            if len(self.errors) > 10:
                lines.append(f"  ... 还有 {len(self.errors) - 10} 个错误未显示")

            lines.append("")

        # 7. 总结
        lines.append("=" * 70)
        lines.append("✅ 分析完成")
        lines.append("=" * 70)
        lines.append("")

        if unused_files:
            lines.append(f"⚠️  发现 {len(unused_files)} 个未使用的文件，建议删除以保持代码整洁。")
        else:
            lines.append("✅ 所有Python文件都被使用，代码已经非常精简！")

        lines.append("")
        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)

    def run(self):
        """执行完整分析流程"""
        print()
        print("=" * 70)
        print("🚀 开始深度依赖分析...")
        print("=" * 70)
        print()

        # 1. 扫描所有Python文件
        self.scan_all_python_files()

        # 2. 分析所有依赖关系
        self.analyze_all_dependencies()

        # 3. 找出未使用的文件
        unused_files = self.find_unused_files()

        # 4. 生成报告
        print("📝 生成分析报告...")
        report = self.generate_report(unused_files)

        # 5. 保存报告
        output_file = self.root_dir / 'DEPENDENCY_DEEP_ANALYSIS.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ 报告已保存到: {output_file}")
        print()

        # 6. 输出到控制台
        print(report)

        return unused_files


def main():
    """主函数"""
    analyzer = DeepDependencyAnalyzer()
    unused_files = analyzer.run()

    # 总结
    print()
    print("=" * 70)
    print("📋 使用说明")
    print("=" * 70)
    print()
    print("1. 查看完整报告:")
    print("   cat DEPENDENCY_DEEP_ANALYSIS.txt")
    print()
    print("2. 发送到Telegram（在Termius中复制）:")
    print("   cat DEPENDENCY_DEEP_ANALYSIS.txt")
    print()
    print("3. 如果决定删除未使用的文件，请先备份后执行清理命令")
    print()
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
