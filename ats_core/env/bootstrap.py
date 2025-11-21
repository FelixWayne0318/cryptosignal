# ats_core/env/bootstrap.py
"""
统一环境引导模块：
- 把 externals/cryptofeed 和 externals/freqtrade 加入 sys.path
- 为整个 CryptoSignal 项目提供统一的启动环境
"""

import os
import sys


def bootstrap_env():
    """
    在任何入口脚本的最开头调用：
        from ats_core.env.bootstrap import bootstrap_env
        bootstrap_env()
    确保可以 import cryptofeed / freqtrade 等外部依赖。
    """
    # 当前文件 -> ats_core/env/bootstrap.py
    current_file = os.path.abspath(__file__)
    env_dir = os.path.dirname(current_file)
    ats_core_dir = os.path.dirname(env_dir)
    project_root = os.path.dirname(ats_core_dir)

    externals_dir = os.path.join(project_root, "externals")
    cryptofeed_dir = os.path.join(externals_dir, "cryptofeed")
    freqtrade_dir = os.path.join(externals_dir, "freqtrade")

    for path in [project_root, externals_dir, cryptofeed_dir, freqtrade_dir]:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)

    # 可选：打印一次日志，便于调试（如不需要可注释）
    # print(f"[bootstrap_env] sys.path updated with project_root={project_root}")
