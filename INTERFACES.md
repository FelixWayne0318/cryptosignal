# CryptoSignal v7.2 模块接口规范

**用途**：在Claude Project中只导入核心文件，通过本文档了解所有辅助模块的API

生成时间：2025-11-14

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📚 接口规范说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 使用约定

1. **所有接口模块都无需导入完整代码**
2. **只需要知道函数签名、输入参数、返回值**
3. **核心流程会调用这些接口，实现细节在仓库中**
4. **如需修改接口实现，回到仓库修改对应文件**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 1️⃣ Sources 模块（数据源）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/sources/`

**职责**：从Binance API获取市场数据

### binance.py

```python
def get_klines(symbol: str, interval: str = '1h', limit: int = 500) -> List[Dict]:
    """
    获取K线数据

    参数:
        symbol: 交易对，如 'BTCUSDT'
        interval: 时间周期，如 '1h', '4h', '1d'
        limit: 数据条数，默认500

    返回:
        List[Dict]: K线数据列表
            [{
                'timestamp': int,       # 时间戳
                'open': float,          # 开盘价
                'high': float,          # 最高价
                'low': float,           # 最低价
                'close': float,         # 收盘价
                'volume': float,        # 成交量
                'quote_volume': float,  # 成交额
                'trades': int           # 成交笔数
            }, ...]
    """
    pass

def get_current_price(symbol: str) -> float:
    """
    获取当前价格

    返回: float 当前价格
    """
    pass

def get_24h_ticker(symbol: str) -> Dict:
    """
    获取24小时行情数据

    返回:
        {
            'price_change_percent': float,  # 24h涨跌幅
            'volume': float,                # 24h成交量
            'quote_volume': float,          # 24h成交额
            'high': float,                  # 24h最高价
            'low': float                    # 24h最低价
        }
    """
    pass
```

### klines.py

```python
def get_klines(symbol: str, interval: str, limit: int) -> List[Dict]:
    """
    获取K线数据（对binance.py的封装，增加缓存）

    接口同 binance.get_klines()
    """
    pass

def calculate_atr(klines: List[Dict], period: int = 14) -> float:
    """
    计算ATR（平均真实波幅）

    返回: float ATR值
    """
    pass
```

### oi.py

```python
def fetch_oi_history(symbol: str, limit: int = 100) -> List[float]:
    """
    获取持仓量(Open Interest)历史数据

    参数:
        symbol: 交易对
        limit: 数据条数

    返回:
        List[float]: 持仓量列表（单位：合约张数）
    """
    pass

def calculate_oi_change_rate(oi_history: List[float]) -> float:
    """
    计算持仓量变化率

    返回: float 变化率（-1.0 ~ 1.0）
    """
    pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 2️⃣ Features 模块（因子计算）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/features/`

**职责**：计算10个核心因子

### 统一接口规范

所有因子计算函数遵循统一模式：

```python
def calc_factor(klines: List[Dict], **kwargs) -> Union[float, Dict[str, float]]:
    """
    返回值范围:
        - 方向性因子: -1.0 ~ 1.0 (负数=空, 正数=多)
        - 强度性因子: 0.0 ~ 1.0 (越大越强)
    """
```

### trend.py - T因子（趋势）

```python
def analyze_trend(klines: List[Dict]) -> Dict[str, float]:
    """
    分析多周期趋势

    返回:
        {
            'trend_direction': float,     # 趋势方向 (-1.0 ~ 1.0)
            'trend_strength': float,      # 趋势强度 (0.0 ~ 1.0)
            'short_ema': float,           # 短期EMA
            'long_ema': float,            # 长期EMA
            'slope': float                # 趋势斜率
        }
    """
    pass

def get_trend_score(klines: List[Dict]) -> float:
    """
    获取综合趋势得分

    返回: float (-1.0 ~ 1.0)
    """
    pass
```

### momentum.py - M因子（动量）

```python
def calc_momentum(klines: List[Dict]) -> float:
    """
    计算动量得分（综合RSI、MACD等）

    返回: float (-1.0 ~ 1.0)
        正值=上涨动量, 负值=下跌动量
    """
    pass

def calculate_rsi(klines: List[Dict], period: int = 14) -> float:
    """
    计算RSI指标

    返回: float (0 ~ 100)
    """
    pass

def calculate_macd(klines: List[Dict]) -> Dict[str, float]:
    """
    计算MACD指标

    返回:
        {
            'macd': float,        # MACD值
            'signal': float,      # 信号线
            'histogram': float    # 柱状图
        }
    """
    pass
```

### confluence.py - C因子（多周期汇聚）

```python
def check_confluence(klines_1h: List[Dict],
                     klines_4h: List[Dict],
                     klines_1d: List[Dict]) -> float:
    """
    检查多周期趋势一致性

    参数:
        klines_1h: 1小时K线
        klines_4h: 4小时K线
        klines_1d: 日线K线

    返回: float (0.0 ~ 1.0)
        1.0 = 所有周期方向一致
        0.0 = 完全不一致
    """
    pass
```

### volume.py - V因子（成交量）

```python
def calc_volume_score(klines: List[Dict]) -> float:
    """
    计算成交量得分

    分析:
        - 成交量异常（与平均值对比）
        - 成交量趋势（上升/下降）
        - 价量配合

    返回: float (0.0 ~ 1.0)
        1.0 = 成交量极度活跃
        0.0 = 成交量极度萎缩
    """
    pass

def detect_volume_spike(klines: List[Dict], threshold: float = 2.0) -> bool:
    """
    检测成交量异常放大

    参数:
        threshold: 异常阈值（倍数）

    返回: bool
    """
    pass
```

### oi_analysis.py - O因子（持仓量）

```python
def calc_oi_score(oi_history: List[float], price_change: float) -> float:
    """
    计算持仓量得分

    参数:
        oi_history: 持仓量历史数据
        price_change: 价格变化率

    返回: float (-1.0 ~ 1.0)
        正值=多头增仓, 负值=空头增仓
    """
    pass

def analyze_oi_price_divergence(oi_history: List[float],
                                  klines: List[Dict]) -> Dict[str, Any]:
    """
    分析持仓量与价格的背离

    返回:
        {
            'divergence': bool,      # 是否背离
            'type': str,             # 'bullish' or 'bearish'
            'strength': float        # 背离强度 (0.0 ~ 1.0)
        }
    """
    pass
```

### liquidity.py - L因子（流动性）

```python
def calc_liquidity_score(volume: float,
                         trades: int,
                         spread: float = None) -> float:
    """
    计算流动性得分

    参数:
        volume: 24h成交量
        trades: 24h成交笔数
        spread: 买卖价差（可选）

    返回: float (0.0 ~ 1.0)
        1.0 = 极高流动性
        0.0 = 极低流动性
    """
    pass
```

### social.py - S因子（社交热度）

```python
def calc_social_score(symbol: str) -> float:
    """
    计算社交热度得分

    数据源:
        - Twitter提及量
        - Reddit讨论量
        - 搜索热度

    返回: float (0.0 ~ 1.0)
        1.0 = 极高热度
        0.0 = 无热度
    """
    pass
```

### innovation.py - I因子（创新性/新币溢价）

```python
def calc_innovation_score(symbol: str, listing_date: str = None) -> float:
    """
    计算创新性得分（新币溢价）

    参数:
        symbol: 交易对
        listing_date: 上线日期（可选，会自动查询）

    返回: float (0.0 ~ 1.0)
        1.0 = 刚上线的新币
        0.0 = 成熟币种

    新币定义:
        - 0-30天: ultra_new (I=1.0)
        - 30-180天: phaseA (I=0.7)
        - 180-365天: phaseB (I=0.4)
        - 365天+: mature (I=0.0)
    """
    pass

def get_coin_age_days(symbol: str) -> int:
    """
    获取币龄（天数）

    返回: int 上线天数
    """
    pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 3️⃣ Factors_v2 模块（v7.2新因子）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/factors_v2/`

**职责**：v7.2版本的精确因子定义

### funding_v2.py - F因子v2（资金费率）

```python
def calc_F_v2(funding_rate: float, oi_change: float) -> float:
    """
    计算资金费率因子v2（精确定义）

    v7.2改进:
        - 多空适配：正向合约和反向合约的资金费率含义相反
        - 归一化：使用tanh映射到 (-1.0, 1.0)

    参数:
        funding_rate: 当前资金费率
        oi_change: 持仓量变化率

    返回: float (-1.0 ~ 1.0)
        正值=空头付费(多头信号)
        负值=多头付费(空头信号)
    """
    pass

def get_funding_rate(symbol: str) -> float:
    """
    获取当前资金费率

    返回: float 资金费率（如 0.0001 表示 0.01%）
    """
    pass
```

### balance.py - B因子（多空平衡）

```python
def calc_balance(cvd: float, taker_buy_ratio: float) -> float:
    """
    计算多空平衡因子

    v7.2新增:
        - CVD(Cumulative Volume Delta): 累计成交量差
        - Taker Buy Ratio: 主动买入占比

    参数:
        cvd: CVD值
        taker_buy_ratio: 主动买入占比 (0.0 ~ 1.0)

    返回: float (-1.0 ~ 1.0)
        正值=多头占优
        负值=空头占优
    """
    pass

def calculate_cvd(klines: List[Dict]) -> float:
    """
    计算CVD(Cumulative Volume Delta)

    返回: float CVD值
    """
    pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 4️⃣ Scoring 模块（评分系统）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/scoring/`

**职责**：标准化、归一化、评分

### scoring_utils.py

```python
class StandardizationChain:
    """标准化处理链"""

    def standardize(self, value: float, method: str = 'robust') -> float:
        """
        标准化单个值

        参数:
            value: 原始值
            method: 标准化方法
                - 'robust': 鲁棒标准化（使用中位数和MAD）
                - 'zscore': Z-score标准化
                - 'minmax': 最小-最大归一化

        返回: float 标准化后的值
        """
        pass

    def fit(self, values: List[float]) -> 'StandardizationChain':
        """
        拟合数据（计算统计量）

        参数:
            values: 历史数据

        返回: self（支持链式调用）
        """
        pass

def directional_score(value: float, positive_is_bullish: bool = True) -> float:
    """
    方向性评分

    参数:
        value: 因子值 (-1.0 ~ 1.0)
        positive_is_bullish: True表示正值=看多

    返回: float (-1.0 ~ 1.0)
    """
    pass

def strength_score(value: float) -> float:
    """
    强度性评分

    参数:
        value: 因子值 (0.0 ~ 1.0)

    返回: float (0.0 ~ 1.0)
    """
    pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 5️⃣ Calibration 模块（统计校准）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/calibration/`

**职责**：基于历史数据校准信心度

### empirical_calibration.py

```python
class EmpiricalCalibrator:
    """经验校准器（Gate6使用）"""

    def record_signal_result(self, confidence: float, result: str, metadata: Dict):
        """
        记录信号结果

        参数:
            confidence: 原始信心度
            result: 'profit' or 'loss'
            metadata: 元数据（交易对、时间等）
        """
        pass

    def get_calibrated_probability(self, confidence: float) -> float:
        """
        获取校准后的概率

        参数:
            confidence: 原始信心度 (0.0 ~ 1.0)

        返回: float 校准后的概率 (0.0 ~ 1.0)
            基于历史数据，该信心度区间的实际胜率
        """
        pass

    def get_statistics(self) -> Dict:
        """
        获取统计信息

        返回:
            {
                'total_signals': int,           # 总信号数
                'win_rate': float,              # 总胜率
                'confidence_bins': List[Dict]   # 各信心度区间统计
            }
        """
        pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 6️⃣ Modulators 模块（调节器）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/modulators/`

**职责**：根据特殊情况调节信心度

### confidence_modulator.py

```python
def adjust_confidence(base_confidence: float,
                      adjustments: Dict[str, float]) -> float:
    """
    调节信心度

    参数:
        base_confidence: 基础信心度
        adjustments: 调节因子
            {
                'new_coin_penalty': float,    # 新币惩罚 (-0.1 ~ 0)
                'high_volatility': float,     # 高波动调节
                'low_liquidity': float        # 低流动性惩罚
            }

    返回: float 调节后的信心度 (0.0 ~ 1.0)
    """
    pass
```

### new_coin_modulator.py

```python
def adjust_for_new_coin(confidence: float, coin_age_days: int) -> float:
    """
    新币信心度调节

    参数:
        confidence: 原始信心度
        coin_age_days: 币龄（天）

    返回: float 调节后的信心度

    调节规则:
        - 0-30天: confidence * 0.8  (新币风险高)
        - 30-180天: confidence * 0.9
        - 180天+: confidence * 1.0  (无惩罚)
    """
    pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 7️⃣ Utils 模块（工具函数）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/utils/`

**职责**：数学工具、技术指标、辅助函数

### math_utils.py

```python
def ema(values: List[float], period: int) -> float:
    """
    计算指数移动平均(EMA)

    返回: float 最新的EMA值
    """
    pass

def sma(values: List[float], period: int) -> float:
    """
    计算简单移动平均(SMA)

    返回: float 最新的SMA值
    """
    pass

def linear_reduce(value: float, old_range: Tuple[float, float],
                   new_range: Tuple[float, float]) -> float:
    """
    线性映射

    参数:
        value: 原始值
        old_range: 原始范围 (min, max)
        new_range: 目标范围 (min, max)

    返回: float 映射后的值

    示例:
        linear_reduce(50, (0, 100), (0, 1)) = 0.5
    """
    pass

def get_effective_F(F: float, is_inverse: bool) -> float:
    """
    获取有效的F因子（处理正向/反向合约）

    参数:
        F: 原始F因子
        is_inverse: 是否为反向合约

    返回: float 有效的F因子
    """
    pass
```

### ta_core.py

```python
def rsi(prices: List[float], period: int = 14) -> float:
    """计算RSI指标"""
    pass

def macd(prices: List[float]) -> Tuple[float, float, float]:
    """计算MACD指标 (macd, signal, histogram)"""
    pass

def bollinger_bands(prices: List[float], period: int = 20) -> Tuple[float, float, float]:
    """计算布林带 (upper, middle, lower)"""
    pass

def atr(klines: List[Dict], period: int = 14) -> float:
    """计算ATR（平均真实波幅）"""
    pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 8️⃣ Analysis 模块（分析报告）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/analysis/`

**职责**：生成分析报告和统计

### report_writer.py

```python
class ReportWriter:
    """报告写入器"""

    def write_scan_report(self, summary: Dict, detail: List[Dict],
                           text_report: str):
        """
        写入扫描报告

        参数:
            summary: 摘要信息
            detail: 详细结果列表
            text_report: 文本格式报告
        """
        pass

    def write_signal_report(self, signal: Dict):
        """写入单个信号报告"""
        pass

def get_report_writer() -> ReportWriter:
    """获取全局报告写入器实例"""
    pass
```

### scan_statistics.py

```python
class ScanStatistics:
    """扫描统计器"""

    def add_symbol_result(self, symbol: str, result: Dict):
        """添加交易对结果"""
        pass

    def get_summary(self) -> Dict:
        """
        获取统计摘要

        返回:
            {
                'total_scanned': int,      # 总扫描数
                'signals_found': int,       # 发现信号数
                'gate_pass_rates': Dict,    # 各闸门通过率
                'avg_confidence': float     # 平均信心度
            }
        """
        pass

def get_global_stats() -> ScanStatistics:
    """获取全局统计实例"""
    pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 9️⃣ Execution 模块（交易执行）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**位置**：`ats_core/execution/`

**职责**：模拟交易和真实交易执行（未来扩展）

### paper_trader.py

```python
class PaperTrader:
    """模拟交易器"""

    def execute_signal(self, signal: Dict) -> Dict:
        """
        执行模拟交易

        参数:
            signal: 信号字典

        返回:
            {
                'entry_price': float,       # 入场价
                'position_size': float,     # 仓位大小
                'stop_loss': float,         # 止损价
                'take_profit': float        # 止盈价
            }
        """
        pass

    def close_position(self, symbol: str, exit_price: float) -> Dict:
        """
        平仓

        返回:
            {
                'pnl': float,               # 盈亏
                'pnl_percent': float,       # 盈亏百分比
                'holding_time': int         # 持有时间（秒）
            }
        """
        pass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 🔟 核心数据结构
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### K线数据结构

```python
Kline = {
    'timestamp': int,           # Unix时间戳（毫秒）
    'open': float,              # 开盘价
    'high': float,              # 最高价
    'low': float,               # 最低价
    'close': float,             # 收盘价
    'volume': float,            # 成交量（基础货币）
    'quote_volume': float,      # 成交额（报价货币）
    'trades': int,              # 成交笔数
    'taker_buy_volume': float,  # 主动买入量
    'taker_buy_quote': float    # 主动买入额
}
```

### 分析结果结构

```python
AnalysisResult = {
    # 基本信息
    'symbol': str,              # 交易对
    'timestamp': int,           # 分析时间戳
    'current_price': float,     # 当前价格

    # 10因子得分
    'factors': {
        'T': float,             # 趋势 (-1.0 ~ 1.0)
        'M': float,             # 动量 (-1.0 ~ 1.0)
        'C': float,             # 汇聚 (0.0 ~ 1.0)
        'V': float,             # 成交量 (0.0 ~ 1.0)
        'O': float,             # 持仓量 (-1.0 ~ 1.0)
        'B': float,             # 多空平衡 (-1.0 ~ 1.0)
        'F': float,             # 资金费率 (-1.0 ~ 1.0)
        'L': float,             # 流动性 (0.0 ~ 1.0)
        'S': float,             # 社交热度 (0.0 ~ 1.0)
        'I': float              # 创新性 (0.0 ~ 1.0)
    },

    # v7.2因子分组
    'factor_groups': {
        'TC': float,            # Trend + Confluence
        'VOM': float,           # Volume + OI + Momentum
        'B': float              # Balance
    },

    # 信号信息
    'signal_direction': str,    # 'LONG' or 'SHORT' or 'NONE'
    'confidence': float,        # 信心度 (0.0 ~ 1.0)
    'calibrated_prob': float,   # 校准后概率 (0.0 ~ 1.0)

    # 7道闸门
    'gates': {
        'gate1_trend': bool,
        'gate2_consistency': bool,
        'gate3_momentum': bool,
        'gate4_new_coin': bool,
        'gate5_factor_groups': bool,
        'gate6_calibration': bool,
        'gate7_confidence': bool
    },

    # 币种信息
    'coin_age_days': int,       # 币龄（天）
    'is_new_coin': bool,        # 是否新币

    # 建议
    'recommended_action': str,  # 'ENTER', 'WAIT', 'NONE'
    'entry_price': float,       # 建议入场价
    'stop_loss': float,         # 止损价
    'take_profit': float        # 止盈价
}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📖 使用示例
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 在Claude Project中引用接口

当你在核心文件中看到：

```python
from ats_core.features.trend import analyze_trend
from ats_core.features.momentum import calc_momentum
```

你只需要知道：

```python
# analyze_trend() 返回什么
trend_result = analyze_trend(klines)
# → {'trend_direction': 0.8, 'trend_strength': 0.7, ...}

# calc_momentum() 返回什么
momentum = calc_momentum(klines)
# → 0.65 (float, -1.0 ~ 1.0)
```

**无需关心内部如何计算RSI、MACD、EMA等细节**

### 修改因子实现

如果需要修改因子计算逻辑：

1. **回到仓库**，找到对应文件（如 `ats_core/features/momentum.py`）
2. **修改实现细节**（如调整RSI周期）
3. **测试**确保返回值类型和范围不变
4. **更新 INTERFACES.md**（如果接口签名改变）

### 添加新因子

如果要添加新因子（如K因子）：

1. **在仓库中**创建 `ats_core/features/new_factor.py`
2. **实现接口**：`def calc_K(klines) -> float`
3. **在核心文件中**调用：`K = calc_K(klines)`
4. **更新 INTERFACES.md**，记录新接口

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ✅ 总结
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 核心原则

1. **接口文件只需要知道"做什么"，不需要知道"怎么做"**
2. **所有接口遵循统一规范（输入、输出、范围）**
3. **核心文件关注流程和逻辑，接口文件提供计算能力**
4. **修改接口实现不影响核心流程**

### Claude Project 工作流

1. **导入12个核心文件**（9,778行代码）
2. **导入本文档** `INTERFACES.md` 作为接口规范
3. **理解系统架构**（参考 `SYSTEM_ARCHITECTURE.md`）
4. **修改核心逻辑**时直接修改核心文件
5. **修改因子实现**时回到仓库修改对应模块

### 优势

- ✅ **Token节省**：38.6%的代码量，100%的功能理解
- ✅ **聚焦核心**：专注于系统流程和业务逻辑
- ✅ **快速定位**：所有关键决策都在核心文件中
- ✅ **易于维护**：接口规范清晰，模块职责明确
