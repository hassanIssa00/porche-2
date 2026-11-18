import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run():
    if not mt5.initialize():
        print("MT5 failed")
        return
    rates = mt5.copy_rates_from_pos('BTCUSDm', mt5.TIMEFRAME_M1, 0, 5000)
    mt5.shutdown()

    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    
    # Technical Indicators
    # EMAs
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # Bollinger Bands (20, 2)
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['bb_upper'] = sma20 + 2.0 * std20
    df['bb_lower'] = sma20 - 2.0 * std20
    df['bb_mid'] = sma20

    # RSI (14)
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))

    # RSI (7) - fast for scalping
    ag7 = gain.ewm(alpha=1/7, adjust=False).mean()
    al7 = loss.ewm(alpha=1/7, adjust=False).mean()
    rs7 = ag7 / al7.replace(0, 1e-9)
    df['rsi7'] = 100 - (100 / (1 + rs7))

    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    df['macd_hist'] = macd - sig

    # Candlestick metrics
    df['body'] = (df['close'] - df['open']).abs()
    df['range'] = df['high'] - df['low']
    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
    df['is_hammer'] = (df['lower_wick'] >= 2 * df['body']) & (df['upper_wick'] <= 0.2 * df['range']) & (df['range'] > 15)
    df['is_star'] = (df['upper_wick'] >= 2 * df['body']) & (df['lower_wick'] <= 0.2 * df['range']) & (df['range'] > 15)

    def backtest(name, signal_func, sl_usd=0.50, tp_usd=0.85):
        sl_dist = sl_usd * 100 # $50 for $0.50
        tp_dist = tp_usd * 100 # $85 for $0.85
        
        trades = []
        in_pos = False
        pos_type = None
        entry_price = 0.0
        
        for i in range(200, len(df) - 1):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            if in_pos:
                if pos_type == 'BUY':
                    if row['low'] <= entry_price - sl_dist:
                        trades.append(('BUY', -sl_usd))
                        in_pos = False
                    elif row['high'] >= entry_price + tp_dist:
                        trades.append(('BUY', tp_usd))
                        in_pos = False
                elif pos_type == 'SELL':
                    if row['high'] >= entry_price + sl_dist:
                        trades.append(('SELL', -sl_usd))
                        in_pos = False
                    elif row['low'] <= entry_price - tp_dist:
                        trades.append(('SELL', tp_usd))
                        in_pos = False
                continue
                
            sig = signal_func(df, i)
            if sig == 'BUY':
                in_pos = True
                pos_type = 'BUY'
                entry_price = row['open']
            elif sig == 'SELL':
                in_pos = True
                pos_type = 'SELL'
                entry_price = row['open']
                
        pnl = [p for _, p in trades]
        wins = [p for p in pnl if p > 0]
        wr = len(wins) / len(pnl) * 100 if pnl else 0
        net = sum(pnl)
        max_loss_streak = 0
        cur_loss = 0
        for _, p in trades:
            if p < 0:
                cur_loss += 1
                max_loss_streak = max(max_loss_streak, cur_loss)
            else:
                cur_loss = 0
        print(f"{name:50s} | Trades: {len(trades):4d} | WR: {wr:4.1f}% | Net: ${net:+7.2f} | Max Loss: {max_loss_streak}")

    print("=" * 95)
    # 1. Bollinger Band Mean Reversion
    def strat_bb_reversion(data, i):
        p = data.iloc[i-1]
        if p['low'] <= p['bb_lower'] and p['close'] > p['open']:
            return 'BUY'
        if p['high'] >= p['bb_upper'] and p['close'] < p['open']:
            return 'SELL'
        return None
    backtest("1. BB Mean Reversion (Touch BB + Reversal candle)", strat_bb_reversion)

    # 2. Bollinger Band + RSI 7 Extreme (<20 / >80)
    def strat_bb_rsi(data, i):
        p = data.iloc[i-1]
        if p['low'] <= p['bb_lower'] and p['rsi7'] < 25 and p['close'] > p['open']:
            return 'BUY'
        if p['high'] >= p['bb_upper'] and p['rsi7'] > 75 and p['close'] < p['open']:
            return 'SELL'
        return None
    backtest("2. BB + Fast RSI(7) Extreme Reversion", strat_bb_rsi)

    # 3. Pinbar / Hammer Rejection at BB
    def strat_pinbar(data, i):
        p = data.iloc[i-1]
        if p['is_hammer'] and p['low'] <= p['bb_lower']:
            return 'BUY'
        if p['is_star'] and p['high'] >= p['bb_upper']:
            return 'SELL'
        return None
    backtest("3. Hammer / Star Rejection at BB Bands", strat_pinbar)

    # 4. EMA 9/21 Dynamic Pullback in 200 EMA Trend
    def strat_ema_trend_pullback(data, i):
        p = data.iloc[i-1]
        p2 = data.iloc[i-2]
        # Uptrend: Close > EMA200 and EMA9 > EMA21
        if p['close'] > p['ema200'] and p['ema9'] > p['ema21']:
            # Pullback to EMA21: low touched EMA21, but closed green above EMA9
            if p['low'] <= p['ema21'] and p['close'] > p['ema9'] and p['close'] > p['open']:
                return 'BUY'
        # Downtrend: Close < EMA200 and EMA9 < EMA21
        if p['close'] < p['ema200'] and p['ema9'] < p['ema21']:
            if p['high'] >= p['ema21'] and p['close'] < p['ema9'] and p['close'] < p['open']:
                return 'SELL'
        return None
    backtest("4. EMA 9/21 Pullback in 200 EMA Major Trend", strat_ema_trend_pullback)

    # 5. Fast Scalp RSI(7) Oversold Bounce with SL=0.50, TP=0.75
    def strat_fast_rsi(data, i):
        p = data.iloc[i-1]
        p2 = data.iloc[i-2]
        if p2['rsi7'] < 20 and p['rsi7'] > p2['rsi7'] and p['close'] > p['open']:
            return 'BUY'
        if p2['rsi7'] > 80 and p['rsi7'] < p2['rsi7'] and p['close'] < p['open']:
            return 'SELL'
        return None
    backtest("5. Fast RSI(7) Extreme (20/80) Turn", strat_fast_rsi, sl_usd=0.50, tp_usd=0.75)
    backtest("6. Fast RSI(7) Extreme (20/80) Turn (TP=0.85)", strat_fast_rsi, sl_usd=0.50, tp_usd=0.85)
    backtest("7. Fast RSI(7) Extreme (20/80) Turn (TP=0.90)", strat_fast_rsi, sl_usd=0.50, tp_usd=0.90)

    # 8. RSI(14) Extreme Reversal
    def strat_rsi14(data, i):
        p = data.iloc[i-1]
        p2 = data.iloc[i-2]
        if p2['rsi'] < 30 and p['rsi'] > p2['rsi'] and p['close'] > p['open']:
            return 'BUY'
        if p2['rsi'] > 70 and p['rsi'] < p2['rsi'] and p['close'] < p['open']:
            return 'SELL'
        return None
    backtest("8. RSI(14) Oversold <30 / Overbought >70 Turn", strat_rsi14, sl_usd=0.50, tp_usd=0.85)

    print("=" * 95)

if __name__ == '__main__':
    run()
