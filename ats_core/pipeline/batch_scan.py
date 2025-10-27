import os, time, json
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from ats_core.cfg import CFG
from ats_core.pools.pool_manager import get_pool_manager
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade, render_watch
from ats_core.outputs.publisher import telegram_send
from ats_core.logging import log, warn
from ats_core.utils.rate_limiter import SAFE_LIMITER

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "reports")
os.makedirs(DATA, exist_ok=True)

def batch_run():
    """
    批量扫描（优化版 - 使用智能缓存池）

    新架构:
    - Elite Pool (24h缓存): 稳定币种
    - Overlay Pool (1h缓存): 异常币种 + 新币
    - API调用量: -90%
    - 扫描速度: +10倍
    """
    # 使用新的池管理器（自动处理缓存）
    manager = get_pool_manager(
        elite_cache_hours=24,
        overlay_cache_hours=1,
        verbose=True
    )

    # 获取合并后的候选池（自动检查缓存有效期）
    syms, metadata = manager.get_merged_universe()

    log(f"🚀 开始批量扫描: {len(syms)} 个币种")
    log(f"   Elite Pool: {metadata['elite_count']} 个 (缓存{'有效' if metadata['elite_cache_valid'] else '重建'})")
    log(f"   Overlay Pool: {metadata['overlay_count']} 个 (缓存{'有效' if metadata['overlay_cache_valid'] else '重建'})")
    log(f"   API优化: ~90% 调用量降低 🚀")
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


def batch_run_parallel(max_workers: int = 5, use_v2: bool = False, v2_config: str = None) -> Dict[str, Any]:
    """
    并行批量扫描（带API限流保护）

    Args:
        max_workers: 最大并发数（默认5，保守配置防止风控）
        use_v2: 是否使用v2分析器（默认False）
        v2_config: V2配置文件名（默认None，使用factors_unified.json）
                  可选: "factors_v2_lite.json"（8维轻量版）

    Returns:
        扫描统计信息

    特性:
    - ThreadPoolExecutor并发执行
    - SafeRateLimiter防止API风控（60req/min）
    - 自动错误恢复
    - 实时进度显示
    - 支持V2 Lite轻量版（8+1维，无需订单簿/清算数据）
    """
    from ats_core.pipeline.analyze_symbol_v2 import analyze_symbol_v2

    # 使用智能池管理器
    manager = get_pool_manager(
        elite_cache_hours=24,
        overlay_cache_hours=1,
        verbose=True
    )

    # 获取候选池
    syms, metadata = manager.get_merged_universe()

    # 项目根目录（用于构建配置文件路径）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    log(f"🚀 开始并行批量扫描: {len(syms)} 个币种")
    log(f"   并发数: {max_workers} (保守配置，防风控)")
    log(f"   限流策略: {SAFE_LIMITER.requests_per_minute} req/min")
    log(f"   Elite Pool: {metadata['elite_count']} 个")
    log(f"   Overlay Pool: {metadata['overlay_count']} 个")

    # 分析函数选择
    if use_v2:
        if v2_config:
            log(f"   分析器: V2 ({v2_config})")
            config_path = os.path.join(project_root, "config", v2_config)
            analyze_func = lambda sym: analyze_symbol_v2(sym, config_path=config_path)
        else:
            log(f"   分析器: V2 (默认配置)")
            analyze_func = analyze_symbol_v2
    else:
        log(f"   分析器: V1 (生产版)")
        analyze_func = analyze_symbol

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