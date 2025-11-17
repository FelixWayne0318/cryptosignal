# coding: utf-8
"""
币种列表动态刷新模块（v7.4.0方案B）

设计原则：
- 零硬编码：所有参数从config读取
- 双缓冲：不影响当前扫描
- 保守容错：失败时保持旧列表
- 完整追溯：记录所有变化历史
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from ats_core.logging import log, warn, error

TZ_UTC = timezone.utc


async def refresh_symbols_list(scanner, client, kline_cache, symbols_active: List[str], refresh_config: dict) -> Tuple[bool, List[str]]:
    """
    动态刷新币种列表（独立函数版本）

    Args:
        scanner: OptimizedBatchScanner实例
        client: Binance客户端
        kline_cache: K线缓存
        symbols_active: 当前活跃币种列表
        refresh_config: 刷新配置字典

    Returns:
        Tuple[bool, List[str]]: (是否成功, 新币种列表)
    """
    log("\n" + "=" * 60)
    log("🔄 开始刷新币种列表（v7.4.0方案B）")
    log("=" * 60)

    refresh_start = time.time()

    try:
        # Step 1: 获取最新交易对列表
        log("\n1️⃣  获取最新币安USDT合约列表...")
        exchange_info = await client.get_exchange_info()

        all_symbols = [
            s["symbol"] for s in exchange_info.get("symbols", [])
            if s["symbol"].endswith("USDT")
            and s["status"] == "TRADING"
            and s["contractType"] == "PERPETUAL"
        ]
        log(f"   总计: {len(all_symbols)} 个USDT永续合约")

        # 获取24h行情数据
        ticker_24h = await client.get_ticker_24h()

        ticker_map = {}
        for ticker in ticker_24h:
            symbol = ticker.get('symbol', '')
            if symbol in all_symbols:
                ticker_map[symbol] = {
                    'volume': float(ticker.get('quoteVolume', 0)),
                    'change_pct': float(ticker.get('priceChangePercent', 0))
                }

        # 流动性过滤
        MIN_VOLUME = 3_000_000
        filtered_symbols = [
            s for s in all_symbols
            if ticker_map.get(s, {}).get('volume', 0) >= MIN_VOLUME
        ]
        log(f"   流动性过滤后: {len(filtered_symbols)} 个币种（24h成交额>3M USDT）")

        # 按流动性排序
        new_symbols = sorted(
            filtered_symbols,
            key=lambda s: ticker_map.get(s, {}).get('volume', 0),
            reverse=True
        )

        # Step 2: 比对变化
        log("\n2️⃣  比对币种列表变化...")
        old_set = set(symbols_active)
        new_set = set(new_symbols)

        added_symbols = list(new_set - old_set)
        removed_symbols = list(old_set - new_set)

        log(f"   新增币种: {len(added_symbols)} 个")
        if added_symbols:
            log(f"      {', '.join(added_symbols[:10])}{'...' if len(added_symbols) > 10 else ''}")

        log(f"   移除币种: {len(removed_symbols)} 个")
        if removed_symbols:
            log(f"      {', '.join(removed_symbols[:10])}{'...' if len(removed_symbols) > 10 else ''}")

        if not added_symbols and not removed_symbols:
            log("   ✅ 币种列表无变化")
            return True, symbols_active

        # Step 3: 新币种K线数据初始化和验证
        log("\n3️⃣  初始化新币种K线数据...")
        new_coin_cfg = refresh_config.get('new_coin_detection', {})
        min_kline_reqs = new_coin_cfg.get('min_kline_requirements', {})

        min_15m = min_kline_reqs.get('15m_min_bars', 20)
        min_1h = min_kline_reqs.get('1h_min_bars', 24)
        min_4h = min_kline_reqs.get('4h_min_bars', 7)
        min_1d = min_kline_reqs.get('1d_min_bars', 3)

        validated_new_symbols = []

        if added_symbols:
            try:
                await kline_cache.initialize_batch(
                    symbols=added_symbols,
                    intervals=['15m', '1h', '4h', '1d'],
                    client=client
                )

                for symbol in added_symbols:
                    k15m = kline_cache.get_klines(symbol, '15m', 100)
                    k1h = kline_cache.get_klines(symbol, '1h', 100)
                    k4h = kline_cache.get_klines(symbol, '4h', 50)
                    k1d = kline_cache.get_klines(symbol, '1d', 10)

                    bars_15m = len(k15m) if k15m else 0
                    bars_1h = len(k1h) if k1h else 0
                    bars_4h = len(k4h) if k4h else 0
                    bars_1d = len(k1d) if k1d else 0

                    if (bars_15m >= min_15m and bars_1h >= min_1h and
                        bars_4h >= min_4h and bars_1d >= min_1d):
                        validated_new_symbols.append(symbol)
                        log(f"   ✅ {symbol}: K线数据充足 (15m={bars_15m}, 1h={bars_1h}, 4h={bars_4h}, 1d={bars_1d})")
                    else:
                        log(f"   ⚠️  {symbol}: K线数据不足")

                log(f"   验证完成: {len(validated_new_symbols)}/{len(added_symbols)} 个新币种数据充足")

            except Exception as e:
                error(f"   ❌ 新币种K线初始化失败: {e}")
                validated_new_symbols = []

        # Step 4: 构建新列表
        log("\n4️⃣  构建新币种列表...")
        symbols_pending = [s for s in symbols_active if s not in removed_symbols]
        symbols_pending.extend(validated_new_symbols)

        # 按流动性重新排序
        symbols_pending = sorted(
            symbols_pending,
            key=lambda s: ticker_map.get(s, {}).get('volume', 0),
            reverse=True
        )

        log(f"   旧列表: {len(symbols_active)} 个币种")
        log(f"   新列表: {len(symbols_pending)} 个币种")

        # Step 5: 记录变化历史
        log("\n5️⃣  记录币种变化历史...")
        _log_symbol_changes(
            timestamp=time.time(),
            total_symbols=len(symbols_pending),
            added=validated_new_symbols,
            removed=removed_symbols,
            ticker_map=ticker_map,
            refresh_config=refresh_config
        )

        refresh_elapsed = time.time() - refresh_start
        log("\n" + "=" * 60)
        log("✅ 币种列表刷新完成！")
        log("=" * 60)
        log(f"   耗时: {refresh_elapsed:.1f}秒")
        log(f"   新增: {len(validated_new_symbols)} 个币种")
        log(f"   移除: {len(removed_symbols)} 个币种")
        log(f"   当前: {len(symbols_pending)} 个币种")
        log("=" * 60)

        return True, symbols_pending

    except Exception as e:
        error(f"❌ 币种列表刷新失败: {e}")
        return False, symbols_active


def _log_symbol_changes(timestamp: float, total_symbols: int,
                       added: list, removed: list, ticker_map: dict,
                       refresh_config: dict):
    """记录币种变化历史到jsonl文件"""
    persistence_cfg = refresh_config.get('persistence', {})
    if not persistence_cfg.get('enabled', True):
        return

    try:
        import json
        from pathlib import Path

        log_file = persistence_cfg.get('log_file', 'data/symbol_list_history.jsonl')
        log_path = Path(__file__).parent.parent.parent / log_file

        # 确保目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建记录
        record = {
            'timestamp': timestamp,
            'datetime_utc': datetime.fromtimestamp(timestamp, tz=TZ_UTC).isoformat(),
            'total_symbols': total_symbols,
            'added_symbols': added,
            'removed_symbols': removed,
            'added_count': len(added),
            'removed_count': len(removed)
        }

        # 追加到jsonl文件
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        log(f"   ✅ 变化历史已记录: {log_path}")

    except Exception as e:
        warn(f"   ⚠️  记录变化历史失败: {e}")
