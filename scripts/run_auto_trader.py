#!/usr/bin/env python
# coding: utf-8
"""
自动交易系统启动脚本（生产环境）

功能:
1. 从环境变量加载配置
2. 初始化自动交易系统
3. 启动WebSocket批量扫描优化
4. 定时扫描和执行交易
5. 发送电报通知

使用方法:
    python scripts/run_auto_trader.py

环境变量:
    BINANCE_API_KEY             - 币安API密钥
    BINANCE_API_SECRET          - 币安API密钥密码
    TELEGRAM_BOT_TOKEN          - 电报Bot Token
    TELEGRAM_CHAT_ID            - 电报Chat ID
    ENABLE_REAL_TRADING         - 是否启用真实交易（false=模拟）
    USE_OPTIMIZED_SCAN          - 是否使用WebSocket优化（true推荐）
    SCAN_INTERVAL_SECONDS       - 扫描间隔（秒）
    MIN_SIGNAL_SCORE            - 最小信号分数
    MAX_CONCURRENT_POSITIONS    - 最大并发仓位
    MAX_POSITION_SIZE_USDT      - 单仓位最大USDT
    MAX_DAILY_LOSS_USDT         - 每日最大亏损USDT
    MAX_LEVERAGE                - 最大杠杆倍数
"""

import os
import sys
import asyncio
import signal
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.execution.auto_trader import AutoTrader
from ats_core.outputs.publisher import telegram_send
from ats_core.logging import log, warn, error


def load_config_from_env():
    """从环境变量加载配置"""

    # 必需的环境变量
    required_vars = [
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise RuntimeError(
            f"缺少必需的环境变量: {', '.join(missing_vars)}\n"
            f"请在 .env 文件中配置或使用 export 设置"
        )

    # 构建配置
    config = {
        # 币安配置
        'binance': {
            'api_key': os.getenv('BINANCE_API_KEY'),
            'api_secret': os.getenv('BINANCE_API_SECRET'),
            'testnet': False,
            'futures_base_url': 'https://fapi.binance.com',
            'ws_futures_url': 'wss://fstream.binance.com'
        },

        # 交易限制
        'trading_limits': {
            'max_concurrent_positions': int(os.getenv('MAX_CONCURRENT_POSITIONS', '5')),
            'max_position_size_usdt': float(os.getenv('MAX_POSITION_SIZE_USDT', '10000')),
            'max_daily_loss_usdt': float(os.getenv('MAX_DAILY_LOSS_USDT', '2000')),
            'max_leverage': int(os.getenv('MAX_LEVERAGE', '10')),
            'min_order_size_usdt': float(os.getenv('MIN_ORDER_SIZE_USDT', '10'))
        },

        # 交易模式
        'enable_real_trading': os.getenv('ENABLE_REAL_TRADING', 'false').lower() == 'true',

        # WebSocket优化
        'use_optimized_scan': os.getenv('USE_OPTIMIZED_SCAN', 'true').lower() == 'true',

        # 扫描配置
        'scan_interval_seconds': int(os.getenv('SCAN_INTERVAL_SECONDS', '300')),
        'min_signal_score': int(os.getenv('MIN_SIGNAL_SCORE', '75'))
    }

    return config


def send_startup_notification(config):
    """发送启动通知"""
    try:
        mode = "🔴 真实交易" if config['enable_real_trading'] else "🟢 模拟模式"
        websocket = "✅ 已启用" if config['use_optimized_scan'] else "❌ 未启用"

        message = f"""
🤖 <b>CryptoSignal 自动交易系统已启动</b>

⚙️ <b>配置信息:</b>
├ 交易模式: {mode}
├ WebSocket优化: {websocket}
├ 扫描间隔: {config['scan_interval_seconds']}秒
├ 最小信号分数: {config['min_signal_score']}
├ 最大并发仓位: {config['trading_limits']['max_concurrent_positions']}
└ 单仓位最大: {config['trading_limits']['max_position_size_usdt']} USDT

📊 <b>风险控制:</b>
├ 每日最大亏损: {config['trading_limits']['max_daily_loss_usdt']} USDT
├ 最大杠杆: {config['trading_limits']['max_leverage']}x
└ 最小订单: {config['trading_limits']['min_order_size_usdt']} USDT

🚀 系统正在初始化，预计2-3分钟完成...
"""
        telegram_send(message.strip())
        log("✅ 启动通知已发送")
    except Exception as e:
        warn(f"发送启动通知失败: {e}")


def send_ready_notification(config):
    """发送就绪通知"""
    try:
        message = f"""
✅ <b>系统初始化完成！</b>

🚀 WebSocket批量扫描优化已激活
📡 K线缓存实时更新中
🔍 开始定时扫描交易信号...

⏰ 下次扫描: {config['scan_interval_seconds']}秒后
"""
        telegram_send(message.strip())
        log("✅ 就绪通知已发送")
    except Exception as e:
        warn(f"发送就绪通知失败: {e}")


async def main():
    """主函数"""
    trader = None

    try:
        # 加载配置
        log("=" * 60)
        log("🚀 CryptoSignal 自动交易系统启动中...")
        log("=" * 60)

        config = load_config_from_env()

        # 显示配置
        log(f"交易模式: {'真实交易' if config['enable_real_trading'] else '模拟模式'}")
        log(f"WebSocket优化: {'已启用' if config['use_optimized_scan'] else '未启用'}")
        log(f"扫描间隔: {config['scan_interval_seconds']}秒")
        log(f"最小信号分数: {config['min_signal_score']}")
        log(f"最大并发仓位: {config['trading_limits']['max_concurrent_positions']}")

        # 发送启动通知
        send_startup_notification(config)

        # 创建配置文件临时目录（如果不存在）
        config_dir = project_root / 'config'
        config_dir.mkdir(exist_ok=True)

        # 写入临时配置文件（AutoTrader需要）
        import json
        config_file = config_dir / 'binance_credentials.json'
        with open(config_file, 'w') as f:
            json.dump({
                'binance': config['binance'],
                'trading_limits': config['trading_limits']
            }, f, indent=2)

        # 创建AutoTrader
        trader = AutoTrader(
            config_path=str(config_file),
            use_optimized_scan=config['use_optimized_scan']
        )

        # 初始化（预热K线缓存，约2-3分钟）
        log("\n" + "=" * 60)
        log("⏳ 初始化系统（预热K线缓存，约2-3分钟）...")
        log("=" * 60)
        await trader.initialize()

        # 发送就绪通知
        send_ready_notification(config)

        log("\n" + "=" * 60)
        log("✅ 系统初始化完成！")
        log("=" * 60)

        # 开始定时扫描
        log(f"\n🔍 开始定时扫描（每{config['scan_interval_seconds']}秒）...")
        log(f"📊 最小信号分数: {config['min_signal_score']}")
        log("=" * 60)

        await trader.start_periodic_scan(
            interval_minutes=config['scan_interval_seconds'] // 60,
            min_score=config['min_signal_score']
        )

    except KeyboardInterrupt:
        log("\n⚠️  收到中断信号，正在停止...")
    except Exception as e:
        error(f"❌ 系统错误: {e}")
        import traceback
        error(traceback.format_exc())

        # 发送错误通知
        try:
            telegram_send(f"❌ 系统错误: {e}\n\n请检查日志并重启服务")
        except:
            pass

        raise
    finally:
        if trader:
            log("\n🛑 正在停止系统...")
            await trader.stop()
            log("✅ 系统已安全停止")

            # 发送停止通知
            try:
                telegram_send("🛑 系统已停止")
            except:
                pass


if __name__ == '__main__':
    # 设置优雅停止
    def signal_handler(sig, frame):
        log(f"\n⚠️  收到信号 {sig}，准备退出...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("👋 再见！")
    except Exception as e:
        error(f"Fatal error: {e}")
        sys.exit(1)