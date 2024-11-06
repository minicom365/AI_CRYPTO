import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # 볼린저밴드
    bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bollinger_mavg'] = bollinger.bollinger_mavg()  # 중앙선
    df['bollinger_hband'] = bollinger.bollinger_hband()  # 상단 밴드
    df['bollinger_lband'] = bollinger.bollinger_lband()  # 하단 밴드

    # RSI (Relative Strength Index)
    rsi = RSIIndicator(close=df['close'], window=14)
    df['rsi'] = rsi.rsi()

    # MACD (Moving Average Convergence Divergence)
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()

    # SMA (Simple Moving Average)
    sma = SMAIndicator(close=df['close'], window=20)
    df['sma'] = sma.sma_indicator()

    # EMA (Exponential Moving Average)
    ema = EMAIndicator(close=df['close'], window=20)
    df['ema'] = ema.ema_indicator()

    # Stochastic Oscillator
    stochastic = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
    df['stoch_k'] = stochastic.stoch()
    df['stoch_d'] = stochastic.stoch_signal()

    # Average True Range (ATR)
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['atr'] = atr.average_true_range()

    # On-Balance Volume (OBV)
    obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
    df['obv'] = obv.on_balance_volume()

    # Fibonacci Retracements (수동 계산)
    high_price = df['high'].max()
    low_price = df['low'].min()
    df['fibonacci_0.236'] = high_price - 0.236 * (high_price - low_price)
    df['fibonacci_0.382'] = high_price - 0.382 * (high_price - low_price)
    df['fibonacci_0.5'] = high_price - 0.5 * (high_price - low_price)
    df['fibonacci_0.618'] = high_price - 0.618 * (high_price - low_price)
    df['fibonacci_0.786'] = high_price - 0.786 * (high_price - low_price)

    return df
