# cs_ext/demo/check_integration.py
from ats_core.env.bootstrap import bootstrap_env

bootstrap_env()


def main():
    print("=== Checking imports ===")

    # 检查 cryptofeed
    try:
        from cryptofeed import FeedHandler  # noqa: F401
        from cryptofeed.exchanges import BinanceFutures  # noqa: F401
        print("[OK] cryptofeed imported successfully.")
    except Exception as e:
        print(f"[FAIL] cryptofeed import failed: {e}")

    # 检查 freqtrade
    try:
        from freqtrade.strategy.interface import IStrategy  # noqa: F401
        print("[OK] freqtrade imported successfully.")
    except Exception as e:
        print(f"[FAIL] freqtrade import failed: {e}")

    # 检查 CryptoSignalStrategy
    try:
        from cs_ext.backtest.freqtrade_bridge import CryptoSignalStrategy  # noqa: F401
        print("[OK] CryptoSignalStrategy imported successfully.")
    except Exception as e:
        print(f"[FAIL] CryptoSignalStrategy import failed: {e}")


if __name__ == "__main__":
    main()
