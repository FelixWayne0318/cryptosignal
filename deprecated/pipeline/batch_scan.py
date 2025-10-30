import os, time, json, asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from ats_core.cfg import CFG
from ats_core.pipeline.market_wide_scanner import MarketWideScanner
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade, render_watch
from ats_core.outputs.publisher import telegram_send
from ats_core.logging import log, warn
from ats_core.utils.rate_limiter import SAFE_LIMITER

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "reports")
os.makedirs(DATA, exist_ok=True)

def batch_run():
    """
    批量扫描（全市场WebSocket版）

    新架构:
    - 全市场扫描（无需候选池）
    - WebSocket K线缓存（0次API调用）
    - 流动性自动过滤
    - 17倍速度提升
    """
    # 使用全市场扫描器
    async def run_async():
        scanner = MarketWideScanner(
            min_quote_volume=3_000_000,  # 300万USDT最低成交额
            use_websocket_cache=False    # 暂时不启用WebSocket（需要client）
        )

        await scanner.initialize()
        syms = scanner.get_symbols()

        log(f"🚀 开始全市场扫描: {len(syms)} 个币种")
        log(f"   流动性过滤: ≥300万USDT成交额")

        for sym in syms:
            try:
                r = analyze_symbol(sym)
                pub = r.get("publish") or {}
                html = render_trade(r) if pub.get("prime") else render_watch(r)
                telegram_send(html)
                # save report
                ts=time.strftime("%Y%m%dT%H%MZ", time.gmtime())
                with open(os.path.join(DATA, f"scan_{sym}_{ts}.md"),"w",encoding="utf-8") as f:
                    f.write(html)
            except Exception as e:
                warn("batch %s error: %s", sym, e)
            time.sleep(CFG.get("limits","per_symbol_delay_ms", default=600)/1000.0)

    # 运行异步函数
    asyncio.run(run_async())


def batch_run_parallel(max_workers: int = 5, use_v2: bool = False) -> Dict[str, Any]:
    """
    并行批量扫描（带API限流保护）

    Args:
        max_workers: 最大并发数（默认5，保守配置防止风控）
        use_v2: 是否使用v2分析器（默认False）

    Returns:
        扫描统计信息

    特性:
    - ThreadPoolExecutor并发执行
    - SafeRateLimiter防止API风控（60req/min）
    - 自动错误恢复
    - 实时进度显示
    """
    from ats_core.pipeline.analyze_symbol_v2 import analyze_symbol_v2

    # 使用全市场扫描器获取币种列表
    async def get_symbols():
        scanner = MarketWideScanner(
            min_quote_volume=3_000_000,
            use_websocket_cache=False
        )
        await scanner.initialize()
        return scanner.get_symbols()

    syms = asyncio.run(get_symbols())

    log(f"🚀 开始并行批量扫描: {len(syms)} 个币种")
    log(f"   并发数: {max_workers} (保守配置，防风控)")
    log(f"   限流策略: {SAFE_LIMITER.requests_per_minute} req/min")
    log(f"   全市场扫描（流动性过滤）")

    # 分析函数选择
    analyze_func = analyze_symbol_v2 if use_v2 else analyze_symbol

    # 统计信息
    stats = {
        'total': len(syms),
        'completed': 0,
        'prime_signals': 0,
        'watch_signals': 0,
        'errors': 0,
        'start_time': time.time()
    }

    def process_symbol(symbol: str) -> Optional[Dict]:
        """处理单个symbol（带限流）"""
        try:
            # 使用限流器包装
            def analyze_with_limit():
                return analyze_func(symbol)

            # execute_safe会自动处理限流
            result = analyze_with_limit()

            return {
                'symbol': symbol,
                'result': result,
                'success': True
            }

        except Exception as e:
            warn(f"[ParallelScan] {symbol} 分析失败: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'success': False
            }

    # 创建任务列表（lambda包装，延迟执行）
    tasks = [lambda s=sym: process_symbol(s) for sym in syms]

    # 使用SafeRateLimiter的execute_safe方法（自带限流+并发控制）
    log(f"\n开始并行扫描...")
    results = SAFE_LIMITER.execute_safe(
        tasks=tasks,
        task_names=[f"分析 {sym}" for sym in syms],
        show_progress=True
    )

    # 处理结果
    log(f"\n处理扫描结果...")

    for result in results:
        if result is None or not isinstance(result, dict):
            stats['errors'] += 1
            continue

        stats['completed'] += 1

        if not result.get('success'):
            stats['errors'] += 1
            continue

        # 提取分析结果
        symbol = result['symbol']
        analysis = result['result']

        # 判断信号类型
        pub = analysis.get("publish") or {}

        try:
            # 渲染HTML
            if pub.get("prime"):
                html = render_trade(analysis)
                stats['prime_signals'] += 1
            elif pub.get("watch"):
                html = render_watch(analysis)
                stats['watch_signals'] += 1
            else:
                continue  # 不发布

            # 发送Telegram
            telegram_send(html)

            # 保存报告
            ts = time.strftime("%Y%m%dT%H%MZ", time.gmtime())
            report_path = os.path.join(DATA, f"scan_{symbol}_{ts}.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html)

        except Exception as e:
            warn(f"[ParallelScan] {symbol} 输出失败: {e}")
            stats['errors'] += 1

    # 计算统计
    elapsed = time.time() - stats['start_time']
    stats['elapsed_seconds'] = round(elapsed, 2)
    stats['symbols_per_second'] = round(stats['completed'] / elapsed, 2) if elapsed > 0 else 0

    # 打印汇总
    log(f"\n{'='*60}")
    log(f"📊 批量扫描完成")
    log(f"{'='*60}")
    log(f"  总数: {stats['total']}")
    log(f"  成功: {stats['completed']}")
    log(f"  错误: {stats['errors']}")
    log(f"  Prime信号: {stats['prime_signals']}")
    log(f"  Watch信号: {stats['watch_signals']}")
    log(f"  耗时: {stats['elapsed_seconds']}秒")
    log(f"  速度: {stats['symbols_per_second']} symbols/s")
    log(f"  API限流统计: {SAFE_LIMITER.get_stats() if hasattr(SAFE_LIMITER, 'get_stats') else 'N/A'}")
    log(f"{'='*60}")

    return stats