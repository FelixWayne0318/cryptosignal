#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统版本统一脚本 v7.3.4

功能：
1. 扫描所有文件中的版本号
2. 统一更新为v7.3.4
3. 生成更新报告
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple

TARGET_VERSION = "v7.3.4"
TARGET_DATE = "2025-11-15"

# 版本号正则模式
VERSION_PATTERNS = [
    (r'v7\.[0-9]\.[0-9](-Full|-[\w]+)?', 'v7.x.x'),
    (r'v6\.[0-9]\.[0-9]', 'v6.x.x'),
    (r'"version":\s*"v?([0-9]\.[0-9]\.[0-9])"', 'json_version'),
    (r'version\s*=\s*["\']([0-9]\.[0-9]\.[0-9])["\']', 'python_version'),
]

# 需要排除的目录
EXCLUDE_DIRS = {
    '.git', '__pycache__', '.pytest_cache', 'node_modules',
    'venv', 'env', '.venv', 'build', 'dist', '*.egg-info'
}

# 需要排除的文件模式
EXCLUDE_FILES = {
    '*.pyc', '*.pyo', '*.log', '*.db', '*.sqlite',
    '*.min.js', '*.min.css', 'package-lock.json',
    'scan_detail.json', 'scan_summary.json'  # 扫描报告不更新
}

# 保留旧版本的文件（历史文档、归档等）
PRESERVE_FILES = {
    'docs/archived',  # 归档文档保持原版本
    'docs/STRATEGIC_DESIGN_FIX_v7.3.3',  # v7.3.3修复文档
    'docs/CONFIG_UNIFICATION_FIX_v7.3.4',  # v7.3.4修复文档
    'docs/HEALTH_CHECK_FIXES_v7.3.3',  # v7.3.3健康检查文档
    'standards/03_VERSION_HISTORY.md',  # 版本历史保持记录
}

class VersionUnifier:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.changes = []
        self.stats = {
            'files_scanned': 0,
            'files_updated': 0,
            'versions_found': {},
            'errors': []
        }

    def should_skip(self, path: Path) -> bool:
        """判断是否应该跳过该文件/目录"""
        # 检查目录
        for part in path.parts:
            if part in EXCLUDE_DIRS:
                return True

        # 检查文件名模式
        for pattern in EXCLUDE_FILES:
            if path.match(pattern):
                return True

        # 检查保留文件
        rel_path = str(path.relative_to(self.root_dir))
        for preserve in PRESERVE_FILES:
            if preserve in rel_path:
                return True

        return False

    def find_version_matches(self, content: str, file_path: str) -> List[Tuple[str, str, str]]:
        """查找文件中的所有版本号匹配"""
        matches = []

        for pattern, vtype in VERSION_PATTERNS:
            for match in re.finditer(pattern, content):
                version_str = match.group(0)
                matches.append((version_str, vtype, match.span()))

                # 记录版本统计
                if version_str not in self.stats['versions_found']:
                    self.stats['versions_found'][version_str] = []
                self.stats['versions_found'][version_str].append(file_path)

        return matches

    def update_version(self, content: str, file_path: str) -> Tuple[str, int]:
        """更新文件中的版本号"""
        updated_content = content
        update_count = 0

        # 特殊处理：setup.sh
        if 'setup.sh' in file_path:
            updated_content = re.sub(
                r'CryptoSignal v[0-9]\.[0-9]\.[0-9](-Full)?',
                f'CryptoSignal {TARGET_VERSION}',
                updated_content
            )
            updated_content = re.sub(
                r'v[0-9]\.[0-9]\.[0-9](-Full)?',
                TARGET_VERSION,
                updated_content
            )
            update_count += updated_content.count(TARGET_VERSION) - content.count(TARGET_VERSION)

        # 特殊处理：README.md
        elif 'README.md' in file_path and 'archived' not in file_path:
            # 更新主版本号
            updated_content = re.sub(
                r'\*\*当前版本\*\*:\s*v[0-9]\.[0-9]\.[0-9]',
                f'**当前版本**: {TARGET_VERSION}',
                updated_content
            )
            updated_content = re.sub(
                r'CryptoSignal v[0-9]\.[0-9]\.[0-9](-Full)?',
                f'CryptoSignal {TARGET_VERSION}',
                updated_content
            )
            updated_content = re.sub(
                r'\*\*版本\*\*:\s*v[0-9]\.[0-9]\.[0-9]',
                f'**版本**: {TARGET_VERSION}',
                updated_content
            )
            updated_content = re.sub(
                r'\*\*最后更新\*\*:\s*\d{4}-\d{2}-\d{2}',
                f'**最后更新**: {TARGET_DATE}',
                updated_content
            )
            update_count = 1 if updated_content != content else 0

        # 特殊处理：JSON配置文件
        elif file_path.endswith('.json'):
            # 更新version字段
            updated_content = re.sub(
                r'"version":\s*"v?[0-9]\.[0-9]\.[0-9]"',
                f'"version": "{TARGET_VERSION}"',
                updated_content
            )
            # 更新_version字段
            updated_content = re.sub(
                r'"_version":\s*"v?[0-9]\.[0-9]\.[0-9]"',
                f'"_version": "{TARGET_VERSION}"',
                updated_content
            )
            update_count = 1 if updated_content != content else 0

        # 普通Python文件和Markdown文件
        else:
            # 只更新明确的版本声明，不更新文档中的历史记录
            if 'version' in content.lower() or 'v7.' in content or 'v6.' in content:
                # 更新v7.x.x -> v7.3.4 (排除v7.3.3, v7.3.4已经是最新)
                updated_content = re.sub(
                    r'v7\.[0-2]\.[0-9](-Full)?',
                    TARGET_VERSION,
                    updated_content
                )
                # 更新v6.x.x -> v7.3.4
                updated_content = re.sub(
                    r'v6\.[0-9]\.[0-9]',
                    TARGET_VERSION,
                    updated_content
                )
                update_count = 1 if updated_content != content else 0

        return updated_content, update_count

    def scan_and_update(self):
        """扫描并更新所有文件"""
        print(f"开始扫描: {self.root_dir}")
        print(f"目标版本: {TARGET_VERSION}")
        print("=" * 60)

        # 遍历所有文件
        for file_path in self.root_dir.rglob('*'):
            if not file_path.is_file():
                continue

            if self.should_skip(file_path):
                continue

            # 只处理文本文件
            if file_path.suffix not in {'.py', '.sh', '.md', '.json', '.txt', '.yaml', '.yml', '.cfg'}:
                continue

            self.stats['files_scanned'] += 1

            try:
                # 读取文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 查找版本号
                matches = self.find_version_matches(content, str(file_path.relative_to(self.root_dir)))

                # 更新版本号
                updated_content, update_count = self.update_version(content, str(file_path))

                # 如果有更新，写回文件
                if updated_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

                    self.changes.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'updates': update_count
                    })
                    self.stats['files_updated'] += 1
                    print(f"✅ 已更新: {file_path.relative_to(self.root_dir)}")

            except Exception as e:
                error_msg = f"处理文件出错 {file_path}: {e}"
                self.stats['errors'].append(error_msg)
                print(f"❌ {error_msg}")

        print("=" * 60)
        self.print_report()

    def print_report(self):
        """打印更新报告"""
        print("\n" + "=" * 60)
        print("版本统一报告")
        print("=" * 60)

        print(f"\n扫描文件数: {self.stats['files_scanned']}")
        print(f"更新文件数: {self.stats['files_updated']}")
        print(f"错误数: {len(self.stats['errors'])}")

        if self.stats['versions_found']:
            print(f"\n发现的版本号：")
            for version, files in sorted(self.stats['versions_found'].items()):
                print(f"  {version}: {len(files)}个文件")

        if self.changes:
            print(f"\n更新的文件:")
            for change in self.changes[:20]:  # 只显示前20个
                print(f"  ✅ {change['file']}")
            if len(self.changes) > 20:
                print(f"  ... 还有{len(self.changes) - 20}个文件")

        if self.stats['errors']:
            print(f"\n错误:")
            for error in self.stats['errors']:
                print(f"  ❌ {error}")

        print("\n" + "=" * 60)
        print(f"✅ 版本统一完成！目标版本: {TARGET_VERSION}")
        print("=" * 60)


def main():
    """主函数"""
    import sys

    # 获取项目根目录
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        # 默认为脚本所在目录的父目录
        root_dir = Path(__file__).parent.parent

    unifier = VersionUnifier(root_dir)
    unifier.scan_and_update()

    return 0 if not unifier.stats['errors'] else 1


if __name__ == '__main__':
    exit(main())
